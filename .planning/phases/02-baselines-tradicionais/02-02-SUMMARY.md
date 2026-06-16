---
phase: 02-baselines-tradicionais
plan: 02
subsystem: nlp-baseline
tags: [upos, pos-tagging, bosque, conllu, rule-based, lexicon, portuguese]

# Dependency graph
requires:
  - phase: 01-foundation
    provides: "src/io/contrato.py (Registro, escrever_jsonl, caminho_resultado) e src/io/corpora.py (carregar_conllu, Sentenca)"
provides:
  - "run_regras.py: baseline tradicional de UPOS por regras (léxico do train + heurísticas morfológicas)"
  - "resultados/base_mapeada/regras/upos.jsonl: predições UPOS (27604 tokens, 1167 sentenças de teste) no contrato comum"
  - "Funções puras reusáveis: construir_lexico, tag_por_regras, anotar"
affects: [03-llm-baselines, 04-comparativo, agregacao]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Léxico derivado SOMENTE do train (sem vazamento do teste)"
    - "Pipeline determinístico de decisão UPOS (pontuação > número > léxico > sufixos > PROPN > NOUN)"
    - "Saída restrita a conjunto fechado UPOS_VALIDOS"

key-files:
  created:
    - run_regras.py
    - tests/test_run_regras.py
    - resultados/base_mapeada/regras/upos.jsonl
  modified: []

key-decisions:
  - "Léxico construído exclusivamente do pt_bosque-ud-train.conllu (token_lower -> UPOS mais frequente); teste nunca alimenta o léxico (anti-vazamento T-02-04)"
  - "UPOS_VALIDOS inclui PART para totalizar as 17 tags do esquema UD (data_facts lista 16 tags presentes no teste; PART completa o conjunto fechado UD usado em corpora)"
  - "Pipeline 100% determinístico (sem aleatoriedade) -> re-execução reproduz o mesmo .jsonl (T-02-06)"
  - "Artefato .jsonl versionado no repositório para reprodutibilidade da tabela comparativa"

patterns-established:
  - "Baseline tradicional = script CLI com funções puras testáveis + emissão do contrato .jsonl da Fase 1"
  - "Teste de alinhamento via subprocess (--limite pequeno + --saida tmp) valida 1:1 com o gold"

requirements-completed: [REQ-03]

# Metrics
duration: 9 min
completed: 2026-06-16
---

# Phase 02 Plan 02: Anotação UPOS por Regras Summary

**Baseline tradicional de UPOS para português via léxico (token->UPOS mais frequente do Bosque train) + heurísticas morfológicas determinísticas, emitindo 27604 predições alinhadas 1:1 ao gold de teste no contrato .jsonl comum.**

## Performance

- **Duration:** 9 min
- **Started:** 2026-06-16T15:04Z (approx)
- **Completed:** 2026-06-16
- **Tasks:** 2
- **Files modified:** 3 (2 created code/test + 1 artefato)

## Accomplishments
- `construir_lexico` lê o TRAIN do Bosque (7018 sentenças) e mapeia cada token de superfície minúsculo para sua UPOS mais frequente — sem ler o teste (anti-vazamento).
- `tag_por_regras` decide a UPOS por pipeline determinístico: pontuação/símbolo -> PUNCT/SYM; padrão numérico/ordinal -> NUM; léxico (prioridade); sufixos morfológicos (-mente->ADV, -ção/-dade->NOUN, -ável/-oso->ADJ, -ar/-er/-ir->VERB); maiúscula inicial -> PROPN; fallback -> NOUN.
- `run_regras.py --limite 1167` gera `resultados/base_mapeada/regras/upos.jsonl` com 27604 registros, alinhados token-a-token a `carregar_conllu(limite=1167)` (ALIGN_OK).
- 100% das tags emitidas pertencem a UPOS_VALIDOS (0 tags fora do esquema).

## Task Commits

