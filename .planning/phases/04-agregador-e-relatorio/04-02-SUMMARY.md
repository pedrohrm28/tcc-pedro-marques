---
phase: 04-agregador-e-relatorio
plan: 02
subsystem: testing
tags: [seqeval, metricas, ner, upos, csv, markdown, agregador, jsonl]

# Dependency graph
requires:
  - phase: 04-agregador-e-relatorio (plano 01)
    provides: "src/metricas.py (metricas_token, metricas_entidade, alinhar) — núcleo puro de métricas"
  - phase: 01-foundation
    provides: "src/io/contrato.py (Registro, ler_jsonl, caminho_resultado) e src/io/corpora.py (carregar_gmb, carregar_conllu)"
provides:
  - "agregar.py: CLI que lê os .jsonl de predição, alinha ao gold por (sentenca_id, posicao), calcula métricas e emite JSON + tabelas MD/CSV + CSV de discrepâncias"
  - "JSON de métricas por (modelo,tarefa) em resultados/<base>/<modelo>/<tarefa>.metricas.json (D-02)"
  - "tabela_ner.{md,csv} e tabela_upos.{md,csv} comparativas por tarefa (D-03)"
  - "discrepancias.csv token-a-token, modelos empilhados (D-04)"
  - "Degradação graciosa quando faltam .jsonl dos LLMs (D-06) e asserção de integridade gold×.jsonl (D-05)"
affects: [05-base-nova, relatorio-final, fase-3-llms]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Alinhamento por (sentenca_id, posicao) via índice dict + sequências por sentença para seqeval"
    - "Degradação graciosa: descobrir_presentes separa presentes/ausentes; erro por-modelo capturado, demais seguem"
    - "Coerção numpy->nativo (_json_seguro) antes de json.dump para escalares do seqeval"

key-files:
  created:
    - agregar.py
    - tests/test_agregar.py
    - resultados/base_mapeada/crf/ner.metricas.json
    - resultados/base_mapeada/regras/upos.metricas.json
    - resultados/base_mapeada/tabela_ner.{md,csv}
    - resultados/base_mapeada/tabela_upos.{md,csv}
    - resultados/base_mapeada/discrepancias.csv
  modified: []

key-decisions:
  - "Novo módulo agregar.py (CLI) reusando src/metricas.py; o comparativo_gold.py legado fica como referência (D-01)"
  - "_json_seguro coage escalares numpy (numpy.float64/int32) do seqeval para tipos nativos antes do json.dump"
  - "Tabelas sempre escritas mesmo só com cabeçalho (NER/UPOS), garantindo artefato presente mesmo sem dados de uma tarefa"

patterns-established:
  - "Pattern: descobrir_presentes(base) -> (presentes, ausentes) varrendo caminho_resultado, nunca levanta por ausência"
  - "Pattern: erro de desalinhamento (D-05) é por-(modelo,tarefa) e acumulado em resumo['erros'], não derruba os demais"

requirements-completed: [REQ-05, REQ-06]

# Metrics
duration: ~20min
completed: 2026-06-17
---

# Phase 4 Plan 02: Agregador e relatório Summary

**CLI `agregar.py` que alinha os .jsonl ao gold por (sentenca_id, posicao), reusa src/metricas.py e emite JSON de métricas + tabelas comparativas NER/UPOS (MD+CSV) + discrepancias.csv, degradando graciosamente quando faltam os .jsonl dos LLMs.**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-06-17T17:03:50Z
- **Completed:** 2026-06-17T17:24Z
- **Tasks:** 2
- **Files modified:** 2 (código) + 7 artefatos reais gerados

