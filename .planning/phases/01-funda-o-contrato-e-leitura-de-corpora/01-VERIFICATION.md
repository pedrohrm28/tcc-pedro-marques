---
phase: 01-funda-o-contrato-e-leitura-de-corpora
verified: 2026-06-16T14:30:00Z
status: passed-with-concerns
score: 2.5/3
overrides_applied: 0
gaps:
  - truth: "requirements.txt cobre as dependências (sklearn-crfsuite, scikit-learn, requests/ollama, etc.)"
    status: partial
    reason: >
      requirements.txt contém apenas `requests` e `seqeval`. As dependências
      sklearn-crfsuite e scikit-learn estão ausentes, apesar de o ROADMAP SC#3
      as listar explicitamente como critério de Phase 1. O código Phase 1
      (loaders + contrato) usa apenas stdlib e não requer essas bibliotecas
      para funcionar, mas o contrato da fase afirma que o arquivo de dependências
      deve cobri-las antecipadamente.
    artifacts:
      - path: "requirements.txt"
        issue: "Contém apenas `requests` e `seqeval`; faltam sklearn-crfsuite, scikit-learn, e ollama (se aplicável)"
    missing:
      - "Adicionar sklearn-crfsuite e scikit-learn ao requirements.txt"
      - "Confirmar se o cliente ollama precisa de pacote Python (ex. ollama-python) ou só requests"
deferred: []
human_verification: []
---

# Phase 1: Fundação — contrato e leitura de corpora — Verification Report

**Phase Goal:** Definir o contrato de saída `.jsonl` que todos os modelos emitem e os loaders
que leem GMB (IOB) e Bosque (CoNLL-U) para gold; estruturar o projeto e dependências.
**Verified:** 2026-06-16T14:30:00Z
**Status:** passed-with-concerns
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Existe um módulo de I/O que lê GMB_dataset.txt em sentenças de (token, tag IOB) e pt_bosque-ud-test.conllu em sentenças de (token, UPOS) | VERIFIED | `src/io/corpora.py` — 149 linhas, implementação completa stdlib. `carregar_gmb()` → 2999 sentenças, `carregar_gmb(limite=150)` → 150; `carregar_conllu()` → 1167 sentenças. GMB[0]: id='1.0', pares[0]=('Thousands','O'). CoNLL-U[0]: pares[0]=('Folha','PROPN'), pares[1]=('--','PUNCT'). 21 testes passam. |
| 2 | Há um schema/escritor `.jsonl` documentado com helper de escrita/leitura | VERIFIED | `src/io/contrato.py` — `Registro` dataclass frozen com os 6 campos exatos (`{tarefa, modelo, sentenca_id, posicao, token, tag_predita}`), `escrever_jsonl`/`ler_jsonl` com round-trip fiel (UTF-8, `ensure_ascii=False`), `caminho_resultado` sanitiza ':' → '_'. `resultados/README.md` documenta schema, convenção de caminhos e separação base_mapeada × base_nova. 5 testes de contrato passam. |
| 3 | `requirements.txt` cobre as dependências (sklearn-crfsuite, scikit-learn, requests/ollama, etc.) e instala sem erro | PARTIAL | `requirements.txt` contém apenas `requests` e `seqeval`. Ausentes: `sklearn-crfsuite`, `scikit-learn`. O código Phase 1 em si funciona completamente sem essas bibliotecas (stdlib puro), mas o ROADMAP SC#3 as exige explicitamente neste arquivo. |

