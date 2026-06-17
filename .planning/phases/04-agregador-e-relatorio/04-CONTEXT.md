# Phase 4: Agregador e relatório - Context

**Gathered:** 2026-06-17
**Status:** Ready for planning
**Source:** In-conversation design discussion (equivalente a discuss-phase)

<domain>
## Phase Boundary

Implementar o agregador que lê **todos os `.jsonl`** de predição (5 modelos × tarefa), alinha ao gold,
calcula métricas (por classe, micro, e nível de entidade para NER via seqeval) e emite:
- **JSON de métricas** por (modelo, tarefa) — REQ-05
- **Tabela comparativa** (Markdown + CSV) dos 5 modelos, uma por tarefa — REQ-06
- **CSV de discrepâncias** token-a-token por modelo — REQ-06

Atende **REQ-05** e **REQ-06**.

**Fora do escopo:** rodar os modelos (Fases 2-3) e a base nova (Fase 5). Esta fase só CONSOME os `.jsonl`.

**Pré-requisito de dados (não bloqueia o código):** as 6 rodadas dos LLMs da Fase 3 ainda NÃO foram
executadas — em `resultados/base_mapeada/` só existem `crf/ner.jsonl` e `regras/upos.jsonl`. O agregador
DEVE ser codificado e testado com `.jsonl` pequenos/sintéticos (mock), não depende dos dados reais para
existir. A tabela final real só sai quando o usuário rodar os LLMs. O agregador deve degradar
graciosamente quando faltam `.jsonl` de algum modelo (reportar "ausente", não quebrar).
</domain>

<decisions>
## Implementation Decisions

### D-01: Reusar a matemática de métricas do comparativo_gold.py legado, extraindo p/ módulo
Mover as funções de métrica validadas do TCC I para **`src/metricas.py`**:
- `metricas_token(gold_seqs, pred_seqs) -> (linhas_por_classe, micro_tuple)` — copiar como está (linha 149 do legado; já retorna dados, não imprime).
- `alinhar(gold_tokens, pred_pares)` — alinhamento por posição (linha 136). NOTA: no nosso pipeline os `.jsonl` JÁ vêm alinhados (garantido nas Fases 2-3), então o alinhamento ao gold é por (sentenca_id, posicao); a função legada serve de referência mas o agregador alinha via o contrato.
- `metricas_entidade(gold_seqs, pred_seqs)` — usa seqeval. **REFATORAR:** o legado IMPRIME no stdout (linhas 181-185); o módulo novo deve RETORNAR (precisao, cobertura, f1) de entidade + o dict por-tipo, sem print, para o agregador montar JSON/tabela.
O `comparativo_gold.py` legado fica **arquivado/referência** (não é mais o ponto de entrada; o main() dele chama Ollama inline — isso é trabalho da Fase 3 agora). LOCKED.

### D-02: Saída JSON — 1 arquivo por (modelo, tarefa)
Cada combinação (modelo, tarefa) gera UM JSON com campos: `por_classe` (P/R/F1/suporte por tag),
`micro` (P/R/F1), `entidade` (só NER, via seqeval: P/R/F1 + por-tipo), `n_tokens`/suporte total, e
`tempo`/`velocidade` (lido do `.meta.json` da Fase 3, quando existir, para os LLMs). Modular: re-rodar
1 modelo reescreve só o JSON dele. A tabela é montada lendo todos os JSONs. LOCKED.
- Local sugerido: `resultados/<base>/<modelo_sanitizado>/<tarefa>.metricas.json` (mesma convenção de pasta do contrato).

### D-03: Tabela comparativa — 1 por tarefa, Markdown + CSV
Uma tabela para **NER**, outra para **UPOS**. Linhas = os 5 modelos (crf, regras, llama3.1:8b,
qwen2.5:3b, llama3.2:3b — só os que tiverem `.jsonl`). Colunas = precisão, cobertura, micro-F1
(+ F1 de entidade SÓ na tabela NER) + tempo/velocidade (preenchido só para os LLMs; CRF/regras ficam "—").
Emitir AMBOS Markdown e CSV, em `resultados/<base>/`. LOCKED.

