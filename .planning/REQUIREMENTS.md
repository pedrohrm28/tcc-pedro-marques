# Requirements: TCC II — Comparativo LLMs open-source vs. modelos tradicionais

## Scope

v1: Pipeline reprodutível que roda 3 modelos (CRF, regras, llama3.1:8b) sobre a base mapeada e produz uma tabela comparativa única + discrepâncias. Depois, geração e execução sobre a base nova.

> **Revisão (2026-06-17):** o LLM open-source passou de `gpt-oss:20b`/`gpt-oss:120b` para `llama3.1:8b` por restrição de hardware local (ver PROJECT.md). De 4 modelos para 3.

## Table Stakes

- **REQ-01 — Contrato de saída comum**: formato `.jsonl` único que todo script de modelo emite (uma linha por token: `{tarefa, modelo, sentenca_id, posicao, token, tag_predita}`). É o que desacopla os modelos do agregador.
- **REQ-05 — Agregador de métricas**: lê os `.jsonl` + gold, alinha token a token, calcula precisão/cobertura/F1 por classe, micro, e em nível de entidade (NER, esquema IOB). Saída em JSON.

## Features

- **REQ-02 — Baseline CRF (NER)** ✅ (02-01): `run_crf.py` treina o CRF a partir das features do `ner.csv`, prediz sobre o conjunto de teste GMB (1167 sentenças — alinhado ao N do POS; evolução sobre as 150 do TCC I), emite `.jsonl` no contrato comum. Modelo treinado persistido em disco para evitar re-treino.
- **REQ-03 — Baseline baseado em regras (POS/UPOS)** ✅ (02-02): `run_regras.py` aplica a anotação por regras sobre o subconjunto Bosque (`.conllu`), emite UPOS no contrato comum.
- **REQ-04 — Runner LLM**: `run_llm.py --modelo llama3.1:8b --tarefa ner|upos`, via Ollama, com `temperature=0`/`seed=42`, parsing robusto da saída do LLM de volta para o contrato comum. (CLI mantém `--modelo` parametrizável para permitir trocar de LLM sem mudar código.)
- **REQ-06 — Saída final**: tabela comparativa dos 3 modelos lado a lado (Markdown/CSV) + CSV de discrepâncias token a token para análise qualitativa.
- **REQ-07 — Base nova**: gerar sentenças inéditas fora de domínio (NER inglês + POS português), rodar os 3 modelos, agregar — cenário de generalização.

## Out of Scope

- Corpus de NER em português — NER herda o GMB (inglês) do TCC I.
- Fine-tuning do LLM — usado pronto via Ollama.
- Parsing de dependências sintáticas do Bosque (HEAD/DEPREL) — só UPOS.
- Reaproveitar números do TCC I — re-rodamos os 4 no mesmo pipeline.

## Success Criteria

1. `python comparativo_gold.py` produz uma tabela com os 3 modelos × (precisão, cobertura, F1) para NER e para UPOS.
2. CRF e regras rodam via código e geram `.jsonl` sem depender de números do TCC I.
3. `llama3.1:8b` roda via Ollama de forma reprodutível (`temperature=0`, `seed=42`).
4. Existe CSV de discrepâncias token a token por modelo.
5. O mesmo pipeline roda sobre a base nova quando ela existir.
