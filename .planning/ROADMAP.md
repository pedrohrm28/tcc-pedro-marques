# Roadmap: TCC II — Comparativo LLMs open-source vs. modelos tradicionais

## Overview

Do contrato de dados ao relatório final: primeiro fixamos o formato `.jsonl` comum e o esqueleto de leitura dos corpora; depois implementamos os dois baselines tradicionais (CRF para NER, regras para POS); então o runner dos 3 LLMs via Ollama (`run_llm.py --modelo ...`); em seguida o agregador que une tudo numa tabela comparativa + discrepâncias; por fim, geramos a base nova e rodamos os 5 modelos nela para avaliar generalização.

> **Revisão (2026-06-17):** LLM trocado de `gpt-oss:20b`/`gpt-oss:120b` (não rodam no hardware local) para **3 LLMs**: `llama3.1:8b` (CPU/offload) + `qwen2.5:3b` + `llama3.2:3b` (GPU). Total: **5 modelos** (3 LLMs + CRF + regras). Os 3 LLMs também são eixo de comparação tamanho/velocidade/qualidade; todos rodam 1 sentença/chamada. Ver PROJECT.md.

## Phases

- [x] **Phase 1: Fundação — contrato e leitura de corpora** - Formato `.jsonl` comum, loaders de GMB/CoNLL-U, scaffolding do projeto
- [x] **Phase 2: Baselines tradicionais** - CRF (NER) treinado do `ner.csv` + modelo de regras (POS) sobre o Bosque
- [x] **Phase 3: Runner LLM (Ollama)** - Inferência reprodutível dos 3 LLMs (llama3.1:8b, qwen2.5:3b, llama3.2:3b) em NER e UPOS
- [ ] **Phase 4: Agregador e relatório** - Métricas alinhadas ao gold, tabela comparativa dos 5 modelos + CSV de discrepâncias
- [ ] **Phase 5: Base nova e generalização** - Gerar sentenças fora de domínio e rodar os 5 modelos nelas

## Phase Details

### Phase 1: Fundação — contrato e leitura de corpora
**Goal**: Definir o contrato de saída `.jsonl` que todos os modelos emitem e os loaders que leem GMB (IOB) e Bosque (CoNLL-U) para gold; estruturar o projeto e dependências.
**Depends on**: Nothing (first phase)
**Requirements**: REQ-01
**Success Criteria** (what must be TRUE):
  1. Existe um módulo de I/O que lê `GMB_dataset.txt` em sentenças de (token, tag IOB) e `pt_bosque-ud-test.conllu` em sentenças de (token, UPOS).
  2. Há um schema/escritor `.jsonl` documentado (`{tarefa, modelo, sentenca_id, posicao, token, tag_predita}`) com helper de escrita/leitura.
  3. `requirements.txt` cobre as dependências (sklearn-crfsuite, scikit-learn, requests/ollama, etc.) e instala sem erro.
**Plans**: 2 plans

Plans:
- [x] 01-01: Loaders de corpora (GMB IOB + CoNLL-U UPOS) e seleção dos subconjuntos (150 / 1167 sentenças)
- [x] 01-02: Schema `.jsonl` do contrato comum + helpers de leitura/escrita + estrutura de pastas `resultados/`

### Phase 2: Baselines tradicionais
**Goal**: Implementar os dois modelos de referência rodando via código e emitindo o contrato comum.
**Depends on**: Phase 1
**Requirements**: REQ-02, REQ-03
**Success Criteria** (what must be TRUE):
  1. `run_crf.py` treina o CRF a partir das features do `ner.csv`, persiste o modelo e prediz sobre o teste GMB, gerando `.jsonl`.
  2. `run_regras.py` produz a anotação UPOS por regras sobre o Bosque e gera `.jsonl`.
  3. Re-rodar o agregador não exige re-treinar o CRF (modelo em disco).
**Plans**: 2 plans

Plans:
- [x] 02-01: `run_crf.py` — treino + predição NER (sklearn-crfsuite, features do ner.csv)
- [x] 02-02: `run_regras.py` — anotação POS/UPOS por regras sobre o Bosque

