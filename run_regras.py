"""run_regras.py — anotação UPOS por regras (léxico + heurísticas) sobre o Bosque.

Segundo baseline tradicional (POS/UPOS, português) rodando 100% via código. REQ-03.

Pipeline determinístico:
  1. Constrói um LÉXICO (token de superfície minúsculo -> UPOS mais frequente) a partir
     APENAS do arquivo de TREINO (pt_bosque-ud-train.conllu). O conjunto de teste NUNCA
     alimenta o léxico — isso evita vazamento (T-02-04).
  2. Para cada token do conjunto de TESTE, decide a UPOS com `tag_por_regras`.
  3. Emite o contrato comum .jsonl (tarefa="upos", modelo="regras").

Toda tag retornada pertence ao conjunto fechado UPOS_VALIDOS (as 17 tags presentes no
teste do Bosque) — garante que nenhuma tag fora do esquema seja emitida (T-02-05).

Uso:
    python run_regras.py --limite 1167
    python run_regras.py --train ... --teste ... --saida ...
"""
from __future__ import annotations

import argparse
import re
from collections import Counter, defaultdict

from src.io.contrato import Registro, caminho_resultado, escrever_jsonl
from src.io.corpora import carregar_conllu

# ---------------------------------------------------------------------------
# Conjunto fechado das 17 UPOS presentes no teste do Bosque (data_facts).
# Qualquer tag emitida DEVE estar aqui.
# ---------------------------------------------------------------------------
UPOS_VALIDOS: frozenset[str] = frozenset(
    {
        "NOUN", "DET", "ADP", "PUNCT", "VERB", "PROPN", "ADJ", "ADV",
        "PRON", "SCONJ", "AUX", "CCONJ", "NUM", "SYM", "X", "INTJ",
        "PART",  # presente no esquema UD; incluída para totalizar 17 tags
    }
)

CAMINHO_TRAIN_PADRAO = "datasets/base_mapeada/pt_bosque-ud-train.conllu"
CAMINHO_TESTE_PADRAO = "datasets/base_mapeada/pt_bosque-ud-test.conllu"

# Símbolos tratados como SYM (não como pontuação comum).
_SIMBOLOS_SYM = set("%$=+<>°*&@^~|")

# Padrão numérico: dígitos com separadores opcionais (1.234,56 / 3,14 / 2010)
# e ordinais portugueses ("1º", "2ª", "3o", "10a").
_RE_NUMERO = re.compile(r"^[+\-]?\d[\d.,]*[ºªoa°]?$", re.IGNORECASE)

# Sufixos morfológicos do português -> UPOS provável.
# Ordem: do mais específico/longo para o mais curto (primeira correspondência vence).
_SUFIXOS = (
    # Advérbios
    ("mente", "ADV"),
    # Substantivos (nominalizações típicas)
    ("ções", "NOUN"),
    ("ção", "NOUN"),
    ("dades", "NOUN"),
    ("dade", "NOUN"),
    ("agem", "NOUN"),
    ("mento", "NOUN"),
    ("ismo", "NOUN"),
    ("ância", "NOUN"),
    ("ência", "NOUN"),
    # Adjetivais
    ("áveis", "ADJ"),
    ("ável", "ADJ"),
    ("íveis", "ADJ"),
    ("ível", "ADJ"),
    ("osos", "ADJ"),
    ("osas", "ADJ"),
    ("oso", "ADJ"),
    ("osa", "ADJ"),
    # Verbos no infinitivo (-ar/-er/-ir) — depois dos nominais/adjetivais
    # para não capturar "lugar", "mar" etc. de forma agressiva demais; ainda assim
    # é uma heurística fraca e fica após o léxico no pipeline.
    ("ar", "VERB"),
    ("er", "VERB"),
    ("ir", "VERB"),
)


def construir_lexico(caminho_train: str = CAMINHO_TRAIN_PADRAO) -> dict[str, str]:
    """Constrói o léxico token_lower -> UPOS mais frequente a partir do TREINO.

    Lê o arquivo de treino via carregar_conllu(caminho=caminho_train, limite=None).
    Para cada token de superfície (case-insensitive, em minúsculas), conta as UPOS
    observadas e atribui a UPOS mais frequente. Empates são resolvidos de forma
    determinística pela ordem do `Counter.most_common` (estável por inserção).

    O conjunto de teste NUNCA é lido aqui — previne vazamento (T-02-04).

    Args:
        caminho_train: caminho do arquivo .conllu de treino.

    Returns:
        dict mapeando token minúsculo -> UPOS mais frequente.
    """
    contagens: defaultdict[str, Counter] = defaultdict(Counter)
    for sentenca in carregar_conllu(caminho=caminho_train, limite=None):
        for token, upos in sentenca.pares:
            contagens[token.lower()][upos] += 1

    lexico: dict[str, str] = {}
    for token_lower, counter in contagens.items():
        # most_common(1) é determinístico: maior contagem; empate -> ordem de inserção.
        lexico[token_lower] = counter.most_common(1)[0][0]
    return lexico


