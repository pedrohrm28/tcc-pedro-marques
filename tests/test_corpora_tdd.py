"""Testes TDD para src/io/corpora.py — fase RED.

Estes testes validam os comportamentos definidos no plano antes da implementação.
Devem falhar enquanto os loaders retornam NotImplementedError.
"""
import pytest
from src.io.corpora import carregar_gmb, carregar_conllu, Sentenca


# ---------------------------------------------------------------------------
# GMB (NER, IOB)
# ---------------------------------------------------------------------------

def test_gmb_retorna_2999_sentencas():
    """carregar_gmb() completo deve ter exatamente 2999 sentenças."""
    sentencas = carregar_gmb()
    assert len(sentencas) == 2999, f"Esperado 2999, obtido {len(sentencas)}"


def test_gmb_limite_150():
    """carregar_gmb(limite=150) deve retornar exatamente 150 sentenças."""
    sentencas = carregar_gmb(limite=150)
    assert len(sentencas) == 150, f"Esperado 150, obtido {len(sentencas)}"


def test_gmb_primeira_sentenca_id():
    """Primeira sentença do GMB deve ter sentenca_id == '1.0'."""
    sentencas = carregar_gmb(limite=1)
    assert sentencas[0].sentenca_id == "1.0", f"Esperado '1.0', obtido '{sentencas[0].sentenca_id}'"


def test_gmb_primeiros_pares_conhecidos():
    """Primeiros 4 pares da primeira sentença GMB devem ser tokens/tags conhecidos."""
    sentencas = carregar_gmb(limite=1)
    pares = sentencas[0].pares
    assert pares[0] == ("Thousands", "O"), f"Par[0] errado: {pares[0]}"
    assert pares[1] == ("of", "O"), f"Par[1] errado: {pares[1]}"
    assert pares[2] == ("demonstrators", "O"), f"Par[2] errado: {pares[2]}"
    assert pares[3] == ("have", "O"), f"Par[3] errado: {pares[3]}"


def test_gmb_sentencas_sao_Sentenca():
    """Todos os elementos retornados devem ser instâncias de Sentenca."""
    sentencas = carregar_gmb(limite=5)
    for s in sentencas:
        assert isinstance(s, Sentenca), f"Esperado Sentenca, obtido {type(s)}"


# ---------------------------------------------------------------------------
# CoNLL-U (POS/UPOS)
# ---------------------------------------------------------------------------

def test_conllu_retorna_1167_sentencas():
    """carregar_conllu() completo deve ter exatamente 1167 sentenças."""
    sentencas = carregar_conllu()
    assert len(sentencas) == 1167, f"Esperado 1167, obtido {len(sentencas)}"


def test_conllu_limite_1167_igual_total():
    """carregar_conllu(limite=1167) deve retornar as mesmas 1167 sentenças."""
    sentencas = carregar_conllu(limite=1167)
    assert len(sentencas) == 1167, f"Esperado 1167, obtido {len(sentencas)}"


def test_conllu_primeiro_par_folha_propn():
    """Primeiro par da primeira sentença do Bosque deve ser ('Folha', 'PROPN')."""
    sentencas = carregar_conllu(limite=1)
    pares = sentencas[0].pares
    assert pares[0] == ("Folha", "PROPN"), f"Par[0] errado: {pares[0]}"


def test_conllu_segundo_par_punct():
    """Segundo par da primeira sentença do Bosque deve ser ('--', 'PUNCT')."""
    sentencas = carregar_conllu(limite=1)
    pares = sentencas[0].pares
    assert pares[1] == ("--", "PUNCT"), f"Par[1] errado: {pares[1]}"


def test_conllu_sem_multiword_ids():
    """Nenhum par deve conter token derivado de linha de range (multiword)."""
    # Verificamos que nenhum sentenca_id ou token é derivado de linha com '-' no ID.
    # Como não temos acesso direto ao ID original, verificamos indiretamente:
    # as UPOS da primeira sentença devem pertencer ao conjunto fechado UD.
    tags_ud_validas = {
        "ADJ", "ADP", "ADV", "AUX", "CCONJ", "DET", "INTJ",
        "NOUN", "NUM", "PART", "PRON", "PROPN", "PUNCT",
        "SCONJ", "SYM", "VERB", "X",
    }
    sentencas = carregar_conllu(limite=1)
    for token, upos in sentencas[0].pares:
        assert upos in tags_ud_validas, (
            f"UPOS inválida '{upos}' para token '{token}' — "
            f"possível multiword não filtrado"
        )
