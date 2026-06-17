"""Agregador de métricas e relatório comparativo (REQ-05, REQ-06 — Fase 4).

Consome os ``.jsonl`` de predição emitidos por cada modelo (contrato comum,
``src/io/contrato.py``), alinha cada predição ao gold por
``(sentenca_id, posicao)`` (gold via ``src/io/corpora.py``), calcula métricas
reusando ``src/metricas.py`` (plano 04-01) e emite os três artefatos da fase:

1. JSON de métricas por ``(modelo, tarefa)`` em
   ``resultados/<base>/<modelo_sanitizado>/<tarefa>.metricas.json`` (D-02).
2. Tabela comparativa por tarefa (NER e UPOS) em Markdown E CSV, em
   ``resultados/<base>/`` (D-03).
3. CSV único de discrepâncias token-a-token em
   ``resultados/<base>/discrepancias.csv`` (D-04).

Princípios:
- NÃO roda modelos nem chama Ollama; só lê ``.jsonl``/``.meta.json`` e o gold.
- Degradação graciosa (D-06): monta as tabelas só com os modelos cujo ``.jsonl``
  existe e reporta quais dos 5 esperados faltam — nunca quebra por ausência.
- Asserção de integridade (D-05): se o nº de registros de um ``.jsonl`` não casar
  com o total de tokens do gold, levanta ``RuntimeError`` claro (no CLI o erro é
  por-modelo e não derruba os demais).
"""
from __future__ import annotations

import argparse
import csv
import json
import os
from typing import Optional

from src.io.contrato import caminho_resultado, ler_jsonl
from src.io.corpora import Sentenca, carregar_conllu, carregar_gmb
from src.metricas import metricas_entidade, metricas_token

# 5 modelos esperados, na ordem em que aparecem nas tabelas (D-03).
MODELOS_ESPERADOS = ["crf", "regras", "llama3.1:8b", "qwen2.5:3b", "llama3.2:3b"]
# Loader do gold por tarefa (D-05).
LOADERS_GOLD = {"ner": carregar_gmb, "upos": carregar_conllu}
TAREFAS = ("ner", "upos")
LIMITE_PADRAO = 1167

# Marcador usado quando uma predição não cobre uma posição do gold (coerente
# com o ``alinhar`` legado de src/metricas.py, que usa "X-AUSENTE").
TAG_AUSENTE = "X-AUSENTE"


# --- Task 1: núcleo (gold, alinhamento, métricas, JSON) --------------------


def carregar_gold(tarefa: str, limite: int = LIMITE_PADRAO) -> list[Sentenca]:
    """Carrega o gold da tarefa via o loader correto (D-05)."""
    loader = LOADERS_GOLD.get(tarefa)
    if loader is None:
        raise ValueError(f"tarefa desconhecida: {tarefa!r} (use {tuple(LOADERS_GOLD)})")
    return loader(limite=limite)


def indexar_gold(gold: list[Sentenca]) -> tuple[dict, list]:
    """Indexa o gold para alinhamento e montagem de sequências por sentença.

    Returns:
        ``(indice, ordem_sentencas)`` onde:
        - ``indice`` = ``{(sentenca_id, posicao): tag_gold}``;
        - ``ordem_sentencas`` = ``[(sentenca_id, [tag_gold, ...]), ...]`` na
          ordem do gold (para montar as sequências por sentença para o seqeval).
    """
    indice: dict[tuple[str, int], str] = {}
    ordem: list[tuple[str, list[str]]] = []
    for s in gold:
        tags = []
        for pos, (_tok, tag_gold) in enumerate(s.pares):
            indice[(s.sentenca_id, pos)] = tag_gold
            tags.append(tag_gold)
        ordem.append((s.sentenca_id, tags))
    return indice, ordem


