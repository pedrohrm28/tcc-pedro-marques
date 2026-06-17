"""Testes para src/llm/prompts.py e src/llm/cliente_ollama.py.

Todos os testes são PUROS — nenhum chama o Ollama real nem faz requests HTTP reais.
O teste do cliente usa monkeypatch para interceptar requests.post.
"""
import json

import pytest

from src.llm.prompts import (
    INSTRUCAO_NER,
    INSTRUCAO_UPOS,
    montar_prompt,
)
from src.llm.cliente_ollama import (
    Resposta,
    gerar,
    tok_por_seg,
)
from run_regras import UPOS_VALIDOS


# ---------------------------------------------------------------------------
# Testes de montar_prompt
# ---------------------------------------------------------------------------

def test_montar_prompt_upos_contem_tokens_json():
    """montar_prompt('upos', ...) contém o JSON dos tokens e menciona 'JSON'."""
    tokens = ["O", "cão"]
    prompt = montar_prompt("upos", tokens)
    # Os tokens devem estar no prompt como JSON serializado
    assert '["O", "cão"]' in prompt or json.dumps(tokens, ensure_ascii=False) in prompt
    # Deve mencionar JSON explicitamente
    assert "JSON" in prompt.upper()
    # Deve mencionar 'cão' (não pode ter omitido por ensure_ascii)
    assert "cão" in prompt


def test_montar_prompt_upos_lista_upos_validos():
    """montar_prompt('upos', ...) menciona as tags UPOS válidas na instrução."""
    prompt = montar_prompt("upos", ["tok"])
    # Pelo menos algumas das 17 UPOS devem aparecer
    upos_encontradas = sum(1 for tag in UPOS_VALIDOS if tag in prompt)
    assert upos_encontradas >= 10, f"Esperava >= 10 UPOS no prompt, encontrei {upos_encontradas}"


def test_montar_prompt_ner_contem_instrucao_iob():
    """montar_prompt('ner', ...) contém instrução IOB."""
    prompt = montar_prompt("ner", ["London", "is", "big"])
    # Instrução NER deve mencionar IOB
    assert "IOB" in prompt or "B-" in prompt
    # Deve conter os tokens
    assert "London" in prompt


def test_montar_prompt_ner_vs_upos_instrucoes_diferentes():
    """montar_prompt usa INSTRUCAO_NER para ner e INSTRUCAO_UPOS para upos (textos distintos)."""
    tokens = ["tok"]
    prompt_ner = montar_prompt("ner", tokens)
    prompt_upos = montar_prompt("upos", tokens)
    assert prompt_ner != prompt_upos
    # NER usa instrução em inglês; UPOS em português
    assert "IOB" in prompt_ner or "B-" in prompt_ner
    assert "UPOS" in prompt_upos or "POS" in prompt_upos


def test_montar_prompt_embute_n_tokens():
    """O prompt informa o número de tokens esperados no array de saída."""
    tokens = ["a", "b", "c", "d"]
    prompt = montar_prompt("upos", tokens)
    # O número 4 deve aparecer no prompt (informa quantos elementos o array deve ter)
    assert "4" in prompt


def test_montar_prompt_tarefa_invalida():
    """montar_prompt levanta ValueError para tarefa desconhecida."""
    with pytest.raises(ValueError, match="tarefa inválida"):
        montar_prompt("xyz", ["tok"])


def test_instrucao_ner_constante_nao_vazia():
    """INSTRUCAO_NER é uma string não vazia com palavras-chave de NER."""
    assert isinstance(INSTRUCAO_NER, str)
    assert len(INSTRUCAO_NER) >= 50
    assert "IOB" in INSTRUCAO_NER or "B-" in INSTRUCAO_NER


def test_instrucao_upos_constante_nao_vazia():
    """INSTRUCAO_UPOS é uma string não vazia com as 17 UPOS listadas."""
    assert isinstance(INSTRUCAO_UPOS, str)
    assert len(INSTRUCAO_UPOS) >= 50
    upos_encontradas = sum(1 for tag in UPOS_VALIDOS if tag in INSTRUCAO_UPOS)
    assert upos_encontradas >= 15, f"Esperava >= 15 UPOS na instrução, encontrei {upos_encontradas}"


