# Phase 3: Runner LLM (Ollama) - Context

**Gathered:** 2026-06-17
**Status:** Ready for planning
**Source:** In-conversation design discussion (equivalente a discuss-phase) + benchmark de hardware

<domain>
## Phase Boundary

Implementar `run_llm.py`: um runner único que roda os **3 LLMs open-source** via Ollama
(`llama3.1:8b`, `qwen2.5:3b`, `llama3.2:3b`) nas duas tarefas (NER em inglês/GMB, UPOS em
português/Bosque), **1 sentença por chamada**, convertendo a saída do LLM de volta ao contrato
`.jsonl` da Fase 1 e registrando tempo/velocidade por modelo.

Atende **REQ-04** e os Success Criteria #1-#5 da Fase 3 no ROADMAP.

**Fora do escopo desta fase:** o agregador/métricas (Fase 4), a base nova (Fase 5). Esta fase só
produz os `.jsonl` de predição dos 3 LLMs e mede o tempo de cada um.
</domain>

<decisions>
## Implementation Decisions

### D-01: Três LLMs via runner único parametrizável
`run_llm.py --modelo <llama3.1:8b|qwen2.5:3b|llama3.2:3b> --tarefa <ner|upos>`. O mesmo código
roda os 3 modelos; `--modelo` é parametrizável (trocar de LLM sem mudar código). Total do TCC:
5 modelos (CRF + regras + 3 LLMs). LOCKED.

### D-02: 1 sentença por chamada (sem batching)
Cada chamada ao Ollama processa exatamente UMA sentença. Batching (várias sentenças/prompt) foi
**descartado**: reduz chamadas mas arrisca o alinhamento token-a-token, que o contrato exige 1:1
com o gold. Integridade dos dados > velocidade. LOCKED.

### D-03: Saída em JSON estruturado
O prompt pede ao LLM um **array JSON de tags** (uma por token, na ordem dos tokens da sentença).
Usar `format=json` do Ollama (`/api/generate` ou `/api/chat`). O parser valida que o comprimento
do array == nº de tokens da sentença; se não bater, aciona o fallback (D-04). LOCKED.
- O run_llm DEVE fornecer ao LLM a lista de tokens já tokenizada (vinda do loader), não pedir que
  o LLM re-tokenize — isso preserva o alinhamento.
- NER: tags IOB (ex "O", "B-geo", "I-per"). UPOS: as 17 UPOS válidas (mesmo conjunto do `run_regras.py`).

### D-04: Tag de fallback rastreável (sem quebrar alinhamento)
Quando a resposta do LLM não alinha (array com tamanho errado, JSON inválido, tag fora do esquema),
preencher o token problemático com tag de fallback: **NER → "O"**, **UPOS → "NOUN"** (tag mais
frequente). Marcar internamente quantos tokens caíram em fallback por (modelo, tarefa) — isso vira
**métrica de robustez** no relatório da Fase 4. O `.jsonl` NUNCA é emitido desalinhado. LOCKED.

### D-05: Reprodutibilidade
`temperature=0` e `seed=42` em toda chamada (options do Ollama). Prompts versionados (texto do
prompt fica no código/arquivo do repo, não improvisado em runtime). LOCKED.

### D-06: Execução retomável via .jsonl incremental + resume
Escrever cada sentença no `.jsonl` conforme processa (append incremental). Ao reiniciar, detectar
quais `sentenca_id` já estão no `.jsonl` e **pular** os já feitos, continuando de onde parou. Sem
dependências extras. Motivo: a rodada do 8B leva horas (~7,6 tok/s); não pode perder progresso se
travar. LOCKED.
- **Atenção (verificado):** `escrever_jsonl` de `src/io/contrato.py` abre com modo `"w"` (sobrescreve,
  NÃO faz append). O runner NÃO pode reusar `escrever_jsonl` para escrita incremental — deve abrir
  o arquivo em modo `"a"` (append) e serializar cada `Registro` no mesmo formato
  (`json.dumps(asdict(r), ensure_ascii=False) + "\n"`, UTF-8). Para detectar o que já foi feito,
  pode usar `ler_jsonl(caminho)` e coletar os `sentenca_id` presentes. Flag `--reiniciar`/`--overwrite`
  para começar do zero (sobrescrever).

### D-07: keep_alive para não recarregar o modelo entre sentenças
Passar `keep_alive` (ex. `-1` ou alto) nas chamadas para o Ollama manter o modelo em memória durante
toda a rodada. Sem isso, o modelo descarrega após ~5 min e recarregar custa ~8-30s (medido). Otimização
SEGURA — não afeta alinhamento. LOCKED.

