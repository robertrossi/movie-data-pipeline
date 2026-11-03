from io import BytesIO
from pathlib import Path
from urllib.error import HTTPError, URLError

import duckdb
import pandas as pd
import pytest
from PIL import Image

import painel
from pipeline import db


@pytest.fixture
def banco_marts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Cria as onze MARTs mínimas em um arquivo isolado para cada teste."""
    database = tmp_path / "painel.duckdb"
    con = duckdb.connect(str(database))
    try:
        con.execute("CREATE SCHEMA marts")
        con.execute(
            "CREATE TABLE marts.filmes_lancados_por_ano AS "
            "SELECT * FROM (VALUES (1999, 4), (2000, 10), (2001, NULL)) "
            "t(release_year, total_movies)"
        )
        con.execute(
            "CREATE TABLE marts.nota_media_tmdb_por_genero AS "
            "SELECT * FROM (VALUES ('Drama', 2, 7.5), ('Comedy', 3, 6.0)) "
            "t(genero, total_filmes, nota_media_tmdb)"
        )
        con.execute(
            "CREATE TABLE marts.quantidade_votos_tmdb_por_genero AS "
            "SELECT * FROM (VALUES ('Drama', 2, 100), ('Comedy', 3, 80)) "
            "t(genero, total_filmes, total_votos_tmdb)"
        )
        con.execute(
            "CREATE TABLE marts.distribuicao_notas_movielens AS "
            "SELECT * FROM (VALUES (0.5, 2, 25.0), (1.0, NULL, NULL)) "
            "t(rating, total_avaliacoes, percentual)"
        )
        con.execute(
            "CREATE TABLE marts.avaliacoes_movielens_ao_longo_do_tempo AS "
            "SELECT * FROM (VALUES (1995, 2), (1996, 5)) "
            "t(ano_avaliacao, total_avaliacoes)"
        )
        con.execute(
            "CREATE TABLE marts.nota_media_movielens_ao_longo_do_tempo AS "
            "SELECT * FROM (VALUES (1995, 2, 3.5), (1996, 5, 4.0)) "
            "t(ano_avaliacao, total_avaliacoes, nota_media)"
        )
        con.execute(
            "CREATE TABLE marts.filmes_mais_avaliados_movielens AS "
            "SELECT 100 + i AS movieId, 900 + i AS tmdbId, "
            "'Filme ' || i AS titulo, 2000 - i AS total_avaliacoes, "
            "4.5 - i / 100.0 AS nota_media_movielens "
            "FROM range(20) t(i) ORDER BY total_avaliacoes DESC"
        )
        con.execute(
            "CREATE TABLE marts.usuarios_mais_ativos AS "
            "SELECT * FROM (VALUES (11, 200, 4.5), (12, 100, 3.5)) "
            "t(userId, total_avaliacoes, nota_media_usuario)"
        )
        con.execute(
            "CREATE TABLE marts.distribuicao_avaliacoes_por_usuario AS "
            "SELECT * FROM (VALUES ('1', 5, 1.0), ('2-10', 10, 2.0), "
            "('11-30', 20, 3.0), ('31-100', 30, 4.0), ('101-500', 40, 5.0), "
            "('501-1000', 6, 6.0), ('>1000', 2, 7.0)) "
            "t(faixa_avaliacoes, total_usuarios, percentual_usuarios)"
        )
        con.execute(
            "CREATE TABLE marts.nota_media_movielens_por_genero AS "
            "SELECT * FROM (VALUES ('Drama', 2, 100, 4.0), "
            "('Comedy', 3, 80, 3.5)) "
            "t(genero, total_filmes, total_avaliacoes, nota_media_movielens)"
        )
        con.execute(
            "CREATE TABLE marts.filmes_mais_avaliados_movielens_por_ano AS "
            "SELECT 2020 AS ano_avaliacao, i::BIGINT AS movieId, "
            "CASE WHEN i IN (1, 2) THEN 900 WHEN i = 3 THEN NULL "
            "ELSE 1000 + i END AS tmdbId, "
            "CASE WHEN i = 3 THEN NULL ELSE 'Filme ' || i END AS titulo, "
            "1000 - i AS total_avaliacoes, 4.0 + i / 100.0 "
            "AS nota_media_movielens, i AS ranking "
            "FROM range(1, 22) t(i) "
            "UNION ALL "
            "SELECT 2021 AS ano_avaliacao, (i + 1)::BIGINT AS movieId, "
            "CASE WHEN i + 1 IN (1, 2) THEN 900 WHEN i + 1 = 3 THEN NULL "
            "ELSE 1000 + i + 1 END AS tmdbId, "
            "CASE WHEN i + 1 = 3 THEN NULL ELSE 'Filme ' || (i + 1) END AS titulo, "
            "2000 - i AS total_avaliacoes, 4.0 + (i + 1) / 100.0 "
            "AS nota_media_movielens, i AS ranking "
            "FROM range(1, 22) t(i)"
        )
        con.execute("CREATE SCHEMA refined")
        con.execute(
            "CREATE TABLE refined.filmes AS "
            "SELECT 900::BIGINT AS id, '/poster.jpg'::VARCHAR AS poster_path"
        )
    finally:
        con.close()
    monkeypatch.setattr(db, "_ARQUIVO_BANCO", database)
    return database


def _consultas_completas():
    return [
        painel.obter_filmes_por_ano(),
        painel.obter_nota_tmdb_por_genero(),
        painel.obter_votos_tmdb_por_genero(),
        painel.obter_distribuicao_notas(),
        painel.obter_avaliacoes_por_ano(),
        painel.obter_nota_media_por_ano(),
        painel.obter_filmes_mais_avaliados(),
        painel.obter_usuarios_mais_ativos(),
        painel.obter_distribuicao_usuarios(),
        painel.obter_nota_movielens_por_genero(),
    ]


def test_consultas_leem_as_dez_marts_em_dataframes(banco_marts):
    resultados = _consultas_completas()
    colunas = [
        ["release_year", "total_movies"],
        ["genero", "total_filmes", "nota_media_tmdb"],
        ["genero", "total_filmes", "total_votos_tmdb"],
        ["rating", "total_avaliacoes", "percentual"],
        ["ano_avaliacao", "total_avaliacoes"],
        ["ano_avaliacao", "total_avaliacoes", "nota_media"],
        ["movieId", "tmdbId", "titulo", "total_avaliacoes", "nota_media_movielens"],
        ["userId", "total_avaliacoes", "nota_media_usuario"],
        ["faixa_avaliacoes", "total_usuarios", "percentual_usuarios"],
        ["genero", "total_filmes", "total_avaliacoes", "nota_media_movielens"],
    ]

    assert all(isinstance(resultado, pd.DataFrame) for resultado in resultados)
    assert [resultado.columns.tolist() for resultado in resultados] == colunas
    assert len(resultados) == 10


def test_filtros_temporais_e_de_genero_sao_aplicados(banco_marts):
    assert painel.obter_filmes_por_ano(2000, 2000)["release_year"].tolist() == [2000]
    assert painel.obter_avaliacoes_por_ano(1996, 1996)["ano_avaliacao"].tolist() == [
        1996
    ]
    assert painel.obter_nota_media_por_ano(1996, 1996)["ano_avaliacao"].tolist() == [
        1996
    ]
    assert painel.obter_nota_tmdb_por_genero("Drama")["genero"].tolist() == ["Drama"]
    assert painel.obter_votos_tmdb_por_genero("Drama")["genero"].tolist() == ["Drama"]
    assert painel.obter_nota_movielens_por_genero("Drama")["genero"].tolist() == [
        "Drama"
    ]
    assert painel.obter_nota_tmdb_por_genero("Drama' OR TRUE --").empty


def test_intervalos_invalidos_sao_rejeitados(banco_marts):
    with pytest.raises(ValueError, match="ano_inicio"):
        painel.obter_filmes_por_ano(2001, 2000)
    with pytest.raises(TypeError, match="ano_inicio"):
        painel.obter_avaliacoes_por_ano("1995", 2000)


def test_top_filmes_aceita_10_ou_20_e_preserva_ordem(banco_marts):
    top_10 = painel.obter_filmes_mais_avaliados(10)
    top_20 = painel.obter_filmes_mais_avaliados(20)

    assert len(top_10) == 10
    assert len(top_20) == 20
    assert top_10["movieId"].tolist() == top_20["movieId"].tolist()[:10]
    assert top_20["total_avaliacoes"].tolist() == sorted(
        top_20["total_avaliacoes"], reverse=True
    )
    with pytest.raises(ValueError, match="10 ou 20"):
        painel.obter_filmes_mais_avaliados(15)


def test_comparacao_ranking_anual_filtra_top_e_preserva_granularidade(banco_marts):
    top_10 = painel.obter_comparacao_ranking_anual(2020, 2021, 10)
    top_20 = painel.obter_comparacao_ranking_anual(2020, 2021, 20)

    assert top_10.columns.tolist() == [
        "ano_avaliacao",
        "movieId",
        "tmdbId",
        "titulo",
        "total_avaliacoes",
        "nota_media_movielens",
        "ranking",
    ]
    assert len(top_10) == 20
    assert len(top_20) == 40
    assert top_10.groupby("ano_avaliacao").size().to_dict() == {2020: 10, 2021: 10}
    assert top_20.groupby("ano_avaliacao").size().to_dict() == {2020: 20, 2021: 20}
    for ano, filmes in top_10.groupby("ano_avaliacao", sort=True):
        assert filmes["ranking"].tolist() == list(range(1, 11))
        assert filmes["total_avaliacoes"].tolist() == sorted(
            filmes["total_avaliacoes"], reverse=True
        )
        assert int(ano) in (2020, 2021)

    ids_ligados_ao_mesmo_tmdb = top_10.loc[
        (top_10["ano_avaliacao"] == 2020) & (top_10["tmdbId"] == 900)
    ].set_index("movieId")
    assert ids_ligados_ao_mesmo_tmdb.loc[1, "total_avaliacoes"] == 999
    assert ids_ligados_ao_mesmo_tmdb.loc[2, "total_avaliacoes"] == 998
    assert ids_ligados_ao_mesmo_tmdb.loc[1, "nota_media_movielens"] == 4.01
    assert ids_ligados_ao_mesmo_tmdb.loc[2, "nota_media_movielens"] == 4.02
    assert ids_ligados_ao_mesmo_tmdb["ranking"].tolist() == [1, 2]

    sem_metadados = top_10.loc[
        (top_10["ano_avaliacao"] == 2020) & (top_10["movieId"] == 3)
    ].iloc[0]
    assert pd.isna(sem_metadados["tmdbId"])
    assert pd.isna(sem_metadados["titulo"])


def test_comparacao_ranking_anual_valida_anos_e_top(banco_marts):
    with pytest.raises(TypeError, match="ano_a"):
        painel.obter_comparacao_ranking_anual("2020", 2021)
    with pytest.raises(TypeError, match="ano_a"):
        painel.obter_comparacao_ranking_anual(True, 2021)
    with pytest.raises(ValueError, match="diferentes"):
        painel.obter_comparacao_ranking_anual(2020, 2020)
    with pytest.raises(ValueError, match="1 e 9999"):
        painel.obter_comparacao_ranking_anual(0, 2020)
    with pytest.raises(ValueError, match="10 ou 20"):
        painel.obter_comparacao_ranking_anual(2020, 2021, 15)
    with pytest.raises(TypeError, match="top_n"):
        painel.obter_comparacao_ranking_anual(2020, 2021, 10.0)


def test_ranking_anual_consulta_top10_top20_e_preserva_ordem(banco_marts):
    anos = painel.obter_anos_ranking_anual()
    top_10 = painel.obter_filmes_mais_avaliados_no_ano(2020, 10)
    top_20 = painel.obter_filmes_mais_avaliados_no_ano(2021, 20)

    assert anos.columns.tolist() == ["ano_avaliacao"]
    assert anos["ano_avaliacao"].tolist() == [2020, 2021]
    assert top_10.columns.tolist() == [
        "ano_avaliacao",
        "movieId",
        "tmdbId",
        "titulo",
        "total_avaliacoes",
        "nota_media_movielens",
        "ranking",
    ]
    assert len(top_10) == 10
    assert len(top_20) == 20
    assert top_10["ano_avaliacao"].unique().tolist() == [2020]
    assert top_10["ranking"].tolist() == list(range(1, 11))
    assert top_10["movieId"].tolist() == list(range(1, 11))
    assert top_10["total_avaliacoes"].tolist() == sorted(
        top_10["total_avaliacoes"], reverse=True
    )
    assert top_20["ranking"].tolist() == list(range(1, 21))

    sem_metadados = top_10.loc[top_10["movieId"] == 3].iloc[0]
    assert pd.isna(sem_metadados["titulo"])
    assert pd.isna(sem_metadados["tmdbId"])

    vazio = painel.obter_filmes_mais_avaliados_no_ano(1900, 10)
    assert vazio.empty
    assert vazio.columns.tolist() == top_10.columns.tolist()


def test_ranking_anual_rejeita_anos_e_limites_invalidos(banco_marts):
    with pytest.raises(TypeError, match="ano"):
        painel.obter_filmes_mais_avaliados_no_ano("2020", 10)
    with pytest.raises(TypeError, match="ano"):
        painel.obter_filmes_mais_avaliados_no_ano(True, 10)
    with pytest.raises(ValueError, match="1 e 9999"):
        painel.obter_filmes_mais_avaliados_no_ano(0, 10)
    with pytest.raises(ValueError, match="10 ou 20"):
        painel.obter_filmes_mais_avaliados_no_ano(2020, 15)
    with pytest.raises(TypeError, match="top_n"):
        painel.obter_filmes_mais_avaliados_no_ano(2020, 10.0)


def test_ranking_anual_usa_conexao_read_only_e_fecha(banco_marts, monkeypatch):
    conectar_real = db.conectar
    chamadas = []
    conexoes = []

    def conectar_rastreada(**kwargs):
        chamadas.append(kwargs)
        con = conectar_real(**kwargs)
        conexoes.append(con)
        return con

    monkeypatch.setattr(db, "conectar", conectar_rastreada)

    painel.obter_filmes_mais_avaliados_no_ano(2020, 10)

    assert chamadas == [{"must_exist": True, "read_only": True}]
    with pytest.raises(duckdb.Error):
        conexoes[0].execute("SELECT 1")


def test_filme_destaque_anual_retorna_primeiro_colocado_e_se_atualiza_por_ano(
    banco_marts,
):
    filme_2020 = painel.obter_filme_mais_avaliado_no_ano(2020).iloc[0]
    filme_2021 = painel.obter_filme_mais_avaliado_no_ano(2021).iloc[0]

    assert filme_2020["ranking"] == 1
    assert filme_2020["movieId"] == 1
    assert filme_2020["tmdbId"] == 900
    assert filme_2020["titulo"] == "Filme 1"
    assert filme_2020["total_avaliacoes"] == 999
    assert filme_2020["nota_media_movielens"] == 4.01
    assert filme_2020["poster_path"] == "/poster.jpg"
    assert filme_2021["ranking"] == 1
    assert filme_2021["movieId"] == 2
    assert filme_2021["total_avaliacoes"] == 1999


def test_filme_destaque_trata_tmdb_e_poster_nulos_e_ano_sem_dados(banco_marts):
    con = duckdb.connect(str(banco_marts))
    try:
        con.execute("INSERT INTO refined.filmes VALUES (901, NULL)")
        con.execute(
            "INSERT INTO marts.filmes_mais_avaliados_movielens_por_ano "
            "VALUES (2022, 300, NULL, 'Sem vínculo TMDB', 5, 3.5, 1), "
            "(2023, 301, 901, 'Sem pôster', 6, 4.0, 1), "
            "(2024, 302, 902, 'Sem metadados', 7, 4.5, 1)"
        )
    finally:
        con.close()

    sem_tmdb = painel.obter_filme_mais_avaliado_no_ano(2022).iloc[0]
    sem_poster = painel.obter_filme_mais_avaliado_no_ano(2023).iloc[0]
    sem_metadados = painel.obter_filme_mais_avaliado_no_ano(2024).iloc[0]
    sem_registros = painel.obter_filme_mais_avaliado_no_ano(1900)

    assert pd.isna(sem_tmdb["tmdbId"])
    assert pd.isna(sem_tmdb["poster_path"])
    assert sem_poster["tmdbId"] == 901
    assert pd.isna(sem_poster["poster_path"])
    assert sem_metadados["tmdbId"] == 902
    assert pd.isna(sem_metadados["poster_path"])
    assert sem_registros.empty
    assert sem_registros.columns.tolist() == sem_tmdb.index.tolist()


def test_poster_tmdb_http_200_retorna_imagem_validada(monkeypatch):
    buffer = BytesIO()
    Image.new("RGB", (2, 3), color="navy").save(buffer, format="PNG")
    conteudo_esperado = buffer.getvalue()
    chamada = {}

    class Resposta:
        status = 200
        headers = {"Content-Type": "image/png"}

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self, tamanho):
            assert tamanho > len(conteudo_esperado)
            return conteudo_esperado

    def urlopen_simulado(requisicao, *, timeout):
        chamada["url"] = requisicao.full_url
        chamada["timeout"] = timeout
        return Resposta()

    monkeypatch.setattr(painel, "urlopen", urlopen_simulado)

    poster = painel.obter_poster_tmdb("/poster-123.jpg")

    assert poster == conteudo_esperado
    assert chamada == {
        "url": "https://image.tmdb.org/t/p/w500/poster-123.jpg",
        "timeout": 5,
    }


def test_poster_tmdb_http_404_retorna_none(monkeypatch):
    def urlopen_404(requisicao, *, timeout):
        raise HTTPError(requisicao.full_url, 404, "Not Found", None, None)

    monkeypatch.setattr(painel, "urlopen", urlopen_404)

    assert painel.obter_poster_tmdb("/ausente.jpg") is None


@pytest.mark.parametrize(
    "erro",
    [TimeoutError("timeout"), URLError("conexão indisponível")],
)
def test_poster_tmdb_timeout_e_falha_de_conexao_retorna_none(monkeypatch, erro):
    def urlopen_com_falha(requisicao, *, timeout):
        raise erro

    monkeypatch.setattr(painel, "urlopen", urlopen_com_falha)

    assert painel.obter_poster_tmdb("/poster-123.jpg") is None


def test_poster_tmdb_nulo_vazio_ou_caminho_invalido_nao_abre_conexao(monkeypatch):
    def urlopen_inesperado(*args, **kwargs):
        pytest.fail("não deveria tentar acessar a rede")

    monkeypatch.setattr(painel, "urlopen", urlopen_inesperado)

    for poster_path in (None, "", "   ", "https://example.com/poster.jpg"):
        assert painel.obter_poster_tmdb(poster_path) is None


def test_poster_tmdb_http_200_com_conteudo_nao_imagem_retorna_none(monkeypatch):
    class Resposta:
        status = 200
        headers = {"Content-Type": "text/html"}

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self, tamanho):
            return b"pagina de erro"

    monkeypatch.setattr(painel, "urlopen", lambda *args, **kwargs: Resposta())

    assert painel.obter_poster_tmdb("/poster-123.jpg") is None


def test_url_poster_tmdb_rejeita_caminhos_invalidos():
    url = painel.montar_url_poster_tmdb("/poster-123.jpg")
    assert url == "https://image.tmdb.org/t/p/w500/poster-123.jpg"
    assert painel.montar_url_poster_tmdb(None) is None
    assert painel.montar_url_poster_tmdb("") is None
    assert painel.montar_url_poster_tmdb("   ") is None
    assert painel.montar_url_poster_tmdb("https://example.com/poster.jpg") is None
    assert painel.montar_url_poster_tmdb("//example.com/poster.jpg") is None
    assert painel.montar_url_poster_tmdb("/poster name.jpg") is None


def test_filme_destaque_usa_conexao_somente_leitura_e_fecha(banco_marts, monkeypatch):
    conectar_real = db.conectar
    chamadas = []
    conexoes = []

    def conectar_rastreada(**kwargs):
        chamadas.append(kwargs)
        con = conectar_real(**kwargs)
        conexoes.append(con)
        return con

    monkeypatch.setattr(db, "conectar", conectar_rastreada)

    painel.obter_filme_mais_avaliado_no_ano(2020)

    assert chamadas == [{"must_exist": True, "read_only": True}]
    with pytest.raises(duckdb.Error):
        conexoes[0].execute("SELECT 1")


def test_filme_destaque_fecha_conexao_quando_consulta_falha(monkeypatch):
    class ConexaoComFalha:
        fechada = False

        def execute(self, sql, parametros):
            raise duckdb.InvalidInputException("falha simulada")

        def close(self):
            self.fechada = True

    con = ConexaoComFalha()
    monkeypatch.setattr(db, "conectar", lambda **kwargs: con)

    with pytest.raises(duckdb.InvalidInputException, match="falha simulada"):
        painel.obter_filme_mais_avaliado_no_ano(2020)

    assert con.fechada


def test_grafico_ranking_anual_preserva_filmes_ordem_e_metadata_nulo(banco_marts):
    df = painel.obter_filmes_mais_avaliados_no_ano(2020, 10)
    figura = painel.criar_grafico_filmes_mais_avaliados_no_ano(df)

    assert len(figura.data) == 1
    assert list(figura.data[0].x) == df["total_avaliacoes"].tolist()
    assert list(figura.data[0].y[:3]) == [
        "01 · Filme 1",
        "02 · Filme 2",
        "03 · Sem título (movieId 3)",
    ]
    assert figura.layout.title.text == "Filmes mais avaliados em 2020"
    assert len(figura.data[0].customdata) == len(df)
    assert figura.data[0].customdata[2][0] is None
    assert figura.data[0].customdata[2][2] is None
    assert list(figura.data[0].marker.color[:3]) == ["#17324D", "#2F6B7C", "#2F6B7C"]
    assert "Nota média MovieLens" in figura.data[0].hovertemplate
    assert "tmdbId" in figura.data[0].hovertemplate
    assert figura.layout.yaxis.autorange == "reversed"


def test_grafico_comparacao_preserva_ordem_e_anos_sem_registro(banco_marts):
    df = painel.obter_comparacao_ranking_anual(2020, 2021, 10)
    figura = painel.criar_grafico_comparacao_ranking_anual(df, 2020, 2021)

    assert figura.layout.title.text == "Comparação do ranking anual de filmes MovieLens"
    assert figura.layout.xaxis.title.text == "Ano da avaliação (UTC)"
    assert figura.layout.yaxis.title.text == "Posição no ranking"
    assert figura.layout.yaxis.autorange == "reversed"
    assert list(figura.data[0].x) == [2020]
    assert list(figura.data[0].y) == [1]
    assert "movieId 1" in figura.data[0].name
    filme_compartilhado = next(
        trace for trace in figura.data if "movieId 2" in trace.name
    )
    assert list(filme_compartilhado.x) == [2020, 2021]
    assert list(filme_compartilhado.y) == [2, 1]
    assert list(figura.data[-1].x) == [2021]
    assert list(figura.data[-1].y) == [10]

    vazio = painel.obter_comparacao_ranking_anual(1900, 1901, 10)
    figura_vazia = painel.criar_grafico_comparacao_ranking_anual(vazio, 1900, 1901)
    assert vazio.empty
    assert len(figura_vazia.data) == 0
    assert any(
        "Sem dados" in anotacao.text for anotacao in figura_vazia.layout.annotations
    )


def test_comparacao_ranking_usa_conexao_read_only_e_fecha(banco_marts, monkeypatch):
    conectar_real = db.conectar
    chamadas = []
    conexoes = []

    def conectar_rastreada(**kwargs):
        chamadas.append(kwargs)
        con = conectar_real(**kwargs)
        conexoes.append(con)
        return con

    monkeypatch.setattr(db, "conectar", conectar_rastreada)

    painel.obter_comparacao_ranking_anual(2020, 2021, 10)

    assert chamadas == [{"must_exist": True, "read_only": True}]
    with pytest.raises(duckdb.Error):
        conexoes[0].execute("SELECT 1")


def test_ordem_do_top_filmes_no_grafico_mantem_o_primeiro_no_topo(banco_marts):
    df = painel.obter_filmes_mais_avaliados(10)
    figura = painel.criar_grafico_filmes_mais_avaliados(df)

    assert list(figura.data[0].y) == df["titulo"].tolist()
    assert figura.layout.yaxis.autorange == "reversed"
    assert list(figura.data[0].x) == df["total_avaliacoes"].tolist()


def test_grafico_usuarios_usa_posicoes_e_preserva_userid_no_hover(banco_marts):
    df = painel.obter_usuarios_mais_ativos()
    figura = painel.criar_grafico_usuarios_mais_ativos(df)

    assert list(figura.data[0].y) == [1, 2]
    assert list(figura.data[0].x) == df["total_avaliacoes"].tolist()
    assert [linha[0] for linha in figura.data[0].customdata] == [11, 12]
    assert "userId" in figura.data[0].hovertemplate
    assert figura.layout.yaxis.title.text == "Posição no ranking"
    assert figura.layout.yaxis.autorange == "reversed"


def test_selecao_de_genero_destaca_sem_remover_os_demais(banco_marts):
    df = painel.obter_nota_tmdb_por_genero()
    figura = painel.criar_grafico_nota_tmdb_por_genero(df, "Drama")

    assert list(figura.data[0].y) == df["genero"].tolist()
    assert len(figura.data[0].marker.color) == len(df)
    assert len(set(figura.data[0].marker.color)) == 2
    assert "customdata[0]" in figura.data[0].hovertemplate


def test_conexao_do_painel_e_somente_leitura_e_fechada(banco_marts, monkeypatch):
    conectar_real = db.conectar
    chamadas = []
    conexoes = []

    def conectar_rastreada(**kwargs):
        chamadas.append(kwargs)
        con = conectar_real(**kwargs)
        conexoes.append(con)
        return con

    monkeypatch.setattr(db, "conectar", conectar_rastreada)

    painel.obter_filmes_por_ano()

    assert chamadas == [{"must_exist": True, "read_only": True}]
    with pytest.raises(duckdb.Error):
        conexoes[0].execute("SELECT 1")


def test_conexao_e_fechada_quando_a_consulta_falha(monkeypatch):
    class ConexaoComFalha:
        fechada = False

        def execute(self, sql, parametros):
            raise duckdb.InvalidInputException("falha simulada")

        def close(self):
            self.fechada = True

    con = ConexaoComFalha()
    monkeypatch.setattr(db, "conectar", lambda **kwargs: con)

    with pytest.raises(duckdb.InvalidInputException, match="falha simulada"):
        painel.obter_filmes_por_ano()

    assert con.fechada


def test_ausencia_de_dados_e_valores_nulos_sao_preservados(banco_marts):
    vazio = painel.obter_filmes_por_ano(1900, 1900)
    figura_vazia = painel.criar_grafico_filmes_por_ano(vazio)
    assert len(figura_vazia.data[0].x) == 0
    assert any(
        "Sem dados" in anotacao.text for anotacao in figura_vazia.layout.annotations
    )

    com_nulo = painel.obter_distribuicao_notas()
    figura = painel.criar_grafico_distribuicao_notas(com_nulo)
    valores = list(figura.data[0].y)
    assert pd.isna(valores[1])
    assert pd.isna(figura.data[0].customdata[1][0])


def test_dez_graficos_tem_titulos_eixos_origem_e_dados(banco_marts):
    dfs = _consultas_completas()
    criadores = [
        painel.criar_grafico_filmes_por_ano,
        painel.criar_grafico_nota_tmdb_por_genero,
        painel.criar_grafico_votos_tmdb_por_genero,
        painel.criar_grafico_distribuicao_notas,
        painel.criar_grafico_avaliacoes_por_ano,
        painel.criar_grafico_nota_media_por_ano,
        painel.criar_grafico_filmes_mais_avaliados,
        painel.criar_grafico_usuarios_mais_ativos,
        painel.criar_grafico_distribuicao_usuarios,
        painel.criar_grafico_nota_movielens_por_genero,
    ]
    mart_names = [
        "filmes_lancados_por_ano",
        "nota_media_tmdb_por_genero",
        "quantidade_votos_tmdb_por_genero",
        "distribuicao_notas_movielens",
        "avaliacoes_movielens_ao_longo_do_tempo",
        "nota_media_movielens_ao_longo_do_tempo",
        "filmes_mais_avaliados_movielens",
        "usuarios_mais_ativos",
        "distribuicao_avaliacoes_por_usuario",
        "nota_media_movielens_por_genero",
    ]
    esperados = [
        ("Filmes por ano de lançamento", "Ano de lançamento", "Quantidade de filmes"),
        ("Nota média TMDB por gênero", "Nota média TMDB", "Gênero"),
        ("Votos TMDB por gênero", "Quantidade de votos TMDB", "Gênero"),
        (
            "Distribuição das avaliações MovieLens",
            "Nota MovieLens",
            "Quantidade de avaliações",
        ),
        (
            "Avaliações MovieLens por ano",
            "Ano da avaliação (UTC)",
            "Quantidade de avaliações",
        ),
        (
            "Nota média MovieLens por ano",
            "Ano da avaliação (UTC)",
            "Nota média MovieLens",
        ),
        (
            "Filmes com mais avaliações MovieLens",
            "Quantidade de avaliações",
            "Filme",
        ),
        (
            "Usuários mais ativos no MovieLens",
            "Quantidade de avaliações",
            "Posição no ranking",
        ),
        (
            "Distribuição da atividade dos usuários",
            "Faixa de avaliações por usuário",
            "Quantidade de usuários",
        ),
        ("Nota média MovieLens por gênero", "Nota média MovieLens", "Gênero"),
    ]

    figuras = [criar(df) for criar, df in zip(criadores, dfs, strict=True)]

    assert len(figuras) == 10
    for figura, mart, (titulo, eixo_x, eixo_y), df in zip(
        figuras, mart_names, esperados, dfs, strict=True
    ):
        assert figura.layout.title.text == titulo
        assert figura.layout.xaxis.title.text == eixo_x
        assert figura.layout.yaxis.title.text == eixo_y
        assert any(
            f"marts.{mart}" in anotacao.text for anotacao in figura.layout.annotations
        )
        assert len(figura.data) == 1
        assert len(figura.data[0].x) == len(df) or len(figura.data[0].y) == len(df)
