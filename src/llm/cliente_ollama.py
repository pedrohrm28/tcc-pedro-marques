"""src/llm/cliente_ollama.py — Cliente HTTP do Ollama (/api/generate) com options reprodutíveis.

Monta chamadas ao Ollama com temperature=0, seed=42, keep_alive=-1 e format="json"
para garantir reprodutibilidade (D-05 do CONTEXT.md). Captura métricas de tempo/velocidade
(D-08): eval_count, eval_duration, load_duration, total_duration.

Usa requests (já presente em requirements.txt) — não adiciona a dependência 'ollama'.

Parte do núcleo puro e mockável do runner LLM (Fase 3, plano 03-01).
"""
from __future__ import annotations

from dataclasses import dataclass

import requests

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------
OLLAMA_URL: str = "http://localhost:11434/api/generate"

# Schema de saída estruturada (Ollama structured outputs).
# Forçar `format="json"` puro fazia cada modelo inventar um schema diferente
# (qwen: {"tokens":[[tok,tag],...]}, llama3.2: {tag:tok invertido}, llama3.1: só 1 token),
# quebrando o parser e zerando os resultados. Um schema explícito (objeto com `tags` =
# array de strings) faz os 3 modelos devolverem o MESMO formato correto. (Fix gap 03.)
FORMATO_TAGS: dict = {
    "type": "object",
    "properties": {"tags": {"type": "array", "items": {"type": "string"}}},
    "required": ["tags"],
}


# ---------------------------------------------------------------------------
# Dataclass de resposta (inclui métricas do Ollama para tok/s)
# ---------------------------------------------------------------------------
@dataclass
class Resposta:
    """Resposta do Ollama com texto decodificado e métricas de inferência.

    Campos:
        texto:             conteúdo do campo "response" (string JSON de tags).
        eval_count:        número de tokens gerados.
        eval_duration_ns:  tempo de geração em nanosegundos.
        load_duration_ns:  tempo de carregamento do modelo em nanosegundos.
        total_duration_ns: tempo total da chamada em nanosegundos.
    """

    texto: str
    eval_count: int
    eval_duration_ns: int
    load_duration_ns: int
    total_duration_ns: int


# ---------------------------------------------------------------------------
# Funções públicas
# ---------------------------------------------------------------------------

def gerar(
    modelo: str,
    prompt: str,
    num_predict: int | None = None,
    url: str = OLLAMA_URL,
    timeout: int = 600,
) -> Resposta:
    """Envia um prompt ao Ollama e retorna a resposta com métricas.

    Monta o corpo da requisição com as options reprodutíveis obrigatórias:
    temperature=0, seed=42, keep_alive=-1, format="json" (D-05/D-07/D-03).

    O parâmetro num_predict (opcional) define um teto de tokens gerados, útil para
    evitar respostas excessivamente longas sem afetar o alinhamento.

    Args:
        modelo:      nome do modelo Ollama (ex "llama3.1:8b", "qwen2.5:3b").
        prompt:      texto do prompt montado por montar_prompt().
        num_predict: teto de tokens de saída (opcional; None = sem limite explícito).
        url:         endpoint do Ollama (default: http://localhost:11434/api/generate).
        timeout:     timeout da requisição HTTP em segundos (default: 600).

    Returns:
        Resposta com texto e métricas de inferência.

    Raises:
        requests.HTTPError: se o servidor retornar status de erro (raise_for_status).
        requests.ConnectionError: se o Ollama não estiver acessível.
        requests.Timeout: se a requisição exceder o timeout.
    """
    options: dict = {
        "temperature": 0,
        "seed": 42,
    }
    if num_predict is not None:
        options["num_predict"] = num_predict

    corpo: dict = {
        "model": modelo,
        "prompt": prompt,
        "stream": False,
        "format": FORMATO_TAGS,  # schema estruturado: {"tags": [str, ...]} (fix gap 03)
        "keep_alive": -1,
        "options": options,
    }

    resp = requests.post(url, json=corpo, timeout=timeout)
    resp.raise_for_status()

    data = resp.json()
    return Resposta(
        texto=data["response"],
        eval_count=data.get("eval_count", 0),
        eval_duration_ns=data.get("eval_duration", 0),
        load_duration_ns=data.get("load_duration", 0),
        total_duration_ns=data.get("total_duration", 0),
    )


def tok_por_seg(r: Resposta) -> float:
    """Calcula tokens por segundo a partir das métricas do Ollama.

    Formula: eval_count / (eval_duration_ns / 1e9).
    Retorna 0.0 se eval_duration_ns for 0 (evita divisão por zero).

    Args:
        r: Resposta retornada por gerar().

    Returns:
        Velocidade de geração em tokens por segundo.
    """
    if r.eval_duration_ns <= 0:
        return 0.0
    return r.eval_count / (r.eval_duration_ns / 1e9)
