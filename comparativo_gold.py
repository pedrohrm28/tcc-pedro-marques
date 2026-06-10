"""
Comparativo LLM open-source (gpt-oss 20B/120B via Ollama) x padrao-ouro
========================================================================
TCC II - Pedro Marques

Compara as saidas do LLM com as anotacoes de referencia (gold standard):
  - NER (esquema IOB): corpus usado com o modelo CRF (arquivo CoNLL: token TAB tag)
  - POS  (UPOS):       treebank Bosque (arquivo CoNLL-U)

Calcula precisao, cobertura (recall) e F1 em nivel de token e, para NER,
tambem em nivel de entidade (seqeval). Gera CSV de discrepancias.

Requisitos:
  pip install requests seqeval
  Ollama instalado e rodando:  ollama pull gpt-oss:20b   (ou gpt-oss:120b)

Uso:
  python comparativo_gold.py --tarefa ner  --gold corpus_crf.conll  --modelo gpt-oss:20b
  python comparativo_gold.py --tarefa upos --gold bosque.conllu     --modelo gpt-oss:20b
"""

import argparse
import csv
import json
import sys
from collections import defaultdict

import requests

OLLAMA_URL = "http://localhost:11434/api/chat"

# ---------------------------------------------------------------------------
# Prompts (espelham os prompts do TCC I, Figuras 1 e 2)
# ---------------------------------------------------------------------------

PROMPT_NER = """Voce e um sistema de Reconhecimento de Entidades Nomeadas (NER) e \
classificacao de intencao para o portugues brasileiro.

Receba a lista de tokens abaixo e devolva APENAS um JSON valido, sem texto extra, \
no formato:
{{"intent": "<intencao>", "tokens": [["token", "TAG_IOB"], ...]}}

Regras:
- Use exatamente os tokens fornecidos, na mesma ordem, sem juntar nem dividir.
- TAG_IOB segue o esquema IOB: O, B-<TIPO>, I-<TIPO>.
- Tipos de entidade possiveis: {tipos}.

Tokens: {tokens}"""

PROMPT_UPOS = """Voce e um etiquetador morfossintatico (POS tagger) do padrao \
Universal Dependencies para o portugues, e tambem classificador de intencao.

Receba a lista de tokens abaixo e devolva APENAS um JSON valido, sem texto extra, \
no formato:
{{"intent": "<intencao>", "tokens": [["token", "UPOS"], ...]}}

Regras:
- Use exatamente os tokens fornecidos, na mesma ordem, sem juntar nem dividir.
- UPOS deve ser uma das tags: ADJ, ADP, ADV, AUX, CCONJ, DET, INTJ, NOUN, NUM, \
PART, PRON, PROPN, PUNCT, SCONJ, SYM, VERB, X.

Tokens: {tokens}"""


# ---------------------------------------------------------------------------
# Leitura dos corpora gold
# ---------------------------------------------------------------------------

def carregar_conll_iob(caminho):
    """CoNLL simples: 'token<TAB>tag' por linha, sentencas separadas por linha vazia."""
    sentencas, atual = [], []
    with open(caminho, encoding="utf-8") as f:
        for linha in f:
            linha = linha.rstrip("\n")
            if not linha.strip():
                if atual:
                    sentencas.append(atual)
                    atual = []
                continue
            partes = linha.split("\t") if "\t" in linha else linha.split()
            atual.append((partes[0], partes[-1]))
    if atual:
        sentencas.append(atual)
    return sentencas


def carregar_conllu(caminho):
    """CoNLL-U (Bosque/UD): colunas ID FORM LEMMA UPOS ... Ignora multiword tokens."""
    sentencas, atual = [], []
    with open(caminho, encoding="utf-8") as f:
        for linha in f:
            linha = linha.rstrip("\n")
            if linha.startswith("#"):
                continue
            if not linha.strip():
                if atual:
                    sentencas.append(atual)
                    atual = []
                continue
            cols = linha.split("\t")
            if "-" in cols[0] or "." in cols[0]:  # multiword tokens / empty nodes
                continue
            atual.append((cols[1], cols[3]))  # (FORM, UPOS)
    if atual:
        sentencas.append(atual)
    return sentencas


