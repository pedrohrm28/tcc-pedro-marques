---
phase: 04-agregador-e-relatorio
verified: 2026-06-17T00:00:00Z
status: passed
score: 3/3 success criteria MET (+ REQ-05/REQ-06 satisfied)
overrides_applied: 0
re_verification:
  previous_status: none
  previous_score: n/a
gaps: []
deferred:
  - truth: "Tabela final com os 3 LLMs (linhas + colunas tempo/tok_s preenchidas)"
    addressed_in: "Phase 3 (runtime do usuário) + consumido automaticamente pela Fase 4 sem mudança de código"
    evidence: "ROADMAP Phase 3 SC#4: 'Cada execução registra tempo total e velocidade (tok/s ou sent/s)'; agregar.ler_meta lê eval_duration_s/tok_por_seg que run_llm.py:185-186 escreve — wiring verificado end-to-end. Rodar os LLMs é runtime, fora do escopo da Fase 4 (04-CONTEXT.md l.18-24)."
---

# Phase 4: Agregador e relatório — Verification Report

**Phase Goal:** O agregador (`src/metricas.py` puro + `agregar.py` CLI) lê todos os `.jsonl`, alinha ao gold, calcula métricas (por classe, micro, e nível de entidade NER via seqeval) e monta a tabela comparativa dos 5 modelos + discrepâncias.
**Verified:** 2026-06-17
**Status:** PASSED
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
| --- | --- | --- | --- |
| 1 | Calcula precisão, cobertura e F1 por classe, micro, e em nível de entidade (NER/IOB) | ✓ MET | `src/metricas.py:33-54` `metricas_token` retorna `(linhas_por_classe, micro)`; `src/metricas.py:61-100` `metricas_entidade` retorna dict via seqeval (precision/recall/f1 + por_tipo). Run real: `crf/ner.metricas.json` tem `por_classe` (17 classes c/ P/R/F1/suporte), `micro` (P=R=F1=0.969), `entidade` (f1=0.776, por_tipo = art/eve/geo/gpe/nat/org/per/tim). UPOS tem por_classe (16) + micro (0.878), `entidade=None` (correto — sem nível de entidade). 25/25 testes verdes. |
| 2 | Emite tabela comparativa (MD/CSV) com modelos × tarefas, incluindo tempo/velocidade dos LLMs | ✓ MET | `agregar.py:243-287` monta+grava `tabela_ner.{md,csv}` e `tabela_upos.{md,csv}`. Run real gerou ambos. NER tem coluna `f1_entidade`, UPOS não (verificado nos 4 arquivos). CRF/regras mostram "—" em `tempo_s`/`tok_s`. Wiring de tempo/velocidade dos LLMs verificado: `agregar.ler_meta` (l.147-158) lê `eval_duration_s`/`tok_por_seg` que `run_llm.py:185-186` escreve no `.meta.json` — nomes de campo casam exatamente; teste sintético com `.meta.json` LLM retornou 12.5/3.4. |
| 3 | Emite CSV de discrepâncias token a token por modelo | ✓ MET | `agregar.py:290-307` `escrever_discrepancias`. Run real gerou `discrepancias.csv` com header exato `tarefa,modelo,sentenca_id,posicao,token,tag_gold,tag_predita`, 4149 linhas de dados, modelos empilhados (crf p/ ner, regras p/ upos). Uma linha por token onde gold != predita (`agregar.py:114-117`). |

**Score:** 3/3 truths MET

### Required Artifacts

