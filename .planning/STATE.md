---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: phase-complete
last_updated: "2026-06-17T17:25:00.000Z"
progress:
  total_phases: 5
  completed_phases: 4
  total_plans: 8
  completed_plans: 8
  percent: 100
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-06-16)

**Core value:** Tabela comparativa única e defensável (precisão/cobertura/F1) dos 5 modelos sobre as mesmas sentenças, reprodutível.
**Current focus:** Fase 4 completa e verificada (PASS 3/3). Pendente: rodar os 3 LLMs (Fase 3) p/ tabela completa; depois Fase 5 (base nova).

## Status

- **Initialized:** 2026-06-16
- **Granularity:** coarse · **Workflow:** light (sem research/plan-check, com verifier)
- **Phases:** 5 (ver ROADMAP.md)
- **Next action:** Fase 4 verificada (PASS 3/3). Rodar os 3 LLMs da Fase 3 (`python run_llm.py --modelo ... --tarefa ...`, 6 execuções) para gerar os .jsonl ausentes e re-rodar `python agregar.py` p/ tabela completa dos 5 modelos. Depois: `/gsd-plan-phase 5` (base nova).
- **Last session:** 2026-06-17 — Plano 04-02 completo (agregar.py: CLI que alinha .jsonl ao gold, calcula métricas via src/metricas.py, emite JSON D-02 + tabelas NER/UPOS MD/CSV + discrepancias.csv; degradação graciosa D-06 e asserção D-05). 17 testes sintéticos passam. Rodada real parcial: CRF NER micro-F1 0.969/entidade-F1 0.776; regras UPOS micro-F1 0.878; 8 LLMs reportados ausentes sem quebrar. Commits: cad2154 (Task 1), a24d275 (Task 2).

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
- **03-02 (runner CLI, 2026-06-17):** fn_gerar injetável no rodar() para mock sem rede. Escrita modo 'a' direto (não escrever_jsonl 'w'). modelo preserva ':' no Registro; caminho sanitiza via caminho_resultado. meta.json com tok/s, sent/s, fallbacks por (modelo, tarefa).
- **04-01 (núcleo de métricas, 2026-06-17):** src/metricas.py puro (sem print/I/O/rede). metricas_token copiado verbatim do comparativo_gold.py (l.149-170): retorna (linhas, micro), suporte=tp+fn, div-zero->0.0. metricas_entidade REFATORADO de print (legado l.181-185) para RETORNAR dict {precisao,cobertura,f1,por_tipo} via seqeval; import lazy + RuntimeError claro se seqeval ausente; por_tipo filtra micro/macro/weighted avg + accuracy. alinhar copiado como referência. seqeval instalado no ambiente (Regra 3).
- **04-02 (CLI agregador, 2026-06-17):** agregar.py reusa src/metricas.py (não reimplementa). Alinhamento por (sentenca_id, posicao) com índice dict; tags ausentes -> "X-AUSENTE". D-05: alinhar_predicao levanta RuntimeError se nº de registros != tokens do gold (no CLI é por-modelo, capturado em resumo['erros'], não derruba os demais). D-06: descobrir_presentes separa presentes/ausentes, nunca levanta por ausência. _json_seguro coage escalares numpy do seqeval (float64/int32) p/ nativos antes do json.dump (Regra 1 - bug). Tabelas NER (com f1_entidade) e UPOS (sem) sempre escritas; tempo/tok_s = "—" p/ crf/regras (sem .meta.json).

## Notes

- Ollama 0.30.6 no ar com os 3 LLMs (✅ baixados e testados 2026-06-17): `llama3.1:8b` (4,9 GB, ~7,6 tok/s, 42% GPU/58% CPU), `llama3.2:3b` (2,0 GB, ~45 tok/s, 80% GPU), `qwen2.5:3b` (1,9 GB, ~59 tok/s, 100% GPU). Os três respondem correto a `temperature=0/seed=42` via API HTTP. Trocados de gpt-oss 20b/120b (não rodam no hardware local). **qwen2.5:3b é ~7,7× mais rápido que o 8B** (cabe 100% na GPU).
- Base nova (Fase 5) ainda não existe — só `.gitkeep` em `datasets/base_nova/`.
