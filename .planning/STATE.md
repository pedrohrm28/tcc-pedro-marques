# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-06-16)

**Core value:** Tabela comparativa única e defensável (precisão/cobertura/F1) dos 4 modelos sobre as mesmas sentenças, reprodutível.
**Current focus:** Phase 1 — Fundação (contrato `.jsonl` + loaders de corpora)

## Status

- **Initialized:** 2026-06-16
- **Granularity:** coarse · **Workflow:** light (sem research/plan-check, com verifier)
- **Phases:** 5 (ver ROADMAP.md)
- **Next action:** `/gsd-plan-phase 1`

## Decisions Log

- Arquitetura: scripts separados por modelo + agregador puro (não orquestrador único).
- Re-rodar os 4 modelos no mesmo pipeline (não reaproveitar números do TCC I).
- NER = GMB (inglês); POS = Bosque (português) — herdado do TCC I.
- `GMB_dataset.txt` = gold de NER; `ner.csv` = input de features do CRF.

## Notes

- Ollama precisa estar no ar com `gpt-oss:20b` e `gpt-oss:120b` baixados antes da Fase 3.
- Base nova (Fase 5) ainda não existe — só `.gitkeep` em `datasets/base_nova/`.
