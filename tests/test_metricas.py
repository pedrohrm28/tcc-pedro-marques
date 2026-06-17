"""Testes de src/metricas.py.

Métricas puras (token + entidade) extraídas/refatoradas do comparativo_gold.py
legado (TCC I). Os valores de P/R/F1 são conferidos à mão em sequências
sintéticas pequenas; comparação via pytest.approx.
"""
from __future__ import annotations

import pytest

from src.metricas import metricas_entidade, metricas_token

# metricas_entidade depende de seqeval; pular os testes de entidade se ausente.
pytest.importorskip("seqeval")


# ---------------------------------------------------------------------------
# Task 1 — metricas_token (nível token, por classe + micro)
# ---------------------------------------------------------------------------


def _linha(linhas, classe):
    """Retorna a tupla (classe, p, r, f, suporte) da `classe` em `linhas`."""
    for tup in linhas:
        if tup[0] == classe:
            return tup
    raise AssertionError(f"classe {classe!r} ausente em {linhas}")


def test_token_classificacao_perfeita():
    """gold == pred => micro P/R/F == 1.0 e cada classe p=r=f=1.0."""
    gold = [["O", "B-geo", "I-geo"]]
    pred = [["O", "B-geo", "I-geo"]]
    linhas, (mp, mr, mf) = metricas_token(gold, pred)
    assert mp == pytest.approx(1.0)
    assert mr == pytest.approx(1.0)
    assert mf == pytest.approx(1.0)
    for classe in ("O", "B-geo", "I-geo"):
        _c, p, r, f, sup = _linha(linhas, classe)
        assert p == pytest.approx(1.0)
        assert r == pytest.approx(1.0)
        assert f == pytest.approx(1.0)
        assert sup == 1


def test_token_um_erro():
    """gold=[O,O,B-geo] pred=[O,O,O]: B-geo cobertura 0; O precisao 2/3; micro 2/3."""
    gold = [["O", "O", "B-geo"]]
    pred = [["O", "O", "O"]]
    linhas, (mp, mr, mf) = metricas_token(gold, pred)
    # B-geo: tp=0, fn=1 -> cobertura 0.0; suporte = tp+fn = 1
    _c, p_geo, r_geo, f_geo, sup_geo = _linha(linhas, "B-geo")
    assert r_geo == pytest.approx(0.0)
    assert f_geo == pytest.approx(0.0)
    assert sup_geo == 1
    # O: tp=2, fp=1 -> precisao 2/3; tp=2, fn=0 -> cobertura 1.0
    _c, p_o, r_o, f_o, sup_o = _linha(linhas, "O")
    assert p_o == pytest.approx(2 / 3)
    assert r_o == pytest.approx(1.0)
    assert sup_o == 2
    # micro: TP=2, FP=1, FN=1 -> p=r=f=2/3
    assert mp == pytest.approx(2 / 3)
    assert mr == pytest.approx(2 / 3)
    assert mf == pytest.approx(2 / 3)


def test_token_divisao_por_zero_nao_quebra():
    """gold=[X] pred=[Y]: sem exceção; X cobertura 0.0; Y precisao 0.0."""
    linhas, (mp, mr, mf) = metricas_token([["X"]], [["Y"]])
    _c, _p, r_x, _f, _sup = _linha(linhas, "X")
    assert r_x == pytest.approx(0.0)
    _c, p_y, _r, _f, _sup = _linha(linhas, "Y")
    assert p_y == pytest.approx(0.0)
    # micro: TP=0, FP=1, FN=1 -> 0.0 sem ZeroDivisionError
    assert mp == pytest.approx(0.0)
    assert mr == pytest.approx(0.0)
    assert mf == pytest.approx(0.0)


def test_token_suporte_conta_ocorrencias_no_gold():
    """gold=[O,O,O] pred=[O,O,O]: linha 'O' suporte == 3."""
    linhas, _micro = metricas_token([["O", "O", "O"]], [["O", "O", "O"]])
    _c, _p, _r, _f, sup = _linha(linhas, "O")
    assert sup == 3


# ---------------------------------------------------------------------------
# Task 2 — metricas_entidade (nível entidade, via seqeval, RETORNA dados)
# ---------------------------------------------------------------------------


def test_entidade_perfeita():
    """Spans idênticos => precisao/cobertura/f1 == 1.0; por_tipo com geo e per."""
    gold = [["B-geo", "I-geo", "O"], ["B-per", "O"]]
    pred = [["B-geo", "I-geo", "O"], ["B-per", "O"]]
    d = metricas_entidade(gold, pred)
    assert d["precisao"] == pytest.approx(1.0)
    assert d["cobertura"] == pytest.approx(1.0)
    assert d["f1"] == pytest.approx(1.0)
    assert "geo" in d["por_tipo"]
    assert "per" in d["por_tipo"]
    assert d["por_tipo"]["geo"]["f1"] == pytest.approx(1.0)
    assert d["por_tipo"]["geo"]["suporte"] == 1
    assert d["por_tipo"]["per"]["f1"] == pytest.approx(1.0)
    assert d["por_tipo"]["per"]["suporte"] == 1


def test_entidade_span_parcial_nao_casa():
    """gold span de 2 tokens vs pred span de 1 token: 'geo' P/R/F1 == 0.0."""
    gold = [["B-geo", "I-geo"]]
    pred = [["B-geo", "O"]]
    d = metricas_entidade(gold, pred)
    assert d["por_tipo"]["geo"]["precisao"] == pytest.approx(0.0)
    assert d["por_tipo"]["geo"]["cobertura"] == pytest.approx(0.0)
    assert d["por_tipo"]["geo"]["f1"] == pytest.approx(0.0)
    assert d["precisao"] == pytest.approx(0.0)
    assert d["cobertura"] == pytest.approx(0.0)
    assert d["f1"] == pytest.approx(0.0)


def test_entidade_nao_imprime(capsys):
    """metricas_entidade não escreve nada no stdout (refatoração do legado)."""
    gold = [["B-geo", "I-geo", "O"]]
    pred = [["B-geo", "I-geo", "O"]]
    metricas_entidade(gold, pred)
    captured = capsys.readouterr()
    assert captured.out == ""


def test_entidade_filtra_chaves_agregadas():
    """por_tipo NÃO contém 'micro avg'/'macro avg'/'weighted avg'/'accuracy'."""
    gold = [["B-geo", "I-geo", "O"], ["B-per", "O"]]
    pred = [["B-geo", "I-geo", "O"], ["B-per", "O"]]
    d = metricas_entidade(gold, pred)
    agregadas = {"micro avg", "macro avg", "weighted avg", "accuracy"}
    assert agregadas.isdisjoint(d["por_tipo"].keys())