# ---------------------------------------------------------------------------
# Chamada ao LLM (Ollama, modelo open-source local)
# ---------------------------------------------------------------------------

def consultar_llm(modelo, prompt, tentativas=3):
    payload = {
        "model": modelo,
        "messages": [{"role": "user", "content": prompt}],
        "format": "json",          # forca saida JSON
        "stream": False,
        "options": {"temperature": 0.0, "seed": 42},  # reprodutibilidade
    }
    for t in range(tentativas):
        try:
            r = requests.post(OLLAMA_URL, json=payload, timeout=300)
            r.raise_for_status()
            conteudo = r.json()["message"]["content"]
            return json.loads(conteudo)
        except (requests.RequestException, json.JSONDecodeError, KeyError) as e:
            print(f"  aviso: tentativa {t+1} falhou ({e})", file=sys.stderr)
    return None


# ---------------------------------------------------------------------------
# Alinhamento e metricas
# ---------------------------------------------------------------------------

def alinhar(gold_tokens, pred_pares):
    """Alinha pela posicao; se o LLM divergir na tokenizacao, marca 'X-DESALINHADO'."""
    pred_tags = []
    pred_lista = pred_pares if isinstance(pred_pares, list) else []
    for i, (tok, _) in enumerate(gold_tokens):
        if i < len(pred_lista) and isinstance(pred_lista[i], (list, tuple)) and len(pred_lista[i]) >= 2:
            pred_tok, pred_tag = pred_lista[i][0], str(pred_lista[i][1])
            pred_tags.append(pred_tag if str(pred_tok) == tok else "X-DESALINHADO")
        else:
            pred_tags.append("X-AUSENTE")
    return pred_tags


def metricas_token(gold_seqs, pred_seqs):
    """Precisao/cobertura/F1 por classe + micro, em nivel de token."""
    tp, fp, fn = defaultdict(int), defaultdict(int), defaultdict(int)
    for g_seq, p_seq in zip(gold_seqs, pred_seqs):
        for g, p in zip(g_seq, p_seq):
            if g == p:
                tp[g] += 1
            else:
                fp[p] += 1
                fn[g] += 1
    classes = sorted(set(list(tp) + list(fp) + list(fn)))
    linhas = []
    TP, FP, FN = sum(tp.values()), sum(fp.values()), sum(fn.values())
    for c in classes:
        p = tp[c] / (tp[c] + fp[c]) if (tp[c] + fp[c]) else 0.0
        r = tp[c] / (tp[c] + fn[c]) if (tp[c] + fn[c]) else 0.0
        f = 2 * p * r / (p + r) if (p + r) else 0.0
        linhas.append((c, p, r, f, tp[c] + fn[c]))
    micro_p = TP / (TP + FP) if (TP + FP) else 0.0
    micro_r = TP / (TP + FN) if (TP + FN) else 0.0
    micro_f = 2 * micro_p * micro_r / (micro_p + micro_r) if (micro_p + micro_r) else 0.0
    return linhas, (micro_p, micro_r, micro_f)


def metricas_entidade(gold_seqs, pred_seqs):
    """Precisao/cobertura/F1 em nivel de ENTIDADE (so para NER/IOB), via seqeval."""
    try:
        from seqeval.metrics import (classification_report, f1_score,
                                     precision_score, recall_score)
    except ImportError:
        print("seqeval nao instalado (pip install seqeval); pulando metricas de entidade.")
        return
    print("\n=== Metricas em nivel de ENTIDADE (seqeval) ===")
    print(classification_report(gold_seqs, pred_seqs, digits=3))
    print(f"Precisao: {precision_score(gold_seqs, pred_seqs):.3f}  "
          f"Cobertura: {recall_score(gold_seqs, pred_seqs):.3f}  "
          f"F1: {f1_score(gold_seqs, pred_seqs):.3f}")


