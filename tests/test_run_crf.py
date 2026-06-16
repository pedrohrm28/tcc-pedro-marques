"""Testes de run_crf.py.

Cobre as funções puras de carregamento/mapeamento ner.csv<->GMB
(Task 1) e o alinhamento token-a-token do .jsonl emitido (Task 3).
"""
from __future__ import annotations

import run_crf
from src.io.contrato import ler_jsonl
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


# ---------------------------------------------------------------------------
# Task 3 — alinhamento do .jsonl emitido
# ---------------------------------------------------------------------------


class _CrfFake:
    """CRF mínimo: prediz "O" para todo token (barato, sem treino).

    O objetivo do teste é o ALINHAMENTO do .jsonl, não a acurácia.
    """

    rotulos = {"O"}

    def predict_single(self, feats):
        return ["O"] * len(feats)


def test_jsonl_alinha_com_gold(tmp_path):
    """O .jsonl emitido bate token-a-token (sentenca_id, posicao, token) com o gold."""
    limite = 5
    mapa = run_crf.carregar_features_ner()
    gold = carregar_gmb(limite=limite)
    crf = _CrfFake()

    registros = run_crf.gerar_registros(crf, mapa, gold)
    saida = tmp_path / "ner.jsonl"
    run_crf.escrever_jsonl(str(saida), registros)

    lidos = ler_jsonl(str(saida))

    # Nº de registros == soma de len(s.pares).
    total_tokens = sum(len(s.pares) for s in gold)
    assert len(lidos) == total_tokens

    # (sentenca_id, posicao, token) batem 1:1 com o gold, em ordem.
    esperado = [
        (s.sentenca_id, pos, tok)
        for s in gold
        for pos, (tok, _tag) in enumerate(s.pares)
    ]
    obtido = [(r.sentenca_id, r.posicao, r.token) for r in lidos]
    assert obtido == esperado

    # Toda tag_predita é um rótulo IOB plausível (aqui só "O" pelo CRF fake).
    rotulos_validos = {"O"} | _CrfFake.rotulos
    for r in lidos:
        assert r.tarefa == "ner" and r.modelo == "crf"
        assert r.tag_predita in rotulos_validos


def test_gerar_registros_aborta_em_desalinhamento(tmp_path):
    """Se os tokens do ner.csv não baterem com o gold, gerar_registros aborta."""
    import pytest
    from src.io.corpora import Sentenca

    mapa = run_crf.carregar_features_ner()
    # Sentença gold falsa com tokens que não existem no ner.csv para o sid "1".
    falsa = Sentenca(sentenca_id="1.0", pares=[("ZZZ", "O"), ("YYY", "O")])
    with pytest.raises(RuntimeError):
        run_crf.gerar_registros(_CrfFake(), mapa, [falsa])