# ---------------------------------------------------------------------------
# Testes do cliente Ollama (com monkeypatch em requests.post — sem Ollama real)
# ---------------------------------------------------------------------------

class _FakeResponse:
    """Objeto fake que simula requests.Response."""

    def __init__(self, data: dict):
        self._data = data

    def raise_for_status(self):
        pass  # no-op

    def json(self):
        return self._data


def test_gerar_corpo_options_reprodutiveis(monkeypatch):
    """O corpo da chamada usa temperature=0, seed=42, keep_alive=-1, format='json'."""
    chamadas: list[dict] = []

    def fake_post(url, json=None, timeout=None):
        chamadas.append(json)
        return _FakeResponse({
            "response": '["O","O"]',
            "eval_count": 2,
            "eval_duration": 1_000_000_000,
            "load_duration": 500_000_000,
            "total_duration": 1_500_000_000,
        })

    monkeypatch.setattr("src.llm.cliente_ollama.requests.post", fake_post)

    resp = gerar("llama3.1:8b", "prompt de teste")

    assert len(chamadas) == 1
    corpo = chamadas[0]

    # Verificar options reprodutíveis obrigatórias
    assert corpo["options"]["temperature"] == 0
    assert corpo["options"]["seed"] == 42
    assert corpo["keep_alive"] == -1
    assert corpo["format"] == "json"
    assert corpo["stream"] is False
    assert corpo["model"] == "llama3.1:8b"


def test_gerar_retorna_resposta_com_metricas(monkeypatch):
    """gerar() retorna Resposta com texto e métricas corretas."""
    def fake_post(url, json=None, timeout=None):
        return _FakeResponse({
            "response": '["O","O"]',
            "eval_count": 2,
            "eval_duration": 1_000_000_000,
            "load_duration": 500_000_000,
            "total_duration": 1_500_000_000,
        })

    monkeypatch.setattr("src.llm.cliente_ollama.requests.post", fake_post)

    resp = gerar("qwen2.5:3b", "prompt")

    assert isinstance(resp, Resposta)
    assert resp.texto == '["O","O"]'
    assert resp.eval_count == 2
    assert resp.eval_duration_ns == 1_000_000_000
    assert resp.load_duration_ns == 500_000_000
    assert resp.total_duration_ns == 1_500_000_000


def test_tok_por_seg_calculo_correto(monkeypatch):
    """tok_por_seg retorna eval_count / (eval_duration_ns/1e9) == 2.0."""
    def fake_post(url, json=None, timeout=None):
        return _FakeResponse({
            "response": '["O","O"]',
            "eval_count": 2,
            "eval_duration": 1_000_000_000,
        })

    monkeypatch.setattr("src.llm.cliente_ollama.requests.post", fake_post)

    resp = gerar("llama3.2:3b", "prompt")
    assert tok_por_seg(resp) == pytest.approx(2.0)


def test_tok_por_seg_zero_quando_eval_duration_zero():
    """tok_por_seg retorna 0.0 quando eval_duration_ns == 0 (evita divisão por zero)."""
    r = Resposta(
        texto="[]",
        eval_count=10,
        eval_duration_ns=0,
        load_duration_ns=0,
        total_duration_ns=0,
    )
    assert tok_por_seg(r) == 0.0


def test_gerar_num_predict_adicionado_ao_options(monkeypatch):
    """Quando num_predict é informado, aparece nos options enviados."""
    chamadas: list[dict] = []

    def fake_post(url, json=None, timeout=None):
        chamadas.append(json)
        return _FakeResponse({
            "response": "[]",
            "eval_count": 0,
            "eval_duration": 0,
        })

    monkeypatch.setattr("src.llm.cliente_ollama.requests.post", fake_post)

    gerar("llama3.1:8b", "p", num_predict=512)
    assert chamadas[0]["options"]["num_predict"] == 512


def test_gerar_sem_num_predict_nao_tem_chave(monkeypatch):
    """Quando num_predict é None, a chave não aparece nos options."""
    chamadas: list[dict] = []

    def fake_post(url, json=None, timeout=None):
        chamadas.append(json)
        return _FakeResponse({"response": "[]", "eval_count": 0, "eval_duration": 0})

    monkeypatch.setattr("src.llm.cliente_ollama.requests.post", fake_post)

    gerar("llama3.2:3b", "p")
    assert "num_predict" not in chamadas[0]["options"]
