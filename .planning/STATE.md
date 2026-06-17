---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: phase-complete
last_updated: "2026-06-16T15:04:14.252Z"
progress:
  total_phases: 5
  completed_phases: 2
  total_plans: 4
  completed_plans: 4
  percent: 100
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-06-16)

**Core value:** Tabela comparativa única e defensável (precisão/cobertura/F1) dos 4 modelos sobre as mesmas sentenças, reprodutível.
**Current focus:** Fase 2 completa (CRF NER + regras UPOS) — pronta para verify/Fase 3

## Status

- **Initialized:** 2026-06-16
- **Granularity:** coarse · **Workflow:** light (sem research/plan-check, com verifier)
- **Phases:** 5 (ver ROADMAP.md)
- **Next action:** Fase 2 verificada (PASS 3/3) — planejar Fase 3 (runner LLM `llama3.1:8b`): `/gsd-plan-phase 3`. Pré-requisito: `ollama pull llama3.1:8b`.
- **Last session:** Fase 2 completa e verificada — 02-01 (CRF NER, 25857 tokens) + 02-02 (regras UPOS, 27604 tokens), ambos alinhados ao gold, sem vazamento treino/teste

## Decisions Log

- Arquitetura: scripts separados por modelo + agregador puro (não orquestrador único).
- Re-rodar os 3 modelos no mesmo pipeline (não reaproveitar números do TCC I).
- **LLM = `llama3.1:8b` (decisão 2026-06-17):** substitui `gpt-oss:20b`/`gpt-oss:120b`, que não rodam no hardware local (7,8 GB RAM, GTX 1650 4 GB VRAM, ~16 GB disco). Comparação passa de 4 para 3 modelos (CRF + regras + 1 LLM open-source). CLI `run_llm.py` mantém `--modelo` parametrizável.
- NER = GMB (inglês); POS = Bosque (português) — herdado do TCC I.
- `GMB_dataset.txt` = gold de NER; `ner.csv` = input de features do CRF.
- **NER usa 1167 sentenças** (= N do POS/Bosque), não as 150 do TCC I. Decisão (2026-06-16): priorizar robustez estatística sobre comparabilidade 1:1; apresentar como evolução do TCC I. GMB tem 2999 disponíveis; `limite` é parâmetro do loader, sem mudança de código na Fase 1. Impacto: ~7,8× mais chamadas de LLM nas Fases 3-4.
- **CRF (02-01):** split explícito sem vazamento — teste = `carregar_gmb(limite=1167)`, treino = ids GMB 1168..2999 (1832 sentenças). ner.csv saneado na leitura (filtro de `sentence_idx` não-numérico + dedupe da duplicação de tokens). Modelo cacheado em `modelos/crf_ner.pkl` (gitignored), `--retrain` força re-treino.

## Notes

- Ollama precisa estar no ar com `llama3.1:8b` baixado antes da Fase 3 (`ollama pull llama3.1:8b`, ~4,7 GB). **Trocado de gpt-oss 20b/120b** (não rodam no hardware local: 7,8 GB RAM, GTX 1650 4 GB) em 2026-06-17.
- Base nova (Fase 5) ainda não existe — só `.gitkeep` em `datasets/base_nova/`.
