"""Mapeamento de esquemas NER para tipos comuns {PER, ORG, LOC, MISC} — Fase 5 (base nova).

O CRF/regras-LLMs predizem no esquema do GMB (geo, gpe, per, org, tim, art, nat, eve),
mas o gold da base nova (CoNLL-2003) usa {PER, ORG, LOC, MISC}. Para comparar de forma
justa (generalização real, não nomenclatura), normalizamos AMBOS — gold e predições —
ao conjunto comum, preservando o prefixo IOB (B-/I-) e "O".

Mapeamento confirmado (decisão Fase 5):
  GMB:  geo,gpe -> LOC | per -> PER | org -> ORG | tim,art,eve,nat -> MISC
  CoNLL-2003: PER,ORG,LOC,MISC -> iguais (já no esquema comum)
  Tipos desconhecidos -> MISC (categoria "outros")
"""
from __future__ import annotations

# tipo (lowercase) -> tipo comum
_MAPA = {
    # GMB
    "geo": "LOC",
    "gpe": "LOC",
    "per": "PER",
    "org": "ORG",
    "tim": "MISC",
    "art": "MISC",
    "eve": "MISC",
    "nat": "MISC",
    # CoNLL-2003 (já comuns; minúsculo p/ casar)
    "loc": "LOC",
    "misc": "MISC",
}

TIPOS_COMUNS = {"PER", "ORG", "LOC", "MISC"}


def mapear_tag(tag: str) -> str:
    """Normaliza uma tag IOB para o esquema comum {O, B-PER/ORG/LOC/MISC, I-...}.

    - "O" -> "O".
    - "B-<tipo>" / "I-<tipo>" -> "B-<COMUM>" / "I-<COMUM>" via _MAPA (case-insensitive).
    - Tipo não reconhecido -> MISC (mantém o prefixo).
    - Qualquer coisa fora do padrão IOB -> "O".

    Args:
        tag: tag IOB no esquema original (ex "B-geo", "I-PER", "O").

    Returns:
        Tag IOB no esquema comum (ex "B-LOC", "I-PER", "O").
    """
    if not tag or tag == "O":
        return "O"
    if len(tag) < 2 or tag[1] != "-" or tag[0] not in ("B", "I"):
        return "O"
    prefixo = tag[0]
    tipo = tag[2:].lower()
    comum = _MAPA.get(tipo, "MISC")
    return f"{prefixo}-{comum}"


def mapear_sequencia(tags: list[str]) -> list[str]:
    """Aplica mapear_tag a uma lista de tags."""
    return [mapear_tag(t) for t in tags]
