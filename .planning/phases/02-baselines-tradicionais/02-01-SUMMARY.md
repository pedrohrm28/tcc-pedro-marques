---
phase: 02-baselines-tradicionais
plan: 01
subsystem: ml-baseline
tags: [crf, sklearn-crfsuite, ner, iob, joblib, jsonl]

# Dependency graph
requires:
  - phase: 01-foundation
    provides: "contrato .jsonl (Registro, escrever_jsonl, caminho_resultado), loader carregar_gmb"
provides:
  - "run_crf.py: treino+predição CRF emitindo o contrato .jsonl (tarefa=ner, modelo=crf)"
  - "modelos/crf_ner.pkl: modelo CRF serializado (cache, gitignored)"
  - "resultados/base_mapeada/crf/ner.jsonl: 25857 predições NER IOB das 1167 sentenças de teste"
  - "carregar_features_ner / features_e_labels_para_sids: parsing saneado do ner.csv"
affects: [03-llm, 05-base-nova, agregador-comparativo]

# Tech tracking
tech-stack:
  added: [sklearn-crfsuite, python-crfsuite, joblib]
  patterns:
    - "Saneamento de corpus na leitura: filtro de linha malformada + dedupe de duplicação"
    - "Cache de modelo em disco (joblib) com flag --retrain"
    - "Asserção defensiva de alinhamento token-a-token antes de emitir o contrato"

key-files:
  created:
    - run_crf.py
    - tests/test_run_crf.py
    - modelos/crf_ner.pkl
    - resultados/base_mapeada/crf/ner.jsonl
  modified:
    - .gitignore

key-decisions:
  - "Split explícito treino/teste: teste = carregar_gmb(limite=1167); treino = ids 1168..2999 (1832 sentenças). Sem vazamento."
  - "Todas as 25 features do ner.csv usadas (exceto sentence_idx agrupador e tag label); word e lemma entram como feature."
  - "Hiperparâmetros CRF: lbfgs, c1=0.1, c2=0.1, max_iterations=100, all_possible_transitions=True."
  - "Modelo cacheado em modelos/crf_ner.pkl (gitignored); --retrain força re-treino."

patterns-established:
  - "Pure functions testáveis + CLI argparse no mesmo script de modelo"
  - "Dedupe comparando (word, tag) por sentença; filtro de sid não-numérico"

requirements-completed: [REQ-02]

# Metrics
duration: 12 min
completed: 2026-06-16
---

# Phase 2 Plan 01: CRF NER Baseline Summary

**Baseline CRF (sklearn-crfsuite) treinado nas 25 features do ner.csv, prevendo IOB sobre as 1167 sentenças de teste do GMB e emitindo 25857 predições no contrato .jsonl comum, alinhadas token-a-token ao gold.**

## Performance

- **Duration:** 12 min
- **Started:** 2026-06-16T14:59:00Z (approx)
- **Completed:** 2026-06-16T15:12:00Z
- **Tasks:** 3
- **Files modified:** 4 created, 1 modified

