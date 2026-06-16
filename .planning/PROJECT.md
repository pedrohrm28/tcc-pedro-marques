# TCC II — Comparativo de LLMs open-source vs. modelos tradicionais (NER e POS tagging)

## What This Is

Ferramenta de avaliação reprodutível que compara o desempenho de **LLMs open-source** (gpt-oss 20B e 120B, via Ollama) contra **modelos tradicionais de extração** — um **CRF** (Conditional Random Fields) para NER e um **modelo baseado em regras** para POS tagging — usando anotações de referência (gold standard) curadas por linguistas. É a continuação do TCC I, que comparou o GPT-4.1 Nano contra esses mesmos dois baselines; aqui o LLM proprietário é trocado por LLMs open-source.

## Core Value

Produzir uma **tabela comparativa única e defensável** (precisão, cobertura, F1) dos 4 modelos sobre as mesmas sentenças, com discrepâncias token a token para análise qualitativa — tudo reprodutível (`temperature=0`, `seed=42`).

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] REQ-01: Contrato de saída comum (`.jsonl` de predições) que todos os scripts de modelo emitem
- [ ] REQ-02: Baseline CRF (NER) treinado a partir do `ner.csv` e prevendo sobre o conjunto de teste GMB
- [ ] REQ-03: Baseline baseado em regras (POS/UPOS) sobre o subconjunto Bosque (.conllu)
- [ ] REQ-04: Runner gpt-oss (20B e 120B via Ollama) para NER e UPOS, com `temperature=0`/`seed=42`
- [ ] REQ-05: Agregador (`comparativo_gold.py`) que alinha predições ao gold e calcula precisão/cobertura/F1 (por classe, micro, e nível de entidade para NER)
- [ ] REQ-06: Saída final: tabela comparativa dos 4 modelos + CSV de discrepâncias token a token
- [ ] REQ-07: Geração da base nova (sentenças fora de domínio) e execução dos 4 modelos sobre ela

### Out of Scope

- Corpus de NER em português — o NER do TCC I sempre foi o GMB (inglês); só a tarefa de POS é em português (Bosque). Confirmado pelo autor.
- Re-treinar/fine-tunar os LLMs — usamos os gpt-oss prontos via Ollama.
- Análise sintática/dependências do Bosque (colunas HEAD/DEPREL do CoNLL-U) — só usamos UPOS.
- Reaproveitar números do TCC I — decidido re-rodar os 4 modelos no mesmo pipeline para uniformidade total.

## Context

- **Continuação do TCC I** (`TCC I - Pedro Marques-revisado.pdf`): comparou GPT-4.1 Nano × CRF (NER, 150 sentenças IOB) × anotação por regras Bosque (POS, 1167 sentenças UPOS). Conclusão: métodos tradicionais venceram em métricas agregadas; LLM se destacou em flexibilidade.
- **Datasets** em `datasets/base_mapeada/`:
  - `GMB_dataset.txt` — Groningen Meaning Bank (inglês), gold de NER (token + tag IOB).
  - `ner.csv` — mesmo corpus do GMB com 25 colunas de *features* já extraídas → input de treino do CRF (conforme notebook Kaggle).
  - `pt_bosque-ud-train.conllu` / `pt_bosque-ud-test.conllu` — treebank Bosque/UD (português) → gold de UPOS.
- **Referências de origem dos baselines:**
  - CRF: https://www.kaggle.com/code/bavalpreet26/ner-using-crf/notebook
  - Modelo baseado em regras (Bosque): https://github.com/UniversalDependencies/UD_Portuguese-Bosque
- **Decisão de arquitetura:** scripts separados por modelo (heterogêneos: CRF treina sobre 1M linhas, regras é determinístico, LLMs são lentos via Ollama) + agregador puro que lê os `.jsonl`. Isolamento de falha, re-execução barata do LLM sem re-rodar o CRF, e metodologia defensável na banca.

## Constraints

- **Tech stack**: Python; `sklearn-crfsuite`/scikit-learn (CRF); Ollama (gpt-oss); parsing CoNLL/CoNLL-U.
- **Reprodutibilidade**: `temperature=0`, `seed=42` para os LLMs.
- **Ambiente**: Ollama precisa estar no ar com os modelos baixados (`gpt-oss:20b`, `gpt-oss:120b`); 120B é grande e lento.
- **Idioma**: NER em inglês (GMB), POS em português (Bosque) — intencional, herdado do TCC I.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Scripts separados + agregador, não orquestrador único | Modelos heterogêneos e LLMs lentos; isola falha e barateia re-execução do prompt | — Pending |
| Re-rodar os 4 modelos no mesmo pipeline | Uniformidade total + base nova não tem números prontos do TCC I | — Pending |
| GMB (inglês) como gold de NER | Herdado do TCC I; só POS é em português | — Pending |
| `GMB_dataset.txt` como gold, `ner.csv` só como input do CRF | As 25 colunas do csv são features do CRF, ruído para o gold | — Pending |

---
*Last updated: 2026-06-16 after project initialization*
