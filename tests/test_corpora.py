"""Smoke tests para src/io/corpora.py contra os arquivos reais.

Roda contra os datasets em datasets/base_mapeada/ — execução a partir da raiz do projeto.
Usa: python -m pytest tests/test_corpora.py

Importações via: from src.io.corpora import ...
"""
import pytest

from src.io.corpora import carregar_gmb, carregar_conllu, Sentenca

# ---------------------------------------------------------------------------
# GMB (NER, IOB)
# ---------------------------------------------------------------------------

def test_gmb_contagem():
    """Contagem correta do dataset completo e do subconjunto NER."""
    assert len(carregar_gmb()) == 2999
    assert len(carregar_gmb(limite=150)) == 150


def test_gmb_primeira_sentenca():
    """Id e pares iniciais conhecidos da primeira sentença GMB."""
    sentencas = carregar_gmb(limite=1)
    s = sentencas[0]
    assert s.sentenca_id == "1.0"
    assert s.pares[0] == ("Thousands", "O")
    assert s.pares[1] == ("of", "O")
    assert s.pares[2] == ("demonstrators", "O")
    assert s.pares[3] == ("have", "O")


def test_gmb_encoding():
    """Leitura completa não levanta UnicodeDecodeError — confirma encoding latin-1."""
    # Basta completar sem exceção; o arquivo tem caracteres 0x85 que quebram em UTF-8.
    sentencas = carregar_gmb()
    assert len(sentencas) > 0


# ---------------------------------------------------------------------------
# CoNLL-U (POS/UPOS)
# ---------------------------------------------------------------------------

def test_conllu_contagem():
    """Arquivo de teste Bosque tem exatamente 1167 sentenças."""
    assert len(carregar_conllu()) == 1167


def test_conllu_primeira_sentenca():
    """Primeiros dois pares conhecidos da primeira sentença do Bosque."""
    sentencas = carregar_conllu(limite=1)
    pares = sentencas[0].pares
    assert pares[0] == ("Folha", "PROPN"), f"Par[0] errado: {pares[0]}"
    assert pares[1] == ("--", "PUNCT"), f"Par[1] errado: {pares[1]}"


def test_conllu_pula_multiword():
    """Nenhum token da primeira sentença deve ter UPOS fora do conjunto fechado UD.

    IDs de multiword (ex. '8-9') e empty-node (ex. '8.1') têm '_' como UPOS,
    que não pertence ao conjunto UD. Se o filtro funcionar, todos os UPOS são válidos.
    """
    tags_ud_validas = {
        "ADJ", "ADP", "ADV", "AUX", "CCONJ", "DET", "INTJ",
        "NOUN", "NUM", "PART", "PRON", "PROPN", "PUNCT",
        "SCONJ", "SYM", "VERB", "X",
    }
    sentencas = carregar_conllu(limite=1)
    for token, upos in sentencas[0].pares:
        assert upos in tags_ud_validas, (
            f"UPOS inválida '{upos}' para token '{token}' — "
            f"possível multiword/empty-node não filtrado"
        )
