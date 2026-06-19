"""Extrator das 25 features do CRF para texto NER novo (CoNLL-2003) — Fase 5.

Reproduz exatamente as features do `ner.csv` (notebook Kaggle) para sentenças que NÃO
estão no ner.csv, permitindo o CRF treinado predizer sobre a base nova.

Features por token (mesmos nomes do header do ner.csv, exceto sentence_idx/tag):
  word, lemma, pos, shape  +  prev-*, prev-prev-*, next-*, next-next-*  +  prev-iob, prev-prev-iob

- pos: vem do próprio CoNLL-2003 (coluna POS) — não re-taggeia.
- lemma: SnowballStemmer('english') — verificado: bate com os lemas do ner.csv.
- shape: regras que reproduzem as 11 categorias do ner.csv.
- prev-iob / prev-prev-iob: preenchidos SEQUENCIALMENTE durante a predição (predição
  anterior do próprio CRF), não com o gold. Uso realista (decisão Fase 5). Início = __START__.

Bordas usam os sentinelas do ner.csv: __START1__/__START2__ e __END1__/__END2__.
"""
from __future__ import annotations

from nltk.stem import SnowballStemmer

_STEM = SnowballStemmer("english")

START1, START2 = "__START1__", "__START2__"
END1, END2 = "__END1__", "__END2__"


def _shape(token: str) -> str:
    """Reproduz a categoria 'shape' do ner.csv (11 categorias)."""
    if not token:
        return "other"
    if all(not c.isalnum() for c in token):
        return "punct"
    # número (dígitos, com separadores , . e sinais)
    sem_sep = token.replace(",", "").replace(".", "").replace("-", "").replace("/", "")
    if sem_sep.isdigit():
        return "number"
    if "-" in token and any(c.isalpha() for c in token):
        return "contains-hyphen"
    if token.endswith(".") and len(token) > 1:
        # abreviação: maiúsculas + ponto (ex "U.S.") senão ending-dot
        nucleo = token.rstrip(".")
        if nucleo.isupper() and len(nucleo) <= 4:
            return "abbreviation"
        return "ending-dot"
    if token.isupper() and len(token) > 1:
        return "uppercase"
    if token[0].isupper() and token[1:].islower():
        return "capitalized"
    if token.islower():
        return "lowercase"
    # camelcase: minúscula seguida de maiúscula
    if any(token[i].islower() and token[i + 1].isupper() for i in range(len(token) - 1)):
        return "camelcase"
    if token[0].islower():
        return "lowercase"
    return "mixedcase"


def _lemma(token: str) -> str:
    return _STEM.stem(token)


def construir_features_sentenca(tokens: list[str], pos: list[str]) -> list[dict]:
    """Monta a lista de dicts de features (uma por token) para uma sentença.

    NÃO preenche prev-iob/prev-prev-iob com valores reais aqui — coloca placeholders
    __START__ que devem ser sobrescritos pela decodificação sequencial (predizer_sequencial).

    Args:
        tokens: tokens de superfície da sentença.
        pos:    POS tag de cada token (do CoNLL-2003), mesma ordem.

    Returns:
        Lista de dicts de features (chaves = nomes do ner.csv, exceto sentence_idx/tag).
    """
    n = len(tokens)
    lemmas = [_lemma(t) for t in tokens]
    shapes = [_shape(t) for t in tokens]

    def w(i):  # word com sentinela de borda
        if i < 0:
            return START1 if i == -1 else START2
        if i >= n:
            return END1 if i == n else END2
        return tokens[i]

    def p(i):  # pos
        if i < 0:
            return START1 if i == -1 else START2
        if i >= n:
            return END1 if i == n else END2
        return pos[i]

    def lm(i):
        if i < 0:
            return "__start1__" if i == -1 else "__start2__"
        if i >= n:
            return "__end1__" if i == n else "__end2__"
        return lemmas[i]

    def sh(i):
        if i < 0 or i >= n:
            return "wildcard"
        return shapes[i]

    feats_list: list[dict] = []
    for i in range(n):
        feats = {
            "word": w(i),
            "lemma": lm(i),
            "pos": p(i),
            "shape": sh(i),
            "next-word": w(i + 1),
            "next-pos": p(i + 1),
            "next-shape": sh(i + 1),
            "next-lemma": lm(i + 1),
            "next-next-word": w(i + 2),
            "next-next-pos": p(i + 2),
            "next-next-shape": sh(i + 2),
            "next-next-lemma": lm(i + 2),
            "prev-word": w(i - 1),
            "prev-pos": p(i - 1),
            "prev-shape": sh(i - 1),
            "prev-lemma": lm(i - 1),
            "prev-prev-word": w(i - 2),
            "prev-prev-pos": p(i - 2),
            "prev-prev-shape": sh(i - 2),
            "prev-prev-lemma": lm(i - 2),
            # iob preenchido sequencialmente (placeholder por enquanto)
            "prev-iob": START1 if i == 0 else "__PENDENTE__",
            "prev-prev-iob": START2 if i <= 1 else "__PENDENTE__",
        }
        feats_list.append(feats)
    return feats_list


def predizer_sequencial(crf, tokens: list[str], pos: list[str]) -> list[str]:
    """Prediz tags IOB token-a-token, preenchendo prev-iob com a PREDIÇÃO anterior (realista).

    Decodificação sequencial: para cada token i, atualiza prev-iob/prev-prev-iob com as tags
    já preditas (não com o gold) antes de chamar o CRF. Reproduz o uso real do modelo.

    Args:
        crf:    modelo sklearn-crfsuite treinado.
        tokens: tokens da sentença.
        pos:    POS de cada token.

    Returns:
        Lista de tags IOB preditas (len == len(tokens)).
    """
    feats = construir_features_sentenca(tokens, pos)
    preditas: list[str] = []
    for i, f in enumerate(feats):
        f["prev-iob"] = START1 if i == 0 else preditas[i - 1]
        f["prev-prev-iob"] = START2 if i <= 1 else preditas[i - 2]
        # CRF prediz 1 token por vez usando a sequência [f] (features já contextualizadas)
        tag = crf.predict_single([f])[0]
        preditas.append(tag)
    return preditas