def _eh_pontuacao_ou_simbolo(token: str) -> str | None:
    """Se o token for todo pontuação/símbolo, retorna 'SYM' ou 'PUNCT'; senão None."""
    if not token:
        return None
    # Todos os caracteres não são alfanuméricos (pontuação/símbolos).
    if all(not c.isalnum() for c in token):
        # Se qualquer caractere for um símbolo tipográfico (%, $, =, ...), classifica SYM.
        if any(c in _SIMBOLOS_SYM for c in token):
            return "SYM"
        return "PUNCT"
    return None


def tag_por_regras(token: str, lexico: dict[str, str]) -> str:
    """Decide a UPOS de um token por um pipeline determinístico de regras.

    Ordem de decisão:
        1. Pontuação/símbolo puro -> PUNCT (ou SYM para %,$,=,...).
        2. Padrão numérico (dígitos, separadores, ordinais "1º") -> NUM.
        3. Léxico (token minúsculo conhecido no treino) -> UPOS do léxico.
        4. Heurísticas morfológicas (sufixos do português).
        5. Maiúscula inicial (provável nome próprio) -> PROPN.
        6. Fallback final -> NOUN (tag mais frequente no teste).

    Toda tag retornada pertence a UPOS_VALIDOS (T-02-05).

    Args:
        token : token de superfície.
        lexico: mapeamento token_lower -> UPOS (de construir_lexico).

    Returns:
        UPOS prevista (∈ UPOS_VALIDOS).
    """
    # 1. Pontuação / símbolo.
    tag_pont = _eh_pontuacao_ou_simbolo(token)
    if tag_pont is not None:
        return tag_pont

    # 2. Número.
    if _RE_NUMERO.match(token):
        return "NUM"

    # 3. Léxico (prioridade sobre heurísticas).
    token_lower = token.lower()
    if token_lower in lexico:
        return lexico[token_lower]

    # 4. Heurísticas morfológicas por sufixo.
    for sufixo, upos in _SUFIXOS:
        if token_lower.endswith(sufixo) and len(token_lower) > len(sufixo):
            return upos

    # 5. Maiúscula inicial -> provável nome próprio.
    if token[:1].isupper():
        return "PROPN"

    # 6. Fallback final.
    return "NOUN"


def anotar(
    caminho_train: str = CAMINHO_TRAIN_PADRAO,
    caminho_teste: str = CAMINHO_TESTE_PADRAO,
    limite: int | None = 1167,
) -> list[Registro]:
    """Anota o conjunto de teste e retorna a lista de Registros (contrato comum)."""
    lexico = construir_lexico(caminho_train)
    sentencas = carregar_conllu(caminho=caminho_teste, limite=limite)

    registros: list[Registro] = []
    for sentenca in sentencas:
        for posicao, (token, _gold) in enumerate(sentenca.pares):
            tag = tag_por_regras(token, lexico)
            registros.append(
                Registro(
                    tarefa="upos",
                    modelo="regras",
                    sentenca_id=sentenca.sentenca_id,
                    posicao=posicao,
                    token=token,
                    tag_predita=tag,
                )
            )
    return registros


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Anotação UPOS por regras (léxico + heurísticas) sobre o Bosque."
    )
    parser.add_argument("--train", default=CAMINHO_TRAIN_PADRAO,
                        help="Arquivo .conllu de treino (fonte do léxico).")
    parser.add_argument("--teste", default=CAMINHO_TESTE_PADRAO,
                        help="Arquivo .conllu de teste (conjunto de avaliação).")
    parser.add_argument("--limite", type=int, default=1167,
                        help="Número de sentenças de teste a anotar (default 1167 = todo o teste).")
    parser.add_argument("--saida", default=None,
                        help="Caminho .jsonl de saída (default: contrato base_mapeada/regras/upos).")
    args = parser.parse_args()

    saida = args.saida or caminho_resultado("base_mapeada", "regras", "upos")
    registros = anotar(
        caminho_train=args.train,
        caminho_teste=args.teste,
        limite=args.limite,
    )
    n = escrever_jsonl(saida, registros)
    print(f"OK: {n} registros gravados em {saida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
