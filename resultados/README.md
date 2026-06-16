# Resultados — Convenção de Pastas e Schema de Saída

Este diretório armazena os arquivos `.jsonl` produzidos por cada modelo em cada tarefa.
A estrutura separa **base_mapeada** (corpus original do TCC I) de **base_nova** (corpus
fora de domínio, preenchida na Fase 5).

---

## Schema do Registro de Predição

Cada linha de um `.jsonl` é um objeto JSON com os seguintes campos (REQ-01):

```json
{
  "tarefa":      "ner",
  "modelo":      "crf",
  "sentenca_id": "1.0",
  "posicao":     0,
  "token":       "The",
  "tag_predita": "O"
}
```

| Campo         | Tipo | Descrição                                                                |
|---------------|------|--------------------------------------------------------------------------|
| `tarefa`      | str  | `"ner"` ou `"upos"` — identifica a tarefa de avaliação                  |
| `modelo`      | str  | Nome do modelo: `"crf"`, `"regras"`, `"gpt-oss:20b"`, `"gpt-oss:120b"` ou `"gold"` |
| `sentenca_id` | str  | ID estável da sentença: `"1.0"` (GMB) ou `"CF756-1"` (Bosque)          |
| `posicao`     | int  | Índice 0-based do token dentro da sentença — chave de alinhamento       |
| `token`       | str  | Token de superfície (preservado com acentos, ex `"notícia"`)            |
| `tag_predita` | str  | Tag IOB para NER (ex `"B-ORG"`, `"O"`) ou UPOS para POS (ex `"NOUN"`)  |

O gold padrão reutiliza o **mesmo schema** com `modelo="gold"`.
O alinhamento no agregador (Fase 4) usa a chave `(tarefa, sentenca_id, posicao)`.

---

## Convenção de Caminho

Os caminhos dos arquivos `.jsonl` são gerados pela função `caminho_resultado` em
`src/io/contrato.py`:

```
resultados/<base>/<modelo_sanitizado>/<tarefa>.jsonl
```

Exemplos:

```
resultados/base_mapeada/crf/ner.jsonl
resultados/base_mapeada/regras/upos.jsonl
resultados/base_mapeada/gpt-oss_20b/ner.jsonl
resultados/base_mapeada/gpt-oss_20b/upos.jsonl
resultados/base_mapeada/gpt-oss_120b/ner.jsonl
resultados/base_mapeada/gpt-oss_120b/upos.jsonl
resultados/base_mapeada/gold/ner.jsonl
resultados/base_mapeada/gold/upos.jsonl
```

### Por que sanitizar `:`?

O Windows proíbe o caractere `:` em nomes de arquivo. Por isso, `caminho_resultado`
substitui `:` por `_` no nome do modelo:
- `gpt-oss:20b`  → diretório `gpt-oss_20b`
- `gpt-oss:120b` → diretório `gpt-oss_120b`

O campo `modelo` no JSON **mantém** o valor original (com `:`), pois é apenas um
identificador de metadado — não um caminho de arquivo.

---

## Estrutura de Pastas

```
resultados/
  base_mapeada/               # Corpus original (TCC I): GMB (NER) + Bosque (UPOS)
    crf/
      ner.jsonl               # Predições do CRF (NER sobre GMB)
    regras/
      upos.jsonl              # Predições do modelo baseado em regras (UPOS sobre Bosque)
    gpt-oss_20b/
      ner.jsonl               # Predições do gpt-oss:20b (NER)
      upos.jsonl              # Predições do gpt-oss:20b (UPOS)
    gpt-oss_120b/
      ner.jsonl               # Predições do gpt-oss:120b (NER)
      upos.jsonl              # Predições do gpt-oss:120b (UPOS)
    gold/
      ner.jsonl               # Anotações de referência (NER, GMB)
      upos.jsonl              # Anotações de referência (UPOS, Bosque)
  base_nova/                  # Corpus fora de domínio (preenchida na Fase 5)
    <mesma estrutura acima>
```

---

## Quais modelos produzem o quê?

| Modelo           | Tarefa(s)    | Corpus      | Fase      |
|------------------|--------------|-------------|-----------|
| `crf`            | NER          | GMB         | Fase 2    |
| `regras`         | UPOS         | Bosque      | Fase 2    |
| `gpt-oss:20b`    | NER + UPOS   | GMB/Bosque  | Fase 3    |
| `gpt-oss:120b`   | NER + UPOS   | GMB/Bosque  | Fase 3    |
| `gold`           | NER + UPOS   | GMB/Bosque  | Fase 1    |

---

## Regra de separação base_mapeada × base_nova

- **base_mapeada**: todas as sentenças presentes no TCC I — conjunto fixo, mapeado.
  Usada para comparação com resultados históricos.
- **base_nova**: sentenças fora de domínio, geradas na Fase 5. Testa generalização.

Os dois experimentos **nunca se misturam** — arquivos de base_mapeada e base_nova
ficam em subárvores separadas dentro de `resultados/`.
