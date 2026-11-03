from pathlib import Path

import duckdb

from pipeline import db, marts


def _prepare_database(path: Path, *, refined_tables=("avaliacoes",)) -> None:
    con = duckdb.connect(str(path))
    try:
        con.execute("CREATE SCHEMA refined")
        for table in refined_tables:
            if table == "avaliacoes":
                con.execute(
                    "CREATE TABLE refined.avaliacoes AS "
                    "SELECT 1::BIGINT AS timestamp, 4.0::DOUBLE AS rating"
                )
            else:
                con.execute(
                    f"CREATE TABLE refined.{table} AS SELECT 1 AS id"
                )
        con.execute("CREATE SCHEMA marts")
        con.execute("CREATE TABLE marts.legada AS SELECT 99 AS valor")
    finally:
        con.close()


def _connect_to(path: Path):
    return lambda *, must_exist=False: duckdb.connect(str(path))


def _scalar(path: Path, query: str):
    con = duckdb.connect(str(path), read_only=True)
    try:
        return con.execute(query).fetchone()[0]
    finally:
        con.close()


def test_publicacao_seletiva_05_06_preserva_marts_nao_selecionadas(
    tmp_path, monkeypatch
):
    database = tmp_path / "temporario.duckdb"
    _prepare_database(database)
    monkeypatch.setattr(db, "conectar", _connect_to(database))

    assert marts.main(["--only", "05", "06"]) == 0

    assert _scalar(database, "SELECT valor FROM marts.legada") == 99
    assert _scalar(
        database,
        "SELECT COUNT(*) FROM marts.avaliacoes_movielens_ao_longo_do_tempo",
    ) == 1
    assert _scalar(
        database,
        "SELECT COUNT(*) FROM marts.nota_media_movielens_ao_longo_do_tempo",
    ) == 1


def test_indicador_inexistente_e_rejeitado_antes_de_conectar(monkeypatch, capsys):
    def conectar_inesperado(**kwargs):
        raise AssertionError("não deveria abrir o banco")

    monkeypatch.setattr(db, "conectar", conectar_inesperado)

    assert marts.main(["--only", "99"]) == 1
    assert "Indicadores não encontrados: 99" in capsys.readouterr().out


def test_prefixo_de_indicador_duplicado_e_rejeitado(tmp_path, monkeypatch, capsys):
    sql_dir = tmp_path / "sql"
    sql_dir.mkdir()
    (sql_dir / "05_um.sql").write_text("SELECT 1", encoding="utf-8")
    (sql_dir / "05_dois.sql").write_text("SELECT 2", encoding="utf-8")
    monkeypatch.setattr(marts, "_PASTA_MARTS", sql_dir)

    assert marts.main(["--only", "05"]) == 1
    assert "Indicador 05 duplicado" in capsys.readouterr().out


def test_resultado_vazio_reverte_substituicao(tmp_path, monkeypatch):
    database = tmp_path / "temporario.duckdb"
    _prepare_database(database)
    sql_dir = tmp_path / "sql"
    sql_dir.mkdir()
    (sql_dir / "05_vazia.sql").write_text(
        "SELECT * FROM refined.avaliacoes WHERE FALSE", encoding="utf-8"
    )
    con = duckdb.connect(str(database))
    con.execute("CREATE TABLE marts.vazia AS SELECT 5 AS valor")
    con.close()
    monkeypatch.setattr(db, "conectar", _connect_to(database))
    monkeypatch.setattr(marts, "_PASTA_MARTS", sql_dir)

    assert marts.main(["--only", "05"]) == 1
    assert _scalar(database, "SELECT valor FROM marts.vazia") == 5


def test_falha_seletiva_reverte_todas_as_tabelas_selecionadas(
    tmp_path, monkeypatch
):
    database = tmp_path / "temporario.duckdb"
    _prepare_database(database)
    sql_dir = tmp_path / "sql"
    sql_dir.mkdir()
    (sql_dir / "05_primeira.sql").write_text(
        "SELECT 10 AS valor", encoding="utf-8"
    )
    (sql_dir / "06_falha.sql").write_text(
        "SELECT FROM", encoding="utf-8"
    )
    con = duckdb.connect(str(database))
    con.execute("CREATE TABLE marts.primeira AS SELECT 5 AS valor")
    con.close()
    monkeypatch.setattr(db, "conectar", _connect_to(database))
    monkeypatch.setattr(marts, "_PASTA_MARTS", sql_dir)

    assert marts.main(["--only", "05", "06"]) == 1

    assert _scalar(database, "SELECT valor FROM marts.primeira") == 5
    assert _scalar(database, "SELECT valor FROM marts.legada") == 99
    assert not _scalar(
        database,
        "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
        "WHERE table_schema='marts' AND table_name='falha')",
    )


def test_publicacao_completa_mantem_recriacao_de_todo_schema(
    tmp_path, monkeypatch
):
    database = tmp_path / "temporario.duckdb"
    _prepare_database(database, refined_tables=("filmes", "avaliacoes", "links"))
    sql_dir = tmp_path / "sql"
    sql_dir.mkdir()
    (sql_dir / "01_filmes.sql").write_text(
        "SELECT id FROM refined.filmes", encoding="utf-8"
    )
    (sql_dir / "02_links.sql").write_text(
        "SELECT id FROM refined.links", encoding="utf-8"
    )
    monkeypatch.setattr(db, "conectar", _connect_to(database))
    monkeypatch.setattr(marts, "_PASTA_MARTS", sql_dir)

    assert marts.main([]) == 0

    assert _scalar(
        database,
        "SELECT COUNT(*) FROM information_schema.tables "
        "WHERE table_schema='marts' AND table_name='legada'",
    ) == 0
    assert _scalar(
        database,
        "SELECT COUNT(*) FROM information_schema.tables "
        "WHERE table_schema='marts'",
    ) == 2


def test_seletiva_informa_origens_refined_ausentes(tmp_path, monkeypatch, capsys):
    database = tmp_path / "temporario.duckdb"
    _prepare_database(database, refined_tables=())
    monkeypatch.setattr(db, "conectar", _connect_to(database))

    assert marts.main(["--only", "05"]) == 1
    assert "refined.avaliacoes" in capsys.readouterr().out
    assert _scalar(database, "SELECT valor FROM marts.legada") == 99


def test_conexao_must_exist_nao_cria_banco(tmp_path, monkeypatch):
    database = tmp_path / "ausente.duckdb"
    monkeypatch.setattr(db, "_ARQUIVO_BANCO", database)

    try:
        db.conectar(must_exist=True)
    except FileNotFoundError:
        pass
    else:
        raise AssertionError("era esperado FileNotFoundError")

    assert not database.exists()
