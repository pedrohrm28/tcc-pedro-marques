---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: phase-planned
last_updated: "2026-06-16T15:02:09.634Z"
progress:
  total_phases: 5
  completed_phases: 1
  total_plans: 4
  completed_plans: 2
  percent: 50
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-06-16)

**Core value:** Tabela comparativa única e defensável (precisão/cobertura/F1) dos 4 modelos sobre as mesmas sentenças, reprodutível.
**Current focus:** Phase 2 planejada (run_crf + run_regras) — pronta para executar

## Status

- **Initialized:** 2026-06-16
- **Granularity:** coarse · **Workflow:** light (sem research/plan-check, com verifier)
- **Phases:** 5 (ver ROADMAP.md)
- **Next action:** `/gsd-execute-phase 2`

## Decisions Log

- Arquitetura: scripts separados por modelo + agregador puro (não orquestrador único).
- Re-rodar os 4 modelos no mesmo pipeline (não reaproveitar números do TCC I).
- NER = GMB (inglês); POS = Bosque (português) — herdado do TCC I.
- `GMB_dataset.txt` = gold de NER; `ner.csv` = input de features do CRF.
- **NER usa 1167 sentenças** (= N do POS/Bosque), não as 150 do TCC I. Decisão (2026-06-16): priorizar robustez estatística sobre comparabilidade 1:1; apresentar como evolução do TCC I. GMB tem 2999 disponíveis; `limite` é parâmetro do loader, sem mudança de código na Fase 1. Impacto: ~7,8× mais chamadas de LLM nas Fases 3-4.

## Notes

- Ollama precisa estar no ar com `gpt-oss:20b` e `gpt-oss:120b` baixados antes da Fase 3.
- Base nova (Fase 5) ainda não existe — só `.gitkeep` em `datasets/base_nova/`.
