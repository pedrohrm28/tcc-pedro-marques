"""Testes de run_llm.py — alinhamento, resume, fallback, reiniciar, métricas e modelo com ':'.

NENHUM teste chama o Ollama real. O cliente é mockado via fn_gerar injetável:
a função fake recebe (modelo, prompt, num_predict) e devolve um Resposta com
texto = JSON do tamanho certo (ou errado, para testar fallback) e métricas fixas.

Usa --limite pequeno (5 sentenças) para ser rápido (< 30s sem Ollama no ar).
"""
from __future__ import annotations

import json
from collections import Counter

import pytest

import run_llm
from src.llm.cliente_ollama import Resposta
from src.io.contrato import ler_jsonl, caminho_resultado
from src.io.corpora import carregar_conllu, carregar_gmb


# ---------------------------------------------------------------------------
# Helper: fábrica de fn_gerar fake
# ---------------------------------------------------------------------------


def _make_fake_gerar(tag: str = "NOUN", tamanho_errado: int | None = None):
    """Devolve uma função fn_gerar fake que retorna Resposta com JSON fixo.

    Args:
        tag:            tag a repetir no array de saída (default "NOUN").
        tamanho_errado: se fornecido, devolve sempre um array com esse tamanho,
                        independente do prompt — para testar o caminho de fallback.
    """

    def _fake(modelo: str, prompt: str, num_predict=None) -> Resposta:
        # Extrai o nº de tokens do prompt: "Input tokens (N tokens):"
        import re

        match = re.search(r"Input tokens \((\d+) tokens\)", prompt)
        n_prompt = int(match.group(1)) if match else 5

        n_saida = tamanho_errado if tamanho_errado is not None else n_prompt
        texto = json.dumps([tag] * n_saida)
        return Resposta(
            texto=texto,
            eval_count=n_saida,
            eval_duration_ns=1_000_000_000,  # 1 segundo fixo
            load_duration_ns=0,
            total_duration_ns=1_000_000_000,
        )

    return _fake


# ---------------------------------------------------------------------------
# Test 1 — alinhamento token-a-token (upos)
# ---------------------------------------------------------------------------


def test_alinhamento_upos(tmp_path):
    """O .jsonl alinha token-a-token (sentenca_id, posicao, token) com o gold UPOS."""
    limite = 5
    caminho = str(tmp_path / "upos.jsonl")
    fake = _make_fake_gerar(tag="NOUN")

    run_llm.rodar("fake-model", "upos", limite=limite, caminho_saida=caminho, fn_gerar=fake)

    lidos = ler_jsonl(caminho)
    gold = carregar_conllu(limite=limite)
    total_tokens = sum(len(s.pares) for s in gold)

    # Nº de registros == soma de len(s.pares) das 5 sentenças.
    assert len(lidos) == total_tokens

    # (sentenca_id, posicao, token) batem 1:1 com o gold, em ordem.
    esperado = [
        (s.sentenca_id, pos, tok)
        for s in gold
        for pos, (tok, _) in enumerate(s.pares)
    ]
    obtido = [(r.sentenca_id, r.posicao, r.token) for r in lidos]
    assert obtido == esperado

    # modelo preservado sem sanitização.
    assert all(r.modelo == "fake-model" for r in lidos)
    assert all(r.tarefa == "upos" for r in lidos)


# ---------------------------------------------------------------------------
# Test 2 — fallback quando array tem tamanho errado
# ---------------------------------------------------------------------------


def test_fallback_array_tamanho_errado(tmp_path):
    """Quando fake devolve array de tamanho errado, fallback total ocorre.

    O .jsonl ainda tem len == total de tokens (alinhamento preservado) e
    o meta retornado tem fallbacks == total de tokens gerados com fallback.
    """
    limite = 5
    caminho = str(tmp_path / "upos_fallback.jsonl")
    # Array de tamanho 1 (sempre errado) -> fallback total por sentença.
    fake = _make_fake_gerar(tag="NOUN", tamanho_errado=1)

    meta = run_llm.rodar("fake-model", "upos", limite=limite, caminho_saida=caminho, fn_gerar=fake)

    lidos = ler_jsonl(caminho)
    gold = carregar_conllu(limite=limite)
    total_tokens = sum(len(s.pares) for s in gold)

    # Alinhamento preservado mesmo com fallback total.
    assert len(lidos) == total_tokens

    # Todas as tags são o valor de fallback UPOS.
    assert all(r.tag_predita == "NOUN" for r in lidos)

    # meta registra fallbacks = total de tokens (uma sentença com 1 token "real" não
    # conta; o fallback total usa len(tokens) por sentença).
    assert meta["fallbacks"] == total_tokens


# ---------------------------------------------------------------------------
# Test 3 — resume: sentenças já feitas são puladas
# ---------------------------------------------------------------------------