## Accomplishments
- `agregar.py` (núcleo + relatório): alinhamento por (sentenca_id, posicao), métricas via `src/metricas.py`, JSON D-02 por (modelo,tarefa), tabelas D-03 (NER com f1_entidade, UPOS sem), `discrepancias.csv` D-04 com header exato.
- Degradação graciosa (D-06): `descobrir_presentes` separa presentes/ausentes; `agregar` reporta os ausentes e captura erro de desalinhamento por-modelo sem derrubar os demais.
- Asserção de integridade (D-05): `alinhar_predicao` levanta `RuntimeError` claro quando nº de registros do .jsonl != total de tokens do gold.
- 17 testes (gold sintético + .jsonl mínimos em tmp, sem dados reais nem Ollama) — todos passando.
- Rodou contra os dados REAIS atuais (crf/ner + regras/upos), gerando a tabela PARCIAL: CRF NER micro-F1 0.969 / entidade-F1 0.776 (25857 tokens); regras UPOS micro-F1 0.878 — e reportou as 8 combinações de LLM ausentes sem quebrar.

## Task Commits

Each task was committed atomically:

1. **Task 1: Núcleo do agregador (alinhar, métricas, JSON D-02)** - `cad2154` (feat)
2. **Task 2: Tabelas MD/CSV, discrepancias.csv, CLI, degradação graciosa** - `a24d275` (feat)

## Files Created/Modified
- `agregar.py` - CLI agregador: carregar_gold/indexar_gold/alinhar_predicao/calcular_metricas/ler_meta/escrever_metricas_json (Task 1) + descobrir_presentes/montar_tabela/escrever_tabelas/escrever_discrepancias/agregar/main (Task 2).
- `tests/test_agregar.py` - 17 testes com gold sintético e .jsonl mínimos em tmp.
- `resultados/base_mapeada/crf/ner.metricas.json`, `regras/upos.metricas.json` - JSON D-02 reais.
- `resultados/base_mapeada/tabela_ner.{md,csv}`, `tabela_upos.{md,csv}` - tabelas comparativas parciais (D-03).
- `resultados/base_mapeada/discrepancias.csv` - 4149 discrepâncias token-a-token (header exato, D-04).

## Decisions Made
- Novo `agregar.py` reusando `src/metricas.py` (não reimplementa a matemática), conforme D-01.
- Tabelas sempre gravadas (mesmo só com cabeçalho) para garantir artefato presente por tarefa.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Coerção de escalares numpy do seqeval antes do json.dump**
- **Found during:** Task 1 (test_escrever_metricas_json)
- **Issue:** `metricas_entidade` (seqeval) retorna `numpy.float64`/`numpy.int32` em precisao/cobertura/f1/suporte; `json.dump` levanta `TypeError: Object of type int32 is not JSON serializable`. Quebraria toda escrita de JSON D-02 para a tarefa NER em runs reais.
- **Fix:** Helper `_json_seguro` que coage recursivamente escalares numpy (via `.item()`) para tipos nativos antes de serializar.
- **Files modified:** agregar.py
- **Verification:** test_escrever_metricas_json passa; rodada real gera crf/ner.metricas.json válido (entidade-F1 0.776).
- **Committed in:** cad2154 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Correção essencial — sem ela a escrita do JSON de NER quebraria em produção. Sem scope creep.

## Issues Encountered
- `seqeval` emite `UndefinedMetricWarning` para classes sem amostras previstas na rodada real (esperado para tags raras); não afeta a corretude das métricas agregadas.

## User Setup Required
None - sem configuração de serviço externo. A tabela final completa só sai quando o usuário rodar os 3 LLMs da Fase 3 (gera os 6 .jsonl ausentes); o agregador já está pronto para incorporá-los sem alteração de código.

## Next Phase Readiness
- REQ-05 e REQ-06 atendidos: agregador testado e funcional contra dados reais (tabela parcial crf+regras).
- Quando os .jsonl dos LLMs existirem, basta re-rodar `python agregar.py --base base_mapeada` — os modelos presentes entram automaticamente nas tabelas e ganham colunas tempo/velocidade dos .meta.json.
- Pronto para a Fase 5 (base nova): `agregar.py --base base_nova` funciona sem mudança.

## Self-Check: PASSED

- Arquivos criados verificados (agregar.py, tests/test_agregar.py, 2 .metricas.json, 4 tabelas, discrepancias.csv, SUMMARY).
- Commits verificados: cad2154 (Task 1), a24d275 (Task 2).

---
*Phase: 04-agregador-e-relatorio*
*Completed: 2026-06-17*