# ---------------------------------------------------------------------------
# Pipeline principal
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="Comparativo LLM open-source x gold standard")
    ap.add_argument("--tarefa", choices=["ner", "upos"], required=True)
    ap.add_argument("--gold", required=True, help="arquivo gold (CoNLL p/ ner, CoNLL-U p/ upos)")
    ap.add_argument("--modelo", default="gpt-oss:20b", help="gpt-oss:20b ou gpt-oss:120b")
    ap.add_argument("--limite", type=int, default=0, help="processar apenas N sentencas (0 = todas)")
    ap.add_argument("--saida", default="resultados", help="prefixo dos arquivos de saida")
    args = ap.parse_args()

    if args.tarefa == "ner":
        sentencas = carregar_conll_iob(args.gold)
        tipos = sorted({t.split("-", 1)[1] for s in sentencas for _, t in s if "-" in t})
        prompt_base = PROMPT_NER
    else:
        sentencas = carregar_conllu(args.gold)
        tipos = []
        prompt_base = PROMPT_UPOS

    if args.limite:
        sentencas = sentencas[: args.limite]
    print(f"{len(sentencas)} sentencas carregadas | modelo: {args.modelo}")

    gold_seqs, pred_seqs, discrepancias, falhas = [], [], [], 0

    for idx, sent in enumerate(sentencas, 1):
        tokens = [tok for tok, _ in sent]
        gold = [tag for _, tag in sent]
        prompt = prompt_base.format(tokens=json.dumps(tokens, ensure_ascii=False),
                                    tipos=", ".join(tipos))
        resposta = consultar_llm(args.modelo, prompt)
        if resposta is None:
            falhas += 1
            pred = ["X-FALHA"] * len(tokens)
            intent = ""
        else:
            pred = alinhar(sent, resposta.get("tokens", []))
            intent = resposta.get("intent", "")

        gold_seqs.append(gold)
        pred_seqs.append(pred)
        for tok, g, p in zip(tokens, gold, pred):
            if g != p:
                discrepancias.append([idx, tok, g, p, intent])
        print(f"\r{idx}/{len(sentencas)} sentencas processadas", end="", flush=True)
    print()

    # --- Metricas em nivel de token ---
    linhas, (mp, mr, mf) = metricas_token(gold_seqs, pred_seqs)
    print("\n=== Metricas em nivel de TOKEN ===")
    print(f"{'classe':<15}{'precisao':>10}{'cobertura':>11}{'F1':>8}{'suporte':>9}")
    for c, p, r, f, sup in linhas:
        print(f"{c:<15}{p:>10.3f}{r:>11.3f}{f:>8.3f}{sup:>9}")
    print(f"{'MICRO':<15}{mp:>10.3f}{mr:>11.3f}{mf:>8.3f}")

    # --- Metricas em nivel de entidade (NER) ---
    if args.tarefa == "ner":
        metricas_entidade(gold_seqs, pred_seqs)

    # --- Arquivos de saida ---
    with open(f"{args.saida}_discrepancias.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["sentenca", "token", "gold", "llm", "intent"])
        w.writerows(discrepancias)
    with open(f"{args.saida}_metricas.json", "w", encoding="utf-8") as f:
        json.dump({
            "modelo": args.modelo, "tarefa": args.tarefa,
            "sentencas": len(sentencas), "falhas_llm": falhas,
            "micro": {"precisao": mp, "cobertura": mr, "f1": mf},
            "por_classe": [{"classe": c, "precisao": p, "cobertura": r,
                            "f1": fv, "suporte": s} for c, p, r, fv, s in linhas],
        }, f, ensure_ascii=False, indent=2)
    print(f"\nArquivos gerados: {args.saida}_metricas.json | {args.saida}_discrepancias.csv")
    print(f"Falhas de resposta do LLM: {falhas}")


if __name__ == "__main__":
    main()