def test_resume_pula_sentencas_feitas(tmp_path):
    """Resume não reprocessa nem duplica sentenças já presentes no .jsonl.

    Rodada 1: processa as 2 primeiras sentenças.
    Rodada 2: processa as 5 primeiras com um fake que LEVANTA se chamado
              para os sentenca_id das 2 primeiras — prova que foram puladas.
    Ao final, cada sentenca_id aparece exatamente uma vez (com todas as suas posições).
    """
    limite_parcial = 2
    limite_total = 5
    caminho = str(tmp_path / "upos_resume.jsonl")
    fake_normal = _make_fake_gerar(tag="NOUN")

    # Rodada 1: processa só as 2 primeiras.
    run_llm.rodar("fake-model", "upos", limite=limite_parcial, caminho_saida=caminho, fn_gerar=fake_normal)

    # Coletar os sentenca_id já feitos.
    gold_parcial = carregar_conllu(limite=limite_parcial)
    ids_feitos = {s.sentenca_id for s in gold_parcial}

    # Fake para rodada 2: levanta se chamado para ids já feitos.
    def _fake_assertivo(modelo, prompt, num_predict=None):
        import re
        # Extrair tokens do prompt para identificar a sentença.
        match = re.search(r"Input tokens \(\d+ tokens\): (\[.*?\])", prompt)
        if match:
            tokens = json.loads(match.group(1))
            gold_total = carregar_conllu(limite=limite_total)
            for s in gold_total:
                if [tok for tok, _ in s.pares] == tokens and s.sentenca_id in ids_feitos:
                    raise AssertionError(
                        f"Resume falhou: sentença {s.sentenca_id!r} foi reprocessada!"
                    )
        return _make_fake_gerar(tag="NOUN")(modelo, prompt, num_predict)

    # Rodada 2: processa as 5 sentenças (deve pular as 2 primeiras).
    run_llm.rodar("fake-model", "upos", limite=limite_total, caminho_saida=caminho, fn_gerar=_fake_assertivo)

    lidos = ler_jsonl(caminho)
    gold_total = carregar_conllu(limite=limite_total)

    # Nº de registros == total de tokens das 5 sentenças (sem duplicação).
    total_tokens = sum(len(s.pares) for s in gold_total)
    assert len(lidos) == total_tokens

    # Cada sentenca_id aparece exatamente com as suas posições (0..n-1), sem duplicação.
    por_sentenca: dict[str, list[int]] = {}
    for r in lidos:
        por_sentenca.setdefault(r.sentenca_id, []).append(r.posicao)

    for s in gold_total:
        posicoes = por_sentenca[s.sentenca_id]
        assert posicoes == list(range(len(s.pares))), (
            f"Sentença {s.sentenca_id!r}: posições {posicoes} != esperado {list(range(len(s.pares)))}"
        )


# ---------------------------------------------------------------------------
# Test 4 — reiniciar: não acumula registros de rodada anterior
# ---------------------------------------------------------------------------


def test_reiniciar_nao_duplica(tmp_path):
    """Após uma rodada, rodar novamente com reiniciar=True produz o mesmo nº de registros."""
    limite = 5
    caminho = str(tmp_path / "upos_reiniciar.jsonl")
    fake = _make_fake_gerar(tag="NOUN")

    run_llm.rodar("fake-model", "upos", limite=limite, caminho_saida=caminho, fn_gerar=fake)
    lidos_1 = ler_jsonl(caminho)

    # Rodar de novo com reiniciar=True: deve começar do zero.
    run_llm.rodar("fake-model", "upos", limite=limite, caminho_saida=caminho, reiniciar=True, fn_gerar=fake)
    lidos_2 = ler_jsonl(caminho)

    # O nº de registros deve ser idêntico ao de uma rodada limpa.
    assert len(lidos_2) == len(lidos_1)


# ---------------------------------------------------------------------------
# Test 5 — métricas retornadas por rodar()
# ---------------------------------------------------------------------------


def test_metricas_no_retorno(tmp_path):
    """O dict retornado por rodar() tem as chaves obrigatórias com valores coerentes."""
    limite = 5
    caminho = str(tmp_path / "upos_meta.jsonl")
    fake = _make_fake_gerar(tag="NOUN")

    meta = run_llm.rodar("fake-model", "upos", limite=limite, caminho_saida=caminho, fn_gerar=fake)

    assert "tok_por_seg" in meta
    assert "sent_por_seg" in meta
    assert "sentencas" in meta
    assert "fallbacks" in meta
    assert "wall_clock_s" in meta

    assert meta["tok_por_seg"] >= 0.0
    assert meta["sent_por_seg"] >= 0.0
    assert meta["sentencas"] == limite

    # O meta.json deve ter sido criado ao lado do .jsonl.
    import os
    caminho_meta = caminho.replace(".jsonl", ".meta.json")
    assert os.path.exists(caminho_meta), f"meta.json não encontrado em {caminho_meta}"
    with open(caminho_meta, encoding="utf-8") as f:
        meta_lido = json.load(f)
    assert meta_lido["modelo"] == "fake-model"
    assert meta_lido["tarefa"] == "upos"


# ---------------------------------------------------------------------------
# Test 6 — modelo mantém ':' no Registro; caminho sanitiza para '_'
# ---------------------------------------------------------------------------


def test_modelo_preserva_dois_pontos(tmp_path):
    """r.modelo mantém o ':' (ex "llama3.1:8b"); o caminho sanitiza para '_'."""
    limite = 3
    caminho = str(tmp_path / "ner_llama.jsonl")
    fake = _make_fake_gerar(tag="O")

    run_llm.rodar("llama3.1:8b", "ner", limite=limite, caminho_saida=caminho, fn_gerar=fake)

    lidos = ler_jsonl(caminho)
    assert len(lidos) > 0

    # Todos os registros devem ter o nome com ':' preservado.
    assert all(r.modelo == "llama3.1:8b" for r in lidos), (
        f"Algum registro tem modelo diferente: {set(r.modelo for r in lidos)}"
    )

    # O caminho padrão via caminho_resultado deve sanitizar o ':' para '_'.
    caminho_padrao = caminho_resultado("base_mapeada", "llama3.1:8b", "ner")
    assert "llama3.1_8b" in caminho_padrao, (
        f"caminho_resultado não sanitizou ':' para '_': {caminho_padrao}"
    )
    assert ":" not in caminho_padrao, (
        f"caminho_resultado ainda contém ':': {caminho_padrao}"
    )
