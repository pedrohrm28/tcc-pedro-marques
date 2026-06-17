"""Testes de agregar.py (Fase 4 — REQ-05/REQ-06).

Todos os testes usam gold SINTÉTICO (objetos Sentenca montados à mão) e .jsonl
mínimos em tmp_path. NÃO carregam os corpora reais nem rodam Ollama.
"""
from __future__ import annotations

import json

import pytest

import agregar
from src.io.contrato import Registro, escrever_jsonl
from src.io.corpora import Sentenca


# ---------------------------------------------------------------------------
# Helpers sintéticos
# ---------------------------------------------------------------------------


def _gold_ner():
    """Gold NER mínimo: 2 sentenças, 3 tokens no total."""
    return [
        Sentenca("1", [("a", "O"), ("b", "B-geo")]),
        Sentenca("2", [("c", "O")]),
    ]


def _registros_ner(modelo="crf", tags=("O", "B-geo", "O")):
    """Registros .jsonl casando com _gold_ner (3 tokens)."""
    chaves = [("1", 0, "a"), ("1", 1, "b"), ("2", 0, "c")]
    return [
        Registro(
            tarefa="ner",
            modelo=modelo,
            sentenca_id=sid,
            posicao=pos,
            token=tok,
            tag_predita=tag,
        )
        for (sid, pos, tok), tag in zip(chaves, tags)
    ]


# ---------------------------------------------------------------------------
# Task 1 — alinhamento, métricas, JSON, meta
# ---------------------------------------------------------------------------


def test_alinhar_predicao_casa_por_chave():
    """gold_seqs/pred_seqs agrupados por sentença; discrepância só onde diverge."""
    gold = _gold_ner()
    registros = _registros_ner(tags=("O", "I-geo", "O"))  # diverge em (1,1)
    gold_seqs, pred_seqs, discrepancias = agregar.alinhar_predicao(gold, registros)

    assert gold_seqs == [["O", "B-geo"], ["O"]]
    assert pred_seqs == [["O", "I-geo"], ["O"]]
    assert [len(g) for g in gold_seqs] == [len(p) for p in pred_seqs]
    # Uma discrepância: sentença "1", posição 1, token "b", gold B-geo, pred I-geo.
    assert discrepancias == [("1", 1, "b", "B-geo", "I-geo")]


def test_alinhar_predicao_sem_discrepancia():
    gold = _gold_ner()
    registros = _registros_ner(tags=("O", "B-geo", "O"))
    _, _, discrepancias = agregar.alinhar_predicao(gold, registros)
    assert discrepancias == []


def test_alinhar_predicao_aborta_em_desalinhamento():
    """Menos registros que tokens do gold -> RuntimeError claro (D-05)."""
    gold = _gold_ner()  # 3 tokens
    registros = _registros_ner(tags=("O", "B-geo", "O"))[:2]  # só 2
    with pytest.raises(RuntimeError):
        agregar.alinhar_predicao(gold, registros)


def test_indexar_gold():
    gold = _gold_ner()
    indice, ordem = agregar.indexar_gold(gold)
    assert indice[("1", 0)] == "O"
    assert indice[("1", 1)] == "B-geo"
    assert indice[("2", 0)] == "O"
    assert ordem == [("1", ["O", "B-geo"]), ("2", ["O"])]


def test_calcular_metricas_ner_inclui_entidade():
    gold = _gold_ner()
    registros = _registros_ner(tags=("O", "B-geo", "O"))
    gold_seqs, pred_seqs, _ = agregar.alinhar_predicao(gold, registros)
    m = agregar.calcular_metricas("ner", gold_seqs, pred_seqs)
    assert m["entidade"] is not None
    assert "precisao" in m["entidade"] and "f1" in m["entidade"]
    assert m["n_tokens"] == 3
    assert "precisao" in m["micro"]
    assert isinstance(m["por_classe"], list) and m["por_classe"]


