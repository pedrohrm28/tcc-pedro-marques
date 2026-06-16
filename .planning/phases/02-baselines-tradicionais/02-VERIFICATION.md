---
phase: 02-baselines-tradicionais
verified: 2026-06-16T00:00:00Z
status: passed
score: 3/3 success criteria verified (5/5 plan truths each)
overrides_applied: 0
re_verification:
  previous_status: null
  note: "Initial verification (no prior VERIFICATION.md)"
---

# Phase 2: Baselines tradicionais — Verification Report

**Phase Goal:** Implementar os dois modelos de referência (baselines tradicionais) rodando via código e emitindo o contrato comum `.jsonl`.
**Verified:** 2026-06-16
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `run_crf.py` treina o CRF das features do `ner.csv`, persiste o modelo e prediz sobre o teste GMB, gerando `.jsonl` | ✓ VERIFIED | `run_crf.py:65-127` (parse 25 features latin-1), `:161-208` (treino + `joblib.dump` em `modelos/crf_ner.pkl`), `:227-259` (predição + emissão). Confirmado: `ner.jsonl` = 25857 registros = `sum(len(s.pares) for carregar_gmb(limite=1167))`; alinhamento full 1:1 `True`; tarefa=`{ner}`, modelo=`{crf}`. |
| 2 | `run_regras.py` produz anotação UPOS por regras sobre o Bosque e gera `.jsonl` | ✓ VERIFIED | `run_regras.py:83-108` (léxico), `:124-168` (pipeline determinístico de 6 regras), `:171-194` (emissão). Confirmado: `upos.jsonl` = 27604 registros = total de tokens de `carregar_conllu(limite=1167)`; alinhamento full 1:1 `True`; tarefa=`{upos}`, modelo=`{regras}`; 0 tags fora de UPOS_VALIDOS. |
| 3 | Re-rodar o agregador não exige re-treinar o CRF (modelo em disco) | ✓ VERIFIED | `run_crf.py:195-197`: se `os.path.exists(caminho_modelo) and not retrain` → `joblib.load`. Spy em `treinar_crf` com pkl presente e `retrain=False`: `training called on cache hit: False`, objeto carregado tipo `CRF`. `modelos/crf_ner.pkl` (632K) existe em disco. |

