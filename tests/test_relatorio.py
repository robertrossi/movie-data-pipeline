import re
from pathlib import Path

import duckdb
import pandas as pd
import pytest

import relatorio
from pipeline import db


@pytest.fixture
def banco_relatorio(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    database = tmp_path / "relatorio.duckdb"
    con = duckdb.connect(str(database))
    try:
        con.execute("CREATE SCHEMA marts")
        con.execute("CREATE SCHEMA refined")
        con.execute(
            "CREATE TABLE marts.filmes_lancados_por_ano AS "
            "SELECT * FROM (VALUES (2001, 2), (2002, 3)) "
            "v(release_year, total_movies)"
        )
        con.execute(
            "CREATE TABLE marts.nota_media_tmdb_por_genero AS "
            "SELECT * FROM (VALUES ('Drama', 2, 7.5)) "
            "v(genero, total_filmes, nota_media_tmdb)"
        )
        con.execute(
            "CREATE TABLE marts.quantidade_votos_tmdb_por_genero AS "
            "SELECT * FROM (VALUES ('Drama', 2, 100)) "
            "v(genero, total_filmes, total_votos_tmdb)"
        )
        con.execute(
            "CREATE TABLE marts.distribuicao_notas_movielens AS "
            "SELECT * FROM (VALUES (4.0, 3, 60.0)) "
            "v(rating, total_avaliacoes, percentual)"
        )
        con.execute(
            "CREATE TABLE marts.avaliacoes_movielens_ao_longo_do_tempo AS "
            "SELECT * FROM (VALUES (2020, 3), (2021, 4)) "
            "v(ano_avaliacao, total_avaliacoes)"
        )
        con.execute(
            "CREATE TABLE marts.nota_media_movielens_ao_longo_do_tempo AS "
            "SELECT * FROM (VALUES (2020, 3, 4.0), (2021, 4, 4.5)) "
            "v(ano_avaliacao, total_avaliacoes, nota_media)"
        )
        con.execute(
            "CREATE TABLE marts.filmes_mais_avaliados_movielens AS "
            "SELECT * FROM (VALUES (1, 101, 'Filme', 10, 4.0)) "
            "v(movieId, tmdbId, titulo, total_avaliacoes, nota_media_movielens)"
        )
        con.execute(
            "CREATE TABLE marts.usuarios_mais_ativos AS "
            "SELECT * FROM (VALUES (10, 3, 4.0)) "
            "v(userId, total_avaliacoes, nota_media_usuario)"
        )
        con.execute(
            "CREATE TABLE marts.distribuicao_avaliacoes_por_usuario AS "
            "SELECT * FROM (VALUES ('1', 1, 100.0)) "
            "v(faixa_avaliacoes, total_usuarios, percentual_usuarios)"
        )
        con.execute(
            "CREATE TABLE marts.nota_media_movielens_por_genero AS "
            "SELECT * FROM (VALUES ('Drama', 1, 3, 4.0)) "
            "v(genero, total_filmes, total_avaliacoes, nota_media_movielens)"
        )
        con.execute(
            "CREATE TABLE marts.filmes_mais_avaliados_movielens_por_ano AS "
            "SELECT * FROM (VALUES "
            "(2020, 1, 101, 'Filme Um', 3, 4.0, 1), "
            "(2021, 1, 101, 'Filme Um', 4, 4.5, 1)) "
            "v(ano_avaliacao, movieId, tmdbId, titulo, total_avaliacoes, "
            "nota_media_movielens, ranking)"
        )
        con.execute(
            "CREATE TABLE refined.filmes AS "
            "SELECT 101::BIGINT AS id, '/poster.jpg'::VARCHAR AS poster_path"
        )
    finally:
        con.close()
    monkeypatch.setattr(db, "_ARQUIVO_BANCO", database)
    return database


def test_relatorio_renderiza_quatro_secoes_14_graficos_e_um_plotly_cdn(
    banco_relatorio: Path,
) -> None:
    html = relatorio._renderizar_relatorio()

    assert all(
        f'<section class="report-section"><h2>{secao}</h2>' in html
        for secao in ("Visão geral", "Gêneros", "Filmes e avaliações", "Usuários")
    )
    assert relatorio._GRAFICOS == [f"g{numero:02d}" for numero in range(1, 15)]
    assert len(set(relatorio._GRAFICOS)) == 14
    assert html.count("https://cdn.plot.ly/") == 1
    assert "Dados de " in html
    assert "Cinema Analytics" in html


def test_relatorio_gera_ids_estaveis_e_conteudo_repetivel_exceto_data(
    banco_relatorio: Path,
) -> None:
    primeiro = relatorio._renderizar_relatorio()
    ids_primeiro = relatorio._GRAFICOS.copy()
    segundo = relatorio._renderizar_relatorio()
    ids_segundo = relatorio._GRAFICOS.copy()

    def normalizar_data(conteudo: str) -> str:
        return re.sub(
            r"Dados de \d{2}/\d{2}/\d{4} \d{2}:\d{2}",
            "Dados de <data> <hora>",
            conteudo,
        )

    assert ids_primeiro == ids_segundo == [f"g{i:02d}" for i in range(1, 15)]
    assert normalizar_data(primeiro) == normalizar_data(segundo)


def test_main_salva_html_com_rodape_em_caminho_de_saida_temporario(
    banco_relatorio: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    arquivo_saida = tmp_path / "relatorio_gerado.html"
    monkeypatch.setattr(relatorio, "_ARQUIVO_SAIDA", arquivo_saida)

    relatorio.main()

    conteudo = arquivo_saida.read_text(encoding="utf-8")
    assert conteudo.startswith("<!doctype html>")
    assert "Dados de " in conteudo
    assert len(re.findall(r'id="g\d{2}"', conteudo)) == 14


def test_intervalo_padrao_respeita_periodo_e_dados_disponiveis() -> None:
    dados = pd.DataFrame({"ano": [1995, 2020]})

    assert relatorio._intervalo_padrao(dados, "ano", (2000, 2016)) == (2000, 2016)
    assert relatorio._intervalo_padrao(dados, "ano", (2025, 2030)) == (1995, 2020)
    assert relatorio._intervalo_padrao(pd.DataFrame({"ano": []}), "ano") is None
    assert relatorio._intervalo_padrao(pd.DataFrame({"ano": [2000]}), "ano") == (
        2000,
        2000,
    )


def test_cartao_escapa_titulo_html() -> None:
    cartao = relatorio._cartao_grafico("<script>alert(1)</script>", "<div></div>")

    assert "&lt;script&gt;" in cartao
    assert "<script>alert(1)</script>" not in cartao
