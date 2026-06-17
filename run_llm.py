"""Runner CLI dos 3 LLMs via Ollama — 1 sentença por chamada, emissão incremental, resume e métricas.

Executa os modelos LLM (llama3.1:8b, qwen2.5:3b, llama3.2:3b) via Ollama sobre os corpora
de NER (GMB) e UPOS (Bosque), emitindo o contrato `.jsonl` token-a-token alinhado com o gold.

Características principais:
- 1 sentença por chamada ao Ollama (sem batching) — garante alinhamento 1:1 com o gold (D-03).
- Escrita incremental em modo append (modo 'a' direto — NÃO usa o escritor 'w' do contrato) (D-06).
- Resume automático: ao retomar sem --reiniciar, pula sentenças cujo sentenca_id já está no .jsonl.
- Persiste métricas por (modelo, tarefa) em <tarefa>.meta.json (tok/s, sent/s, total de fallbacks) (D-08).
- fn_gerar injetável: os testes passam uma função fake para mockar o Ollama sem rede.

REQ-04. Fase 3, plano 03-02.
"""
from __future__ import annotations

import argparse
import json
import os
import time
from dataclasses import asdict
from typing import Callable, Optional

from src.io.contrato import Registro, ler_jsonl, caminho_resultado
from src.io.corpora import carregar_gmb, carregar_conllu
from src.llm.prompts import montar_prompt
from src.llm.cliente_ollama import gerar, Resposta
from src.llm.parser import alinhar_tags

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

LIMITE_PADRAO = 1167

LOADERS: dict[str, Callable] = {
    "ner": carregar_gmb,
    "upos": carregar_conllu,
}


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------


def _sentencas_feitas(caminho: str) -> set[str]:
    """Retorna o conjunto de sentenca_id já presentes no .jsonl (para resume).

    Se o arquivo não existir, retorna set() (nada feito ainda).

    Args:
        caminho: caminho do arquivo .jsonl de saída.

    Returns:
        Conjunto de sentenca_id já gravados.
    """
    if not os.path.exists(caminho):
        return set()
    return {r.sentenca_id for r in ler_jsonl(caminho)}


def _append_registros(caminho: str, registros: list[Registro]) -> None:
    """Acrescenta registros ao .jsonl em modo append (uma linha JSON por registro).

    Cria o diretório pai automaticamente. Abre em modo 'a' (append, não sobrescreve).
    Faz flush após cada sentença para garantir durabilidade parcial em caso de crash.

    Args:
        caminho:   caminho do arquivo .jsonl de saída.
        registros: lista de Registro a gravar (todos os tokens de uma sentença).
    """
    dir_pai = os.path.dirname(caminho)
    if dir_pai:
        os.makedirs(dir_pai, exist_ok=True)
    with open(caminho, "a", encoding="utf-8") as f:
        for r in registros:
            f.write(json.dumps(asdict(r), ensure_ascii=False) + "\n")
        f.flush()


# ---------------------------------------------------------------------------
# Função principal de execução (injetável para testes)
# ---------------------------------------------------------------------------