### Phase 3: Runner LLM (Ollama)
**Goal**: Rodar os 3 LLMs (`llama3.1:8b`, `qwen2.5:3b`, `llama3.2:3b`) via Ollama nas duas tarefas, de forma reprodutível, 1 sentença por chamada, convertendo a saída do LLM de volta ao contrato comum e registrando tempo/velocidade por modelo.
**Depends on**: Phase 1
**Requirements**: REQ-04
**Success Criteria** (what must be TRUE):
  1. `run_llm.py --modelo <llama3.1:8b|qwen2.5:3b|llama3.2:3b> --tarefa ner|upos` produz `.jsonl` alinhado token a token ao gold, 1 sentença por chamada (sem batching).
  2. Execução usa `temperature=0` e `seed=42`; prompts versionados; o mesmo script roda os 3 LLMs via `--modelo`.
  3. Parsing robusto: tokens sem resposta do LLM viram tag de fallback rastreável, sem quebrar o alinhamento.
  4. Cada execução registra tempo total e velocidade (tok/s ou sent/s) do modelo, para o eixo de comparação tamanho/velocidade.
  5. Execução retomável: progresso parcial é persistido para não perder horas de processamento se travar.
**Plans**: 2 plans

Plans:
**Wave 1**
- [x] 03-01-PLAN.md — Núcleo puro/mockável: prompts versionados (NER IOB + UPOS) + cliente Ollama reprodutível (temperature=0/seed=42/keep_alive=-1/format=json) + parser robusto com fallback rastreável

**Wave 2** *(blocked on Wave 1 completion)*
- [x] 03-02-PLAN.md — run_llm.py CLI: loop 1 sentença/chamada, emissão `.jsonl` incremental + resume, métricas tok/s e sent/s por (modelo,tarefa)

### Phase 4: Agregador e relatório
**Goal**: `comparativo_gold.py` lê todos os `.jsonl`, alinha ao gold, calcula métricas e monta a tabela comparativa dos 5 modelos + discrepâncias.
**Depends on**: Phase 2, Phase 3
**Requirements**: REQ-05, REQ-06
**Success Criteria** (what must be TRUE):
  1. Calcula precisão, cobertura e F1 por classe, micro, e em nível de entidade (NER/IOB).
  2. Emite uma tabela comparativa única (Markdown/CSV) com os 5 modelos × tarefas, incluindo tempo/velocidade dos LLMs.
  3. Emite CSV de discrepâncias token a token por modelo para análise qualitativa.
**Plans**: TBD

Plans:
- [ ] 04-01: Núcleo de métricas (por classe, micro, nível de entidade) reusando o contrato `.jsonl`
- [ ] 04-02: Agregação multi-modelo → tabela comparativa + CSV de discrepâncias

### Phase 5: Base nova e generalização
**Goal**: Gerar a base nova (fora de domínio) e rodar os 5 modelos nela, reusando todo o pipeline.
**Depends on**: Phase 4
**Requirements**: REQ-07
**Success Criteria** (what must be TRUE):
  1. Existe a base nova em `datasets/base_nova/` (NER inglês + POS português) no formato dos loaders.
  2. Os 5 modelos rodam sobre a base nova e o agregador produz a tabela comparativa correspondente.
  3. Resultados das duas bases ficam separados em `resultados/` para comparação mapeada × nova.
**Plans**: TBD

Plans:
- [ ] 05-01: Geração/curadoria das sentenças da base nova nos formatos esperados
- [ ] 05-02: Execução dos 5 modelos na base nova + relatório comparativo

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5
(Fases 2 e 3 são independentes entre si — podem rodar em paralelo após a Fase 1.)

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Fundação — contrato e leitura | 2/2 | Complete | 2026-06-16 |
| 2. Baselines tradicionais | 2/2 | Complete | 2026-06-16 |
| 3. Runner LLM (3 LLMs, Ollama) | 2/2 | Complete | 2026-06-17 |
| 4. Agregador e relatório | 0/2 | Not started | - |
| 5. Base nova e generalização | 0/2 | Not started | - |
</content>
