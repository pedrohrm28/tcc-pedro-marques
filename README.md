# TCC — Comparativo de LLMs open-source com padrão-ouro (NER e POS tagging)

Avaliação de modelos de linguagem open-source (gpt-oss 20B/120B via Ollama) em tarefas de
**extração/identificação de entidades (NER, esquema IOB)** e **classificação morfossintática
(UPOS)** para o português, comparando as saídas com anotações de referência (gold standard)
produzidas por linguistas.

## Objetivo

Verificar como os modelos se comportam em dois cenários:

1. **Base já mapeada** (`datasets/base_mapeada/`): corpora usados no TCC I — conjunto de
   teste do CRF (150 sentenças, IOB) e subconjunto do treebank Bosque/UD (1167 sentenças,
   UPOS). Permite comparação direta com os resultados do GPT-4.1 Nano e do CRF.
2. **Base nova** (`datasets/base_nova/`): sentenças inéditas, fora do domínio dos corpora
   originais, para avaliar generalização dos modelos.

## Estrutura

```
├── comparativo_gold.py      # script de avaliação (métricas + discrepâncias)
├── datasets/
│   ├── base_mapeada/        # coloque aqui os corpora do TCC I (.conll / .conllu)
│   └── base_nova/           # coloque aqui a base nova
├── resultados/              # saídas geradas pelo script
└── requirements.txt
```

## Uso

```bash
pip install -r requirements.txt
ollama pull gpt-oss:20b   # ou gpt-oss:120b

# NER (formato CoNLL: token<TAB>tag IOB, sentenças separadas por linha vazia)
python comparativo_gold.py --tarefa ner --gold datasets/base_mapeada/corpus_crf.conll --modelo gpt-oss:20b --saida resultados/ner_mapeada

# POS tagging (formato CoNLL-U)
python comparativo_gold.py --tarefa upos --gold datasets/base_mapeada/bosque.conllu --modelo gpt-oss:20b --saida resultados/upos_mapeada
```

Saídas: métricas de precisão, cobertura e F1 (por classe, micro e em nível de entidade
para NER) em JSON, e CSV de discrepâncias token a token para análise qualitativa.

Reprodutibilidade: `temperature=0` e `seed=42`.
