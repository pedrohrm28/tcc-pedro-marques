# Requirements: TCC II — Comparativo LLMs open-source vs. modelos tradicionais

## Scope

v1: Pipeline reprodutível que roda 5 modelos (CRF, regras, llama3.1:8b, qwen2.5:3b, llama3.2:3b) sobre a base mapeada e produz uma tabela comparativa única + discrepâncias. Depois, geração e execução sobre a base nova.

> **Revisão (2026-06-17):** o LLM open-source passou de `gpt-oss:20b`/`gpt-oss:120b` (não rodam no hardware local) para **3 LLMs**: `llama3.1:8b` (CPU/offload) + `qwen2.5:3b` + `llama3.2:3b` (cabem na GPU). Total: 5 modelos. Os 3 LLMs também viram eixo de comparação tamanho/velocidade/qualidade. Todos rodam 1 sentença/chamada (sem batching) para preservar o alinhamento token-a-token. Ver PROJECT.md.

## Table Stakes

- **REQ-01 — Contrato de saída comum**: formato `.jsonl` único que todo script de modelo emite (uma linha por token: `{tarefa, modelo, sentenca_id, posicao, token, tag_predita}`). É o que desacopla os modelos do agregador.
- **REQ-05 — Agregador de métricas**: lê os `.jsonl` + gold, alinha token a token, calcula precisão/cobertura/F1 por classe, micro, e em nível de entidade (NER, esquema IOB). Saída em JSON.

## Features

- **REQ-02 — Baseline CRF (NER)** ✅ (02-01): `run_crf.py` treina o CRF a partir das features do `ner.csv`, prediz sobre o conjunto de teste GMB (1167 sentenças — alinhado ao N do POS; evolução sobre as 150 do TCC I), emite `.jsonl` no contrato comum. Modelo treinado persistido em disco para evitar re-treino.
- **REQ-03 — Baseline baseado em regras (POS/UPOS)** ✅ (02-02): `run_regras.py` aplica a anotação por regras sobre o subconjunto Bosque (`.conllu`), emite UPOS no contrato comum.
- **REQ-04 — Runner LLM**: `run_llm.py --modelo <llama3.1:8b|qwen2.5:3b|llama3.2:3b> --tarefa ner|upos`, via Ollama, com `temperature=0`/`seed=42`, **1 sentença por chamada** (sem batching, para preservar alinhamento), parsing robusto da saída do LLM de volta para o contrato comum. `--modelo` parametrizável: o mesmo script roda os 3 LLMs. Registrar tempo/velocidade por modelo (eixo de comparação).
- **REQ-06 — Saída final**: tabela comparativa dos 5 modelos lado a lado (Markdown/CSV), incluindo tempo/velocidade dos LLMs, + CSV de discrepâncias token a token para análise qualitativa.
- **REQ-07 — Base nova**: gerar sentenças inéditas fora de domínio (NER inglês + POS português), rodar os 5 modelos, agregar — cenário de generalização.

## Out of Scope

- Corpus de NER em português — NER herda o GMB (inglês) do TCC I.
- Fine-tuning dos LLMs — usados prontos via Ollama.
- Parsing de dependências sintáticas do Bosque (HEAD/DEPREL) — só UPOS.
- Reaproveitar números do TCC I — re-rodamos os 5 no mesmo pipeline.
- Batching de sentenças no prompt — descartado (risco ao alinhamento); 1 sentença/chamada.

## Success Criteria

1. `python comparativo_gold.py` produz uma tabela com os 5 modelos × (precisão, cobertura, F1) para NER e para UPOS.
2. CRF e regras rodam via código e geram `.jsonl` sem depender de números do TCC I.
3. Os 3 LLMs (`llama3.1:8b`, `qwen2.5:3b`, `llama3.2:3b`) rodam via Ollama de forma reprodutível (`temperature=0`, `seed=42`), 1 sentença/chamada.
4. Existe CSV de discrepâncias token a token por modelo.
5. O comparativo registra tempo/velocidade de cada LLM (eixo tamanho/velocidade/qualidade).
6. O mesmo pipeline roda sobre a base nova quando ela existir.