def rodar(
    modelo: str,
    tarefa: str,
    limite: int = LIMITE_PADRAO,
    caminho_saida: Optional[str] = None,
    reiniciar: bool = False,
    fn_gerar: Callable = gerar,
    num_predict: Optional[int] = None,
) -> dict:
    """Roda o modelo LLM sobre as sentenças da tarefa e emite o .jsonl incremental.

    Para cada sentença:
    1. Monta o prompt com montar_prompt (tokens já tokenizados — sem re-tokenização).
    2. Chama fn_gerar (default: gerar do cliente_ollama, mockável nos testes).
    3. Alinha as tags com alinhar_tags (garante len(tags)==len(tokens)).
    4. Emite um Registro por token em modo append.
    5. Acumula métricas de tokens gerados, tempo, fallbacks e sentências processadas.

    O campo `modelo` no Registro preserva o nome literal (ex "llama3.1:8b" com ':').
    A sanitização ':' -> '_' acontece apenas no caminho via caminho_resultado (D-02).

    Args:
        modelo:        nome do modelo Ollama (ex "llama3.1:8b").
        tarefa:        "ner" ou "upos".
        limite:        nº máximo de sentenças a processar (default 1167).
        caminho_saida: caminho do .jsonl de saída (default via caminho_resultado).
        reiniciar:     se True, remove o .jsonl existente e recomeça do zero.
        fn_gerar:      função de geração (injetável para mock nos testes).
        num_predict:   teto de tokens gerados pelo Ollama (opcional).

    Returns:
        Dict com métricas: modelo, tarefa, sentencas, tokens, fallbacks,
        eval_duration_s, tok_por_seg, sent_por_seg, wall_clock_s.
    """
    if caminho_saida is None:
        caminho_saida = caminho_resultado("base_mapeada", modelo, tarefa)

    # --reiniciar: apaga o .jsonl existente para começar do zero.
    if reiniciar and os.path.exists(caminho_saida):
        os.remove(caminho_saida)

    # Resume: coleta sentenca_id já presentes (vazio se acabou de reiniciar).
    feitas = _sentencas_feitas(caminho_saida)

    # Carrega sentenças do corpus correto.
    sentencas = LOADERS[tarefa](limite=limite)

    # Acumuladores de métricas.
    tokens_total = 0
    eval_ns_total = 0
    sentencas_proc = 0
    fallbacks_total = 0
    t0 = time.time()

    for s in sentencas:
        # Resume: pular sentença já processada.
        if s.sentenca_id in feitas:
            continue

        tokens_s = [tok for tok, _ in s.pares]
        prompt = montar_prompt(tarefa, tokens_s)
        resp = fn_gerar(modelo, prompt, num_predict)
        tags, n_fb = alinhar_tags(tarefa, tokens_s, resp.texto)

        # Asserção defensiva: o parser garante; se falhar é bug.
        assert len(tags) == len(s.pares), (
            f"Bug no parser: len(tags)={len(tags)} != len(pares)={len(s.pares)} "
            f"para sentença {s.sentenca_id!r}"
        )

        regs = [
            Registro(
                tarefa=tarefa,
                modelo=modelo,
                sentenca_id=s.sentenca_id,
                posicao=pos,
                token=tok,
                tag_predita=tags[pos],
            )
            for pos, (tok, _) in enumerate(s.pares)
        ]
        _append_registros(caminho_saida, regs)

        # Acumular métricas da sentença.
        tokens_total += resp.eval_count
        eval_ns_total += resp.eval_duration_ns
        sentencas_proc += 1
        fallbacks_total += n_fb

    wall = time.time() - t0
    eval_s = eval_ns_total / 1e9

    meta = {
        "modelo": modelo,
        "tarefa": tarefa,
        "sentencas": sentencas_proc,
        "tokens": tokens_total,
        "fallbacks": fallbacks_total,
        "eval_duration_s": eval_s,
        "tok_por_seg": (tokens_total / eval_s if eval_s > 0 else 0.0),
        "sent_por_seg": (sentencas_proc / wall if wall > 0 else 0.0),
        "wall_clock_s": wall,
    }

    # Persistir meta.json ao lado do .jsonl.
    caminho_meta = caminho_saida.replace(".jsonl", ".meta.json")
    dir_meta = os.path.dirname(caminho_meta)
    if dir_meta:
        os.makedirs(dir_meta, exist_ok=True)
    with open(caminho_meta, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    return meta


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: Optional[list[str]] = None) -> int:
    """Ponto de entrada CLI do runner LLM.

    Exemplos de uso:
        python run_llm.py --modelo llama3.1:8b --tarefa ner
        python run_llm.py --modelo qwen2.5:3b --tarefa upos --limite 100
        python run_llm.py --modelo llama3.2:3b --tarefa ner --reiniciar
    """
    parser = argparse.ArgumentParser(
        description=(
            "Runner LLM via Ollama — 1 sentença/chamada, emissão .jsonl incremental com resume.\n"
            "\n"
            "Modelos disponíveis (Fase 3):\n"
            "  llama3.1:8b  — maior/mais forte; roda 42%% GPU / 58%% CPU (~7,6 tok/s)\n"
            "  qwen2.5:3b   — 100%% GPU (~59 tok/s, ~7,7× mais rápido que o 8B)\n"
            "  llama3.2:3b  — 80%% GPU / 20%% CPU (~45 tok/s)\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--modelo",
        required=True,
        help="Nome do modelo Ollama. Ex: llama3.1:8b, qwen2.5:3b, llama3.2:3b",
    )
    parser.add_argument(
        "--tarefa",
        required=True,
        choices=["ner", "upos"],
        help="Tarefa: ner (GMB, inglês) ou upos (Bosque, português).",
    )
    parser.add_argument(
        "--limite",
        type=int,
        default=LIMITE_PADRAO,
        help=f"Nº máximo de sentenças a processar (default {LIMITE_PADRAO}).",
    )
    parser.add_argument(
        "--reiniciar",
        action="store_true",
        help="Apaga o .jsonl existente e começa do zero (sem resume).",
    )
    parser.add_argument(
        "--num-predict",
        type=int,
        default=None,
        dest="num_predict",
        help="Teto de tokens gerados pelo Ollama por chamada (opcional).",
    )
    parser.add_argument(
        "--saida",
        default=None,
        help="Caminho do .jsonl de saída (default: contrato via caminho_resultado).",
    )
    args = parser.parse_args(argv)

    caminho_saida = args.saida or caminho_resultado("base_mapeada", args.modelo, args.tarefa)

    meta = rodar(
        modelo=args.modelo,
        tarefa=args.tarefa,
        limite=args.limite,
        caminho_saida=caminho_saida,
        reiniciar=args.reiniciar,
        fn_gerar=gerar,
        num_predict=args.num_predict,
    )

    print(
        f"[run_llm] {args.modelo} {args.tarefa}: "
        f"{meta['sentencas']} sentenças, "
        f"{meta['tok_por_seg']:.1f} tok/s, "
        f"{meta['fallbacks']} fallbacks"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
