from datetime import datetime, timezone
from pathlib import Path

import duckdb

from pipeline import db, marts


def _epoch(iso_timestamp: str) -> int:
    return int(
        datetime.fromisoformat(iso_timestamp).replace(tzinfo=timezone.utc).timestamp()
    )


def _criar_fontes(database: Path) -> None:
    con = duckdb.connect(str(database))
    try:
        con.execute("CREATE SCHEMA refined")
        con.execute(
            "CREATE TABLE refined.avaliacoes "
            "(movieId BIGINT, rating DOUBLE, timestamp BIGINT)"
        )
        con.executemany(
            "INSERT INTO refined.avaliacoes VALUES (?, ?, ?)",
            [
                (1, 3.0, _epoch("2019-12-31T23:30:00")),
                (1, 4.0, _epoch("2020-01-01T00:30:00")),
                (1, 5.0, _epoch("2020-01-02T00:00:00")),
                (1, 5.0, _epoch("2020-01-03T00:00:00")),
                (2, 4.0, _epoch("2020-01-01T01:00:00")),
                (2, 4.5, _epoch("2020-01-02T01:00:00")),
                (2, 5.0, _epoch("2020-01-03T01:00:00")),
                (3, 2.5, _epoch("2020-01-04T00:00:00")),
                (4, 2.0, _epoch("2020-01-05T00:00:00")),
                (4, 3.0, _epoch("2020-01-06T00:00:00")),
                (1, 4.0, _epoch("2021-01-01T00:00:00")),
                (2, 3.0, _epoch("2021-01-01T01:00:00")),
            ],
        )
        con.execute("CREATE TABLE refined.links (movieId BIGINT, tmdbId BIGINT)")
        con.execute("INSERT INTO refined.links VALUES (1, 101), (2, 102), (4, 101)")
        con.execute("CREATE TABLE refined.filmes (id BIGINT, title VARCHAR)")
        con.execute("INSERT INTO refined.filmes VALUES (101, 'Filme Um')")
    finally:
        con.close()


def _conectar_temporario(database: Path):
    def conectar(*, must_exist=False):
        con = duckdb.connect(str(database))
        con.execute("SET TimeZone = 'America/Sao_Paulo'")
        return con

    return conectar


def test_publicacao_indicador_11_agrega_utc_rankeia_e_preserva_granularidade(
    tmp_path, monkeypatch
):
    database = tmp_path / "indicador_11.duckdb"
    _criar_fontes(database)
    monkeypatch.setattr(db, "_ARQUIVO_BANCO", database)
    monkeypatch.setattr(db, "conectar", _conectar_temporario(database))
    con = duckdb.connect(str(database))
    try:
        con.execute("CREATE SCHEMA marts")
        con.execute("CREATE TABLE marts.legada AS SELECT 42 AS valor")
    finally:
        con.close()

    assert marts.main(["--only", "11"]) == 0

    con = duckdb.connect(str(database), read_only=True)
    try:
        rows = con.execute(
            "SELECT ano_avaliacao, movieId, tmdbId, titulo, total_avaliacoes, "
            "nota_media_movielens, ranking "
            "FROM marts.filmes_mais_avaliados_movielens_por_ano "
            "ORDER BY ano_avaliacao, ranking"
        ).fetchall()
        assert rows == [
            (2019, 1, 101, "Filme Um", 1, 3.0, 1),
            (2020, 1, 101, "Filme Um", 3, 14 / 3, 1),
            (2020, 2, 102, None, 3, 4.5, 2),
            (2020, 4, 101, "Filme Um", 2, 2.5, 3),
            (2020, 3, None, None, 1, 2.5, 4),
            (2021, 1, 101, "Filme Um", 1, 4.0, 1),
            (2021, 2, 102, None, 1, 3.0, 2),
        ]
        assert con.execute("SELECT valor FROM marts.legada").fetchone() == (42,)
        assert con.execute(
            "SELECT COUNT(*) = COUNT(DISTINCT (ano_avaliacao, movieId)) "
            "FROM marts.filmes_mais_avaliados_movielens_por_ano"
        ).fetchone()[0]
    finally:
        con.close()


def test_publicacao_indicador_11_faz_rollback_se_resultado_ficar_vazio(
    tmp_path, monkeypatch
):
    database = tmp_path / "rollback_indicador_11.duckdb"
    _criar_fontes(database)
    sql_dir = tmp_path / "sql"
    sql_dir.mkdir()
    (sql_dir / "11_vazia.sql").write_text(
        "SELECT 2020 AS ano_avaliacao, 1 AS movieId, NULL::BIGINT AS tmdbId, "
        "NULL::VARCHAR AS titulo, 0 AS total_avaliacoes, NULL::DOUBLE AS "
        "nota_media_movielens, 1 AS ranking FROM refined.avaliacoes WHERE FALSE",
        encoding="utf-8",
    )
    con = duckdb.connect(str(database))
    try:
        con.execute("CREATE SCHEMA marts")
        con.execute(
            "CREATE TABLE marts.filmes_mais_avaliados_movielens_por_ano "
            "AS SELECT 1999 AS ano_avaliacao, 77 AS movieId"
        )
    finally:
        con.close()
    monkeypatch.setattr(db, "conectar", _conectar_temporario(database))
    monkeypatch.setattr(marts, "_PASTA_MARTS", sql_dir)

    assert marts.main(["--only", "11"]) == 1

    con = duckdb.connect(str(database), read_only=True)
    try:
        assert con.execute(
            "SELECT ano_avaliacao, movieId "
            "FROM marts.filmes_mais_avaliados_movielens_por_ano"
        ).fetchall() == [(1999, 77)]
    finally:
        con.close()
