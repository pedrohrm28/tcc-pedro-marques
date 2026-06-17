"""Métricas puras de avaliação (nível token e nível entidade).

Núcleo de métricas da Fase 4 (D-01), extraído/refatorado do
``comparativo_gold.py`` legado (TCC I). Módulo SEM efeitos colaterais:
sem ``print`` no caminho de sucesso, sem I/O de arquivo, sem rede. O
agregador (plano 04-02) consome estas funções para montar JSON, tabelas
e CSVs de discrepância.

Origem das funções no legado:
- ``metricas_token`` (l.149-170): COPIADO verbatim — já retorna dados.
- ``alinhar`` (l.136-146): COPIADO como helper/referência de alinhamento.
- ``metricas_entidade`` (l.173-185): REFATORADO — o legado IMPRIME o
  ``classification_report`` e as métricas; aqui RETORNAMOS um dict.
"""
from __future__ import annotations

from collections import defaultdict


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
