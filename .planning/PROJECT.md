# TCC II — Comparativo de LLMs open-source vs. modelos tradicionais (NER e POS tagging)

## What This Is

Ferramenta de avaliação reprodutível que compara o desempenho de **LLMs open-source** (3 modelos, via Ollama: `llama3.1:8b`, `qwen2.5:3b`, `llama3.2:3b`) contra **modelos tradicionais de extração** — um **CRF** (Conditional Random Fields) para NER e um **modelo baseado em regras** para POS tagging — usando anotações de referência (gold standard) curadas por linguistas. É a continuação do TCC I, que comparou o GPT-4.1 Nano contra esses mesmos dois baselines; aqui o LLM proprietário é trocado por LLMs open-source. **5 modelos no total.**

> **Revisão (2026-06-17):** o plano original previa `gpt-oss:20b` e `gpt-oss:120b` via Ollama. Esses modelos não rodam no hardware disponível (7,8 GB RAM, GTX 1650 4 GB VRAM, ~16 GB de disco livre): o 20b precisa de ~16 GB de memória e o 120b de ~80 GB + ~65 GB de download. Decisão: substituir pelos LLMs open-source que rodam localmente.
>
> **Desenho final (2026-06-17): 3 LLMs**, escolhidos para virar também um eixo de comparação tamanho/velocidade/qualidade em hardware modesto. Velocidades medidas (API HTTP, `temperature=0`/`seed=42`, GTX 1650 4 GB):
> - **`llama3.1:8b`** — maior/mais forte, porém roda 42% GPU / 58% CPU (offload): **~7,6 tok/s**.
> - **`llama3.2:3b`** — 80% GPU / 20% CPU: **~45 tok/s**.
> - **`qwen2.5:3b`** — **100% GPU**: **~59 tok/s** (~7,7× o 8B).
>
> Os três responderam corretamente no smoke test. O trade-off é claro: o gargalo do 8B não é "ser grande", é o offload p/ CPU; um 3B que cabe 100% na GPU é ~7,7× mais rápido. Isso é um achado do TCC, não só uma limitação.
>
> Todos rodam **1 sentença por chamada** (sem batching) para garantir alinhamento token-a-token 1:1 com o gold — integridade dos dados acima de velocidade. A pergunta de pesquisa passa a incluir **LLM × LLM** (tamanho/velocidade/qualidade), além de **LLMs × tradicionais**.

## Core Value

Produzir uma **tabela comparativa única e defensável** (precisão, cobertura, F1) dos 5 modelos sobre as mesmas sentenças, com discrepâncias token a token para análise qualitativa — tudo reprodutível (`temperature=0`, `seed=42`).

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] REQ-01: Contrato de saída comum (`.jsonl` de predições) que todos os scripts de modelo emitem
- [ ] REQ-02: Baseline CRF (NER) treinado a partir do `ner.csv` e prevendo sobre o conjunto de teste GMB
- [ ] REQ-03: Baseline baseado em regras (POS/UPOS) sobre o subconjunto Bosque (.conllu)
- [ ] REQ-04: Runner LLM (`run_llm.py --modelo <nome>`) via Ollama p/ os 3 LLMs (`llama3.1:8b`, `qwen2.5:3b`, `llama3.2:3b`) em NER e UPOS, 1 sentença/chamada, `temperature=0`/`seed=42`
- [ ] REQ-05: Agregador (`comparativo_gold.py`) que alinha predições ao gold e calcula precisão/cobertura/F1 (por classe, micro, e nível de entidade para NER)
- [ ] REQ-06: Saída final: tabela comparativa dos 5 modelos (+ coluna de tempo/velocidade por LLM) + CSV de discrepâncias token a token
- [ ] REQ-07: Geração da base nova (sentenças fora de domínio) e execução dos 5 modelos sobre ela

### Out of Scope

