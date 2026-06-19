"""Roda os 5 modelos na BASE NOVA (fora de domínio) — Fase 5.

NER  (inglês): CoNLL-2003 (eng.testb), 100 sentenças. Modelos: crf + 3 LLMs.
UPOS (português): UD_Portuguese-GSD (pt_gsd-ud-test.conllu), 100 sentenças. Modelos: regras + 3 LLMs.

Emite o contrato comum `.jsonl` em resultados/base_nova/<modelo>/<tarefa>.jsonl, com o
campo `modelo` no nome literal. Reusa as funções já testadas dos runners das Fases 2-3:
- CRF:    carregar_ou_treinar + predizer_sequencial (features re-extraídas, prev-iob real)
- regras: construir_lexico + tag_por_regras (léxico do TRAIN do Bosque — mesmo do baseline)
- LLMs:   predizer_tags_chunked (chunk=10) + montar_prompt

Escrita incremental + resume (append; pula sentenças já feitas). CLI:
  python rodar_base_nova.py --modelo crf            # só o CRF (NER)
  python rodar_base_nova.py --modelo regras         # só regras (UPOS)
  python rodar_base_nova.py --modelo llama3.1:8b    # LLM nas DUAS tarefas
  python rodar_base_nova.py --todos                 # tudo (lento por causa do 8B)
"""
from __future__ import annotations

import argparse
import json
import os
import time
from dataclasses import asdict
from typing import Optional

from src.io.contrato import Registro, ler_jsonl, caminho_resultado
from src.io.corpora import carregar_conllu
from src.io.corpora_nova import carregar_conll2003
from src.io.features_ner import predizer_sequencial
from src.llm.prompts import montar_prompt
from src.llm.cliente_ollama import gerar
from src.llm.parser import alinhar_tags

import run_crf
import run_regras
from run_llm import predizer_tags_chunked, CHUNK_PADRAO

BASE = "base_nova"
LIMITE = 100
CONLL2003 = "datasets/base_nova/eng.testb"
GSD = "datasets/base_nova/pt_gsd-ud-test.conllu"
BOSQUE_TRAIN = "datasets/base_mapeada/pt_bosque-ud-train.conllu"
LLMS = ["llama3.1:8b", "qwen2.5:3b", "llama3.2:3b"]


def _saida(modelo: str, tarefa: str) -> str:
    return caminho_resultado(BASE, modelo, tarefa)


def _feitas(caminho: str) -> set[str]:
    if not os.path.exists(caminho):
        return set()
    return {r.sentenca_id for r in ler_jsonl(caminho)}


def _append(caminho: str, regs: list[Registro]) -> None:
    d = os.path.dirname(caminho)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(caminho, "a", encoding="utf-8") as f:
        for r in regs:
            f.write(json.dumps(asdict(r), ensure_ascii=False) + "\n")
        f.flush()


def _emitir(caminho, tarefa, modelo, sentenca_id, tokens, tags):
    assert len(tags) == len(tokens), f"desalinho em {sentenca_id}: {len(tags)} vs {len(tokens)}"
    regs = [Registro(tarefa=tarefa, modelo=modelo, sentenca_id=sentenca_id, posicao=i,
                     token=tok, tag_predita=tags[i]) for i, tok in enumerate(tokens)]
    _append(caminho, regs)


# --------------------------------------------------------------------------- CRF (NER)
def rodar_crf():
    import joblib
    caminho = _saida("crf", "ner")
    feitas = _feitas(caminho)
    if not os.path.exists(run_crf.MODELO_PADRAO):
        raise SystemExit(f"Modelo CRF nao encontrado em {run_crf.MODELO_PADRAO}. "
                         "Rode a Fase 2 (run_crf.py) primeiro para treinar/persistir o modelo.")
    crf = joblib.load(run_crf.MODELO_PADRAO)  # reusa o CRF treinado na base mapeada
    sents = carregar_conll2003(caminho=CONLL2003, limite=LIMITE)
    t0 = time.time()
    n = 0
    for s in sents:
        if s.sentenca_id in feitas:
            continue
        tokens = [tok for tok, _ in s.pares]
        tags = predizer_sequencial(crf, tokens, s.pos)
        _emitir(caminho, "ner", "crf", s.sentenca_id, tokens, tags)
        n += 1
    print(f"[base_nova] crf ner: {n} sentencas novas, {time.time()-t0:.1f}s")


# --------------------------------------------------------------------------- regras (UPOS)
def rodar_regras():
    caminho = _saida("regras", "upos")
    feitas = _feitas(caminho)
    lexico = run_regras.construir_lexico(BOSQUE_TRAIN)  # mesmo léxico do baseline (sem vazamento)
    sents = carregar_conllu(caminho=GSD, limite=LIMITE)
    t0 = time.time()
    n = 0
    for s in sents:
        if s.sentenca_id in feitas:
            continue
        tokens = [tok for tok, _ in s.pares]
        tags = [run_regras.tag_por_regras(tok, lexico) for tok in tokens]
        _emitir(caminho, "upos", "regras", s.sentenca_id, tokens, tags)
        n += 1
    print(f"[base_nova] regras upos: {n} sentencas novas, {time.time()-t0:.1f}s")


# --------------------------------------------------------------------------- LLM (NER e UPOS)
def rodar_llm(modelo: str):
    # NER (CoNLL-2003)
    for tarefa, sents in [
        ("ner", carregar_conll2003(caminho=CONLL2003, limite=LIMITE)),
        ("upos", carregar_conllu(caminho=GSD, limite=LIMITE)),
    ]:
        caminho = _saida(modelo, tarefa)
        feitas = _feitas(caminho)
        t0 = time.time()
        n = 0
        for s in sents:
            if s.sentenca_id in feitas:
                continue
            tokens = [tok for tok, _ in s.pares]
            tags, _, _, _ = predizer_tags_chunked(modelo, tarefa, tokens, gerar, None, CHUNK_PADRAO)
            _emitir(caminho, tarefa, modelo, s.sentenca_id, tokens, tags)
            n += 1
        print(f"[base_nova] {modelo} {tarefa}: {n} sentencas novas, {time.time()-t0:.1f}s")


def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Roda os 5 modelos na base nova (Fase 5).")
    p.add_argument("--modelo", help="crf | regras | <nome do LLM> (roda NER+UPOS do LLM).")
    p.add_argument("--todos", action="store_true", help="Roda crf + regras + os 3 LLMs.")
    args = p.parse_args(argv)

    if args.todos:
        rodar_crf()
        rodar_regras()
        for m in LLMS:
            rodar_llm(m)
    elif args.modelo == "crf":
        rodar_crf()
    elif args.modelo == "regras":
        rodar_regras()
    elif args.modelo:
        rodar_llm(args.modelo)
    else:
        p.error("informe --modelo <nome> ou --todos")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
