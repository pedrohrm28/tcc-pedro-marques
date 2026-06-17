"""Testes TDD para src/llm/parser.py — parser robusto array-JSON -> tags.

Todos os testes são PUROS: nenhum toca rede, HTTP ou Ollama.
RED first: escreve os testes antes da implementação.
"""
import pytest

from src.llm.parser import (
    FALLBACK,
    alinhar_tags,
    extrair_array,
    tag_valida,
)
from run_regras import UPOS_VALIDOS


# ---------------------------------------------------------------------------
# extrair_array
# ---------------------------------------------------------------------------

def test_extrair_array_lista_direta():
    """Resposta que já é um array JSON -> retorna a lista."""
    resultado = extrair_array('["NOUN", "VERB", "DET"]')
    assert resultado == ["NOUN", "VERB", "DET"]


def test_extrair_array_dict_extrai_primeira_lista():
    """Resposta como dict {"tags": [...]} -> extrai a primeira lista de valores."""
    resultado = extrair_array('{"tags": ["O", "B-geo", "I-per"]}')
    assert resultado == ["O", "B-geo", "I-per"]


def test_extrair_array_json_invalido_retorna_none():
    """JSON inválido -> retorna None."""
    assert extrair_array("not json") is None


def test_extrair_array_dict_sem_lista_retorna_none():
    """Dict sem nenhuma lista nos valores -> retorna None."""
    assert extrair_array('{"key": "value"}') is None


def test_extrair_array_lista_vazia():
    """Array vazio -> retorna lista vazia (não None)."""
    resultado = extrair_array("[]")
    assert resultado == []


# ---------------------------------------------------------------------------
# tag_valida
# ---------------------------------------------------------------------------

def test_tag_valida_upos_valida():
    """Tags UPOS do conjunto válido -> True."""
    for tag in ("NOUN", "VERB", "DET", "ADP", "PUNCT"):
        assert tag_valida("upos", tag) is True


def test_tag_valida_upos_invalida():
    """Tags UPOS fora do conjunto -> False."""
    assert tag_valida("upos", "FOO") is False
    assert tag_valida("upos", "") is False
    assert tag_valida("upos", None) is False


def test_tag_valida_ner_aceita_o_e_bio():
    """NER: 'O', 'B-geo', 'I-per' são válidas."""
    assert tag_valida("ner", "O") is True
    assert tag_valida("ner", "B-geo") is True
    assert tag_valida("ner", "I-per") is True


def test_tag_valida_ner_rejeita_vazia_e_none():
    """NER: tag vazia '' e None são inválidas."""
    assert tag_valida("ner", "") is False
    assert tag_valida("ner", None) is False


def test_tag_valida_ner_rejeita_sem_prefixo():
    """NER: tag que não é 'O' nem começa com 'B-'/'I-' -> False."""
    assert tag_valida("ner", "geo") is False


# ---------------------------------------------------------------------------
# alinhar_tags — casos principais
# ---------------------------------------------------------------------------

def test_alinhar_tags_upos_correto():
    """Array JSON correto e do tamanho certo (UPOS) -> tags == array, n_fallback == 0."""
    tokens = ["O", "cão", "corre"]
    resposta = '["DET", "NOUN", "VERB"]'
    tags, n = alinhar_tags("upos", tokens, resposta)
    assert tags == ["DET", "NOUN", "VERB"]
    assert n == 0
    assert len(tags) == len(tokens)


def test_alinhar_tags_tamanho_errado_fallback_total():
    """Array com tamanho errado (3 tags, 2 tokens) -> todas viram fallback, n_fallback == len(tokens)."""
    tokens = ["O", "gato"]
    resposta = '["NOUN", "VERB", "DET"]'  # 3 tags, mas só 2 tokens
    tags, n = alinhar_tags("upos", tokens, resposta)
    assert tags == ["NOUN", "NOUN"]  # FALLBACK["upos"] == "NOUN"
    assert n == len(tokens)
    assert len(tags) == len(tokens)


def test_alinhar_tags_json_invalido_fallback_total():
    """JSON inválido -> fallback total, n_fallback == len(tokens)."""
    tokens = ["The", "cat"]
    resposta = "not json"
    tags, n = alinhar_tags("ner", tokens, resposta)
    assert tags == ["O", "O"]  # FALLBACK["ner"] == "O"
    assert n == len(tokens)
    assert len(tags) == len(tokens)


def test_alinhar_tags_tag_upos_invalida_so_aquela_posicao():
    """Uma tag UPOS inválida ('FOO') no meio -> só aquela posição vira 'NOUN', n_fallback == 1."""
    tokens = ["a", "b", "c"]
    resposta = '["NOUN", "FOO", "VERB"]'
    tags, n = alinhar_tags("upos", tokens, resposta)
    assert tags == ["NOUN", "NOUN", "VERB"]
    assert n == 1
    assert len(tags) == len(tokens)


def test_alinhar_tags_ner_aceita_validas():
    """NER aceita 'O', 'B-geo', 'I-per'; n_fallback == 0."""
    tokens = ["London", "is", "big"]
    resposta = '["B-geo", "O", "O"]'
    tags, n = alinhar_tags("ner", tokens, resposta)
    assert tags == ["B-geo", "O", "O"]
    assert n == 0
    assert len(tags) == len(tokens)


def test_alinhar_tags_ner_tag_vazia_vira_fallback():
    """NER: tag vazia '' vira 'O' e conta 1 fallback."""
    tokens = ["London", "big"]
    resposta = '["B-geo", ""]'
    tags, n = alinhar_tags("ner", tokens, resposta)
    assert tags == ["B-geo", "O"]
    assert n == 1
    assert len(tags) == len(tokens)


def test_alinhar_tags_dict_resposta_aceita():
    """Resposta como dict {'tags': [...]} é aceita (extrair_array extrai a lista)."""
    tokens = ["O", "cão"]
    resposta = '{"tags": ["DET", "NOUN"]}'
    tags, n = alinhar_tags("upos", tokens, resposta)
    assert tags == ["DET", "NOUN"]
    assert n == 0
    assert len(tags) == len(tokens)


def test_alinhar_tags_saida_sempre_upos_validos():
    """Toda tag UPOS de saída pertence a UPOS_VALIDOS para entradas arbitrárias."""
    # Inclui tags inválidas, JSON inválido, dict, tamanho errado
    casos = [
        ('["FOO", "BAR", "BAZ"]', ["a", "b", "c"]),
        ("bad json", ["x", "y"]),
        ('{"tags": ["VERB", "NOUN"]}', ["p", "q"]),
        ('["NOUN"]', ["a", "b", "c"]),  # tamanho errado
    ]
    for resposta, tokens in casos:
        tags, _ = alinhar_tags("upos", tokens, resposta)
        assert len(tags) == len(tokens)
        for tag in tags:
            assert tag in UPOS_VALIDOS, f"tag {tag!r} fora de UPOS_VALIDOS"


def test_fallback_constante_ner_e_upos():
    """FALLBACK dict tem entradas 'ner' e 'upos' com valores corretos."""
    assert FALLBACK["ner"] == "O"
    assert FALLBACK["upos"] == "NOUN"