def alinhar_predicao(gold: list[Sentenca], registros) -> tuple[list, list, list]:
    """Alinha as predições ao gold por ``(sentenca_id, posicao)``.

    Args:
        gold: lista de ``Sentenca`` (token, tag_gold) na ordem do gold.
        registros: lista de ``Registro`` lidos de um ``.jsonl``.

    Returns:
        ``(gold_seqs, pred_seqs, discrepancias)`` agrupados POR SENTENÇA na
        ordem do gold. ``discrepancias`` é uma lista de tuplas
        ``(sentenca_id, posicao, token, tag_gold, tag_predita)`` onde
        ``tag_gold != tag_predita``.

    Raises:
        RuntimeError: se ``len(registros)`` não casar com o total de tokens do
            gold (asserção de integridade D-05).
    """
    total = sum(len(s.pares) for s in gold)
    if len(registros) != total:
        raise RuntimeError(
            f"Desalinhamento: {len(registros)} registros vs {total} tokens do gold"
        )

    pred_por_chave = {(r.sentenca_id, r.posicao): r.tag_predita for r in registros}

    gold_seqs: list[list[str]] = []
    pred_seqs: list[list[str]] = []
    discrepancias: list[tuple] = []

    for s in gold:
        g_seq: list[str] = []
        p_seq: list[str] = []
        for pos, (token, tag_gold) in enumerate(s.pares):
            tag_predita = pred_por_chave.get((s.sentenca_id, pos), TAG_AUSENTE)
            g_seq.append(tag_gold)
            p_seq.append(tag_predita)
            if tag_gold != tag_predita:
                discrepancias.append(
                    (s.sentenca_id, pos, token, tag_gold, tag_predita)
                )
        gold_seqs.append(g_seq)
        pred_seqs.append(p_seq)

    return gold_seqs, pred_seqs, discrepancias


def calcular_metricas(tarefa: str, gold_seqs: list, pred_seqs: list) -> dict:
    """Calcula métricas token (e entidade só para NER) reusando src/metricas.py.

    Returns:
        ``{"por_classe": [...], "micro": {...}, "entidade": <dict|None>,
           "n_tokens": int}``.
    """
    linhas, (micro_p, micro_r, micro_f) = metricas_token(gold_seqs, pred_seqs)
    por_classe = [
        {"classe": c, "precisao": p, "cobertura": r, "f1": f, "suporte": sup}
        for (c, p, r, f, sup) in linhas
    ]
    micro = {"precisao": micro_p, "cobertura": micro_r, "f1": micro_f}
    entidade = metricas_entidade(gold_seqs, pred_seqs) if tarefa == "ner" else None
    n_tokens = sum(len(s) for s in gold_seqs)
    return {
        "por_classe": por_classe,
        "micro": micro,
        "entidade": entidade,
        "n_tokens": n_tokens,
    }


def ler_meta(caminho_jsonl: str) -> tuple:
    """Lê ``<...>.meta.json`` (Fase 3) ao lado do .jsonl, se existir.

    Returns:
        ``(eval_duration_s, tok_por_seg)`` ou ``(None, None)`` se ausente.
    """
    caminho_meta = caminho_jsonl.replace(".jsonl", ".meta.json")
    if not os.path.exists(caminho_meta):
        return None, None
    with open(caminho_meta, encoding="utf-8") as f:
        meta = json.load(f)
    return meta.get("eval_duration_s"), meta.get("tok_por_seg")


