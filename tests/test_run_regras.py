"""Testes TDD para run_regras.py — anotação UPOS por regras.

Task 1 (RED first): regras puras (construir_lexico, tag_por_regras).
Task 2: alinhamento token-a-token do .jsonl emitido com o gold do Bosque.
"""
import json
import subprocess
import sys

import pytest

from run_regras import (
    UPOS_VALIDOS,
    construir_lexico,
    tag_por_regras,
)


# ---------------------------------------------------------------------------
# Task 1 — regras de UPOS
# ---------------------------------------------------------------------------

def test_pontuacao_vira_punct():
    """Token de pontuação pura -> PUNCT."""
    assert tag_por_regras(".", {}) == "PUNCT"
    assert tag_por_regras("--", {}) == "PUNCT"


def test_simbolo_vira_sym_ou_punct():
    """Símbolos como % -> SYM (ou PUNCT)."""
    assert tag_por_regras("%", {}) in {"SYM", "PUNCT"}


def test_numero_vira_num():
    """Dígitos e ordinais -> NUM."""
    assert tag_por_regras("123", {}) == "NUM"
    assert tag_por_regras("2º", {}) == "NUM"


def test_lexico_tem_prioridade():
    """O léxico tem prioridade sobre heurísticas morfológicas."""
    # 'casa' terminaria potencialmente em fallback, mas léxico decide.
    assert tag_por_regras("casa", {"casa": "VERB"}) == "VERB"


def test_sufixo_mente_vira_adv():
    """Sufixo -mente sem léxico -> ADV."""
    assert tag_por_regras("rapidamente", {}) == "ADV"


def test_fallback_noun():
    """Token desconhecido sem sufixo reconhecível -> NOUN (tag mais frequente)."""
    assert tag_por_regras("xyzqwk", {}) == "NOUN"


def test_construir_lexico_nao_vazio_e_de_adp():
    """Léxico do TRAIN é não-vazio e mapeia 'de' -> 'ADP'."""
    lexico = construir_lexico()
    assert isinstance(lexico, dict)
    assert len(lexico) > 0
    assert lexico["de"] == "ADP"


def test_todas_as_tags_em_upos_validos():
    """Toda tag retornada por tag_por_regras pertence ao conjunto UPOS válido."""
    amostras = [".", "%", "123", "2º", "rapidamente", "xyzqwk", "Brasil", "comer"]
    for tok in amostras:
        assert tag_por_regras(tok, {}) in UPOS_VALIDOS


def test_upos_validos_tem_17_tags():
    """O conjunto UPOS_VALIDOS deve conter exatamente as 17 tags do teste."""
    assert len(UPOS_VALIDOS) == 17


# ---------------------------------------------------------------------------
# Task 2 — alinhamento do .jsonl com o gold
# ---------------------------------------------------------------------------

def test_jsonl_alinha_com_gold(tmp_path):
    """O .jsonl emitido alinha token-a-token com carregar_conllu(limite=N)."""
    from src.io.contrato import ler_jsonl
    from src.io.corpora import carregar_conllu

    n = 5
    saida = tmp_path / "upos_teste.jsonl"
    cmd = [
        sys.executable,
        "run_regras.py",
        "--limite",
        str(n),
        "--saida",
        str(saida),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    assert proc.returncode == 0, f"run_regras falhou: {proc.stderr}"

    registros = ler_jsonl(str(saida))
    gold = carregar_conllu(limite=n)

    total_tokens = sum(len(s.pares) for s in gold)
    assert len(registros) == total_tokens, (len(registros), total_tokens)

    # Reconstrói a sequência (sentenca_id, posicao, token) esperada.
    esperado = []
    for s in gold:
        for pos, (tok, _gold) in enumerate(s.pares):
            esperado.append((s.sentenca_id, pos, tok))

    for r, (sid, pos, tok) in zip(registros, esperado):
        assert r.sentenca_id == sid
        assert r.posicao == pos
        assert r.token == tok
        assert r.tarefa == "upos"
        assert r.modelo == "regras"
        assert r.tag_predita in UPOS_VALIDOS
