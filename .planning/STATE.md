---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: Executing Phase 03
last_updated: "2026-06-17T15:29:00Z"
progress:
  total_phases: 5
  completed_phases: 2
  total_plans: 6
  completed_plans: 5
  percent: 75
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-06-16)

**Core value:** Tabela comparativa única e defensável (precisão/cobertura/F1) dos 4 modelos sobre as mesmas sentenças, reprodutível.
**Current focus:** Phase 03 — runner-llm-ollama

## Status

- **Initialized:** 2026-06-16
- **Granularity:** coarse · **Workflow:** light (sem research/plan-check, com verifier)
- **Phases:** 5 (ver ROADMAP.md)
- **Next action:** executar plano 03-02 (run_llm.py CLI: loop 1 sentença/chamada, emissão .jsonl incremental + resume, métricas tok/s).
- **Last session:** 2026-06-17 — Plano 03-01 completo (parser + prompts + cliente Ollama). 33 testes passam sem rede. Commits: ee52969 (Task 1), 348e120 (Task 2).

## Decisions Log

- Arquitetura: scripts separados por modelo + agregador puro (não orquestrador único).
- Re-rodar os 5 modelos no mesmo pipeline (não reaproveitar números do TCC I).
- **LLMs = 3 modelos (decisão 2026-06-17):** `llama3.1:8b` + `qwen2.5:3b` + `llama3.2:3b`, substituindo `gpt-oss:20b`/`gpt-oss:120b` (não rodam no hardware local: 7,8 GB RAM, GTX 1650 4 GB VRAM). Total = **5 modelos** (CRF + regras + 3 LLMs). Os 3 LLMs viram eixo de comparação tamanho/velocidade/qualidade: o 8B roda 58% na CPU (~7,6 tok/s medido), os 3B cabem 100% na GPU (mais rápidos). CLI `run_llm.py --modelo` roda os 3 com o mesmo código.
- **LLM 1 sentença/chamada (decisão 2026-06-17):** sem batching. Agrupar sentenças no prompt reduziria chamadas mas arrisca o alinhamento token-a-token (contrato `.jsonl` exige 1:1 com o gold). Integridade > velocidade. Otimizações seguras (keep_alive, num_predict, format=json) decididas no plano da Fase 3.
- NER = GMB (inglês); POS = Bosque (português) — herdado do TCC I.
- `GMB_dataset.txt` = gold de NER; `ner.csv` = input de features do CRF.
- **NER usa 1167 sentenças** (= N do POS/Bosque), não as 150 do TCC I. Decisão (2026-06-16): priorizar robustez estatística sobre comparabilidade 1:1; apresentar como evolução do TCC I. GMB tem 2999 disponíveis; `limite` é parâmetro do loader, sem mudança de código na Fase 1. Impacto: ~7,8× mais chamadas de LLM nas Fases 3-4.
- **CRF (02-01):** split explícito sem vazamento — teste = `carregar_gmb(limite=1167)`, treino = ids GMB 1168..2999 (1832 sentenças). ner.csv saneado na leitura (filtro de `sentence_idx` não-numérico + dedupe da duplicação de tokens). Modelo cacheado em `modelos/crf_ner.pkl` (gitignored), `--retrain` força re-treino.
- **03-01 (núcleo LLM, 2026-06-17):** UPOS_VALIDOS importado de run_regras (não redefinido no módulo llm) — evita divergência de esquema. extrair_array aceita dict{'tags':[...]} ou lista direta. Fallback total quando len(arr)!=len(tokens). INSTRUCAO_NER em inglês (GMB), INSTRUCAO_UPOS em português (Bosque).

## Notes

- Ollama 0.30.6 no ar com os 3 LLMs (✅ baixados e testados 2026-06-17): `llama3.1:8b` (4,9 GB, ~7,6 tok/s, 42% GPU/58% CPU), `llama3.2:3b` (2,0 GB, ~45 tok/s, 80% GPU), `qwen2.5:3b` (1,9 GB, ~59 tok/s, 100% GPU). Os três respondem correto a `temperature=0/seed=42` via API HTTP. Trocados de gpt-oss 20b/120b (não rodam no hardware local). **qwen2.5:3b é ~7,7× mais rápido que o 8B** (cabe 100% na GPU).
- Base nova (Fase 5) ainda não existe — só `.gitkeep` em `datasets/base_nova/`.
