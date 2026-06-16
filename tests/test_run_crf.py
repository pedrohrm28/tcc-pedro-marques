"""Testes de run_crf.py.

Cobre as funções puras de carregamento/mapeamento ner.csv<->GMB
(Task 1) e o alinhamento token-a-token do .jsonl emitido (Task 3).
"""
from __future__ import annotations

import run_crf
from src.io.corpora import carregar_gmb


# ---------------------------------------------------------------------------
# Task 1 — carregar_features_ner / features_e_labels_para_sids
# ---------------------------------------------------------------------------


def test_carregar_features_ner_descarta_linha_malformada():
    """A linha cujo sentence_idx == 'prev-lemma' (header vazado) é filtrada."""
    mapa = run_crf.carregar_features_ner()
    assert "prev-lemma" not in mapa
    # Todo sid restante deve ser numérico.
    for sid in mapa:
        float(sid)  # não levanta ValueError


def test_sentenca_1_bate_com_gmb():
    """Após dedupe, a sentença '1' do ner.csv == carregar_gmb()[0] (palavra E tag)."""
    mapa = run_crf.carregar_features_ner()
    gold = carregar_gmb(limite=1)[0]
    sid = str(int(float(gold.sentenca_id)))  # "1.0" -> "1"
    tokens_ner = [(t["__word__"], t["__tag__"]) for t in mapa[sid]]
    assert tokens_ner == gold.pares


def test_dedupe_metade_duplicada():
    """Uma sequência exatamente duplicada vira metade; uma não-duplicada fica inteira."""
    dup = [("a", "O"), ("b", "O"), ("a", "O"), ("b", "O")]
    naodup = [("a", "O"), ("b", "O"), ("c", "O")]
    assert run_crf._deduplicar(dup) == dup[:2]
    assert run_crf._deduplicar(naodup) == naodup


def test_features_e_labels_preserva_ordem_e_comprimento():
    mapa = run_crf.carregar_features_ner()
    sids = ["1", "2", "3"]
    X, y, tokens = run_crf.features_e_labels_para_sids(mapa, sids)
    assert len(X) == len(sids) == len(y) == len(tokens)
    for i in range(len(sids)):
        assert len(X[i]) == len(y[i]) == len(tokens[i])
    # As features não devem conter as chaves internas nem sentence_idx/tag.
    primeira = X[0][0]
    assert "__tag__" not in primeira
    assert "__word__" not in primeira
    assert "sentence_idx" not in primeira
    assert "tag" not in primeira
