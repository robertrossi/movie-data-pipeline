from datetime import date
from pathlib import Path

import duckdb
import pytest

from pipeline import db, transformacao


def _registro_filme(**valores: str | None) -> dict[str, str | None]:
    registro = dict.fromkeys(transformacao.FILM_RAW_COLUMNS)
    registro.update(
        {
            "adult": "False",
            "budget": "0",
            "genres": "[{'name': 'Drama', 'id': 18}]",
            "id": "1",
            "imdb_id": "tt0000001",
            "original_language": "en",
            "original_title": "Filme",
            "popularity": "1.5",
            "release_date": "2001-02-03",
            "revenue": None,
            "runtime": "90",
            "status": "Released",
            "title": "Filme",
            "vote_average": "7.5",
            "vote_count": "50",
        }
    )
    registro.update(valores)
    return registro


def _preparar_raw(database: Path, rating: str = "4.5") -> dict[int, dict]:
    con = duckdb.connect(str(database))
    try:
        con.execute("CREATE SCHEMA raw")
        colunas = ", ".join(
            f'"{nome}" VARCHAR' for nome in transformacao.FILM_RAW_COLUMNS
        )
        con.execute(f"CREATE TABLE raw.filmes ({colunas})")
        registros = [
            _registro_filme(id=None, title=None),
            _registro_filme(),
            _registro_filme(),
            _registro_filme(id="77", title="Divergente A"),
            _registro_filme(id="77", title="Divergente B"),
        ]
        nomes = ", ".join(f'"{nome}"' for nome in transformacao.FILM_RAW_COLUMNS)
        placeholders = ", ".join("?" for _ in transformacao.FILM_RAW_COLUMNS)
        for registro in registros:
            con.execute(
                f"INSERT INTO raw.filmes ({nomes}) VALUES ({placeholders})",
                [registro[coluna] for coluna in transformacao.FILM_RAW_COLUMNS],
            )

        con.execute(
            "CREATE TABLE raw.avaliacoes "
            "(userId VARCHAR, movieId VARCHAR, rating VARCHAR, timestamp VARCHAR)"
        )
        con.execute("INSERT INTO raw.avaliacoes VALUES ('10', '1', ?, '100')", [rating])
        con.execute(
            "CREATE TABLE raw.links (movieId VARCHAR, tmdbId VARCHAR, imdbId VARCHAR)"
        )
        con.execute("INSERT INTO raw.links VALUES ('1', '1', 'tt0000001')")
        return {0: registros[0]}
    finally:
        con.close()


def _configurar_rejeicoes_fixture(
    monkeypatch: pytest.MonkeyPatch, rejeitados: dict[int, dict]
) -> None:
    monkeypatch.setattr(transformacao, "MALFORMED_FILM_ROWIDS", tuple(rejeitados))
    monkeypatch.setattr(
        transformacao,
        "EXPECTED_REJECTED_FILM_RECORDS",
        rejeitados,
    )
    monkeypatch.setattr(
        transformacao,
        "MALFORMED_FILM_REJECTION_REASONS",
        {rowid: "Registro sintético de teste" for rowid in rejeitados},
    )
    monkeypatch.setattr(transformacao, "DIVERGENT_FILM_IDS", ("77",))
    monkeypatch.setattr(
        transformacao,
        "DIVERGENT_FILM_REJECTION_REASONS",
        {"77": "Conflito sintético de teste"},
    )


def test_transformacao_converte_tipos_preserva_nulos_e_isola_conflitos(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    database = tmp_path / "transformacao.duckdb"
    rejeitados = _preparar_raw(database)
    _configurar_rejeicoes_fixture(monkeypatch, rejeitados)
    monkeypatch.setattr(db, "_ARQUIVO_BANCO", database)

    assert transformacao.main() == 0

    con = duckdb.connect(str(database), read_only=True)
    try:
        filme = con.execute(
            "SELECT id, budget, revenue, release_date, vote_average, vote_count "
            "FROM refined.filmes"
        ).fetchone()
        assert filme == (1, 0, None, date(2001, 2, 3), 7.5, 50)
        assert con.execute("SELECT COUNT(*) FROM refined.filmes").fetchone() == (1,)
        assert con.execute("SELECT COUNT(*) FROM rejected.filmes").fetchone() == (3,)
        assert con.execute("SELECT rating FROM refined.avaliacoes").fetchone() == (4.5,)
        assert con.execute("SELECT movieId, tmdbId FROM refined.links").fetchone() == (
            1,
            1,
        )
        assert con.execute(
            "SELECT COUNT(*) FILTER (WHERE revenue IS NULL) FROM refined.filmes"
        ).fetchone() == (1,)
    finally:
        con.close()

    assert "Duplicatas integralmente idênticas removidas" in capsys.readouterr().out


def test_transformacao_valor_invalido_reverte_sem_publicacao(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    database = tmp_path / "valor_invalido.duckdb"
    rejeitados = _preparar_raw(database, rating="rating-invalido")
    _configurar_rejeicoes_fixture(monkeypatch, rejeitados)
    monkeypatch.setattr(db, "_ARQUIVO_BANCO", database)
    con = duckdb.connect(str(database))
    con.execute("CREATE SCHEMA refined")
    con.execute("CREATE TABLE refined.marcador AS SELECT 42 AS valor")
    con.close()

    assert transformacao.main() == 1

    con = duckdb.connect(str(database), read_only=True)
    try:
        assert con.execute("SELECT valor FROM refined.marcador").fetchone() == (42,)
        assert con.execute(
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_schema='refined' AND table_name='filmes'"
        ).fetchone() == (0,)
    finally:
        con.close()
    assert "rating-invalido" in capsys.readouterr().out


def test_transformacao_relata_tabelas_raw_ausentes_sem_modificar_banco(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    database = tmp_path / "raw_ausente.duckdb"
    monkeypatch.setattr(db, "_ARQUIVO_BANCO", database)

    assert transformacao.main() == 1

    assert "raw.filmes" in capsys.readouterr().out
    con = duckdb.connect(str(database), read_only=True)
    try:
        assert con.execute(
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_schema IN ('refined', 'rejected')"
        ).fetchone() == (0,)
    finally:
        con.close()


@pytest.mark.parametrize(
    ("insercao", "coluna_da_chave"),
    [
        ("INSERT INTO raw.avaliacoes VALUES ('10', '1', '3.5', '101')", "userId"),
        ("INSERT INTO raw.links VALUES ('1', '2', 'tt0000002')", "movieId"),
    ],
)
def test_transformacao_rejeita_chaves_duplicadas_em_avaliacoes_e_links(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys,
    insercao: str,
    coluna_da_chave: str,
) -> None:
    database = tmp_path / f"duplicidade_{coluna_da_chave}.duckdb"
    rejeitados = _preparar_raw(database)
    _configurar_rejeicoes_fixture(monkeypatch, rejeitados)
    monkeypatch.setattr(db, "_ARQUIVO_BANCO", database)
    con = duckdb.connect(str(database))
    con.execute(insercao)
    con.close()

    assert transformacao.main() == 1

    saida = capsys.readouterr().out
    assert "chave duplicada" in saida
    assert coluna_da_chave in saida
