from pathlib import Path

import duckdb
import pytest

from pipeline import db


def _create_database(path: Path) -> None:
    con = duckdb.connect(str(path))
    try:
        con.execute("CREATE TABLE amostra AS SELECT 42 AS valor")
    finally:
        con.close()


def test_conexao_padrao_cria_e_permite_escrita_em_banco_temporario(
    tmp_path, monkeypatch
):
    database = tmp_path / "padrao.duckdb"
    monkeypatch.setattr(db, "_ARQUIVO_BANCO", database)
    monkeypatch.delenv("MOVIE_DATA_DB_PATH", raising=False)

    con = db.conectar()
    try:
        con.execute("CREATE TABLE amostra AS SELECT 42 AS valor")
        assert con.execute("SELECT valor FROM amostra").fetchone() == (42,)
    finally:
        con.close()

    assert database.is_file()


def test_variavel_de_ambiente_seleciona_banco_alternativo_somente_leitura(
    tmp_path, monkeypatch
):
    database = tmp_path / "alternativo.duckdb"
    _create_database(database)
    monkeypatch.setenv("MOVIE_DATA_DB_PATH", str(database))

    con = db.conectar(must_exist=True, read_only=True)
    try:
        assert con.execute("SELECT valor FROM amostra").fetchone() == (42,)
        with pytest.raises(duckdb.Error):
            con.execute("CREATE TABLE bloqueada AS SELECT 1")
    finally:
        con.close()


def test_must_exist_recusa_banco_inexistente(tmp_path, monkeypatch):
    database = tmp_path / "ausente.duckdb"
    monkeypatch.setattr(db, "_ARQUIVO_BANCO", database)

    with pytest.raises(FileNotFoundError, match="Banco DuckDB não encontrado"):
        db.conectar(must_exist=True)

    assert not database.exists()


def test_read_only_permite_consulta_e_recusa_escrita(tmp_path, monkeypatch):
    database = tmp_path / "leitura.duckdb"
    _create_database(database)
    monkeypatch.setattr(db, "_ARQUIVO_BANCO", database)

    con = db.conectar(read_only=True)
    try:
        assert con.execute("SELECT valor FROM amostra").fetchone() == (42,)
        with pytest.raises(duckdb.Error):
            con.execute("CREATE TABLE bloqueada AS SELECT 1")
    finally:
        con.close()


def test_must_exist_e_read_only_funcionam_em_conjunto(tmp_path, monkeypatch):
    database = tmp_path / "somente_leitura.duckdb"
    _create_database(database)
    monkeypatch.setattr(db, "_ARQUIVO_BANCO", database)

    con = db.conectar(must_exist=True, read_only=True)
    try:
        assert con.execute("SELECT valor FROM amostra").fetchone() == (42,)
    finally:
        con.close()


def test_read_only_recusa_criar_banco_ausente(tmp_path, monkeypatch):
    database = tmp_path / "ausente_read_only.duckdb"
    monkeypatch.setattr(db, "_ARQUIVO_BANCO", database)

    with pytest.raises(FileNotFoundError, match="Banco DuckDB não encontrado"):
        db.conectar(read_only=True)

    assert not database.exists()


def test_falha_de_conexao_nao_mantem_arquivo_bloqueado(tmp_path, monkeypatch):
    database = tmp_path / "invalido.duckdb"
    database.write_text("não é um banco DuckDB", encoding="utf-8")
    monkeypatch.setattr(db, "_ARQUIVO_BANCO", database)

    with pytest.raises(duckdb.Error):
        db.conectar(must_exist=True)

    moved_database = tmp_path / "invalido_renomeado.duckdb"
    database.rename(moved_database)
    assert moved_database.is_file()
