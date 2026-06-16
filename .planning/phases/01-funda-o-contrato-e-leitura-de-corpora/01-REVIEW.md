---
phase: 01-funda-o-contrato-e-leitura-de-corpora
reviewed: 2026-06-16T00:00:00Z
depth: standard
files_reviewed: 5
files_reviewed_list:
  - src/io/corpora.py
  - src/io/contrato.py
  - tests/test_corpora.py
  - tests/test_corpora_tdd.py
  - tests/test_contrato.py
findings:
  critical: 0
  warning: 4
  info: 4
  total: 8
status: issues-found
---

# Phase 01: Code Review Report

**Reviewed:** 2026-06-16
**Depth:** standard
**Files Reviewed:** 5
**Status:** issues_found

## Summary

Reviewed the Phase 01 foundation: corpus loaders (`carregar_gmb`, `carregar_conllu`) and the
`.jsonl` prediction contract (`Registro`, `escrever_jsonl`, `ler_jsonl`, `caminho_resultado`),
plus their tests. The code is clean, stdlib-only as required, well documented in pt-BR, and the
happy-path verification against the real corpus files passes (2999/150 GMB sentences, 1167 Bosque
sentences, accent-preserving round-trip).

No security vulnerabilities were found — this is local file I/O with no network or auth surface,
and no `eval`/injection/secret patterns. No Critical findings.

However, the loaders encode several silent assumptions about the *exact* shape of the two specific
corpus files in `datasets/base_mapeada/`. These pass today because the current files happen to
satisfy them, but the parsers will silently produce wrong groupings (not raise) if fed the more
common variants of the same formats. For a thesis whose entire metric pipeline depends on
token-aligned gold data, "silently wrong" is the dangerous failure mode. The four Warnings below
are about robustness against those variants and against schema drift on read. I verified each claim
against the real files.

## Warnings

### WR-01: CoNLL-U sentence boundary breaks on CRLF / whitespace-only blank lines

**File:** `src/io/corpora.py:107,110`
**Issue:** Sentence segmentation depends on `linha == ""` after `linha = linha.rstrip("\n")`.
On a CoNLL-U file saved with Windows line endings (`\r\n`), the separator line becomes `"\r"`,
which is not equal to `""`, so the blank line is then treated as a token line, hits
`cols = linha.split("\t")` → `len(cols) < 4` → `continue`, and the sentence is *never closed*.
The result is that all tokens collapse into a single `Sentenca` (or far fewer than 1167) with no
error raised. The current Bosque file is LF-only (verified), so tests pass — but this is an
environment-dependent landmine on Windows (the documented target platform), e.g. if the file is
re-saved, git `core.autocrlf` rewrites it, or the same loader is reused for the Phase 5 base nova.
A whitespace-only blank line (spaces/tabs before the newline) fails the same way.

**Fix:** Strip all trailing whitespace and test emptiness on the stripped value:
```python
for linha in f:
    linha = linha.rstrip("\n").rstrip("\r")
    if linha.strip() == "":          # robust blank-line / EOS detection
        if pares_correntes:
            ...
        continue
```
Add a regression test that feeds a small `\r\n`-terminated CoNLL-U fixture and asserts the
sentence count.

### WR-02: GMB loader silently mis-groups if 'Sentence #' is forward-filled (only on first token)

**File:** `src/io/corpora.py:63,66-69`
**Issue:** Grouping uses `row[1]` ('Sentence #') as the key on *every* row. The file currently in
`datasets/base_mapeada/` populates `Sentence #` on every token (verified), so this works. But the
canonical/Kaggle GMB `ner_dataset.csv` distribution fills `Sentence #` only on the *first* token of
each sentence and leaves it blank thereafter (a forward-fill layout). If such a variant is ever
substituted, every blank `row[1]` becomes a single giant group keyed on `""`, and the loader
returns a wildly wrong sentence count with no error. The `len(row) < 5` guard does not catch this
because the row still has 5 columns — only the id is empty. Given the thesis depends on exactly 150
NER sentences, a silent regrouping corrupts every downstream metric.

**Fix:** Either (a) assert the invariant so failure is loud, or (b) support forward-fill. Minimal
loud guard:
```python
sentenca_id = row[1].strip()
if not sentenca_id:
    raise ValueError(f"linha sem 'Sentence #' (variante forward-fill não suportada): {row!r}")
```
Better: carry the last non-empty id forward (`sid = row[1].strip() or ultimo_sid`) to support both
layouts, and add a test asserting `len(carregar_gmb()) == 2999` stays exact.

### WR-03: ler_jsonl raises uncontextualized TypeError/ValueError on schema drift or corrupt lines

