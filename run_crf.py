"""Baseline tradicional de NER: CRF (sklearn-crfsuite) sobre as features do ner.csv.

Pipeline:
  1. Lê `datasets/base_mapeada/ner.csv` (latin-1, 25 colunas) e agrupa por `sentence_idx`,
     filtrando a linha malformada (header vazado) e deduplicando tokens repetidos.
  2. Treina um CRF nas sentenças GMB-mapeadas FORA do conjunto de teste (ids 1168..2999),
     evitando vazamento treino/teste. O modelo é persistido em `modelos/crf_ner.pkl`
     e reutilizado se já existir (flag --retrain força re-treino).
  3. Prediz sobre as 1167 sentenças de teste (carregar_gmb(limite=1167)) e emite o contrato
     comum `.jsonl` (tarefa="ner", modelo="crf") em `resultados/base_mapeada/crf/ner.jsonl`,
     alinhado token-a-token com o gold.

REQ-02. Fase 2 — baselines tradicionais.
"""
from __future__ import annotations

import argparse
import csv
import os
from typing import Optional

from src.io.contrato import Registro, caminho_resultado, escrever_jsonl
from src.io.corpora import carregar_gmb

# --- Constantes ------------------------------------------------------------

NER_CSV_PADRAO = "datasets/base_mapeada/ner.csv"
MODELO_PADRAO = "modelos/crf_ner.pkl"
LIMITE_PADRAO = 1167          # conjunto de teste oficial da fase
SID_TREINO_MAX = 2999         # último id GMB disponível

# Colunas que NÃO entram como feature do CRF.
# A coluna row-index (índice 0, header vazio) é tratada à parte na leitura.
COLUNAS_EXCLUIDAS = {"sentence_idx", "tag"}


# --- Task 1: carregamento / mapeamento puro --------------------------------


