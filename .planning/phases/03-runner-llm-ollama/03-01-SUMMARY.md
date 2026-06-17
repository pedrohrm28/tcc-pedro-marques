---
phase: 03-runner-llm-ollama
plan: 01
subsystem: llm
tags: [ollama, parser, prompts, ner, upos, iob, requests, tdd]

# Dependency graph
requires:
  - phase: 02-baselines
    provides: UPOS_VALIDOS (frozenset 17 tags) em run_regras.py — reutilizado pelo parser LLM

provides:
  - src/llm/parser.py — parser robusto array-JSON->tags com fallback rastreável (alinhar_tags/extrair_array/tag_valida)
  - src/llm/prompts.py — prompts versionados NER (IOB, inglês) e UPOS (17 tags, português) + montar_prompt
  - src/llm/cliente_ollama.py — cliente HTTP Ollama com temperature=0/seed=42/keep_alive=-1/format=json e captura de métricas
  - tests/test_llm_parser.py — 19 testes puros do parser (sem rede)
  - tests/test_llm_prompts.py — 14 testes de prompts e cliente mockado (sem Ollama real)

affects:
  - 03-02 (emissão/resume/CLI run_llm.py — consome parser, prompts e cliente_ollama diretamente)
  - 04-agregador (usa tok/s e eval_count/eval_duration para tabela comparativa de velocidade)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Parser defensivo: extrair_array + tag_valida + alinhar_tags com fallback rastreável token-a-token"
    - "Prompts versionados em constantes no repo (não improvisados em runtime)"
    - "Cliente HTTP Ollama com options fixas (temperature=0/seed=42/keep_alive=-1/format=json)"
    - "TDD RED->GREEN: testes escritos antes da implementação, todos passam sem rede"

key-files:
  created:
    - src/llm/__init__.py
    - src/llm/parser.py
    - src/llm/prompts.py
    - src/llm/cliente_ollama.py
    - tests/test_llm_parser.py
    - tests/test_llm_prompts.py
  modified: []

key-decisions:
  - "UPOS_VALIDOS importado de run_regras (não redefinido no módulo llm) — evita divergência de esquema"
  - "extrair_array aceita tanto lista direta quanto dict{'tags':[...]} — robustez contra variação de formato do LLM"
  - "Fallback total quando len(arr) != len(tokens) — descarta array inteiro, não tenta reaproveitar posições"
  - "INSTRUCAO_NER em inglês (NER = GMB), INSTRUCAO_UPOS em português (UPOS = Bosque) — fiel ao idioma do corpus"

patterns-established:
  - "alinhar_tags nunca retorna lista de tamanho diferente de len(tokens) — invariante do contrato"
  - "tok_por_seg retorna 0.0 quando eval_duration_ns <= 0 — sem divisão por zero"
  - "Testes do cliente usam monkeypatch em requests.post — sem dependência de Ollama real"

requirements-completed: [REQ-04]

# Metrics
duration: 4min
completed: 2026-06-17
---

# Phase 03 Plan 01: Runner LLM — Núcleo Puro (Parser, Prompts, Cliente Ollama) Summary

**Parser robusto array-JSON->tags com fallback rastreável (NER "O"/UPOS "NOUN"), prompts versionados IOB/UPOS embutindo tokens do loader, e cliente HTTP Ollama reprodutível (temperature=0/seed=42/keep_alive=-1) capturando eval_count/eval_duration para tok/s — 33 testes passam sem rede.**

## Performance

- **Duration:** 4 min
- **Started:** 2026-06-17T15:24:52Z
- **Completed:** 2026-06-17T15:28:45Z
- **Tasks:** 2
- **Files criados:** 6

## Accomplishments

- Parser `alinhar_tags` garante `len(tags)==len(tokens)` sempre — invariante do contrato do runner LLM
- Fallback rastreável com contagem: JSON inválido, tamanho errado ou tag fora do esquema aplicam `FALLBACK[tarefa]` token-a-token e contam cada correção (métrica de robustez para Fase 4)
- Prompts versionados `INSTRUCAO_NER` (IOB, inglês) e `INSTRUCAO_UPOS` (17 UPOS, português) fixos no repo — reprodutibilidade D-05
- Cliente Ollama com `temperature=0/seed=42/keep_alive=-1/format=json` e captura de `eval_count/eval_duration` para `tok_por_seg()`
- TDD RED->GREEN: testes escritos antes da implementação; 33 testes passam sem Ollama no ar

## Task Commits

Cada task foi commitado atomicamente:

1. **Task 1: Parser robusto array-JSON->tags com fallback rastreável** — `ee52969` (feat)
2. **Task 2: Prompts versionados NER/UPOS e cliente Ollama reprodutível** — `348e120` (feat)

## Files Created/Modified

- `src/llm/__init__.py` — módulo llm (vazio, marca o pacote)
- `src/llm/parser.py` — `extrair_array`, `tag_valida`, `FALLBACK`, `alinhar_tags`; importa `UPOS_VALIDOS` de `run_regras`
- `src/llm/prompts.py` — `INSTRUCAO_NER`, `INSTRUCAO_UPOS`, `montar_prompt`; usa `UPOS_VALIDOS` na instrução UPOS
- `src/llm/cliente_ollama.py` — `OLLAMA_URL`, `Resposta` (dataclass), `gerar()`, `tok_por_seg()`
- `tests/test_llm_parser.py` — 19 testes do parser (sem rede): array correto, tamanho errado, JSON inválido, tag inválida, NER, dict response, UPOS válidas
- `tests/test_llm_prompts.py` — 14 testes de montagem de prompt e cliente mockado (monkeypatch em requests.post)

## Decisions Made

- **UPOS_VALIDOS reutilizado de run_regras:** não redefinir as 17 tags no módulo `llm` — qualquer divergência de esquema seria um bug silencioso.
- **extrair_array aceita dict com lista:** o LLM pode retornar `{"tags": [...]}` ou `[...]`; aceitar ambos evita fallback desnecessário por variação de formato.
- **Fallback total quando comprimento errado:** descartar o array inteiro (não tentar reaproveitar posições) — mais seguro e previsível para o alinhamento.
- **Idioma das instruções:** NER em inglês (corpus GMB), UPOS em português (corpus Bosque) — fiel ao idioma de cada corpus.

## Deviations from Plan

Nenhuma — plano executado exatamente como especificado.

## Issues Encountered

Nenhum.

## Next Phase Readiness

- Plano 03-02 pode consumir `src/llm/parser`, `src/llm/prompts` e `src/llm/cliente_ollama` diretamente para montar o `run_llm.py` com CLI, emissão `.jsonl` incremental e resume.
- Sem dependências de rede nos testes: `python -m pytest tests/test_llm_parser.py tests/test_llm_prompts.py -q` passa com Ollama fora do ar.
- Nenhum bloqueador identificado para o plano 03-02.

## Self-Check: PASSED

Arquivos criados verificados:
- `src/llm/__init__.py` — ENCONTRADO
- `src/llm/parser.py` — ENCONTRADO
- `src/llm/prompts.py` — ENCONTRADO
- `src/llm/cliente_ollama.py` — ENCONTRADO
- `tests/test_llm_parser.py` — ENCONTRADO
- `tests/test_llm_prompts.py` — ENCONTRADO

Commits verificados:
- `ee52969` — Task 1 (feat(03-01): parser robusto)
- `348e120` — Task 2 (feat(03-01): prompts versionados e cliente Ollama)

---
*Phase: 03-runner-llm-ollama*
*Completed: 2026-06-17*