def _json_seguro(obj):
    """Converte tipos numpy (do seqeval) em tipos nativos serializáveis.

    seqeval retorna ``numpy.float64``/``numpy.int32`` em precisao/cobertura/f1 e
    suporte; ``json.dump`` não os serializa. Coage recursivamente para float/int
    nativos (e demais escalares via ``.item()``) antes de gravar (Rule 1 — bug).
    """
    if isinstance(obj, dict):
        return {k: _json_seguro(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_seguro(v) for v in obj]
    if hasattr(obj, "item") and not isinstance(obj, (str, bytes)):
        return obj.item()  # numpy escalar -> Python nativo
    return obj


def escrever_metricas_json(
    base: str, modelo: str, tarefa: str, metricas: dict, tempo, velocidade
) -> str:
    """Escreve o JSON de métricas D-02 ao lado do .jsonl. Retorna o caminho."""
    caminho = caminho_resultado(base, modelo, tarefa).replace(
        ".jsonl", ".metricas.json"
    )
    payload = {
        "modelo": modelo,
        "tarefa": tarefa,
        "por_classe": metricas["por_classe"],
        "micro": metricas["micro"],
        "entidade": metricas["entidade"],
        "n_tokens": metricas["n_tokens"],
        "tempo": tempo,
        "velocidade": velocidade,
    }
    dir_pai = os.path.dirname(caminho)
    if dir_pai:
        os.makedirs(dir_pai, exist_ok=True)
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(_json_seguro(payload), f, ensure_ascii=False, indent=2)
    return caminho


# --- Task 2: descoberta, tabelas, discrepâncias, orquestração, CLI ---------

# Colunas das tabelas por tarefa (D-03). UPOS não tem f1_entidade.
COLUNAS_NER = ["modelo", "precisao", "cobertura", "micro_f1", "f1_entidade", "tempo_s", "tok_s"]
COLUNAS_UPOS = ["modelo", "precisao", "cobertura", "micro_f1", "tempo_s", "tok_s"]
# Modelos sem .meta.json (não-LLM): tempo/velocidade = "—" na tabela (D-03).
MODELOS_SEM_META = {"crf", "regras"}
HEADER_DISCREPANCIAS = [
    "tarefa", "modelo", "sentenca_id", "posicao", "token", "tag_gold", "tag_predita"
]


def descobrir_presentes(
    base: str, modelos=MODELOS_ESPERADOS, tarefas=TAREFAS
) -> tuple[list, list]:
    """Varre (modelo, tarefa) e separa presentes de ausentes (D-06).

    Returns:
        ``(presentes, ausentes)`` — listas de tuplas ``(modelo, tarefa)``.
        ``presentes`` = aqueles cujo ``caminho_resultado`` existe no disco;
        ``ausentes`` = os demais (dos ``len(modelos) * len(tarefas)`` esperados).
        Nunca levanta por ausência (degradação graciosa).
    """
    presentes: list[tuple[str, str]] = []
    ausentes: list[tuple[str, str]] = []
    for modelo in modelos:
        for tarefa in tarefas:
            if os.path.exists(caminho_resultado(base, modelo, tarefa)):
                presentes.append((modelo, tarefa))
            else:
                ausentes.append((modelo, tarefa))
    return presentes, ausentes


def formatar_num(x) -> str:
    """3 casas decimais; None/ausente -> '—'."""
    if x is None:
        return "—"
    return f"{x:.3f}"


def montar_tabela(tarefa: str, linhas_por_modelo: list[dict]) -> tuple[str, list]:
    """Monta a tabela da tarefa em Markdown e em linhas CSV (D-03).

    Args:
        tarefa: "ner" ou "upos".
        linhas_por_modelo: lista de dicts com chaves ``modelo``, ``precisao``,
            ``cobertura``, ``micro_f1``, ``f1_entidade`` (só NER), ``tempo_s``,
            ``tok_s``. Valores numéricos ou None.

    Returns:
        ``(markdown, linhas_csv)`` — ``linhas_csv`` inclui a linha de cabeçalho.
    """
    colunas = COLUNAS_NER if tarefa == "ner" else COLUNAS_UPOS

    linhas_csv: list[list[str]] = [list(colunas)]
    for linha in linhas_por_modelo:
        celulas = [str(linha.get("modelo", ""))]
        for col in colunas[1:]:
            celulas.append(formatar_num(linha.get(col)))
        linhas_csv.append(celulas)

    # Markdown
    md = ["| " + " | ".join(colunas) + " |"]
    md.append("| " + " | ".join("---" for _ in colunas) + " |")
    for celulas in linhas_csv[1:]:
        md.append("| " + " | ".join(celulas) + " |")
    markdown = "\n".join(md) + "\n"

    return markdown, linhas_csv


def escrever_tabelas(
    base: str, tarefa: str, markdown: str, linhas_csv: list
) -> tuple[str, str]:
    """Grava ``tabela_<tarefa>.md`` e ``tabela_<tarefa>.csv`` em resultados/<base>/."""
    dir_base = os.path.join("resultados", base)
    os.makedirs(dir_base, exist_ok=True)
    caminho_md = os.path.join(dir_base, f"tabela_{tarefa}.md")
    caminho_csv = os.path.join(dir_base, f"tabela_{tarefa}.csv")
    with open(caminho_md, "w", encoding="utf-8") as f:
        f.write(markdown)
    with open(caminho_csv, "w", encoding="utf-8", newline="") as f:
        escritor = csv.writer(f)
        escritor.writerows(linhas_csv)
    return caminho_md, caminho_csv


def escrever_discrepancias(base: str, registros_discrepancia: list) -> str:
    """Grava o CSV único de discrepâncias em resultados/<base>/ (D-04).

    Args:
        registros_discrepancia: lista de tuplas/listas na ordem do header
            ``tarefa,modelo,sentenca_id,posicao,token,tag_gold,tag_predita``.

    Returns:
        Caminho do ``discrepancias.csv``.
    """
    dir_base = os.path.join("resultados", base)
    os.makedirs(dir_base, exist_ok=True)
    caminho = os.path.join(dir_base, "discrepancias.csv")
    with open(caminho, "w", encoding="utf-8", newline="") as f:
        escritor = csv.writer(f)
        escritor.writerow(HEADER_DISCREPANCIAS)
        escritor.writerows(registros_discrepancia)
    return caminho


def agregar(base: str, limite: int = LIMITE_PADRAO) -> dict:
    """Orquestra a agregação completa para uma base.

    Para cada ``(modelo, tarefa)`` presente: carrega o gold (cache por tarefa),
    lê o ``.jsonl``, alinha, calcula métricas, escreve o JSON D-02, acumula a
    linha da tabela e as discrepâncias. Erros de desalinhamento de UM modelo são
    capturados e reportados — não derrubam os demais (D-05/D-06). Ao final,
    escreve as tabelas NER e UPOS e o CSV único de discrepâncias.

    Returns:
        ``{"presentes": [...], "ausentes": [...], "erros": [...],
           "arquivos": [...]}``.
    """
    presentes, ausentes = descobrir_presentes(base)
    erros: list[str] = []
    arquivos: list[str] = []

    cache_gold: dict[str, list[Sentenca]] = {}
    linhas_por_tarefa: dict[str, list[dict]] = {t: [] for t in TAREFAS}
    discrepancias_todas: list[list] = []

    for modelo, tarefa in presentes:
        try:
            if tarefa not in cache_gold:
                cache_gold[tarefa] = carregar_gold(tarefa, limite=limite)
            gold = cache_gold[tarefa]

            caminho_jsonl = caminho_resultado(base, modelo, tarefa)
            registros = ler_jsonl(caminho_jsonl)
            gold_seqs, pred_seqs, discrepancias = alinhar_predicao(gold, registros)

            metricas = calcular_metricas(tarefa, gold_seqs, pred_seqs)
            tempo, velocidade = ler_meta(caminho_jsonl)
            caminho_json = escrever_metricas_json(
                base, modelo, tarefa, metricas, tempo, velocidade
            )
            arquivos.append(caminho_json)

            ent = metricas["entidade"]
            linhas_por_tarefa[tarefa].append(
                {
                    "modelo": modelo,
                    "precisao": metricas["micro"]["precisao"],
                    "cobertura": metricas["micro"]["cobertura"],
                    "micro_f1": metricas["micro"]["f1"],
                    "f1_entidade": ent["f1"] if ent else None,
                    "tempo_s": None if modelo in MODELOS_SEM_META else tempo,
                    "tok_s": None if modelo in MODELOS_SEM_META else velocidade,
                }
            )

            for (sid, pos, token, tag_gold, tag_predita) in discrepancias:
                discrepancias_todas.append(
                    [tarefa, modelo, sid, pos, token, tag_gold, tag_predita]
                )
        except Exception as e:  # noqa: BLE001 — erro por-modelo não derruba os demais
            erros.append(f"{modelo}/{tarefa}: {e}")

    # Tabelas por tarefa (sempre escreve, mesmo só com cabeçalho).
    for tarefa in TAREFAS:
        markdown, linhas_csv = montar_tabela(tarefa, linhas_por_tarefa[tarefa])
        caminho_md, caminho_csv = escrever_tabelas(base, tarefa, markdown, linhas_csv)
        arquivos.extend([caminho_md, caminho_csv])

    arquivos.append(escrever_discrepancias(base, discrepancias_todas))

    return {
        "presentes": presentes,
        "ausentes": ausentes,
        "erros": erros,
        "arquivos": arquivos,
    }


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Agrega .jsonl de predição em métricas, tabelas e CSV de discrepâncias."
    )
    parser.add_argument("--base", default="base_mapeada", help="base_mapeada ou base_nova.")
    parser.add_argument(
        "--limite", type=int, default=LIMITE_PADRAO, help="Nº de sentenças do gold."
    )
    args = parser.parse_args(argv)

    resumo = agregar(args.base, limite=args.limite)

    print(f"[agregar] base={args.base} — {len(resumo['presentes'])} presente(s).")
    for modelo, tarefa in resumo["ausentes"]:
        print(f"[agregar] ausente: {modelo}/{tarefa}")
    for erro in resumo["erros"]:
        print(f"[agregar] ERRO {erro}")
    for arquivo in resumo["arquivos"]:
        print(f"[agregar] gerado: {arquivo}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