**File:** `src/io/contrato.py:74-77`
**Issue:** `Registro(**json.loads(linha))` propagates raw exceptions with no file/line context:
an extra key yields `TypeError: Registro.__init__() got an unexpected keyword argument 'extra'`
(verified), a missing key yields a different `TypeError`, a malformed JSON line yields
`json.JSONDecodeError`, and a bad `tarefa` yields `ValueError`. Since these `.jsonl` files are
produced by multiple independent model runners (CRF, regras, two LLMs) in Phases 2-4, a single
malformed line aborts the whole read with a message that does not say *which file* or *which line*.
This is a debuggability/robustness defect for the format that is "o coração do REQ-01".

**Fix:** Wrap per-line parsing and annotate:
```python
for n, linha in enumerate(f, 1):
    linha = linha.strip()
    if not linha:
        continue
    try:
        registros.append(Registro(**json.loads(linha)))
    except (TypeError, ValueError, json.JSONDecodeError) as e:
        raise ValueError(f"{caminho}:{n}: registro .jsonl inválido: {e}") from e
```
Add a test feeding a line with a missing/extra field and assert the error names the file and line.

### WR-04: caminho_resultado only sanitizes ':' in `modelo`, and emits backslashes on Windows

**File:** `src/io/contrato.py:99-100`
**Issue:** Two coupled problems. (1) `os.path.join("resultados", base, modelo_sanitizado, ...)`
returns `resultados\base_mapeada\...` on Windows, but both the docstring (line 86) and
`resultados/README.md` document forward-slash paths. Any code or test that string-compares the
returned path against a `/`-style literal, or that records the path into a `.jsonl`/report for
cross-platform reproducibility, will mismatch. The thesis artifacts are meant to be portable.
(2) Only `modelo` has `:` replaced; `base` and `tarefa` are interpolated unsanitized. `tarefa` is
validated upstream only inside `Registro`, but `caminho_resultado` accepts arbitrary `base`/`tarefa`
strings, so a stray `:` or path separator there is not neutralized. This is a latent
path-construction inconsistency rather than an exploit (inputs are internal), but it undermines the
stated Windows-safety guarantee that is the function's whole reason to exist.

**Fix:** Normalize separators and sanitize all path segments uniformly:
```python
def _seg(s: str) -> str:
    return s.replace(":", "_")
caminho = os.path.join("resultados", _seg(base), _seg(modelo), f"{_seg(tarefa)}.jsonl")
return caminho.replace(os.sep, "/")   # if forward-slash contract is intended
```
If backslashes are acceptable, then update the docstring and README to stop promising `/`.

## Info

### IN-01: GMB grouping merges non-contiguous repeats of the same id into one sentence

**File:** `src/io/corpora.py:66-73`
**Issue:** Because grouping accumulates into a `dict` keyed by id, if the same `Sentence #` value
ever reappears after a different id (non-contiguous), its tokens are appended to the earlier
sentence rather than forming a new one. Verified: the current file has zero non-contiguous repeats,
so this is correct today. It is a silent assumption worth a guard or comment, since the docstring
claims "ordem de aparição" which a streaming/contiguous parser would honor but the dict approach
does not for repeats.

**Fix:** Document the contiguity assumption, or detect a reappearing id and raise/segment. A
streaming approach (close the current sentence when `sentenca_id` changes) also fixes WR-02 and this
at once.

### IN-02: GMB sentence ordering is file-order, not numeric — fine here, fragile if relied upon

**File:** `src/io/corpora.py:54,72`
**Issue:** "Ordem estável de aparição" equals file order, which for this file coincides with numeric
order (`1.0, 2.0, ... 2999.0`). If a future GMB export is not pre-sorted, `limite=150` would take a
different 150 sentences. Determinism is preserved (same file → same output) but the *selection* is
not numerically defined. Acceptable per the plan ("ordem do arquivo"), flagging so it is a conscious
choice.

**Fix:** None required; consider a one-line comment that first-N == first-N-in-file, not
first-N-by-id.

### IN-03: Unused `import pytest` in test modules

**File:** `tests/test_corpora.py:8`, `tests/test_corpora_tdd.py:6`
**Issue:** `import pytest` is present but `pytest` is never referenced in
`tests/test_corpora.py` or `tests/test_corpora_tdd.py` (no `pytest.raises`, `mark`, or `fixture`).
Dead import. (`tests/test_contrato.py` does use `pytest.raises`, so its import is justified.)

**Fix:** Remove the unused `import pytest` from the two corpora test files.

### IN-04: `Sentenca` is frozen but holds a mutable `list[Par]`, weakening immutability

**File:** `src/io/corpora.py:25-28`
**Issue:** `@dataclass(frozen=True)` prevents attribute rebinding but `pares: list[Par]` is still
mutable in place (`s.pares.append(...)` works), and the loaders build each sentence by mutating a
list they then store. This is harmless given current usage but the `frozen=True` advertises a
stronger guarantee than is delivered, and shared-list aliasing could surprise a future caller.

**Fix:** Optional — store `pares: tuple[Par, ...]` and freeze on construction
(`Sentenca(sid, tuple(pares_correntes))`), or document that `pares` is not deeply immutable.

---

_Reviewed: 2026-06-16_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