### D-08: Métricas de tempo/velocidade por modelo
Registrar tempo total da rodada e velocidade (tok/s e/ou sentenças/s) por (modelo, tarefa). A API
`/api/generate` retorna `eval_count`, `eval_duration`, `load_duration` — usar esses campos. Persistir
num arquivo (ex. `resultados/base_mapeada/<modelo>/<tarefa>.meta.json` ou um CSV de tempos) para a
tabela comparativa da Fase 4 incluir o eixo velocidade. LOCKED.

### Claude's Discretion
- Biblioteca de acesso ao Ollama: cliente HTTP via `requests` (já está em requirements.txt) chamando
  `http://localhost:11434/api/generate`, OU o pacote `ollama` (PyPI). Preferência leve: `requests`,
  para não adicionar dependência — mas a critério do planner/executor.
- Texto exato dos prompts de NER e UPOS (instruções, exemplos few-shot se necessário) — desenhar para
  maximizar tags válidas, mantendo determinismo. Versionar no repo.
- Estrutura interna do código (funções, módulos), desde que testável e com alinhamento garantido.
- Formato exato do arquivo de métricas (JSON vs CSV).
- Limite de `num_predict` por chamada (teto de tokens) — pode ajudar a evitar respostas longas demais.
- Número de plans e divisão em waves (sugestão: cliente+prompts+parser numa base, emissão/resume/métricas
  na outra), a critério do planner.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Contrato de saída (.jsonl)
- `src/io/contrato.py` — `Registro` (campos tarefa/modelo/sentenca_id/posicao/token/tag_predita),
  `escrever_jsonl` (modo "w" — sobrescreve!), `ler_jsonl`, `caminho_resultado(base, modelo, tarefa)`.
  `caminho_resultado` sanitiza ':' → '_' (ex `llama3.1:8b` → pasta `llama3.1_8b`).

### Loaders de corpora (test sets, tokens já tokenizados)
- `src/io/corpora.py` — `carregar_gmb(limite=1167)` (NER, sentenças GMB "N.0" com pares
  (token, tag_IOB_gold)); `carregar_conllu(caminho=..., limite=1167)` (UPOS, sentenças Bosque
  "CF756-1" com pares (token, upos_gold)). Os runners iteram esses na ORDEM do loader e usam
  `enumerate(s.pares)` para `posicao`.

### Baselines da Fase 2 (padrão de runner + emissão + alinhamento a copiar)
- `run_crf.py` — runner NER que emite `.jsonl` alinhado a `carregar_gmb(limite=1167)`; padrão de
  asserção defensiva de alinhamento antes de emitir.
- `run_regras.py` — runner UPOS; tem o conjunto `UPOS_VALIDOS` (17 tags) que o LLM UPOS deve respeitar.
- `tests/test_run_crf.py`, `tests/test_run_regras.py` — padrões de teste de alinhamento do `.jsonl`.

### Ambiente
- Ollama 0.30.6 instalado (`C:\Users\paula\AppData\Local\Programs\Ollama\ollama.exe`), API em
  `http://localhost:11434`. 3 modelos baixados e testados (`temperature=0/seed=42` confirmado).
</canonical_refs>

<specifics>
## Specific Ideas

**Velocidades medidas (API HTTP, temperature=0/seed=42, GTX 1650 4 GB):**
- `llama3.1:8b` — ~7,6 tok/s (42% GPU / 58% CPU offload) → rodada longa (horas); resume crítico.
- `llama3.2:3b` — ~45 tok/s (80% GPU).
- `qwen2.5:3b` — ~59 tok/s (100% GPU) — ~7,7× o 8B.

**Volume:** 1167 sentenças × 2 tarefas × 3 modelos = 6 rodadas de 1167 chamadas (7002 chamadas no total).

**Contrato de emissão (igual à Fase 2):** para cada sentença `s` do loader (na ordem) e cada
`posicao, (token, _gold)` em `enumerate(s.pares)`, emitir
`Registro(tarefa, modelo=<nome com ':'>, sentenca_id=s.sentenca_id, posicao, token, tag_predita)`.
O `modelo` no Registro mantém o nome real (ex "llama3.1:8b"); a sanitização ':'→'_' é só no caminho do arquivo.

**Asserção de alinhamento (copiar do run_crf):** antes de emitir cada sentença, garantir que a
lista de tags tem o mesmo comprimento que `s.pares`; se não, aplicar fallback token-a-token (D-04).
</specifics>

<deferred>
## Deferred Ideas

- Retry da sentença N vezes antes do fallback — considerado, mas adiado: começamos só com fallback
  rastreável (D-04). Pode ser adicionado depois se a taxa de fallback for alta.
- Cache da resposta crua do LLM por sentença (re-parsear sem re-chamar) — adiado em favor do
  `.jsonl` incremental (D-06), mais simples.
</deferred>

---

*Phase: 03-runner-llm-ollama*
*Context gathered: 2026-06-17 via in-conversation design discussion + hardware benchmark*
