"""src/llm/prompts.py — Prompts versionados de NER (IOB) e UPOS para o runner LLM.

Os textos de instrução são fixos no repositório (D-05 do CONTEXT.md: prompts versionados).
A função montar_prompt embute a lista de tokens já tokenizada (vinda do loader), de modo que
o LLM não re-tokeniza — garante alinhamento 1:1 com o gold (D-03).

Parte do núcleo puro e mockável do runner LLM (Fase 3, plano 03-01).
"""
from __future__ import annotations

import json

from run_regras import UPOS_VALIDOS

# ---------------------------------------------------------------------------
# Instrução versionada para NER (IOB, inglês)
# ---------------------------------------------------------------------------
INSTRUCAO_NER: str = """\
You are a Named Entity Recognition (NER) tagger.

Your task: given a list of tokens (already tokenized), label each token with its IOB tag.
Valid IOB tags: "O" (outside any entity), "B-<type>" (beginning of entity), "I-<type>" (inside entity).
Common entity types: geo, org, per, gpe, tim, art, nat, eve.

RULES:
- Do NOT re-tokenize or split any token.
- Return ONLY a valid JSON array of tags, one tag per token, in the SAME order as the input tokens.
- The output array MUST have EXACTLY the same number of elements as the input list.
- Do NOT add any commentary, explanation, or extra text outside the JSON array.
- Example input: ["London", "is", "a", "city"]
- Example output: ["B-geo", "O", "O", "O"]
"""

# ---------------------------------------------------------------------------
# Instrução versionada para UPOS (português, 17 UPOS do UD)
# ---------------------------------------------------------------------------
_UPOS_LISTA: str = ", ".join(sorted(UPOS_VALIDOS))

INSTRUCAO_UPOS: str = f"""\
Você é um anotador de partes do discurso (POS tagger) para o português.

Sua tarefa: dada uma lista de tokens (já tokenizados), rotule cada token com a sua tag UPOS (Universal POS).
Tags UPOS válidas (exatamente estas 17): {_UPOS_LISTA}

REGRAS:
- NÃO re-tokenize nem divida nenhum token.
- Retorne APENAS um array JSON válido de tags, uma por token, NA MESMA ORDEM da lista de entrada.
- O array de saída DEVE ter EXATAMENTE o mesmo número de elementos que a lista de entrada.
- NÃO adicione comentários, explicações ou qualquer texto fora do array JSON.
- Exemplo de entrada: ["O", "gato", "corre"]
- Exemplo de saída: ["DET", "NOUN", "VERB"]
"""


def montar_prompt(tarefa: str, tokens: list[str]) -> str:
    """Monta o prompt final para envio ao LLM, embutindo os tokens já tokenizados.

    Concatena a instrução versionada da tarefa com a lista de tokens serializada como JSON.
    O prompt deixa explícito que o array de saída deve ter len(tokens) elementos (D-03).

    Args:
        tarefa:  "ner" ou "upos".
        tokens:  lista de tokens da sentença (vinda do loader — NÃO re-tokenizar).

    Returns:
        String do prompt completo pronto para envio ao Ollama.
    """
    if tarefa == "ner":
        instrucao = INSTRUCAO_NER
    elif tarefa == "upos":
        instrucao = INSTRUCAO_UPOS
    else:
        raise ValueError(f"tarefa inválida: {tarefa!r} (use 'ner' ou 'upos')")

    tokens_json = json.dumps(tokens, ensure_ascii=False)
    n = len(tokens)

    prompt = (
        f"{instrucao}\n"
        f"Input tokens ({n} tokens): {tokens_json}\n"
        f"Output JSON array ({n} elements):"
    )
    return prompt
