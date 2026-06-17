---
phase: 04-agregador-e-relatorio
plan: 01
subsystem: testing
tags: [metricas, seqeval, ner, upos, iob, precision-recall-f1, tdd]

# Dependency graph
requires:
  - phase: 02-baselines
    provides: ".jsonl de predição (contrato Registro) que o agregador alinha ao gold"
provides:
  - "src/metricas.py: funções puras metricas_token (token, por classe + micro) e metricas_entidade (entidade via seqeval, RETORNA dados)"
  - "alinhar(): helper de alinhamento por posição (referência do legado)"
  - "tests/test_metricas.py: 8 testes sintéticos com P/R/F1 conferidos à mão (token + entidade IOB)"
affects: [04-02-agregador-cli, relatorio, tabela-comparativa]

# Tech tracking
tech-stack:
  added: [seqeval (instalado; já estava em requirements.txt)]
  patterns:
    - "Métricas como funções puras: sem print, sem I/O, sem rede — testáveis com sequências sintéticas"
    - "Refatoração print->return: legado imprimia no stdout, novo módulo RETORNA dict para o agregador montar JSON/tabela"

key-files:
  created:
    - src/metricas.py
    - tests/test_metricas.py
  modified: []

key-decisions:
  - "metricas_token copiado VERBATIM do comparativo_gold.py (l.149-170): matemática validada do TCC I, não re-derivada"
  - "metricas_entidade levanta RuntimeError claro se seqeval ausente (não silencia) — número é obrigatório para a tabela (T-04-02)"
  - "por_tipo filtra chaves agregadas do classification_report (micro/macro/weighted avg, accuracy) — só tipos de entidade"

patterns-established:
  - "TDD para aritmética de métricas: RED com sequências gold/pred mínimas e P/R/F1 conhecidos à mão (pytest.approx)"
  - "Import lazy de dependência opcional dentro da função, com erro de domínio claro no except ImportError"

requirements-completed: [REQ-05]

# Metrics
duration: 3min
completed: 2026-06-17
---

# Phase 4 Plan 01: src/metricas.py (núcleo de métricas) Summary

**Módulo puro de métricas extraído do comparativo_gold.py legado: metricas_token (P/R/F1 por classe + micro, nível token) copiado verbatim, e metricas_entidade refatorado de print-no-stdout para RETORNAR dict (precisao/cobertura/f1 + por_tipo) via seqeval.**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-06-17T16:57:35Z
- **Completed:** 2026-06-17T17:00:49Z
- **Tasks:** 2
- **Files modified:** 2 (ambos criados)

## Accomplishments
- `metricas_token` copiado verbatim do legado (l.149-170): retorna `(linhas, (micro_p, micro_r, micro_f))`, divisão-por-zero -> 0.0, suporte = tp+fn por classe.
- `metricas_entidade` REFATORADO: o legado imprimia `classification_report` + métricas no stdout (l.181-185); o novo RETORNA `{"precisao","cobertura","f1","por_tipo"}` via seqeval, sem print, filtrando chaves agregadas.
- `alinhar` copiado como helper de referência (l.136-146).
- 8 testes sintéticos passam (4 token + 4 entidade IOB) com P/R/F1 conferidos à mão; módulo puro (print count = 0).
- Tratamento controlado de seqeval ausente: `RuntimeError("seqeval não instalado (pip install seqeval)")`.

## Task Commits

Cada task seguiu o ciclo TDD (RED test -> GREEN feat):

1. **Task 1: metricas_token + alinhar (do legado)**
   - `f51177d` test(04-01) — testes RED de metricas_token
   - `0cd9821` feat(04-01) — implementação metricas_token + alinhar
2. **Task 2: metricas_entidade (seqeval) refatorado para RETORNAR**
   - `9dcc76a` test(04-01) — testes RED de metricas_entidade IOB
   - `675623b` feat(04-01) — implementação metricas_entidade

_TDD gate: sequência test(...) -> feat(...) presente para ambas as tasks._

## Files Created/Modified
- `src/metricas.py` - Funções puras: `metricas_token` (token, por classe + micro), `metricas_entidade` (entidade via seqeval, RETORNA dict), `alinhar` (helper de alinhamento por posição).
- `tests/test_metricas.py` - 8 testes sintéticos: classificação perfeita, um erro de token, divisão por zero, suporte; entidade perfeita, span parcial não casa, não imprime (capsys), chaves agregadas filtradas.

## Decisions Made
- `metricas_token` copiado verbatim — matemática já validada no TCC I, não há ganho em re-derivar.
- `metricas_entidade` levanta erro claro em vez de retornar None quando seqeval falta: silenciar produziria tabela com número faltando sem aviso.
- Import de seqeval feito lazy (dentro da função) para o módulo importar mesmo sem a dependência (só `metricas_entidade` exige seqeval).
- Floats crus, sem arredondamento (o agregador 04-02 formata com 3 casas) — testes usam `pytest.approx`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Instalado seqeval (ausente no ambiente)**
- **Found during:** Task 2 (metricas_entidade)
- **Issue:** seqeval consta em requirements.txt (linha 2) mas não estava instalado no ambiente Python; os testes de entidade e o import de `seqeval.metrics` falhariam.
- **Fix:** `python -m pip install seqeval` (previsto pelo próprio plano como desvio Regra 3).
- **Files modified:** Nenhum (requirements.txt já listava seqeval).
- **Verification:** `python -c "from seqeval.metrics import precision_score"` imprime "seqeval OK"; 8 testes passam.
- **Committed in:** N/A (instalação de ambiente, sem mudança de arquivo versionado).

---

**Total deviations:** 1 auto-fixed (1 blocking).
**Impact on plan:** Instalação de dependência prevista pelo plano. Sem scope creep.

## Issues Encountered
- O proxy `rtk` reescreve `python -m pytest` e por padrão filtra a saída ("No tests collected" no stdout filtrado); resolvido executando via `rtk proxy python -m pytest` para ver o resultado bruto. Não afetou o código nem os testes.

## TDD Gate Compliance
Ambas as tasks têm commit `test(...)` (RED) seguido de `feat(...)` (GREEN). Nenhum teste passou inesperadamente na fase RED (ImportError confirmado antes de cada implementação). Sem fase REFACTOR necessária.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `src/metricas.py` pronto para o plano 04-02 (CLI agregador) consumir: `metricas_token` para por_classe/micro e `metricas_entidade` para o nível de entidade do NER.
- Sem stubs. Sem bloqueios.

## Self-Check: PASSED
- Arquivos: src/metricas.py, tests/test_metricas.py, 04-01-SUMMARY.md — todos presentes.
- Commits: f51177d, 0cd9821, 9dcc76a, 675623b — todos no histórico.

---
*Phase: 04-agregador-e-relatorio*
*Completed: 2026-06-17*