def test_calcular_metricas_upos_sem_entidade():
    gold = [Sentenca("1", [("o", "DET"), ("gato", "NOUN")])]
    registros = [
        Registro("upos", "regras", "1", 0, "o", "DET"),
        Registro("upos", "regras", "1", 1, "gato", "NOUN"),
    ]
    gold_seqs, pred_seqs, _ = agregar.alinhar_predicao(gold, registros)
    m = agregar.calcular_metricas("upos", gold_seqs, pred_seqs)
    assert m["entidade"] is None
    assert m["n_tokens"] == 2


def test_escrever_metricas_json(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    gold = _gold_ner()
    registros = _registros_ner(tags=("O", "B-geo", "O"))
    gold_seqs, pred_seqs, _ = agregar.alinhar_predicao(gold, registros)
    m = agregar.calcular_metricas("ner", gold_seqs, pred_seqs)

    caminho = agregar.escrever_metricas_json(
        "base_mapeada", "crf", "ner", m, tempo=None, velocidade=None
    )
    assert caminho.endswith("ner.metricas.json")

    with open(caminho, encoding="utf-8") as f:
        dados = json.load(f)
    for chave in (
        "modelo",
        "tarefa",
        "por_classe",
        "micro",
        "entidade",
        "n_tokens",
        "tempo",
        "velocidade",
    ):
        assert chave in dados
    assert dados["modelo"] == "crf"
    assert dados["tarefa"] == "ner"
    assert dados["tempo"] is None and dados["velocidade"] is None


def test_ler_meta_ausente(tmp_path):
    caminho_jsonl = str(tmp_path / "ner.jsonl")
    assert agregar.ler_meta(caminho_jsonl) == (None, None)


def test_ler_meta_presente(tmp_path):
    caminho_jsonl = tmp_path / "ner.jsonl"
    caminho_meta = tmp_path / "ner.meta.json"
    caminho_meta.write_text(
        json.dumps({"eval_duration_s": 12.5, "tok_por_seg": 100.0}),
        encoding="utf-8",
    )
    tempo, velocidade = agregar.ler_meta(str(caminho_jsonl))
    assert tempo == 12.5
    assert velocidade == 100.0


# ---------------------------------------------------------------------------
# Task 2 — descoberta, tabelas, discrepâncias, CLI, degradação graciosa
# ---------------------------------------------------------------------------


def test_formatar_num():
    assert agregar.formatar_num(0.6666) == "0.667"
    assert agregar.formatar_num(None) == "—"


def test_descobrir_presentes_degrada_gracioso(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from src.io.contrato import caminho_resultado

    # Só cria crf/ner.jsonl.
    escrever_jsonl(caminho_resultado("base_mapeada", "crf", "ner"), _registros_ner())

    presentes, ausentes = agregar.descobrir_presentes("base_mapeada")
    assert ("crf", "ner") in presentes
    assert ("llama3.1:8b", "ner") in ausentes
    assert ("regras", "upos") in ausentes
    # 5 modelos x 2 tarefas = 10; 1 presente, 9 ausentes.
    assert len(presentes) + len(ausentes) == 10
    assert len(presentes) == 1


def test_montar_tabela_ner_tem_f1_entidade():
    markdown, linhas_csv = agregar.montar_tabela("ner", [])
    assert "f1_entidade" in linhas_csv[0]
    assert "f1_entidade" in markdown


def test_montar_tabela_upos_sem_f1_entidade():
    markdown, linhas_csv = agregar.montar_tabela("upos", [])
    assert "f1_entidade" not in linhas_csv[0]
    assert "f1_entidade" not in markdown


def test_montar_tabela_crf_tempo_travessao():
    linha = {
        "modelo": "crf",
        "precisao": 0.9,
        "cobertura": 0.8,
        "micro_f1": 0.85,
        "f1_entidade": 0.7,
        "tempo_s": None,
        "tok_s": None,
    }
    _, linhas_csv = agregar.montar_tabela("ner", [linha])
    linha_crf = linhas_csv[1]
    assert linha_crf[0] == "crf"
    assert linha_crf[-1] == "—" and linha_crf[-2] == "—"  # tok_s, tempo_s


def test_agregar_degradacao_graciosa(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from src.io.contrato import caminho_resultado

    # Gold sintético via monkeypatch dos loaders usados em agregar.
    monkeypatch.setattr(
        agregar,
        "carregar_gmb",
        lambda **k: [Sentenca("1", [("a", "O"), ("b", "B-geo")]), Sentenca("2", [("c", "O")])],
    )
    monkeypatch.setattr(
        agregar,
        "carregar_conllu",
        lambda **k: [Sentenca("1", [("o", "DET")])],
    )
    # Os loaders ficam dentro do dict LOADERS_GOLD (resolvido em import-time);
    # repatch para apontar para os fakes.
    monkeypatch.setitem(agregar.LOADERS_GOLD, "ner", agregar.carregar_gmb)
    monkeypatch.setitem(agregar.LOADERS_GOLD, "upos", agregar.carregar_conllu)

    # Só crf/ner presente (casa com gold de 3 tokens).
    escrever_jsonl(
        caminho_resultado("base_mapeada", "crf", "ner"),
        _registros_ner(tags=("O", "B-geo", "O")),
    )

    resumo = agregar.agregar("base_mapeada")

    import os

    assert os.path.exists("resultados/base_mapeada/tabela_ner.md")
    assert os.path.exists("resultados/base_mapeada/tabela_ner.csv")
    assert os.path.exists("resultados/base_mapeada/tabela_upos.md")

    with open("resultados/base_mapeada/tabela_ner.csv", encoding="utf-8") as f:
        conteudo = f.read()
    assert "crf" in conteudo
    assert "llama3.1:8b" not in conteudo  # LLM ausente não vira linha

    assert resumo["ausentes"]  # não vazio
    assert resumo["erros"] == []
    assert ("crf", "ner") in resumo["presentes"]


def test_agregar_discrepancias_csv(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from src.io.contrato import caminho_resultado

    monkeypatch.setattr(
        agregar,
        "carregar_gmb",
        lambda **k: [Sentenca("1", [("a", "O"), ("b", "B-geo")]), Sentenca("2", [("c", "O")])],
    )
    monkeypatch.setattr(agregar, "carregar_conllu", lambda **k: [])
    monkeypatch.setitem(agregar.LOADERS_GOLD, "ner", agregar.carregar_gmb)
    monkeypatch.setitem(agregar.LOADERS_GOLD, "upos", agregar.carregar_conllu)

    # 1 token diverge: posição (1,1) gold B-geo, pred I-geo.
    escrever_jsonl(
        caminho_resultado("base_mapeada", "crf", "ner"),
        _registros_ner(tags=("O", "I-geo", "O")),
    )

    agregar.agregar("base_mapeada")

    with open("resultados/base_mapeada/discrepancias.csv", encoding="utf-8") as f:
        linhas = f.read().strip().splitlines()
    assert linhas[0] == "tarefa,modelo,sentenca_id,posicao,token,tag_gold,tag_predita"
    # Uma única discrepância esperada.
    assert linhas[1] == "ner,crf,1,1,b,B-geo,I-geo"
    assert len(linhas) == 2


def test_agregar_desalinhamento_reportado_nao_quebra(tmp_path, monkeypatch):
    """.jsonl com nº de tokens != gold -> erro reportado, demais não derrubam."""
    monkeypatch.chdir(tmp_path)
    from src.io.contrato import caminho_resultado

    monkeypatch.setattr(
        agregar,
        "carregar_gmb",
        lambda **k: [Sentenca("1", [("a", "O"), ("b", "B-geo")]), Sentenca("2", [("c", "O")])],
    )
    monkeypatch.setattr(agregar, "carregar_conllu", lambda **k: [])
    monkeypatch.setitem(agregar.LOADERS_GOLD, "ner", agregar.carregar_gmb)
    monkeypatch.setitem(agregar.LOADERS_GOLD, "upos", agregar.carregar_conllu)

    # Só 2 registros para 3 tokens do gold.
    escrever_jsonl(
        caminho_resultado("base_mapeada", "crf", "ner"),
        _registros_ner(tags=("O", "B-geo", "O"))[:2],
    )

    resumo = agregar.agregar("base_mapeada")  # NÃO levanta
    assert len(resumo["erros"]) == 1
    assert "crf/ner" in resumo["erros"][0]
