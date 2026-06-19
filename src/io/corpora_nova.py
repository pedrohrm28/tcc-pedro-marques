"""Loaders da BASE NOVA (fora de domínio) — Fase 5.

- CoNLL-2003 (eng.testb) -> NER inglês (token, POS, tag IOB). Domínio: notícias Reuters.
- UD_Portuguese-GSD (pt_gsd-ud-test.conllu) -> UPOS português. Domínio: web/Google (≠ Bosque).

O UPOS reusa `carregar_conllu` de corpora.py (formato CoNLL-U idêntico). Este módulo
adiciona só o loader do CoNLL-2003, cujo formato é diferente (colunas separadas por espaço).

Conversão IOB1 -> IOB2: o CoNLL-2003 usa IOB1 (só `I-` no início; `B-` apenas para separar
duas entidades adjacentes do mesmo tipo). O resto do projeto usa IOB2 (sempre `B-` no início
de entidade). Normalizamos para IOB2 para casar com o esquema dos modelos.

Cada Sentenca também carrega os POS tags (para alimentar o extrator de features do CRF).
"""
from __future__ import annotations

from dataclasses import dataclass

from src.io.corpora import Sentenca  # reusa o dataclass (sentenca_id, pares[(token,tag)])


@dataclass(frozen=True)
class SentencaPos:
    """Sentença do CoNLL-2003 com tags NER (IOB2) E POS, para o extrator de features do CRF."""
    sentenca_id: str
    pares: list[tuple[str, str]]   # [(token, tag_IOB2_gold), ...]
    pos: list[str]                 # POS tag de cada token (mesma ordem dos pares)


def _iob1_para_iob2(tags: list[str]) -> list[str]:
    """Converte uma sequência de tags IOB1 para IOB2.

    IOB1: token recebe `I-T` por padrão; `B-T` só quando segue OUTRA entidade do mesmo tipo.
    IOB2: o PRIMEIRO token de toda entidade recebe `B-T`; os seguintes `I-T`.

    Regra: um `I-T` vira `B-T` se o token anterior NÃO faz parte da mesma entidade T
    (anterior é `O`, ou de tipo diferente, ou é o começo da sentença).
    """
    out: list[str] = []
    for i, tag in enumerate(tags):
        if tag == "O" or not tag.startswith(("I-", "B-")):
            out.append("O" if tag == "O" else tag)
            continue
        tipo = tag[2:]
        ant = tags[i - 1] if i > 0 else "O"
        ant_tipo = ant[2:] if ant.startswith(("I-", "B-")) else None
        if tag.startswith("I-") and ant_tipo == tipo:
            out.append(tag)            # continuação legítima
        else:
            out.append("B-" + tipo)    # início de entidade -> B-
    return out


def carregar_conll2003(
    caminho: str = "datasets/base_nova/eng.testb",
    limite: int | None = None,
) -> list[SentencaPos]:
    """Lê o CoNLL-2003 (eng.testb) e retorna sentenças com (token, tag IOB2) + POS.

    Formato de cada linha: `TOKEN POS CHUNK NER` (separado por espaço).
    Sentenças separadas por linha em branco. Linhas `-DOCSTART-` são descartadas.
    A coluna NER (IOB1) é normalizada para IOB2.

    Args:
        caminho: caminho do eng.testb.
        limite:  nº máximo de sentenças (first-N em ordem). None = todas.

    Returns:
        Lista de SentencaPos. sentenca_id = "c2003-{i}" (1-based, ordem de aparição).
    """
    sentencas: list[SentencaPos] = []
    tokens_cur: list[str] = []
    tags_cur: list[str] = []
    pos_cur: list[str] = []
    idx = 0

    def _fechar():
        nonlocal tokens_cur, tags_cur, pos_cur, idx
        if tokens_cur:
            idx += 1
            tags_iob2 = _iob1_para_iob2(tags_cur)
            sentencas.append(SentencaPos(
                sentenca_id=f"c2003-{idx}",
                pares=list(zip(tokens_cur, tags_iob2)),
                pos=list(pos_cur),
            ))
        tokens_cur, tags_cur, pos_cur = [], [], []

    with open(caminho, encoding="utf-8") as f:
        for linha in f:
            linha = linha.rstrip("\n")
            if linha == "":
                _fechar()
                if limite is not None and len(sentencas) >= limite:
                    return sentencas[:limite]
                continue
            if linha.startswith("-DOCSTART-"):
                continue
            cols = linha.split()
            if len(cols) < 4:
                continue
            tokens_cur.append(cols[0])
            pos_cur.append(cols[1])
            tags_cur.append(cols[3])

    _fechar()
    if limite is not None:
        return sentencas[:limite]
    return sentencas