1. **Task 1 (RED): testes de regras e alinhamento** - `89e2cc6` (test)
2. **Task 1 (GREEN): implementação run_regras.py (léxico + regras + CLI)** - `67da323` (feat)
3. **Task 2: emissão do .jsonl alinhado + artefato** - `3c114f5` (feat)

**Plan metadata:** committed separadamente (docs: complete plan)

_TDD: Task 1 seguiu RED (89e2cc6) -> GREEN (67da323). Task 2 (CLI/jsonl) foi implementado junto à GREEN por compartilhar o arquivo; o artefato e o teste de alinhamento foram commitados em 3c114f5._

## Files Created/Modified
- `run_regras.py` - Script CLI de anotação UPOS por regras; funções puras `construir_lexico`, `tag_por_regras`, `anotar`; `UPOS_VALIDOS`; `main()` com argparse (--train/--teste/--limite/--saida).
- `tests/test_run_regras.py` - 10 testes: pontuação, símbolo, número, prioridade do léxico, sufixo -mente, fallback NOUN, léxico não-vazio (de->ADP), tags ∈ UPOS_VALIDOS, contagem de 17 tags, alinhamento do .jsonl com o gold.
- `resultados/base_mapeada/regras/upos.jsonl` - 27604 predições UPOS (1167 sentenças de teste), contrato comum, tarefa="upos", modelo="regras".

## Decisions Made
- Léxico exclusivamente do train (anti-vazamento, T-02-04).
- Pipeline determinístico (T-02-06): empates de frequência no léxico resolvidos por `Counter.most_common` (ordem de inserção estável).
- Sufixos verbais (-ar/-er/-ir) colocados após nominais/adjetivais no pipeline para reduzir falsos positivos; ainda assim ficam após o léxico (heurística fraca).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] UPOS_VALIDOS precisou de 17 tags, mas data_facts lista 16 do teste**
- **Found during:** Task 1 (definição de UPOS_VALIDOS e teste `test_upos_validos_tem_17_tags`)
- **Issue:** O `<data_facts>` enumera 16 UPOS presentes no teste (NOUN..INTJ), mas o `<behavior>` exige "as 17 acima" e o teste planejado afirma `len(UPOS_VALIDOS) == 17`. As 16 do teste não totalizam 17.
- **Fix:** Adicionada `PART` ao conjunto fechado UPOS_VALIDOS, alinhando-o às 17 tags do esquema UD já usado em `tests/test_corpora_tdd.py`. PART só seria emitida via léxico se ocorresse no train; não afeta o alinhamento nem introduz tags inválidas.
- **Files modified:** run_regras.py
- **Verification:** `python -m pytest tests/test_run_regras.py -q` (10 passed); 0 tags fora do esquema no .jsonl gerado.
- **Committed in:** `67da323`

---

**Total deviations:** 1 auto-fixed (1 blocking).
**Impact on plan:** Resolve uma inconsistência 16-vs-17 entre data_facts e o critério de teste, sem escopo extra. Conjunto fechado consistente com o esquema UD do projeto.

## Issues Encountered
None - planned work executed cleanly. Léxico verificado (de->ADP, 12735 ocorrências no train), alinhamento confirmado (27604 tokens), distribuição predita coerente (NOUN dominante).

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Ambos os baselines tradicionais (CRF em 02-01, regras em 02-02) emitem o contrato comum sobre as mesmas 1167 sentenças.
- Pronto para Fase 03 (baselines LLM) e posterior agregação/comparativo.
- Sem blockers.

## Self-Check: PASSED
- FOUND: run_regras.py
- FOUND: tests/test_run_regras.py
- FOUND: resultados/base_mapeada/regras/upos.jsonl
- FOUND commit: 89e2cc6 (test RED)
- FOUND commit: 67da323 (feat GREEN)
- FOUND commit: 3c114f5 (feat jsonl)
- pytest: 10 passed | ALIGN_OK 27604 | tags fora do esquema: 0

---
*Phase: 02-baselines-tradicionais*
*Completed: 2026-06-16*
