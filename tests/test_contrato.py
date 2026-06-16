"""Testes de round-trip e validação do contrato de saída (.jsonl). REQ-01."""
import os
import pytest
from src.io.contrato import Registro, escrever_jsonl, ler_jsonl, caminho_resultado


def test_round_trip(tmp_path):
    """Escrever e ler de volta deve produzir lista idêntica."""
    registros = [
        Registro("ner", "gold", "1.0", 0, "The", "O"),
        Registro("ner", "crf", "1.0", 1, "notícia", "B-ORG"),
        Registro("upos", "gold", "CF756-1", 6, "notícia", "NOUN"),
    ]
    caminho = str(tmp_path / "out.jsonl")
    n = escrever_jsonl(caminho, registros)
    lidos = ler_jsonl(caminho)
    assert n == 3
    assert lidos == registros


def test_uma_linha_por_token(tmp_path):
    """O arquivo deve ter exatamente N linhas para N registros."""
    registros = [
        Registro("ner", "gold", "1.0", i, f"tok{i}", "O")
        for i in range(5)
    ]
    caminho = str(tmp_path / "tokens.jsonl")
    escrever_jsonl(caminho, registros)
    with open(caminho, encoding="utf-8") as f:
        linhas = [l for l in f.readlines() if l.strip()]
    assert len(linhas) == 5


def test_tarefa_invalida():
    """Construir Registro com tarefa inválida deve levantar ValueError."""
    with pytest.raises(ValueError, match="tarefa inválida"):
        Registro("pos", "gold", "1.0", 0, "token", "NOUN")


def test_caminho_resultado_windows():
    """caminho_resultado deve sanitizar ':' e conter 'base_mapeada'."""
    caminho = caminho_resultado("base_mapeada", "gpt-oss:120b", "upos")
    basename = os.path.basename(caminho)
    assert ":" not in basename
    assert "base_mapeada" in caminho


def test_acento_preservado(tmp_path):
    """Round-trip de token com acento deve preservar o caractere íntegro."""
    r = Registro("ner", "gold", "1.0", 0, "notícia", "O")
    caminho = str(tmp_path / "acento.jsonl")
    escrever_jsonl(caminho, [r])
    lidos = ler_jsonl(caminho)
    assert lidos[0].token == "notícia"
    assert "í" in lidos[0].token
