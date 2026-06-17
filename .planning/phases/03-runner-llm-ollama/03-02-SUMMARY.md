---
phase: 03-runner-llm-ollama
plan: 02
subsystem: runner
tags: [ollama, runner, cli, jsonl, resume, métricas, ner, upos, tdd]

# Dependency graph
requires:
  - phase: 03-runner-llm-ollama
    plan: 01
    provides: src/llm/parser.py (alinhar_tags), src/llm/prompts.py (montar_prompt), src/llm/cliente_ollama.py (gerar/Resposta)
  - phase: 01-contrato
    provides: src/io/contrato.py (Registro/ler_jsonl/caminho_resultado), src/io/corpora.py (carregar_gmb/carregar_conllu)

provides:
  - run_llm.py — runner CLI dos 3 LLMs via Ollama, emissão .jsonl incremental/resume + métricas tok/s/sent/s
  - tests/test_run_llm.py — 6 testes com Ollama mockado (fn_gerar fake, sem rede)

affects:
  - 04-agregador (lê os .jsonl de predição emitidos por run_llm.py + meta.json de métricas)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Escrita incremental modo 'a' com flush por sentença — durabilidade parcial sob crash"
    - "Resume via ler_jsonl: coleta sentenca_id presentes, pula sentenças feitas"
    - "fn_gerar injetável: tests passam fake sem rede; produção usa gerar() do cliente_ollama"
    - "Asserção defensiva assert len(tags)==len(s.pares) antes da emissão — bug detectado na borda do contrato"
    - "meta.json ao lado do .jsonl: tok/s, sent/s, fallbacks, wall_clock_s por (modelo, tarefa)"

key-files:
  created:
    - run_llm.py
    - tests/test_run_llm.py
  modified: []

key-decisions:
  - "fn_gerar injetável no rodar(): testes passam fake sem Ollama no ar; padrão seguido de run_crf.py"
  - "Escrita em modo 'a' direto (não escrever_jsonl que abre em 'w') — append incremental por sentença"
  - "modelo mantém ':' no Registro (ex llama3.1:8b); sanitização ':'->'_' só no caminho via caminho_resultado"
  - "meta.json criado com caminho derivado do .jsonl (.jsonl -> .meta.json); não polui o repo (gitignored)"
  - "Fallback total via alinhar_tags quando array errado — asserção defensiva garante invariante antes da emissão"

# Metrics
duration: 3min
completed: 2026-06-17
---

# Phase 03 Plan 02: Runner LLM — CLI run_llm.py (Loop, Resume, Métricas) Summary

**Runner CLI que executa os 3 LLMs via Ollama (1 sentença/chamada), emitindo `.jsonl` incremental em modo append com resume automático e persistindo métricas tok/s e sent/s por (modelo, tarefa) — 6 testes passam sem Ollama no ar.**

## Performance

- **Duration:** 3 min
- **Started:** 2026-06-17T15:32:13Z
- **Completed:** 2026-06-17T15:35:00Z
- **Tasks:** 2
- **Files criados:** 2

## Accomplishments

- `run_llm.py` implementado com loop 1 sentença/chamada, escrita incremental modo append e resume automático via `ler_jsonl` (sem duplicação de sentenças)
- `--reiniciar` remove o `.jsonl` existente e recomeça do zero; sem `--reiniciar` retoma de onde parou
- `fn_gerar` injetável: testes passam um fake sem rede; produção usa `gerar()` do `cliente_ollama`
- Asserção defensiva `assert len(tags) == len(s.pares)` antes da emissão — detecta bug no contrato do parser
- `modelo` mantém o nome literal com `:` no `Registro` (ex `"llama3.1:8b"`); o caminho sanitiza via `caminho_resultado`
- `<tarefa>.meta.json` persistido ao lado do `.jsonl` com `tok_por_seg`, `sent_por_seg`, `fallbacks`, `wall_clock_s`
- 6 testes com `fn_gerar` fake: alinhamento, fallback (array errado), resume, reiniciar, métricas, modelo com `:`

## Task Commits

Cada task foi commitado atomicamente:

1. **Task 1: run_llm.py — loop 1 sentença/chamada, emissão incremental, resume, métricas** — `831a4f1` (feat)
2. **Task 2: Testes de alinhamento, resume e fallback com Ollama mockado** — `2c04a0e` (feat)

## Files Created/Modified

- `run_llm.py` — `_sentencas_feitas`, `_append_registros`, `rodar`, `main`; 284 linhas
- `tests/test_run_llm.py` — 6 testes com `fn_gerar` fake; 268 linhas

## Decisions Made

- **fn_gerar injetável:** seguindo padrão do runner CRF (`_CrfFake`), o parâmetro `fn_gerar=gerar` no `rodar()` permite mock sem alterar a interface de produção.
- **Escrita em modo 'a' direto:** `escrever_jsonl` do contrato abre em `'w'` (sobrescreve). O runner mantém escrita incremental abrindo manualmente em `'a'` com flush por sentença.
- **modelo preserva ':':** o Registro armazena o nome real do modelo para rastreabilidade; a sanitização é responsabilidade do caminho (já implementada em `caminho_resultado`).
- **meta.json derivado do caminho:** `caminho.replace(".jsonl", ".meta.json")` evita um parâmetro extra; caminho resultante segue a mesma estrutura `resultados/<base>/<modelo_san>/`.

## Deviations from Plan

Nenhuma — plano executado exatamente como especificado.

## TDD Gate Compliance

O plano marca Task 2 com `tdd="true"`. A implementação da Task 1 precedeu os testes (estrutura do plano). Os 6 testes passam em GREEN na primeira execução — nenhuma iteração RED necessária pois o contrato estava completo antes dos testes serem escritos.

## Issues Encountered

Nenhum.

## Next Phase Readiness

- `python run_llm.py --modelo llama3.1:8b --tarefa ner` está pronto para executar as 6 rodadas completas (1167 sentenças × 3 modelos × 2 tarefas = ~21k chamadas ao Ollama).
- `python -m pytest tests/test_run_llm.py -q` passa em < 30s sem Ollama no ar.
- Plano 04-agregador pode consumir `resultados/base_mapeada/<modelo>/<tarefa>.jsonl` e `.meta.json` diretamente.
- Nenhum bloqueador identificado para o plano 04.

## Self-Check: PASSED

Arquivos criados verificados:
- `run_llm.py` — ENCONTRADO
- `tests/test_run_llm.py` — ENCONTRADO

Commits verificados:
- `831a4f1` — Task 1 (feat(03-02): runner CLI run_llm.py)
- `2c04a0e` — Task 2 (feat(03-02): testes de alinhamento)

---
*Phase: 03-runner-llm-ollama*
*Completed: 2026-06-17*