## Accomplishments
- `run_crf.py` lê o `ner.csv` (latin-1, 25 colunas), filtra a linha de header vazado (`sentence_idx == "prev-lemma"`) e desfaz o artefato de duplicação por sentença.
- CRF treinado em 1832 sentenças GMB-mapeadas FORA do teste (ids 1168..2999), garantindo zero vazamento treino/teste, e persistido em `modelos/crf_ner.pkl`.
- Cache de modelo: re-execução carrega o `.pkl` do disco sem re-treinar (atende SC#3); `--retrain` força novo treino.
- `resultados/base_mapeada/crf/ner.jsonl` com 25857 registros (`tarefa=ner`, `modelo=crf`), alinhados 1:1 com `carregar_gmb(limite=1167)` — verificado por `ALIGN_OK 25857`.

## Task Commits

Each task was committed atomically:

1. **Task 1: Carregador/mapeador ner.csv↔GMB com dedupe e filtro (TDD)** - `2a125e6` (feat)
2. **Task 2: Treino + persistência do CRF e CLI com cache** - `e4c9666` (chore — .gitignore; código de treino incluído no commit da Task 1)
3. **Task 3: Emissão do .jsonl no contrato comum, alinhado ao gold** - `30a5cb8` (feat)

_Nota TDD: a Task 1 seguiu RED→GREEN (teste de import falhou, depois 4 testes passaram); por o `run_crf.py` ter sido escrito num único arquivo coeso, o código de treino (Task 2) e de emissão (Task 3) já estava presente no commit da Task 1, com os commits subsequentes capturando .gitignore e os testes de alinhamento._

**Plan metadata:** (este commit)

## Files Created/Modified
- `run_crf.py` - Script CLI: parsing saneado do ner.csv, treino/cache do CRF, emissão do .jsonl (≈300 linhas)
- `tests/test_run_crf.py` - 6 testes: filtro malformado, sentença "1" == GMB, dedupe, ordem/comprimento, alinhamento do .jsonl, abort em desalinhamento
- `modelos/crf_ner.pkl` - Modelo CRF serializado (joblib), gitignored
- `resultados/base_mapeada/crf/ner.jsonl` - 25857 predições NER IOB
- `.gitignore` - adiciona `modelos/*.pkl`

## Decisions Made
- **Split explícito sem vazamento:** teste = primeiras 1167 sentenças GMB; treino = ids inteiros 1168..2999 presentes no `ner.csv` (1832 sentenças). Implementado em `sids_treino_fora_do_teste`.
- **Todas as 25 features** (decisão LOCKED do plano): todas as colunas exceto `sentence_idx` (agrupador) e `tag` (label), com `word`/`lemma` como features. A coluna row-index (índice 0) é descartada.
- **Dedupe robusto:** comparação por `(word, tag)` da primeira vs. segunda metade da sentença, em vez de comparar dicts inteiros, para evitar diferenças espúrias em features posicionais.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Instalação de sklearn-crfsuite**
- **Found during:** Setup (antes da Task 1)
- **Issue:** `sklearn-crfsuite` constava em `requirements.txt` mas não estava instalado no ambiente Python global; `import sklearn_crfsuite` falhava com `ModuleNotFoundError`, bloqueando Task 2.
- **Fix:** `python -m pip install sklearn-crfsuite` (instalou sklearn-crfsuite 0.5.0, python-crfsuite 0.9.12).
- **Files modified:** Nenhum (dependência já declarada em requirements.txt).
- **Verification:** `import sklearn_crfsuite` OK; `CRF.fit` treina e `predict_single` prediz.
- **Committed in:** N/A (mudança de ambiente, sem alteração de arquivo versionado).

---

**Total deviations:** 1 auto-fixed (1 blocking — instalação de dependência já declarada).
**Impact on plan:** Mudança apenas de ambiente; nenhuma alteração de design ou escopo. Plano executado conforme escrito.

## Issues Encountered
None — os data_facts do plano (latin-1, 25 colunas, dedupe, filtro de `prev-lemma`, mapeamento GMB "N.0" ↔ ner.csv "N") foram confirmados na prática e o alinhamento bateu 100% (25857/25857 tokens).

## User Setup Required
None - nenhuma configuração de serviço externo necessária.

## Next Phase Readiness
- Primeiro baseline tradicional (NER, CRF) completo e emitindo o contrato comum, pronto para o agregador comparativo.
- `modelos/crf_ner.pkl` é cache local reprodutível (gitignored); regenerável com `python run_crf.py --retrain`.
- Plan 02-02 (run_regras, UPOS) já consta como SUMMARY no repositório; Fase 2 a caminho de conclusão.

## Verification Results
- `python -m pytest tests/test_run_crf.py -x -q` → **6 passed**
- `python -m pytest tests/ -q` → **37 passed** (suíte completa)
- `python run_crf.py --limite 1167` → gera `resultados/base_mapeada/crf/ner.jsonl` + `modelos/crf_ner.pkl`; re-execução carrega do disco sem re-treino.
- `ALIGN_OK 25857` — nº de registros == total de tokens das 1167 sentenças; `(sentenca_id, posicao, token)` alinham 1:1 com `carregar_gmb(limite=1167)`.

## Self-Check: PASSED

- Arquivos criados verificados em disco: run_crf.py, tests/test_run_crf.py, modelos/crf_ner.pkl, resultados/base_mapeada/crf/ner.jsonl.
- Commits presentes: 2a125e6 (Task 1), e4c9666 (Task 2), 30a5cb8 (Task 3).
- Verificações do plano re-executadas: pytest 6/6, ALIGN_OK 25857.

---
*Phase: 02-baselines-tradicionais*
*Completed: 2026-06-16*