| Artifact | Expected | Status | Details |
| --- | --- | --- | --- |
| `src/metricas.py` | metricas_token + metricas_entidade (RETORNA) + alinhar | ✓ VERIFIED | 100 linhas. 3 funções presentes (l.20/33/61). 0 `print(`. metricas_entidade termina em `return {...}` (l.95-100). Importa seqeval lazy com RuntimeError claro se ausente (l.78-82). |
| `agregar.py` | CLI: lê .jsonl, alinha ao gold por (sid,pos), reusa metricas, JSON+tabelas+discrepâncias, degradação graciosa | ✓ VERIFIED | 408 linhas. main() (l.384). Reusa `metricas_token/metricas_entidade` (l.33), `ler_jsonl/caminho_resultado` (l.31), `carregar_gmb/carregar_conllu` (l.32). NÃO reimplementa matemática (grep defaultdict/precision_score/tp[ = 0 matches). Alinhamento por (sentenca_id, posicao) l.101/111. |
| `tests/test_metricas.py` + `tests/test_agregar.py` | testes sintéticos sem dados reais/Ollama | ✓ VERIFIED | 25 testes passam em 0.98s (`rtk proxy python -m pytest`). |
| `resultados/base_mapeada/tabela_{ner,upos}.{md,csv}` | tabelas comparativas | ✓ VERIFIED | 4 arquivos regenerados na rodada de verificação; byte-idênticos aos commitados (git diff vazio → determinístico). |
| `resultados/base_mapeada/discrepancias.csv` | CSV token-a-token | ✓ VERIFIED | Regenerado, 4150 linhas, header exato. |
| `resultados/base_mapeada/{crf/ner,regras/upos}.metricas.json` | JSON D-02 por (modelo,tarefa) | ✓ VERIFIED | Regenerados; estrutura completa (por_classe/micro/entidade/n_tokens/tempo/velocidade). |

### Key Link Verification

| From | To | Via | Status | Details |
| --- | --- | --- | --- | --- |
| agregar.py | src.metricas | import + chamada | ✓ WIRED | l.33 import; l.131/137 chamadas. Sem reimplementação. |
| agregar.py | src.io.contrato | ler_jsonl/caminho_resultado | ✓ WIRED | l.31; usados l.337-338, 181, 229. |
| agregar.py | src.io.corpora | carregar_gmb/carregar_conllu | ✓ WIRED | l.32; LOADERS_GOLD l.38, usado l.55/334. |
| agregar.py | run_llm.py .meta.json | ler_meta (eval_duration_s/tok_por_seg) | ✓ WIRED | Campos casam (run_llm.py:185-186 ↔ agregar.py:158); teste sintético confirmou leitura 12.5/3.4. |
| agregar.py | resultados/<base>/*.{md,csv,json} | escrita de artefatos | ✓ WIRED | Run real gerou os 7 artefatos. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| --- | --- | --- | --- | --- |
| tabela_ner.{md,csv} | micro/f1_entidade do crf | metricas_token + metricas_entidade sobre 25857 tokens reais alinhados ao gold GMB | ✓ Sim (0.969 / 0.776) | ✓ FLOWING |
| tabela_upos.{md,csv} | micro do regras | metricas_token sobre 27604 tokens reais alinhados ao gold Bosque | ✓ Sim (0.878) | ✓ FLOWING |
| discrepancias.csv | 4149 linhas | tokens onde gold != predita (alinhamento real) | ✓ Sim | ✓ FLOWING |
| col tempo_s/tok_s (LLMs) | ler_meta | .meta.json da Fase 3 | N/A na base atual (LLMs não rodados) — "—" correto; wiring provado por teste sintético | ✓ FLOWING (caminho LLM verificado isoladamente) |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| --- | --- | --- | --- |
| Suite de testes | `rtk proxy python -m pytest tests/test_metricas.py tests/test_agregar.py -q` | 25 passed in 0.98s | ✓ PASS |
| Run real degradação graciosa | `python agregar.py --base base_mapeada` (após apagar artefatos) | 2 presente(s), 8 ausentes reportados, 7 arquivos gerados, sem exceção | ✓ PASS |
| Coluna f1_entidade só no NER | leitura dos 4 arquivos de tabela | NER tem f1_entidade=0.776; UPOS não tem a coluna | ✓ PASS |
| "—" tempo/tok_s p/ crf/regras | leitura tabela_*.csv | crf,...,—,— e regras,...,—,— | ✓ PASS |
| Determinismo | `git diff --stat resultados/` após regenerar | diff vazio (byte-idêntico) | ✓ PASS |
| Asserção D-05 (desalinhamento) | `alinhar_predicao` com 1 reg vs 2 tokens | RuntimeError("Desalinhamento: 1 registros vs 2 tokens do gold") | ✓ PASS |
| Wiring tempo/velocidade LLM | ler_meta com .meta.json sintético | (12.5, 3.4) lido corretamente | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| --- | --- | --- | --- | --- |
| REQ-05 | 04-01, 04-02 | Agregador de métricas (P/R/F1 por classe, micro, entidade via seqeval; JSON por modelo/tarefa) | ✓ SATISFIED | metricas.py + agregar.py; *.metricas.json reais |
| REQ-06 | 04-02 | Saída final: tabela comparativa MD+CSV por tarefa (com tempo/velocidade LLM, "—" p/ tradicionais) + discrepancias.csv; degradação graciosa | ✓ SATISFIED | tabelas + discrepancias.csv reais; ausentes reportados sem quebrar |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| --- | --- | --- | --- | --- |
| src/metricas.py | — | print() | none | 0 ocorrências — metricas_entidade RETORNA (refatoração do legado confirmada) |
| agregar.py | — | TODO/FIXME/stub/pass | none | 0 ocorrências |
| agregar.py | 365 | `except Exception` broad | ℹ️ Info | Intencional (D-05/D-06): erro por-modelo acumulado em resumo['erros'], não derruba os demais. Coerente com degradação graciosa. |

### Deferred Items

| # | Item | Addressed In | Evidence |
| --- | --- | --- | --- |
| 1 | Tabela com as 3 linhas de LLM + colunas tempo/tok_s preenchidas | Phase 3 runtime (consumido pela Fase 4 sem mudança de código) | Rodar os 6 `.jsonl` dos LLMs é runtime do usuário, explicitamente fora do escopo da Fase 4 (04-CONTEXT.md l.18-24). O wiring está pronto e verificado (run_llm.py:185-186 ↔ agregar.ler_meta). NÃO é gap. |

### Human Verification Required

Nenhum item requer verificação humana. Todos os critérios foram verificados programaticamente contra o código real e a saída de comandos executados. Não há comportamento visual, em tempo real ou de serviço externo a confirmar nesta fase (o agregador é puro consumo de arquivos + cálculo determinístico).

### Gaps Summary

Nenhum gap. Os 3 Success Criteria do ROADMAP estão MET, verificados contra o código real e a execução do agregador (não apenas contra os SUMMARYs):

- **SC#1** — `metricas_token` (por classe + micro) e `metricas_entidade` (entidade IOB via seqeval que RETORNA, 0 prints) existem e produzem números reais (crf NER micro 0.969 / entidade 0.776; regras UPOS 0.878).
- **SC#2** — Tabelas MD+CSV por tarefa geradas; NER com `f1_entidade`, UPOS sem; "—" para crf/regras; wiring tempo/velocidade dos LLMs verificado end-to-end (campos do `.meta.json` casam).
- **SC#3** — `discrepancias.csv` com header exato, 4149 linhas token-a-token, modelos empilhados.

Confirmações adicionais: 25/25 testes verdes; reuso de `src/metricas.py` (sem reimplementar matemática); degradação graciosa real (2 presentes, 8 ausentes reportados sem quebrar); asserção de integridade D-05 dispara com erro claro; saída determinística (regeneração byte-idêntica). A ausência dos `.jsonl` dos 3 LLMs é runtime da Fase 3 (fora do escopo), tratada graciosamente — corretamente classificada como deferred, não gap.

---

_Verified: 2026-06-17_
_Verifier: Claude (gsd-verifier)_