def _deduplicar(pares: list) -> list:
    """Remove o artefato de duplicação do ner.csv.

    Muitas sentenças têm seus tokens repetidos exatamente (primeira metade ==
    segunda metade). Se for o caso, retorna apenas a primeira metade; caso
    contrário, retorna a lista intacta.

    Funciona tanto para listas de tuplas (token, tag) quanto para listas de
    dicts de features.
    """
    n = len(pares)
    if n % 2 == 0 and n > 0 and pares[: n // 2] == pares[n // 2 :]:
        return pares[: n // 2]
    return pares


def _sid_numerico(valor: str) -> bool:
    """True se `valor` converte para float (ex '1', '1.0'); descarta header vazado."""
    try:
        float(valor)
        return True
    except (ValueError, TypeError):
        return False


def carregar_features_ner(caminho: str = NER_CSV_PADRAO) -> dict[str, list[dict]]:
    """Lê ner.csv (latin-1) e agrupa por sentence_idx em dicts de features.

    - Filtra linhas cujo `sentence_idx` não é numérico (descarta a linha 'prev-lemma').
    - Aplica DEDUPE por sentença (primeira metade se exatamente duplicada).
    - Cada token vira um dict de features (todas as colunas exceto sentence_idx e tag,
      e a coluna row-index 0), mais as chaves internas:
        "__tag__"  = label IOB (coluna `tag`)
        "__word__" = token de superfície (coluna `word`)

    Returns:
        {sentence_idx_str: [ {features..., "__tag__":..., "__word__":...}, ... ]}
        na ordem de aparição dos tokens dentro de cada sentença.
    """
    grupos: dict[str, list[dict]] = {}
    ordem: list[str] = []

    with open(caminho, encoding="latin-1", newline="") as f:
        leitor = csv.reader(f)
        header = next(leitor, None)
        if header is None:
            return {}

        # Índices das colunas relevantes (header[0] é a coluna row-index, vazia).
        idx_sentence = header.index("sentence_idx")
        idx_tag = header.index("tag")
        idx_word = header.index("word")
        # Colunas que entram como feature: tudo exceto índice 0, sentence_idx e tag.
        idx_features = [
            i
            for i, nome in enumerate(header)
            if i != 0 and nome not in COLUNAS_EXCLUIDAS
        ]

        for row in leitor:
            if len(row) != len(header):
                continue
            sid = row[idx_sentence]
            if not _sid_numerico(sid):
                continue
            feats = {header[i]: row[i] for i in idx_features}
            feats["__tag__"] = row[idx_tag]
            feats["__word__"] = row[idx_word]
            if sid not in grupos:
                grupos[sid] = []
                ordem.append(sid)
            grupos[sid].append(feats)

    # Aplicar dedupe por sentença, comparando pelos (word, tag) para robustez.
    mapa: dict[str, list[dict]] = {}
    for sid in ordem:
        tokens = grupos[sid]
        n = len(tokens)
        if (
            n % 2 == 0
            and n > 0
            and [(t["__word__"], t["__tag__"]) for t in tokens[: n // 2]]
            == [(t["__word__"], t["__tag__"]) for t in tokens[n // 2 :]]
        ):
            tokens = tokens[: n // 2]
        mapa[sid] = tokens

    return mapa


def _features_token(feats: dict) -> dict:
    """Extrai apenas as features (descarta chaves internas __tag__/__word__)."""
    return {k: v for k, v in feats.items() if not k.startswith("__")}


def features_e_labels_para_sids(
    mapa: dict[str, list[dict]], sids: list[str]
) -> tuple[list[list[dict]], list[list[str]], list[list[str]]]:
    """Monta X (features), y (tags) e tokens (palavras) na ordem de `sids`.

    sids ausentes do mapa são ignorados silenciosamente (não há features para eles).

    Returns:
        (X, y, tokens) — listas paralelas; X[i]/y[i]/tokens[i] correspondem a sids[i].
    """
    X: list[list[dict]] = []
    y: list[list[str]] = []
    tokens: list[list[str]] = []
    for sid in sids:
        seq = mapa.get(sid)
        if not seq:
            continue
        X.append([_features_token(t) for t in seq])
        y.append([t["__tag__"] for t in seq])
        tokens.append([t["__word__"] for t in seq])
    return X, y, tokens


# --- Task 2: treino + persistência -----------------------------------------


def treinar_crf(X_train, y_train):
    """Treina um CRF (lbfgs) sobre as features-dict do ner.csv."""
    import sklearn_crfsuite

    crf = sklearn_crfsuite.CRF(
        algorithm="lbfgs",
        c1=0.1,
        c2=0.1,
        max_iterations=100,
        all_possible_transitions=True,
    )
    crf.fit(X_train, y_train)
    return crf


def carregar_ou_treinar(
    mapa: dict[str, list[dict]],
    sids_treino: list[str],
    caminho_modelo: str = MODELO_PADRAO,
    retrain: bool = False,
):
    """Carrega o CRF do disco se existir; caso contrário treina e persiste.

    Args:
        mapa          : saída de carregar_features_ner.
        sids_treino   : sentence_idx das sentenças de treino (fora do teste).
        caminho_modelo: caminho do .pkl (criado se necessário).
        retrain       : força re-treino mesmo que o .pkl exista.

    Returns:
        objeto CRF treinado.
    """
    import joblib

    if os.path.exists(caminho_modelo) and not retrain:
        print(f"[crf] carregando modelo do disco: {caminho_modelo}")
        return joblib.load(caminho_modelo)

    X_train, y_train, _ = features_e_labels_para_sids(mapa, sids_treino)
    print(f"[crf] treinando em {len(X_train)} sentenças...")
    crf = treinar_crf(X_train, y_train)

    dir_pai = os.path.dirname(caminho_modelo)
    if dir_pai:
        os.makedirs(dir_pai, exist_ok=True)
    joblib.dump(crf, caminho_modelo)
    print(f"[crf] modelo salvo em: {caminho_modelo}")
    return crf


def sids_treino_fora_do_teste(
    mapa: dict[str, list[dict]], sids_teste: set[str]
) -> list[str]:
    """Ids de treino = inteiros 1168..2999 presentes no mapa e fora do teste."""
    sids: list[str] = []
    inicio = max((int(s) for s in sids_teste), default=0) + 1
    for n in range(inicio, SID_TREINO_MAX + 1):
        s = str(n)
        if s in mapa and s not in sids_teste:
            sids.append(s)
    return sids


# --- Task 3: emissão do .jsonl alinhado ------------------------------------


def gerar_registros(crf, mapa: dict[str, list[dict]], test_sents) -> list[Registro]:
    """Prediz sobre o test set e monta os Registros alinhados ao gold.

    Para cada sentença gold `s`, usa as features do ner.csv do sid
    `str(int(float(s.sentenca_id)))` (deduplicadas) e assegura, defensivamente,
    que os tokens batem token-a-token com `s.pares` antes de emitir.
    """
    registros: list[Registro] = []
    for s in test_sents:
        sid = str(int(float(s.sentenca_id)))
        seq = mapa.get(sid)
        tokens_gold = [w for w, _ in s.pares]
        tokens_ner = [t["__word__"] for t in seq] if seq else []
        if tokens_ner != tokens_gold:
            raise RuntimeError(
                f"Desalinhamento na sentença {s.sentenca_id!r} (sid ner.csv {sid!r}): "
                f"{len(tokens_gold)} tokens gold vs {len(tokens_ner)} no ner.csv. "
                "Abortando para não emitir .jsonl desalinhado."
            )
        feats = [_features_token(t) for t in seq]
        tags = crf.predict_single(feats)
        for posicao, ((token, _gold), tag) in enumerate(zip(s.pares, tags)):
            registros.append(
                Registro(
                    tarefa="ner",
                    modelo="crf",
                    sentenca_id=s.sentenca_id,
                    posicao=posicao,
                    token=token,
                    tag_predita=tag,
                )
            )
    return registros


# --- CLI -------------------------------------------------------------------


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Treina/aplica CRF NER e emite o .jsonl do contrato.")
    parser.add_argument("--ner-csv", default=NER_CSV_PADRAO, help="Caminho do ner.csv (features).")
    parser.add_argument("--limite", type=int, default=LIMITE_PADRAO, help="Nº de sentenças de teste GMB.")
    parser.add_argument("--retrain", action="store_true", help="Força re-treino do CRF.")
    parser.add_argument("--modelo", default=MODELO_PADRAO, help="Caminho do .pkl do modelo.")
    parser.add_argument("--saida", default=None, help="Caminho do .jsonl (default: contrato).")
    args = parser.parse_args(argv)

    mapa = carregar_features_ner(args.ner_csv)
    test_sents = carregar_gmb(limite=args.limite)
    sids_teste = {str(int(float(s.sentenca_id))) for s in test_sents}
    sids_treino = sids_treino_fora_do_teste(mapa, sids_teste)

    crf = carregar_ou_treinar(mapa, sids_treino, args.modelo, retrain=args.retrain)

    registros = gerar_registros(crf, mapa, test_sents)
    saida = args.saida or caminho_resultado("base_mapeada", "crf", "ner")
    n = escrever_jsonl(saida, registros)
    print(f"[crf] {n} registros gravados em {saida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
