---
phase: 01-funda-o-contrato-e-leitura-de-corpora
plan: "02"
subsystem: io/contract
tags: [contrato, jsonl, dataclass, round-trip, resultados, ner, upos]
dependency_graph:
  requires: []
  provides: [src/io/contrato.py, resultados/README.md, tests/test_contrato.py]
  affects: [fase-2-crf, fase-2-regras, fase-3-llm, fase-4-agregador]
tech_stack:
  added: []
  patterns: [dataclass frozen, newline-delimited JSON, UTF-8 ensure_ascii=False, TDD red-green]
key_files:
  created:
    - src/io/contrato.py
    - src/__init__.py
    - src/io/__init__.py
    - tests/test_contrato.py
    - tests/__init__.py
    - resultados/README.md
    - resultados/base_mapeada/.gitkeep
    - resultados/base_nova/.gitkeep
  modified: []
decisions:
  - "caminho_resultado substitui ':' por '_' para compatibilidade Windows (gpt-oss:20b -> gpt-oss_20b)"
  - "Registro frozen=True para imutabilidade e igualdade por valor em round-trip assertions"
  - "TDD: test commit (RED) antes do impl commit (GREEN) — gate sequence respeitada"
  - "Safeguard: src/__init__.py e src/io/__init__.py criados apenas se ausentes (idempotente)"
metrics:
  duration_seconds: 170
  completed_date: "2026-06-16"
  tasks_completed: 3
  files_created: 8
---

# Phase 01 Plan 02: Contrato .jsonl + Estrutura resultados/ Summary

Dataclass `Registro` com 6 campos + helpers `escrever_jsonl`/`ler_jsonl`/`caminho_resultado` usando apenas stdlib, com round-trip fiel de acentos (UTF-8, `ensure_ascii=False`) e separação `resultados/base_mapeada` x `base_nova` documentada em README.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (RED) | Schema do contrato — testes (TDD) | beafb21 | tests/test_contrato.py |
| 1 (GREEN) | Schema do contrato — implementação | 62c4a5c | src/io/contrato.py, src/__init__.py, src/io/__init__.py, tests/__init__.py |
| 2 | Estrutura e documentação de resultados/ | be70272 | resultados/README.md, resultados/base_mapeada/.gitkeep, resultados/base_nova/.gitkeep |
| 3 | Round-trip test do contrato | beafb21 | (já incluído no commit RED do TDD) |

## Verification Results

- `python -c "from src.io.contrato import Registro, escrever_jsonl, ler_jsonl, caminho_resultado"` — OK
- `python -m pytest tests/test_contrato.py -q` — 5 passed
- `resultados/README.md` existe com `base_mapeada` e `tag_predita` — OK
- `resultados/base_mapeada/.gitkeep` e `resultados/base_nova/.gitkeep` existem — OK
- Sem dependências novas em requirements.txt — OK

## TDD Gate Compliance

| Gate | Commit | Status |
|------|--------|--------|
| RED (test) | beafb21 | PASSED — tests falhavam com ModuleNotFoundError antes do impl |
| GREEN (feat) | 62c4a5c | PASSED — 5/5 testes passam após implementação |
| REFACTOR | N/A | Não necessário — código limpo de primeira |

## Deviations from Plan

None - plan executed exactly as written.

Nota: O arquivo `tests/test_contrato.py` foi criado no step TDD RED da Task 1 (commit `beafb21`), cobrindo todos os 5 testes exigidos pelo plano na Task 3. Não houve conflito — a Task 3 é automaticamente satisfeita pelo passo TDD RED da Task 1.

## Known Stubs

None. Todos os campos do Registro são reais, a lógica de serialização é completa, e os testes assertam igualdade exata.

## Threat Flags

None. Sem novos endpoints de rede, caminhos de autenticação ou mudanças de schema em fronteiras de confiança. Apenas I/O em sistema de arquivos local (stdlib `json`, `os`).

## Self-Check

- [x] `src/io/contrato.py` exists: FOUND
- [x] `tests/test_contrato.py` exists: FOUND
- [x] `resultados/README.md` exists: FOUND
- [x] `resultados/base_mapeada/.gitkeep` exists: FOUND
- [x] `resultados/base_nova/.gitkeep` exists: FOUND
- [x] Commit beafb21 exists: FOUND
- [x] Commit 62c4a5c exists: FOUND
- [x] Commit be70272 exists: FOUND

## Self-Check: PASSED