- Corpus de NER em português — o NER do TCC I sempre foi o GMB (inglês); só a tarefa de POS é em português (Bosque). Confirmado pelo autor.
- Re-treinar/fine-tunar os LLMs — usamos os modelos prontos via Ollama.
- Análise sintática/dependências do Bosque (colunas HEAD/DEPREL do CoNLL-U) — só usamos UPOS.
- Reaproveitar números do TCC I — decidido re-rodar os 5 modelos no mesmo pipeline para uniformidade total.
- Batching de sentenças no prompt do LLM — descartado: arrisca o alinhamento token-a-token; rodamos 1 sentença/chamada.

## Context

- **Continuação do TCC I** (`TCC I - Pedro Marques-revisado.pdf`): comparou GPT-4.1 Nano × CRF (NER, 150 sentenças IOB) × anotação por regras Bosque (POS, 1167 sentenças UPOS). Conclusão: métodos tradicionais venceram em métricas agregadas; LLM se destacou em flexibilidade.
- **Datasets** em `datasets/base_mapeada/`:
  - `GMB_dataset.txt` — Groningen Meaning Bank (inglês), gold de NER (token + tag IOB).
  - `ner.csv` — mesmo corpus do GMB com 25 colunas de *features* já extraídas → input de treino do CRF (conforme notebook Kaggle).
  - `pt_bosque-ud-train.conllu` / `pt_bosque-ud-test.conllu` — treebank Bosque/UD (português) → gold de UPOS.
- **Referências de origem dos baselines:**
  - CRF: https://www.kaggle.com/code/bavalpreet26/ner-using-crf/notebook
  - Modelo baseado em regras (Bosque): https://github.com/UniversalDependencies/UD_Portuguese-Bosque
- **Decisão de arquitetura:** scripts separados por modelo (heterogêneos: CRF treina sobre 1M linhas, regras é determinístico, o LLM é lento via Ollama) + agregador puro que lê os `.jsonl`. Isolamento de falha, re-execução barata do LLM sem re-rodar o CRF, e metodologia defensável na banca.

## Constraints

- **Tech stack**: Python; `sklearn-crfsuite`/scikit-learn (CRF); Ollama (3 LLMs); parsing CoNLL/CoNLL-U.
- **Reprodutibilidade**: `temperature=0`, `seed=42` para os LLMs.
- **Ambiente**: Ollama no ar com os 3 modelos baixados: `llama3.1:8b` (4,9 GB, roda 58% CPU / 42% GPU, ~7,6 tok/s), `qwen2.5:3b` e `llama3.2:3b` (~2 GB cada, cabem 100% na GPU GTX 1650 4 GB). Máquina local: 7,8 GB RAM.
- **Idioma**: NER em inglês (GMB), POS em português (Bosque) — intencional, herdado do TCC I.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Scripts separados + agregador, não orquestrador único | Modelos heterogêneos e LLMs lentos; isola falha e barateia re-execução do prompt | — Pending |
| Re-rodar os 5 modelos no mesmo pipeline | Uniformidade total + base nova não tem números prontos do TCC I | — Pending |
| GMB (inglês) como gold de NER | Herdado do TCC I; só POS é em português | — Pending |
| `GMB_dataset.txt` como gold, `ner.csv` só como input do CRF | As 25 colunas do csv são features do CRF, ruído para o gold | — Pending |
| LLMs = `llama3.1:8b` + `qwen2.5:3b` + `llama3.2:3b`, não gpt-oss 20b/120b | Hardware local não roda 20b/120b; 3 LLMs viram eixo de comparação tamanho/velocidade/qualidade (8B na CPU vs. 3B na GPU) | ✅ 2026-06-17 |
| 1 sentença por chamada (sem batching) | Garante alinhamento token-a-token 1:1 com o gold; integridade > velocidade | ✅ 2026-06-17 |

---
*Last updated: 2026-06-17 — LLMs definidos: llama3.1:8b + qwen2.5:3b + llama3.2:3b (3 LLMs + 2 tradicionais = 5 modelos); 1 sentença/chamada*
