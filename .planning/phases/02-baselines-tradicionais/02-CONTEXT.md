# Phase 2: Baselines tradicionais — Context

**Gathered:** 2026-06-16
**Status:** Ready for planning
**Source:** Interactive (light workflow — sem discuss-phase formal)

<domain>
## Phase Boundary

Implementar os dois modelos de referência (baselines tradicionais) rodando via código e emitindo o contrato `.jsonl` comum definido na Fase 1:
- **REQ-02 — CRF (NER, inglês)**: `run_crf.py` treina sobre as features do `ner.csv`, persiste o modelo, prediz sobre o conjunto de teste GMB e emite `.jsonl`.
- **REQ-03 — Regras (POS/UPOS, português)**: `run_regras.py` anota UPOS por regras sobre o Bosque e emite `.jsonl`.

Fora de escopo: agregador de métricas (REQ-05, fase posterior), LLMs (Fases 3-4), base nova (Fase 5).
</domain>

<decisions>
## Implementation Decisions (LOCKED)

### CRF (run_crf.py)
- **Usar todas as 25 features do `ner.csv`** como entrada do CRF (lemma, pos, shape, janelas prev/next-*, prev-iob/prev-prev-iob, etc.). Fiel ao notebook Kaggle de origem (https://www.kaggle.com/code/bavalpreet26/ner-using-crf/notebook).
- **Persistir o modelo treinado em disco** (joblib ou pickle, ex. `modelos/crf_ner.pkl`) para que re-rodar o agregador NÃO exija re-treino — atende diretamente o SC#3 da fase.
- **Split treino/teste explícito**: treinar nas sentenças FORA do conjunto de teste e prever sobre as 1167 sentenças de avaliação. Evitar vazamento treino/teste.

### Regras (run_regras.py)
- **Anotação UPOS por regras** (léxico + heurísticas morfológicas) sobre o Bosque, inspirada no repositório UD_Portuguese-Bosque (https://github.com/UniversalDependencies/UD_Portuguese-Bosque).

### Contrato de saída
- Ambos scripts emitem o contrato `.jsonl` da Fase 1 via `src/io/contrato.py` (`Registro` + `escrever_jsonl` + `caminho_resultado`), uma linha por token: `{tarefa, modelo, sentenca_id, posicao, token, tag_predita}`.
- `tarefa="ner"` para o CRF, `tarefa="upos"` para as regras.
- Saída em `resultados/base_mapeada/`.

### Tamanho de amostra (decisão herdada — ver STATE.md Decisions Log)
- **NER usa 1167 sentenças** (= N do POS), NÃO as 150 do TCC I. Robustez sobre comparabilidade 1:1; apresentado como evolução do TCC I.

### Claude's Discretion
- Formato exato de serialização do modelo (joblib vs pickle), hiperparâmetros do CRF (c1/c2, max_iterations), e estrutura precisa das regras de POS ficam a critério do planner/implementação, desde que as decisões travadas acima sejam respeitadas.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Contrato e loaders (Fase 1)
- `src/io/contrato.py` — `Registro` dataclass + `escrever_jsonl`/`ler_jsonl`/`caminho_resultado`. Schema de saída obrigatório.
- `src/io/corpora.py` — `carregar_gmb` (GMB gold, IOB) e `carregar_conllu` (Bosque gold, UPOS). `limite` = first-N estável.
- `resultados/README.md` — convenção de pastas e schema documentado.

### Requisitos e roadmap
- `.planning/REQUIREMENTS.md` — REQ-02, REQ-03.
- `.planning/ROADMAP.md` — Fase 2, success criteria.

### Referências externas dos baselines
- CRF: https://www.kaggle.com/code/bavalpreet26/ner-using-crf/notebook
- Regras POS: https://github.com/UniversalDependencies/UD_Portuguese-Bosque
</canonical_refs>

<specifics>
## Fatos verificados sobre os dados (CRÍTICO para o planner)

**`ner.csv`** (input de features do CRF):
- 1.050.797 linhas (~1,05M tokens), 25 colunas + índice. Header:
  `,lemma,next-lemma,next-next-lemma,next-next-pos,next-next-shape,next-next-word,next-pos,next-shape,next-word,pos,prev-iob,prev-lemma,prev-pos,prev-prev-iob,prev-prev-lemma,prev-prev-pos,prev-prev-shape,prev-prev-word,prev-shape,prev-word,sentence_idx,shape,word,tag`
- `sentence_idx` agrupa tokens em sentenças; `word` = token; `tag` = label IOB gold.
- **~41.776 valores distintos de `sentence_idx`** (máx 47959). ASCII/CSV padrão.

**`GMB_dataset.txt`** (gold de NER usado por `carregar_gmb`):
- TSV latin-1, **2999 sentenças** (coluna `Sentence #`, ex. `1.0`).

**⚠ DESCASAMENTO A RESOLVER (concern primário de planejamento):**
`ner.csv` (~41.776 sentenças) e `GMB_dataset.txt` (2999 sentenças via `carregar_gmb`) são groupings DIFERENTES do GMB. O CRF treina/prediz sobre linhas do `ner.csv`, mas o gold para alinhamento do `.jsonl` (Fase 5 / agregador) vem de `carregar_gmb`. O planner DEVE definir explicitamente:
1. Como o conjunto de teste do CRF (1167 sentenças) é definido e como ele se alinha às sentenças gold de `carregar_gmb` (mesma ordem? mesmos tokens? mesmo id?).
2. Garantir que `sentenca_id`/`posicao` emitidos no `.jsonl` permitam alinhamento token-a-token com o gold no agregador.
Se os dois arquivos compartilham ordem de tokens, definir o teste como as primeiras 1167 sentenças de `carregar_gmb` e mapear; caso contrário, o teste do CRF deve ser derivado do MESMO grouping do gold. Resolver isso é pré-requisito para o `.jsonl` ser comparável.
</specifics>

<deferred>
## Deferred Ideas
- Agregação de métricas, discrepâncias, e comparação final — REQ-05/REQ-06, fases posteriores.
- Otimização de hiperparâmetros do CRF além do baseline — não nesta fase.
</deferred>

---

*Phase: 02-baselines-tradicionais*
*Context gathered: 2026-06-16 (interactive, light workflow)*