### D-04: CSV de discrepâncias — completo com contexto
Colunas: `tarefa, modelo, sentenca_id, posicao, token, tag_gold, tag_predita` — uma linha por token
ONDE gold != predita. Permite filtrar por modelo/tarefa e achar padrões de erro. Um CSV por base
(`resultados/<base>/discrepancias.csv`) com os modelos empilhados (coluna `modelo` distingue). LOCKED.

### D-05: Gold via loaders, não re-parse
O gold vem de `carregar_gmb(limite=1167)` (NER) e `carregar_conllu(limite=1167)` (UPOS) — mesma fonte
das Fases 2-3. O agregador alinha cada `.jsonl` ao gold por (sentenca_id, posicao). Asserção: nº de
registros do `.jsonl` deve casar com o total de tokens do gold; se não, reportar erro claro (não métricas silenciosamente erradas). LOCKED.

### Claude's Discretion
- Nome do entrypoint: refatorar `comparativo_gold.py` para virar o agregador novo OU criar `agregar.py` novo + arquivar o legado. Preferência: novo módulo `src/metricas.py` (puro, testável) + um CLI agregador; o legado vira referência. A critério do planner.
- Como descobrir quais modelos têm `.jsonl` (varrer `resultados/<base>/*/` vs lista fixa de 5 modelos).
- Arredondamento/formatação dos números na tabela (ex 3 casas decimais, como o legado usa `digits=3`).
- Divisão em planos/waves. Sugestão: 04-01 = `src/metricas.py` (extrair+refatorar+testar, puro), 04-02 = CLI agregador (lê .jsonl, monta JSON + tabelas MD/CSV + CSV discrepâncias). A critério do planner.
- Se NER usa esquema IOB para seqeval (sim — o gold GMB é IOB; confirmar que seqeval recebe sequências por sentença).
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Métricas legadas a extrair (TCC I)
- `comparativo_gold.py` — `metricas_token` (l.149, retorna (linhas, micro) — copiar), `metricas_entidade`
  (l.173, seqeval — REFATORAR para retornar em vez de print), `alinhar` (l.136, referência).
  IGNORAR `consultar_llm`/`carregar_conll_iob`/`carregar_conllu`/`main` do legado (são da Fase 3 inline/legado).

### Contrato e gold
- `src/io/contrato.py` — `Registro`, `ler_jsonl(caminho)` (lê os .jsonl de predição), `caminho_resultado(base, modelo, tarefa)` (':' → '_').
- `src/io/corpora.py` — `carregar_gmb(limite=1167)` (gold NER IOB), `carregar_conllu(limite=1167)` (gold UPOS).

### Predições existentes (entrada do agregador)
- `resultados/base_mapeada/crf/ner.jsonl` (25857 registros), `resultados/base_mapeada/regras/upos.jsonl` (27604 registros).
- Dos LLMs: AINDA NÃO existem — o agregador deve tratar ausência graciosamente.

### Métricas/meta da Fase 3
- Os `.meta.json` de tempo/velocidade por (modelo,tarefa) emitidos pela Fase 3 (D-08 da Fase 3) — fonte das colunas de tempo/velocidade na tabela.

### Dependência
- `requirements.txt` deve conter `seqeval` (usado para métricas de entidade).
</canonical_refs>

<specifics>
## Specific Ideas

**5 modelos esperados na tabela:** crf, regras, llama3.1:8b, qwen2.5:3b, llama3.2:3b. Mas só montar
linha para os que têm `.jsonl` presente (degradar gracioso; reportar quais faltam).

**Métricas por tarefa:**
- NER (inglês/GMB, IOB): por_classe + micro (token) + ENTIDADE (seqeval).
- UPOS (português/Bosque): por_classe + micro (token). Sem nível de entidade.

**Testes baratos:** testar `src/metricas.py` com sequências gold/pred sintéticas pequenas (valores de
P/R/F1 conhecidos à mão); testar o agregador com `.jsonl` mínimos em tmp (ex 2 modelos × 3 sentenças).
Não depender dos dados reais nem rodar LLM.
</specifics>

<deferred>
## Deferred Ideas

- Gráficos/plots da comparação — fora do escopo do TCC nesta fase (tabela + CSV bastam).
- Significância estatística entre modelos — não pedido; adiável.
</deferred>

---

*Phase: 04-agregador-e-relatorio*
*Context gathered: 2026-06-17 via in-conversation design discussion*
