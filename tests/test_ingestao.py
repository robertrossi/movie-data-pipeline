from pathlib import Path

import duckdb
import pytest

from pipeline import db, ingestao


def test_ingestao_le_csvs_preserva_texto_vazio_e_registros(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pasta_raw = tmp_path / "raw"
    pasta_raw.mkdir()
    banco = tmp_path / "temporario.duckdb"
    monkeypatch.setattr(db, "PASTA_RAW", pasta_raw)
    monkeypatch.setattr(db, "_ARQUIVO_BANCO", banco)

    for arquivo, _ in ingestao.ARQUIVOS_TABELAS:
        conteudo = 'id,texto\n1,NA\n2,""\n'
        (pasta_raw / arquivo).write_text(conteudo, encoding="utf-8")

    ingestao.main()

    con = duckdb.connect(str(banco), read_only=True)
    try:
        for _, tabela in ingestao.ARQUIVOS_TABELAS:
            resultado = con.execute(
                f"SELECT id, texto FROM raw.{tabela} ORDER BY id"
            ).fetchall()
            assert resultado == [("1", "NA"), ("2", None)]
    finally:
        con.close()


def test_ingestao_lista_arquivos_ausentes_sem_criar_banco(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    pasta_raw = tmp_path / "raw_vazia"
    pasta_raw.mkdir()
    banco = tmp_path / "nao_criado.duckdb"
    monkeypatch.setattr(db, "PASTA_RAW", pasta_raw)
    monkeypatch.setattr(db, "_ARQUIVO_BANCO", banco)

    with pytest.raises(SystemExit) as erro:
        ingestao.main()

    assert erro.value.code == 1
    saida = capsys.readouterr().out
    assert all(arquivo in saida for arquivo, _ in ingestao.ARQUIVOS_TABELAS)
    assert not banco.exists()


def test_ingestao_nao_abre_banco_quando_falta_apenas_um_csv(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pasta_raw = tmp_path / "raw_parcial"
    pasta_raw.mkdir()
    banco = tmp_path / "nao_criado.duckdb"
    monkeypatch.setattr(db, "PASTA_RAW", pasta_raw)
    monkeypatch.setattr(db, "_ARQUIVO_BANCO", banco)
    for arquivo, _ in ingestao.ARQUIVOS_TABELAS[:-1]:
        (pasta_raw / arquivo).write_text("id\n1\n", encoding="utf-8")

    with pytest.raises(SystemExit, match="1"):
        ingestao.main()

    assert not banco.exists()
