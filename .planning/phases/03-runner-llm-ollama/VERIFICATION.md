---
phase: 03-runner-llm-ollama
verified: 2026-06-17T16:00:00Z
status: passed
score: 9/9 must-haves verified
overrides_applied: 0
gaps: []
---

# Fase 03: Runner LLM (Ollama) — Relatório de Verificação

**Objetivo da Fase:** Rodar os 3 LLMs (`llama3.1:8b`, `qwen2.5:3b`, `llama3.2:3b`) via Ollama nas duas tarefas (NER/UPOS), de forma reprodutível, 1 sentença por chamada, convertendo a saída do LLM de volta ao contrato `.jsonl` e registrando tempo/velocidade por modelo.
**Verificado:** 2026-06-17T16:00:00Z
**Status:** GOAL ACHIEVED
**Re-verificação:** Não — verificação inicial.

---

## Truths Observáveis (Success Criteria do ROADMAP)

| # | Truth | Status | Evidência |
|---|-------|--------|-----------|
| SC1 | `run_llm.py --modelo X --tarefa Y` produz `.jsonl` alinhado token-a-token ao gold, 1 sentença por chamada | VERIFICADO | `run_llm.py:141-168` — loop `for s in sentencas` processa uma sentença por iteração; `alinhar_tags` garante `len(tags)==len(s.pares)` antes da emissão; test_alinhamento_upos (test_run_llm.py:62) valida alinhamento 1:1 com gold |
| SC2 | Execução usa `temperature=0` e `seed=42`; prompts versionados; mesmo script roda os 3 LLMs via `--modelo` | VERIFICADO | `cliente_ollama.py:79-93` — `options={"temperature": 0, "seed": 42}`, `"format":"json"`, `"keep_alive":-1`; `prompts.py:18-52` — `INSTRUCAO_NER` e `INSTRUCAO_UPOS` como constantes fixas no repo; `run_llm.py:226-229` — `--modelo` aceita qualquer string (não há allowlist rígida, documentando os 3 no help) |
| SC3 | Parsing robusto: tokens sem resposta válida do LLM viram tag de fallback rastreável, sem quebrar alinhamento | VERIFICADO | `parser.py:116-135` — `alinhar_tags`: JSON inválido/array de tamanho errado → fallback total (`n_fallback=len(tokens)`); tag inválida individual → fallback na posição; `FALLBACK={"ner":"O","upos":"NOUN"}`; 19 testes em test_llm_parser.py cobrem todos os casos |
| SC4 | Cada execução registra tempo total e velocidade (tok/s e sent/s) por (modelo, tarefa) | VERIFICADO | `run_llm.py:179-197` — dict `meta` com `tok_por_seg`, `sent_por_seg`, `eval_duration_s`, `wall_clock_s`, `fallbacks`; persistido como `<tarefa>.meta.json` via `caminho_saida.replace(".jsonl", ".meta.json")`; test_metricas_no_retorno valida presença e coerência |
| SC5 | Execução retomável: progresso parcial é persistido para não perder processamento | VERIFICADO | `run_llm.py:47-60` — `_sentencas_feitas` coleta `sentenca_id` via `ler_jsonl`; `run_llm.py:143` — `if s.sentenca_id in feitas: continue`; `run_llm.py:76` — modo `"a"` (append); `--reiniciar` remove o arquivo e começa do zero; test_resume_pula_sentencas_feitas valida ausência de duplicação |

**Pontuação de Truths:** 5/5 ✓

---

## Must-Haves dos Planos (03-01 e 03-02)

### Plano 03-01

| # | Truth | Status | Evidência (arquivo:linha) |
|---|-------|--------|--------------------------|
| P01-T1 | Prompts versionados de NER (IOB) e UPOS no repositório, em código, não improvisados em runtime | VERIFICADO | `prompts.py:18-52` — `INSTRUCAO_NER` e `INSTRUCAO_UPOS` como constantes de módulo; conteúdo não muda em runtime |
| P01-T2 | Cliente Ollama monta chamada com temperature=0, seed=42, keep_alive=-1 e format=json para 1 sentença | VERIFICADO | `cliente_ollama.py:79-93` — todas as 4 chaves presentes no corpo da requisição; test_gerar_corpo_options_reprodutiveis (test_llm_prompts.py:113) verifica via monkeypatch |
| P01-T3 | Parser converte array JSON de tags em lista alinhada token-a-token | VERIFICADO | `parser.py:88-135` — `alinhar_tags` garante `len(tags)==len(tokens)` invariavelmente |
| P01-T4 | Fallback rastreável (NER "O", UPOS "NOUN") com contagem; nunca quebra alinhamento | VERIFICADO | `parser.py:20-23` — `FALLBACK={"ner":"O","upos":"NOUN"}`; lógica em `alinhar_tags` conta cada token corrigido; `n_fallback` retornado sempre |
| P01-T5 | Toda tag UPOS pertence às 17 UPOS válidas; NER usa esquema IOB | VERIFICADO | `parser.py:15,77` — `UPOS_VALIDOS` importado de `run_regras` (não redefinido); `tag_valida("ner",...)` aceita "O" e prefixos "B-"/"I-"; test_alinhar_tags_saida_sempre_upos_validos valida saída sempre em UPOS_VALIDOS |

