"""Testes de agregar.py (Fase 4 — REQ-05/REQ-06).

Todos os testes usam gold SINTÉTICO (objetos Sentenca montados à mão) e .jsonl
mínimos em tmp_path. NÃO carregam os corpora reais nem rodam Ollama.
"""
from __future__ import annotations

import json

import pytest

import agregar
from src.io.contrato import Registro, escrever_jsonl
from src.io.corpora import Sentenca


# ---------------------------------------------------------------------------
# Helpers sintéticos
# ---------------------------------------------------------------------------


def _gold_ner():
    """Gold NER mínimo: 2 sentenças, 3 tokens no total."""
    return [
        Sentenca("1", [("a", "O"), ("b", "B-geo")]),
        Sentenca("2", [("c", "O")]),
    ]


def _registros_ner(modelo="crf", tags=("O", "B-geo", "O")):
    """Registros .jsonl casando com _gold_ner (3 tokens)."""
    chaves = [("1", 0, "a"), ("1", 1, "b"), ("2", 0, "c")]
    return [
        Registro(
            tarefa="ner",
            modelo=modelo,
            sentenca_id=sid,
            posicao=pos,
            token=tok,
            tag_predita=tag,
        )
        for (sid, pos, tok), tag in zip(chaves, tags)
    ]


# ---------------------------------------------------------------------------
# Task 1 — alinhamento, métricas, JSON, meta
# ---------------------------------------------------------------------------


def test_alinhar_predicao_casa_por_chave():
    """gold_seqs/pred_seqs agrupados por sentença; discrepância só onde diverge."""
    gold = _gold_ner()
    registros = _registros_ner(tags=("O", "I-geo", "O"))  # diverge em (1,1)
    gold_seqs, pred_seqs, discrepancias = agregar.alinhar_predicao(gold, registros)

    assert gold_seqs == [["O", "B-geo"], ["O"]]
    assert pred_seqs == [["O", "I-geo"], ["O"]]
    assert [len(g) for g in gold_seqs] == [len(p) for p in pred_seqs]
    # Uma discrepância: sentença "1", posição 1, token "b", gold B-geo, pred I-geo.
    assert discrepancias == [("1", 1, "b", "B-geo", "I-geo")]


def test_alinhar_predicao_sem_discrepancia():
    gold = _gold_ner()
    registros = _registros_ner(tags=("O", "B-geo", "O"))
    _, _, discrepancias = agregar.alinhar_predicao(gold, registros)
    assert discrepancias == []


def test_alinhar_predicao_aborta_em_desalinhamento():
    """Menos registros que tokens do gold -> RuntimeError claro (D-05)."""
    gold = _gold_ner()  # 3 tokens
    registros = _registros_ner(tags=("O", "B-geo", "O"))[:2]  # só 2
    with pytest.raises(RuntimeError):
        agregar.alinhar_predicao(gold, registros)


def test_indexar_gold():
    gold = _gold_ner()
    indice, ordem = agregar.indexar_gold(gold)
    assert indice[("1", 0)] == "O"
    assert indice[("1", 1)] == "B-geo"
    assert indice[("2", 0)] == "O"
    assert ordem == [("1", ["O", "B-geo"]), ("2", ["O"])]


def test_calcular_metricas_ner_inclui_entidade():
    gold = _gold_ner()
    registros = _registros_ner(tags=("O", "B-geo", "O"))
    gold_seqs, pred_seqs, _ = agregar.alinhar_predicao(gold, registros)
    m = agregar.calcular_metricas("ner", gold_seqs, pred_seqs)
    assert m["entidade"] is not None
    assert "precisao" in m["entidade"] and "f1" in m["entidade"]
    assert m["n_tokens"] == 3
    assert "precisao" in m["micro"]
    assert isinstance(m["por_classe"], list) and m["por_classe"]


def test_calcular_metricas_upos_sem_entidade():
    gold = [Sentenca("1", [("o", "DET"), ("gato", "NOUN")])]
    registros = [
        Registro("upos", "regras", "1", 0, "o", "DET"),
        Registro("upos", "regras", "1", 1, "gato", "NOUN"),
    ]
    gold_seqs, pred_seqs, _ = agregar.alinhar_predicao(gold, registros)
    m = agregar.calcular_metricas("upos", gold_seqs, pred_seqs)
    assert m["entidade"] is None
    assert m["n_tokens"] == 2


def test_escrever_metricas_json(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    gold = _gold_ner()
    registros = _registros_ner(tags=("O", "B-geo", "O"))
    gold_seqs, pred_seqs, _ = agregar.alinhar_predicao(gold, registros)
    m = agregar.calcular_metricas("ner", gold_seqs, pred_seqs)

    caminho = agregar.escrever_metricas_json(
        "base_mapeada", "crf", "ner", m, tempo=None, velocidade=None
    )
    assert caminho.endswith("ner.metricas.json")

    with open(caminho, encoding="utf-8") as f:
        dados = json.load(f)
    for chave in (
        "modelo",
        "tarefa",
        "por_classe",
        "micro",
        "entidade",
        "n_tokens",
        "tempo",
        "velocidade",
    ):
        assert chave in dados
    assert dados["modelo"] == "crf"
    assert dados["tarefa"] == "ner"
    assert dados["tempo"] is None and dados["velocidade"] is None


def test_ler_meta_ausente(tmp_path):
    caminho_jsonl = str(tmp_path / "ner.jsonl")
    assert agregar.ler_meta(caminho_jsonl) == (None, None)


def test_ler_meta_presente(tmp_path):
    caminho_jsonl = tmp_path / "ner.jsonl"
    caminho_meta = tmp_path / "ner.meta.json"
    caminho_meta.write_text(
        json.dumps({"eval_duration_s": 12.5, "tok_por_seg": 100.0}),
        encoding="utf-8",
    )
    tempo, velocidade = agregar.ler_meta(str(caminho_jsonl))
    assert tempo == 12.5
    assert velocidade == 100.0
