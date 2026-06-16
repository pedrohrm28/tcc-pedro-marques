---
phase: 01-funda-o-contrato-e-leitura-de-corpora
plan: "01"
subsystem: io
tags: [corpus, loader, gmb, conllu, ner, pos, stdlib, tdd]
dependency_graph:
  requires: []
  provides: [src.io.corpora, carregar_gmb, carregar_conllu, Sentenca]
  affects: [fase-2-crf, fase-3-regras, fase-4-llm, fase-5-base-nova]
tech_stack:
  added: []
  patterns: [dataclass-frozen, csv-reader-tsv, conllu-parser]
key_files:
  created:
    - src/__init__.py
    - src/io/__init__.py
    - src/io/corpora.py
    - tests/__init__.py
    - tests/test_corpora_tdd.py
    - tests/test_corpora.py
  modified: []
decisions:
  - encoding-gmb-latin1: GMB_dataset.txt lido com latin-1; quebra em byte 37422 com UTF-8
  - stdlib-only: Loaders usam apenas csv (stdlib); sem novas dependências em requirements.txt
  - dataset-path-relative: Caminhos relativos para datasets/ — execução a partir da raiz do projeto
  - tdd-red-green: Seguiu ciclo RED (stubs) → GREEN (implementação) com commits separados
metrics:
  duration: "3m 21s"
  completed: "2026-06-16T13:13:01Z"
  tasks_completed: 3
  files_created: 6
  files_modified: 0
---

# Phase 01 Plan 01: Loaders de Corpora Gold (GMB + Bosque/UD) Summary

Loaders determinísticos stdlib-only para GMB (NER IOB, inglês) e Bosque/UD (UPOS, português), com seleção first-N estável e smoke tests validados contra os arquivos reais (2999/150 sentenças GMB, 1167 Bosque).

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 0 | Scaffold do pacote e contrato de tipos | 0c80242 | src/__init__.py, src/io/__init__.py, src/io/corpora.py (stubs) |
| 1 RED | Testes TDD — fase RED | 597bd29 | tests/__init__.py, tests/test_corpora_tdd.py |
| 1 GREEN | Implementar loaders GMB e CoNLL-U | 8864520 | src/io/corpora.py (implementação completa) |
| 2 | Smoke tests contra os arquivos reais | a8db0f1 | tests/test_corpora.py |

## Verification Results

- `from src.io.corpora import carregar_gmb, carregar_conllu, Sentenca` — OK
- `carregar_gmb()` → 2999 sentenças; `carregar_gmb(limite=150)` → 150
- `carregar_conllu()` → 1167 sentenças; `carregar_conllu(limite=1167)` → 1167
- `g[0].sentenca_id == '1.0'`; `g[0].pares[0] == ('Thousands', 'O')` — OK
- `c[0].pares[0] == ('Folha', 'PROPN')`; `c[0].pares[1] == ('--', 'PUNCT')` — OK
- `python -m pytest tests/test_corpora.py` — 6 passed
- `python -m pytest tests/test_corpora_tdd.py` — 10 passed
- Nenhuma dependência nova adicionada em requirements.txt

## Key Decisions

| Decision | Rationale |
|----------|-----------|
| encoding latin-1 para GMB | O byte 0x85 na linha 37422 quebra em UTF-8; confirmado por inspeção prévia do plano |
| stdlib csv.reader | Sem necessidade de pandas/numpy; mantém portabilidade e zero dependências extras |
| Caminhos relativos | Usuário executa pytest/python a partir da raiz do projeto (convenção Python padrão) |
| TDD RED→GREEN | Garante que os testes realmente validam comportamento; commits separados auditáveis |
| sent_id fallback | CoNLL-U pode não ter `# sent_id`; fallback para índice 1-based como string |

## TDD Gate Compliance

- RED gate: commit `597bd29` — `test(01-01): add failing tests for GMB e CoNLL-U loaders (TDD RED)`
- GREEN gate: commit `8864520` — `feat(01-01): implementar loaders GMB e CoNLL-U (TDD GREEN)`
- REFACTOR: não necessário — código já limpo e direto

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Datasets não presentes no worktree**

- **Found during:** Task 1 verification setup
- **Issue:** O worktree (`agent-a8ad8fc7e8d126f89`) contém apenas `.gitkeep` em `datasets/base_mapeada/`; os arquivos reais (GMB_dataset.txt, pt_bosque-ud-test.conllu) existem apenas no main repo (`/c/Users/paula/source/repos/tcc-pedro-marques/datasets/base_mapeada/`).
- **Fix:** Verificações e testes foram executados a partir do main repo com `PYTHONPATH` apontando para o worktree. Código implementado com caminhos relativos padrão — funciona corretamente quando executado da raiz do projeto.
- **Files modified:** Nenhum (ajuste de execução apenas)
- **Impact:** Zero — os loaders funcionam corretamente quando executados da raiz do projeto conforme documentado.

## Known Stubs

None.

## Threat Flags

None — módulo de leitura de arquivos locais, sem superfície de rede ou endpoints.

## Self-Check: PASSED

- src/__init__.py: FOUND
- src/io/__init__.py: FOUND
- src/io/corpora.py: FOUND (86+ linhas, sem NotImplementedError)
- tests/__init__.py: FOUND
- tests/test_corpora_tdd.py: FOUND (10 testes, todos passam)
- tests/test_corpora.py: FOUND (6 testes, todos passam)
- Commit 0c80242: FOUND
- Commit 597bd29: FOUND
- Commit 8864520: FOUND
- Commit a8db0f1: FOUND
