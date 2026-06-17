"""src/llm/parser.py — Parser robusto array-JSON -> lista de tags alinhada token-a-token.

Converte a resposta crua do LLM (string JSON) numa lista de tags com o MESMO comprimento
que a lista de tokens da sentença. Aplica fallback rastreável (NER "O", UPOS "NOUN") e
conta os tokens consertados.

Importa UPOS_VALIDOS de run_regras (não redefine as 17 tags).

Parte do núcleo puro e mockável do runner LLM (Fase 3, plano 03-01).
"""
from __future__ import annotations

import json

from run_regras import UPOS_VALIDOS

# ---------------------------------------------------------------------------
# Fallback por tarefa (D-04 do CONTEXT.md).
# ---------------------------------------------------------------------------
FALLBACK: dict[str, str] = {
    "ner": "O",
    "upos": "NOUN",
}


def extrair_array(resposta_crua: str) -> list | None:
    """Tenta extrair um array de tags da resposta JSON do LLM.

    Lógica:
    - Faz json.loads na resposta crua.
    - Se o resultado for uma lista, retorna-a diretamente.
    - Se for um dict, retorna a primeira lista encontrada nos valores.
    - Se json.loads falhar ou não houver lista, retorna None.

    Args:
        resposta_crua: string retornada pelo campo "response" do Ollama.

    Returns:
        Lista de tags, ou None se não for possível extrair.
    """
    try:
        dados = json.loads(resposta_crua)
    except (json.JSONDecodeError, ValueError):
        return None

    if isinstance(dados, list):
        return dados

    if isinstance(dados, dict):
        # Retorna a primeira lista encontrada nos valores do dicionário.
        for valor in dados.values():
            if isinstance(valor, list):
                return valor
        return None

    return None


def tag_valida(tarefa: str, tag) -> bool:
    """Verifica se uma tag individual é válida para a tarefa especificada.

    Regras:
    - tarefa "upos": tag deve ser string e pertencer a UPOS_VALIDOS.
    - tarefa "ner": tag deve ser string não vazia e ser "O" ou começar com "B-" ou "I-".

    Args:
        tarefa: "upos" ou "ner".
        tag:    valor retornado pelo LLM para esta posição.

    Returns:
        True se a tag é válida para a tarefa; False caso contrário.
    """
    if not isinstance(tag, str):
        return False

    if tarefa == "upos":
        return tag in UPOS_VALIDOS

    if tarefa == "ner":
        if not tag:
            return False
        return tag == "O" or tag[:2] in {"B-", "I-"}

    # Tarefa desconhecida: rejeita.
    return False


def alinhar_tags(
    tarefa: str,
    tokens: list[str],
    resposta_crua: str,
) -> tuple[list[str], int]:
    """Converte a resposta crua do LLM numa lista de tags alinhada token-a-token.

    Garante SEMPRE que len(tags) == len(tokens). Aplica fallback rastreável
    (FALLBACK[tarefa]) quando necessário e conta quantos tokens foram corrigidos.

    Lógica:
    1. Extrai o array com extrair_array.
    2. Se arr is None OU len(arr) != len(tokens):
       -> tags = [FALLBACK[tarefa]] * len(tokens), n_fallback = len(tokens).
    3. Caso contrário, para cada posição:
       - Se tag_valida(tarefa, arr[i]): usa arr[i].
       - Senão: usa FALLBACK[tarefa] e incrementa n_fallback.

    Args:
        tarefa:       "ner" ou "upos".
        tokens:       lista de tokens da sentença (vinda do loader).
        resposta_crua: string JSON retornada pelo campo "response" do Ollama.

    Returns:
        Tupla (tags, n_fallback):
        - tags: lista de tags alinhada; len(tags) == len(tokens) SEMPRE.
        - n_fallback: número de tokens que receberam o fallback.
    """
    fallback = FALLBACK[tarefa]
    n_tokens = len(tokens)

    arr = extrair_array(resposta_crua)

    # Array inválido (None) ou comprimento errado: fallback total.
    if arr is None or len(arr) != n_tokens:
        return [fallback] * n_tokens, n_tokens

    # Validar token a token.
    tags: list[str] = []
    n_fallback = 0
    for i in range(n_tokens):
        if tag_valida(tarefa, arr[i]):
            tags.append(arr[i])
        else:
            tags.append(fallback)
            n_fallback += 1

    return tags, n_fallback
