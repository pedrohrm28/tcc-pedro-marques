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


if __name__ == "__main__":
    raise SystemExit(main())  # noqa: F821 — main definido no plano 04-02 Task 2