### Plano 03-02

| # | Truth | Status | Evidência (arquivo:linha) |
|---|-------|--------|--------------------------|
| P02-T1 | run_llm.py --modelo X --tarefa ner\|upos roda 1 sentença por chamada (sem batching) | VERIFICADO | `run_llm.py:141-168` — loop `for s in sentencas` com `fn_gerar` chamado uma vez por sentença |
| P02-T2 | .jsonl emitido alinha token-a-token com o gold do loader | VERIFICADO | `run_llm.py:157-168` — `enumerate(s.pares)` monta registros na ordem do loader; asserção defensiva `assert len(tags)==len(s.pares)` em :152 |
| P02-T3 | .jsonl escrito incrementalmente (modo append) e execução é retomável | VERIFICADO | `run_llm.py:76` — `open(caminho, "a", encoding="utf-8")`; lógica de resume em :60,143 |
| P02-T4 | Campo `modelo` do Registro mantém nome real com `:` (ex `llama3.1:8b`); só o caminho sanitiza | VERIFICADO | `run_llm.py:158-165` — `modelo=modelo` no `Registro` sem sanitização; `caminho_resultado` em `contrato.py:99` aplica `replace(":", "_")`; test_modelo_preserva_dois_pontos valida ambos |

**Pontuação de Must-Haves dos Planos:** 9/9 ✓

---

## Artefatos Requeridos

| Artefato | Min. Linhas | Existe | Substancial | Wired | Status |
|----------|-------------|--------|-------------|-------|--------|
| `src/llm/__init__.py` | — | Sim | (pacote) | Sim | VERIFICADO |
| `src/llm/parser.py` | 60 | Sim | 136 linhas | Importado por run_llm.py | VERIFICADO |
| `src/llm/prompts.py` | 40 | Sim | 84 linhas | Importado por run_llm.py | VERIFICADO |
| `src/llm/cliente_ollama.py` | 50 | Sim | 123 linhas | Importado por run_llm.py | VERIFICADO |
| `run_llm.py` | 120 | Sim | 284 linhas | CLI funcional (`--help` OK) | VERIFICADO |
| `tests/test_llm_parser.py` | — | Sim | 19 testes | Passam sem rede | VERIFICADO |
| `tests/test_llm_prompts.py` | — | Sim | 14 testes | Passam com monkeypatch | VERIFICADO |
| `tests/test_run_llm.py` | — | Sim | 6 testes | Passam com fn_gerar fake | VERIFICADO |

---

## Verificação de Links-Chave (Wiring)

| De | Para | Via | Status | Detalhe |
|----|------|-----|--------|---------|
| `src/llm/parser.py` | `run_regras.UPOS_VALIDOS` | `from run_regras import UPOS_VALIDOS` | WIRED | `parser.py:15` — importa e usa em `tag_valida` (:77) e em `alinhar_tags` via `FALLBACK` |
| `src/llm/cliente_ollama.py` | `http://localhost:11434/api/generate` | `requests.post` com options temperature/seed/keep_alive/format | WIRED | `cliente_ollama.py:20,86-95` — URL constante, todas as 4 options no corpo |
| `src/llm/parser.py` | lista de tokens da sentença | `len(arr) != n_tokens` → fallback; token-a-token quando alinha | WIRED | `parser.py:122-135` — fallback total se comprimento diferente, individual por posição |
| `run_llm.py` | `src/llm.alinhar_tags / montar_prompt / gerar` | imports diretos | WIRED | `run_llm.py:26-28` — `from src.llm.prompts import montar_prompt`, `from src.llm.cliente_ollama import gerar, Resposta`, `from src.llm.parser import alinhar_tags` |
| `run_llm.py` | `.jsonl` incremental | `open(caminho, "a")` + `asdict` + `json.dumps` | WIRED | `run_llm.py:63-79` — `_append_registros` abre em modo `"a"` com flush |
| `run_llm.py` | `ler_jsonl` (resume) | coleta `sentenca_id` presentes para pular | WIRED | `run_llm.py:60,143` — `{r.sentenca_id for r in ler_jsonl(caminho)}`, `if s.sentenca_id in feitas: continue` |
| `run_llm.py` | `<tarefa>.meta.json` | substituição `.jsonl` → `.meta.json` + `json.dump` | WIRED | `run_llm.py:192-197` — `caminho_saida.replace(".jsonl", ".meta.json")` |

---

## Cobertura de REQ-04

