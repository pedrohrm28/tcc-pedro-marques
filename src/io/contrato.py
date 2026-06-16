"""Contrato de saída comum (.jsonl) emitido por todos os modelos. REQ-01."""
from __future__ import annotations
import json
import os
from dataclasses import dataclass, asdict
from typing import Iterable

TAREFAS_VALIDAS = {"ner", "upos"}


@dataclass(frozen=True)
class Registro:
    """Registro de predição de um único token.

    Campos:
        tarefa       : "ner" ou "upos"
        modelo       : ex "crf", "regras", "gpt-oss:20b", "gpt-oss:120b", ou "gold"
        sentenca_id  : id estável da sentença (ex "1.0" GMB, "CF756-1" Bosque)
        posicao      : índice 0-based do token dentro da sentença
        token        : token de superfície
        tag_predita  : IOB (ner) ou UPOS (upos)
    """

    tarefa: str          # "ner" | "upos"
    modelo: str          # "crf" | "regras" | "gpt-oss:20b" | "gpt-oss:120b" | "gold"
    sentenca_id: str
    posicao: int
    token: str
    tag_predita: str

    def __post_init__(self):
        if self.tarefa not in TAREFAS_VALIDAS:
            raise ValueError(
                f"tarefa inválida: {self.tarefa!r} (use {TAREFAS_VALIDAS})"
            )


def escrever_jsonl(caminho: str, registros: Iterable[Registro]) -> int:
    """Grava registros em formato newline-delimited JSON (UTF-8, sem ASCII-escape).

    Cria os diretórios pais automaticamente se não existirem.

    Args:
        caminho  : caminho completo do arquivo .jsonl a ser criado/sobrescrito.
        registros: iterável de Registro.

    Returns:
        Número de registros gravados.
    """
    dir_pai = os.path.dirname(caminho)
    if dir_pai:
        os.makedirs(dir_pai, exist_ok=True)
    contagem = 0
    with open(caminho, "w", encoding="utf-8") as f:
        for r in registros:
            f.write(json.dumps(asdict(r), ensure_ascii=False) + "\n")
            contagem += 1
    return contagem


def ler_jsonl(caminho: str) -> list[Registro]:
    """Lê um arquivo .jsonl e retorna a lista de Registros.

    Linhas em branco são ignoradas silenciosamente.

    Args:
        caminho: caminho do arquivo .jsonl a ser lido.

    Returns:
        Lista de Registro na mesma ordem em que foram gravados.
    """
    registros: list[Registro] = []
    with open(caminho, encoding="utf-8") as f:
        for linha in f:
            linha = linha.strip()
            if linha:
                registros.append(Registro(**json.loads(linha)))
    return registros


def caminho_resultado(base: str, modelo: str, tarefa: str) -> str:
    """Monta o caminho convencionado para um arquivo de resultados.

    Exemplo:
        caminho_resultado("base_mapeada", "gpt-oss:20b", "ner")
        → "resultados/base_mapeada/gpt-oss_20b/ner.jsonl"

    O ':' no nome do modelo é substituído por '_' para compatibilidade
    com o sistema de arquivos do Windows (que proíbe ':' em nomes de arquivo).

    Args:
        base  : "base_mapeada" ou "base_nova"
        modelo: nome do modelo (ex "crf", "gpt-oss:20b")
        tarefa: "ner" ou "upos"

    Returns:
        Caminho relativo ao diretório raiz do projeto.
    """
    modelo_sanitizado = modelo.replace(":", "_")
    return os.path.join("resultados", base, modelo_sanitizado, f"{tarefa}.jsonl")
