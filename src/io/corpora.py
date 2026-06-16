"""Loaders de corpora gold para o comparativo de NER/POS.

GMB_dataset.txt -> sentenças de (token, tag IOB) para NER (inglês).
pt_bosque-ud-*.conllu -> sentenças de (token, UPOS) para POS (português).

Uso típico:
    from src.io.corpora import carregar_gmb, carregar_conllu, Sentenca

    # NER: subconjunto de 150 sentenças
    sentencas_ner = carregar_gmb(limite=150)

    # POS: todas as 1167 sentenças do arquivo de teste
    sentencas_pos = carregar_conllu(limite=1167)
"""
from __future__ import annotations

from dataclasses import dataclass

# Uma sentença é uma lista de pares (token, tag).
# A tag é IOB no GMB (ex. 'O', 'B-geo', 'I-per') e UPOS no Bosque (ex. 'NOUN', 'VERB').
Par = tuple[str, str]


@dataclass(frozen=True)
class Sentenca:
    sentenca_id: str   # id estável da sentença (ex '1.0' no GMB, 'CF756-1' no Bosque)
    pares: list[Par]   # lista de (token, tag) na ordem do texto


def carregar_gmb(
    caminho: str = "datasets/base_mapeada/GMB_dataset.txt",
    limite: int | None = None,
) -> list[Sentenca]:
    """Lê GMB_dataset.txt e retorna sentenças de (token, tag IOB).

    Args:
        caminho: Caminho para o arquivo GMB_dataset.txt (encoding latin-1).
        limite:  Número máximo de sentenças a retornar (first-N em ordem estável).
                 None = todas (2999 sentenças no dataset completo).
                 Para NER, usar limite=150.

    Returns:
        Lista de Sentenca com sentenca_id = id da coluna 'Sentence #' (ex '1.0').
    """
    raise NotImplementedError


def carregar_conllu(
    caminho: str = "datasets/base_mapeada/pt_bosque-ud-test.conllu",
    limite: int | None = None,
) -> list[Sentenca]:
    """Lê um arquivo CoNLL-U e retorna sentenças de (token, UPOS).

    Pula comentários ('#'), IDs de multiword (contêm '-') e empty-node (contêm '.').
    Usa apenas colunas ID, FORM e UPOS.

    Args:
        caminho: Caminho para o arquivo .conllu (encoding UTF-8).
        limite:  Número máximo de sentenças a retornar (first-N em ordem estável).
                 None = todas (1167 sentenças no arquivo de teste do Bosque).
                 Para POS, usar limite=1167 (= arquivo inteiro).

    Returns:
        Lista de Sentenca com sentenca_id extraído da linha '# sent_id = ...'
        ou índice sequencial 1-based como fallback.
    """
    raise NotImplementedError