| Critério REQ-04 | Status | Evidência |
|-----------------|--------|-----------|
| CLI `--modelo <llama3.1:8b\|qwen2.5:3b\|llama3.2:3b> --tarefa ner\|upos` | SATISFEITO | `run_llm.py:226-259` — argparse com `--modelo` obrigatório (3 modelos no help) e `--tarefa choices=["ner","upos"]` |
| 1 sentença por chamada (sem batching) | SATISFEITO | `run_llm.py:141-168` — loop unitário; `fn_gerar` chamado uma vez por sentença |
| `temperature=0` / `seed=42` | SATISFEITO | `cliente_ollama.py:79-82` |
| Parsing robusto de volta ao contrato comum | SATISFEITO | `parser.py` + `run_llm.py:149,152-168` |
| `--modelo` parametrizável (mesmo script, 3 LLMs) | SATISFEITO | `run_llm.py:87` — `modelo: str` sem allowlist rígida |
| Registrar tempo/velocidade por modelo | SATISFEITO | `run_llm.py:179-197` — meta.json com tok/s, sent/s, wall_clock_s |

---

## Execução da Suite de Testes

```
python -m pytest tests/test_llm_parser.py tests/test_llm_prompts.py tests/test_run_llm.py -v
```

**Resultado: 39 passed** (sem Ollama no ar — todos os testes usam mocks/funções fake)

```
python -m pytest tests/ -v
```

**Resultado: 76 passed** (suite completa — nenhuma regressão nas fases anteriores)

---

## Anti-Padrões Verificados

| Arquivo | Padrão Verificado | Resultado |
|---------|-------------------|-----------|
| `run_llm.py` | Uso de `escrever_jsonl` (modo `"w"`) | AUSENTE — zero ocorrências; usa `open(...,"a")` diretamente |
| `run_llm.py` | TODO/FIXME/placeholder | AUSENTE |
| `src/llm/parser.py` | Redefinição das 17 UPOS | AUSENTE — importa `UPOS_VALIDOS` de `run_regras` |
| `tests/test_run_llm.py` | Chamadas reais ao Ollama (`localhost:11434`) | AUSENTE — todos os testes usam `fn_gerar` fake |
| `tests/test_llm_prompts.py` | Chamadas reais ao Ollama | AUSENTE — `monkeypatch` em `requests.post` |

---

## Verificação Comportamental (Spot-Checks)

| Comportamento | Comando | Resultado |
|---------------|---------|-----------|
| CLI `--help` lista 3 modelos e tarefas ner/upos | `python run_llm.py --help` | PASS — llama3.1:8b, qwen2.5:3b, llama3.2:3b visíveis; `--tarefa {ner,upos}` |
| Fallback UPOS: `["NOUN","FOO"]` → `["NOUN","NOUN"]`, n=1 | `python -c "from src.llm.parser import alinhar_tags; t,n=alinhar_tags('upos',['a','b'],'[\"NOUN\",\"FOO\"]'); assert t==['NOUN','NOUN'] and n==1; print('FB_OK')"` | PASS — imprime `FB_OK` |
| Prompt embute tokens e menciona JSON | `python -c "from src.llm.prompts import montar_prompt; p=montar_prompt('upos',['O','cão']); assert 'cão' in p and 'JSON' in p.upper(); print('PROMPT_OK')"` | PASS — imprime `PROMPT_OK` |
| Sanitização de caminho `:` → `_` | `python -c "from src.io.contrato import caminho_resultado; p=caminho_resultado('base_mapeada','llama3.1:8b','ner'); assert 'llama3.1_8b' in p and ':' not in p; print('OK')"` | PASS — `resultados\base_mapeada\llama3.1_8b\ner.jsonl` |

---

## Verificação Humana Necessária

Nenhum item requer verificação humana para os critérios desta fase. As 6 rodadas completas (1167 sentenças × 3 modelos × 2 tarefas ≈ 7002 chamadas Ollama, horas de runtime) são **trabalho de execução do usuário**, não critério de verificação desta fase — conforme documentado em `03-02-PLAN.md` seção `<verification>`.

---

## Resumo dos Gaps

Nenhum gap encontrado.

---

## Veredicto

**GOAL ACHIEVED**

Todos os 9 must-haves verificados, 5/5 Success Criteria do ROADMAP satisfeitos, 39/39 testes da fase passam sem rede, suite completa 76/76 sem regressões.

O runner `run_llm.py` entrega:
- CLI parametrizável com os 3 modelos e 2 tarefas, 1 sentença por chamada
- Reprodutibilidade via temperature=0/seed=42/keep_alive=-1/format=json (constantes no código)
- Prompts versionados (`INSTRUCAO_NER` IOB em inglês, `INSTRUCAO_UPOS` 17 tags em português)
- Parser robusto com fallback rastreável (NER "O", UPOS "NOUN") e contagem de fallbacks
- Emissão `.jsonl` incremental em modo append + resume via `ler_jsonl` (pula sentença_id presentes)
- `modelo` preservado com `:` no `Registro`; sanitização `:` → `_` apenas no caminho do arquivo
- Métricas `tok_por_seg`, `sent_por_seg`, `fallbacks`, `wall_clock_s` persistidas em `.meta.json` por (modelo, tarefa)

---

_Verificado: 2026-06-17T16:00:00Z_
_Verificador: Claude (gsd-verifier)_