**Score:** 3/3 success criteria verified.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `run_crf.py` | Script CLI treino+predição CRF, contrato .jsonl | ✓ VERIFIED | 289 linhas; funções puras + CLI argparse; importa contrato e corpora reais |
| `run_regras.py` | Script CLI anotação UPOS por regras | ✓ VERIFIED | 223 linhas; léxico + heurísticas + CLI; sem stubs/TODO |
| `modelos/crf_ner.pkl` | Modelo CRF serializado (cache) | ✓ VERIFIED | 632.6K em disco; gitignored (`.gitignore:6 modelos/*.pkl`); carrega como objeto `CRF` |
| `resultados/base_mapeada/crf/ner.jsonl` | Predições NER IOB, 1167 sentenças | ✓ VERIFIED | 2.8M; 25857 registros; alinhado 1:1 ao gold |
| `resultados/base_mapeada/regras/upos.jsonl` | Predições UPOS, 1167 sentenças | ✓ VERIFIED | 3.2M; 27604 registros; alinhado 1:1 ao gold |
| `tests/test_run_crf.py` | Testes mapeamento + alinhamento | ✓ VERIFIED | Existe; parte das 16 passagens |
| `tests/test_run_regras.py` | Testes regras + alinhamento | ✓ VERIFIED | Existe; parte das 16 passagens |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| run_crf.py | carregar_gmb(limite=1167) | import src.io.corpora; define test set | ✓ WIRED | `:23` import, `:275` `carregar_gmb(limite=args.limite)` |
| run_crf.py | ner.csv (sentence_idx) | leitura latin-1, dedupe, filtro | ✓ WIRED | `:82` `encoding="latin-1"`, `:89` `header.index("sentence_idx")`, dedupe `:117-125`, filtro `:103` |
| run_crf.py | crf/ner.jsonl | escrever_jsonl + caminho_resultado | ✓ WIRED | `:282-283` |
| run_regras.py | carregar_conllu(limite=1167) | import; itera tokens teste | ✓ WIRED | `:26` import, `:178` `carregar_conllu(caminho=caminho_teste, limite=limite)` |
| run_regras.py | pt_bosque-ud-train.conllu | construir_lexico do train | ✓ WIRED | `:100` lê SOMENTE `caminho_train`; teste nunca alimenta léxico |
| run_regras.py | regras/upos.jsonl | escrever_jsonl + caminho_resultado | ✓ WIRED | `:211-217` |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| ner.jsonl | tags do CRF | `crf.predict_single(feats)` sobre features reais do ner.csv (149.8M) | Sim — predições reais, asserção de alinhamento aborta em desalinho (`:240-245`) | ✓ FLOWING |
| upos.jsonl | tag_por_regras | léxico de 7018 sentenças train + heurísticas | Sim — distribuição com 16 UPOS distintas, NOUN dominante | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Test suites pass | `pytest tests/test_run_crf.py tests/test_run_regras.py -q` | 16 passed | ✓ PASS |
| CRF .jsonl count == gold tokens | python ler_jsonl vs carregar_gmb(1167) | 25857 == 25857 | ✓ PASS |
| CRF full token alignment | tuple-by-tuple compare | `True` | ✓ PASS |
| Regras .jsonl count == gold tokens | python ler_jsonl vs carregar_conllu(1167) | 27604 == 27604 | ✓ PASS |
| Regras full token alignment | tuple-by-tuple compare | `True` | ✓ PASS |
| All UPOS tags in schema | set diff vs UPOS_VALIDOS | empty | ✓ PASS |
| CRF cache loads w/o retrain | spy on treinar_crf, retrain=False | not called | ✓ PASS |
| CRF no train/test leakage | intersection of train/test sids | empty (1167 test, 1832 train, all >1167) | ✓ PASS |
| Regras lexicon train-only | path check + code read | train≠test, construir_lexico reads only train | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| REQ-02 | 02-01 | Baseline CRF (NER): treina das features do ner.csv, prediz GMB, emite .jsonl, modelo persistido | ✓ SATISFIED | SC#1 + SC#3 verified above |
| REQ-03 | 02-02 | Baseline regras (POS/UPOS): anotação por regras sobre Bosque, emite .jsonl | ✓ SATISFIED | SC#2 verified above |

No orphaned requirements: REQUIREMENTS.md maps only REQ-02/REQ-03 to Phase 2, both claimed by plans.

### Anti-Patterns Found

None. Grep for `TODO|FIXME|XXX|HACK|PLACEHOLDER|not implemented|NotImplementedError|pass$` across `run_*.py`: no matches. Both scripts are substantive (289 / 223 lines) with real data flow.

### Human Verification Required

None. All success criteria were verifiable programmatically (counts, alignment, cache path via spy, leakage via set intersection, lexicon source via code path). No visual/real-time/external-service behavior in this phase.

### Gaps Summary

No gaps. All three ROADMAP success criteria are MET against the actual codebase, not merely the SUMMARY claims:

- SC#1 (CRF): MET — trains from real 25-feature ner.csv, persists `modelos/crf_ner.pkl`, predicts over GMB test, emits 25857-record `.jsonl` aligned 1:1 to gold.
- SC#2 (Regras): MET — rule pipeline over Bosque emits 27604-record `.jsonl` aligned 1:1, all tags in UPOS schema.
- SC#3 (Cache): MET — re-running with the pkl present loads from disk; training is not invoked (confirmed by instrumenting `treinar_crf`).

Additional defensive properties verified beyond the SCs: no CRF train/test leakage (disjoint sid sets), rules lexicon built strictly from `pt_bosque-ud-train.conllu`, and the SUMMARY's reported numbers (25857 / 27604) reproduced exactly.

---

_Verified: 2026-06-16_
_Verifier: Claude (gsd-verifier)_