**Score:** 2.5/3 truths verified (2 VERIFIED, 1 PARTIAL)

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/__init__.py` | Pacote src importável | VERIFIED | Exists, empty — pacote importável |
| `src/io/__init__.py` | Pacote io importável | VERIFIED | Exists, empty — pacote importável |
| `src/io/corpora.py` | Loaders GMB (IOB) + CoNLL-U (UPOS) + `Sentenca` | VERIFIED | 149 linhas; exports `carregar_gmb`, `carregar_conllu`, `Sentenca`; sem NotImplementedError |
| `src/io/contrato.py` | Dataclass `Registro` + `escrever_jsonl`/`ler_jsonl`/`caminho_resultado` | VERIFIED | 101 linhas; todos os 4 exports presentes e funcionais |
| `tests/test_corpora.py` | Smoke tests contra arquivos reais | VERIFIED | 6 testes, todos passam (`pytest -v`) |
| `tests/test_corpora_tdd.py` | Testes TDD (RED→GREEN) | VERIFIED | 10 testes, todos passam |
| `tests/test_contrato.py` | Round-trip e validação do contrato | VERIFIED | 5 testes, todos passam |
| `resultados/README.md` | Documenta schema + convenção de pastas | VERIFIED | Contém `base_mapeada`, `tag_predita`, schema JSON, tabela de campos, convenção de caminhos |
| `resultados/base_mapeada/.gitkeep` | Placeholder de pasta | VERIFIED | Exists |
| `resultados/base_nova/.gitkeep` | Placeholder de pasta | VERIFIED | Exists |
| `requirements.txt` | Dependências completas do projeto | PARTIAL | Contém `requests`, `seqeval`; faltam `sklearn-crfsuite`, `scikit-learn` |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `tests/test_corpora.py` | `src/io/corpora.py` | `from src.io.corpora import carregar_gmb, carregar_conllu, Sentenca` | WIRED | Import real na linha 10; funções exercidas em 6 testes |
| `tests/test_corpora_tdd.py` | `src/io/corpora.py` | `from src.io.corpora import carregar_gmb, carregar_conllu, Sentenca` | WIRED | Import real na linha 3; 10 testes comportamentais |
| `tests/test_contrato.py` | `src/io/contrato.py` | `from src.io.contrato import Registro, escrever_jsonl, ler_jsonl, caminho_resultado` | WIRED | Import real na linha 3; 5 testes de round-trip |
| `src/io/corpora.py` | `datasets/base_mapeada/GMB_dataset.txt` | `open(caminho, encoding='latin-1', newline='')` | WIRED | Linha 56; encoding latin-1 correto; leitura verificada (2999 sentenças) |
| `src/io/corpora.py` | `datasets/base_mapeada/pt_bosque-ud-test.conllu` | `open(caminho, encoding='utf-8')` | WIRED | Linha 105; leitura verificada (1167 sentenças, multiword filtrado) |
| `src/io/contrato.py` | `resultados/` | `caminho_resultado(base, modelo, tarefa)` | WIRED | Linha 100; gera `resultados/<base>/<modelo_sanitizado>/<tarefa>.jsonl` |

---

## Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|-------------------|--------|
| `src/io/corpora.py` — `carregar_gmb` | `grupos`, `ordem` → `sentencas` | `csv.reader` sobre `GMB_dataset.txt` (latin-1) | Sim — 2999 sentenças reais, primeira com ('Thousands','O') verificado | FLOWING |
| `src/io/corpora.py` — `carregar_conllu` | `pares_correntes` → `sentencas` | `open(utf-8)` linha a linha sobre `.conllu` | Sim — 1167 sentenças reais, multiword filtrado corretamente | FLOWING |
| `src/io/contrato.py` — `ler_jsonl` | `registros` | `json.loads` por linha do arquivo | Sim — round-trip testado com assertiva de igualdade exata | FLOWING |

---

## Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| carregar_gmb() retorna 2999 sentenças | `python -c "from src.io.corpora import carregar_gmb; print(len(carregar_gmb()))"` | 2999 | PASS |
| carregar_gmb(limite=150) retorna 150 | `python -c "from src.io.corpora import carregar_gmb; print(len(carregar_gmb(limite=150)))"` | 150 | PASS |
| carregar_conllu() retorna 1167 | `python -c "from src.io.corpora import carregar_conllu; print(len(carregar_conllu()))"` | 1167 | PASS |
| GMB[0] id e primeiro par corretos | `python -c "..."` | sentenca_id='1.0', pares[0]=('Thousands','O') | PASS |
| CoNLL-U[0] pares corretos | `python -c "..."` | pares[0]=('Folha','PROPN'), pares[1]=('--','PUNCT') | PASS |
| contrato.py imports | `python -c "from src.io.contrato import Registro, escrever_jsonl, ler_jsonl, caminho_resultado; print('OK')"` | OK | PASS |
| caminho_resultado sanitiza ':' | verificado via python | path não contém ':' no basename | PASS |
| Suite completa de testes | `python -m pytest tests/ -q` | 21 passed | PASS |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|---------|
| REQ-01 | 01-01-PLAN, 01-02-PLAN | Contrato de saída comum `.jsonl` (schema, helpers, loaders gold) | SATISFIED | `src/io/contrato.py` implementa `Registro` + `escrever_jsonl`/`ler_jsonl`; `src/io/corpora.py` implementa loaders gold para GMB e CoNLL-U; `resultados/README.md` documenta o contrato |

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `requirements.txt` | 1-2 | Dependências ausentes: sklearn-crfsuite, scikit-learn | Warning | Phase 2 (`run_crf.py`) não instalará dependências automaticamente se o requirements.txt não for atualizado |

Nenhum stub, placeholder, `TODO`, `FIXME`, `return null`, `return []` vazio sem dados reais ou `NotImplementedError` encontrado nos arquivos de implementação. Os loaders são implementação completa e funcional.

---

## Human Verification Required

Nenhum item requer verificação humana. Todos os comportamentos críticos são verificáveis programaticamente e foram confirmados pelos testes e spot-checks acima.

---

## Gaps Summary

### Gap G-01: requirements.txt incompleto (WARNING — não bloqueia Phase 1)

**Truth falhada:** SC#3 — "`requirements.txt` cobre as dependências (sklearn-crfsuite, scikit-learn, requests/ollama, etc.) e instala sem erro."

**O que existe:** `requests`, `seqeval`

**O que está ausente:** `sklearn-crfsuite`, `scikit-learn` (e possivelmente `ollama` se um cliente Python for usado na Fase 3)

**Impacto:** O código da Phase 1 (`src/io/corpora.py`, `src/io/contrato.py`) usa exclusivamente stdlib Python — ele funciona sem essas bibliotecas. Porém, o ROADMAP SC#3 afirma explicitamente que `requirements.txt` deve cobri-las na Phase 1.

**Contexto de deferimento (por que não é blocker absoluto):** As bibliotecas ausentes são consumidas pelo `run_crf.py` (Phase 2 — REQ-02) e pelo runner LLM (Phase 3 — REQ-04), não por nenhum módulo da Phase 1. Do ponto de vista de execução, Phase 1 está completa e funcional. O gap é real em relação ao contrato textual da SC, mas não compromete a operabilidade do que a Phase 1 entrega.

**Ação recomendada:** Adicionar ao `requirements.txt` antes de iniciar a Phase 2:
```
requests
seqeval
sklearn-crfsuite
scikit-learn
```
E confirmar se a integração Ollama (Phase 3) requer o pacote `ollama` (PyPI) ou apenas `requests`.

---

## Nota sobre commits verificados

Todos os commits declarados nos SUMMARYs foram verificados no histórico git:

| Commit | Descrição |
|--------|-----------|
| `0c80242` | scaffold pacote src/io e contrato de tipos |
| `597bd29` | testes TDD RED |
| `8864520` | loaders GMB e CoNLL-U TDD GREEN |
| `a8db0f1` | smoke tests contra arquivos reais |
| `beafb21` | schema contrato TDD RED (inclui test_contrato.py) |
| `62c4a5c` | Registro + helpers contrato GREEN |
| `be70272` | resultados/ structure + README |

---

_Verified: 2026-06-16T14:30:00Z_
_Verifier: Claude (gsd-verifier)_
