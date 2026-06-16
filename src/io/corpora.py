"""Loaders de corpora gold para o comparativo de NER/POS.

GMB_dataset.txt -> sentenças de (token, tag IOB) para NER (inglês).
pt_bosque-ud-*.conllu -> sentenças de (token, UPOS) para POS (português).

Uso típico:
    from src.io.corpora import carregar_gmb, carregar_conllu, Sentenca

    # NER: subconjunto de 1167 sentenças (alinhado ao N do POS; ver Decisions Log)
    sentencas_ner = carregar_gmb(limite=1167)

    # POS: todas as 1167 sentenças do arquivo de teste
    sentencas_pos = carregar_conllu(limite=1167)
"""
from __future__ import annotations

import csv
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

    O arquivo é TSV (tab-separated) com encoding latin-1 (ISO-8859-1).
    Header: ['', 'Sentence #', 'Word', 'POS', 'Tag'] — ignorado.
    Agrupamento pela coluna 'Sentence #' (col1), mantendo ordem de aparição.

    Args:
        caminho: Caminho para o arquivo GMB_dataset.txt (encoding latin-1).
        limite:  Número máximo de sentenças a retornar (first-N em ordem estável).
                 None = todas (2999 sentenças no dataset completo).
                 Para NER, usar limite=1167 (alinhado ao N do POS; ver Decisions Log).

    Returns:
        Lista de Sentenca com sentenca_id = valor da coluna 'Sentence #' (ex '1.0').
    """
    sentencas: list[Sentenca] = []
    # Mapeia sentenca_id -> lista de pares (preserva ordem de inserção, Python 3.7+)
    grupos: dict[str, list[Par]] = {}
    # Mantém ordem estável de primeira aparição de cada id
    ordem: list[str] = []

    with open(caminho, encoding="latin-1", newline="") as f:
        leitor = csv.reader(f, delimiter="\t")
        # Pular o header
        next(leitor, None)
        for row in leitor:
            if len(row) < 5:
                continue
            sentenca_id = row[1]
            token = row[2]
            tag = row[4]
            if sentenca_id not in grupos:
                grupos[sentenca_id] = []
                ordem.append(sentenca_id)
            grupos[sentenca_id].append((token, tag))

    # Montar Sentencas na ordem de aparição
    for sid in ordem:
        sentencas.append(Sentenca(sentenca_id=sid, pares=grupos[sid]))

    if limite is not None:
        sentencas = sentencas[:limite]

    return sentencas


def carregar_conllu(
    caminho: str = "datasets/base_mapeada/pt_bosque-ud-test.conllu",
    limite: int | None = None,
) -> list[Sentenca]:
    """Lê um arquivo CoNLL-U e retorna sentenças de (token, UPOS).

    Pula comentários ('#'), IDs de multiword (contêm '-') e empty-node (contêm '.').
    Usa apenas colunas ID (col0), FORM (col1) e UPOS (col3).

    Args:
        caminho: Caminho para o arquivo .conllu (encoding UTF-8).
        limite:  Número máximo de sentenças a retornar (first-N em ordem estável).
                 None = todas (1167 sentenças no arquivo de teste do Bosque).
                 Para POS, usar limite=1167 (= arquivo inteiro).

    Returns:
        Lista de Sentenca com sentenca_id extraído de '# sent_id = ...'
        ou índice sequencial 1-based como fallback.
    """
    sentencas: list[Sentenca] = []
    pares_correntes: list[Par] = []
    sent_id_corrente: str | None = None
    indice = 0  # índice sequencial 1-based para fallback

    with open(caminho, encoding="utf-8") as f:
        for linha in f:
            linha = linha.rstrip("\n")

            # Linha em branco: fecha a sentença atual
            if linha == "":
                if pares_correntes:
                    indice += 1
                    sid = sent_id_corrente if sent_id_corrente else str(indice)
                    sentencas.append(Sentenca(sentenca_id=sid, pares=pares_correntes))
                    pares_correntes = []
                    sent_id_corrente = None
                    if limite is not None and len(sentencas) >= limite:
                        break
                continue

            # Linhas de comentário
            if linha.startswith("#"):
                # Capturar sent_id se presente
                if linha.startswith("# sent_id = "):
                    sent_id_corrente = linha[len("# sent_id = "):].strip()
                continue

            # Linha de token
            cols = linha.split("\t")
            if len(cols) < 4:
                continue

            token_id = cols[0]
            # Pular IDs de multiword (contêm '-') e empty-node (contêm '.')
            if "-" in token_id or "." in token_id:
                continue

            form = cols[1]
            upos = cols[3]
            pares_correntes.append((form, upos))

    # Fechar última sentença se arquivo não termina com linha em branco
    if pares_correntes and (limite is None or len(sentencas) < limite):
        indice += 1
        sid = sent_id_corrente if sent_id_corrente else str(indice)
        sentencas.append(Sentenca(sentenca_id=sid, pares=pares_correntes))

    return sentencas
