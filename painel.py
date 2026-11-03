"""Consultas e visualizações da camada analítica Movie Analytics.

As funções de consulta leem somente tabelas já publicadas no schema ``marts``.
Cada chamada abre uma conexão DuckDB somente leitura e a fecha ao terminar.
As funções de gráfico recebem DataFrames para manter a camada desacoplada da
interface que vier a consumir o painel.
"""

from __future__ import annotations

from http.client import HTTPException
from io import BytesIO
from numbers import Integral
from typing import Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

import pandas as pd
import plotly.graph_objects as go
from PIL import Image, UnidentifiedImageError

from pipeline import db

_MART_01 = "filmes_lancados_por_ano"
_MART_02 = "nota_media_tmdb_por_genero"
_MART_03 = "quantidade_votos_tmdb_por_genero"
_MART_04 = "distribuicao_notas_movielens"
_MART_05 = "avaliacoes_movielens_ao_longo_do_tempo"
_MART_06 = "nota_media_movielens_ao_longo_do_tempo"
_MART_07 = "filmes_mais_avaliados_movielens"
_MART_08 = "usuarios_mais_ativos"
_MART_09 = "distribuicao_avaliacoes_por_usuario"
_MART_10 = "nota_media_movielens_por_genero"
_MART_11 = "filmes_mais_avaliados_movielens_por_ano"
_TIMEOUT_POSTER_SEGUNDOS = 5
_TAMANHO_MAXIMO_POSTER_BYTES = 12 * 1024 * 1024


def _consultar(sql: str, parametros: Sequence[object] = ()) -> pd.DataFrame:
    """Executa uma consulta de leitura e sempre fecha a conexão local."""
    con = db.conectar(must_exist=True, read_only=True)
    try:
        return con.execute(sql, list(parametros)).fetchdf()
    finally:
        con.close()


def _validar_intervalo(
    ano_inicio: int | None, ano_fim: int | None
) -> tuple[list[str], list[int]]:
    """Valida limites anuais e devolve predicados fixos com parâmetros."""
    predicados = []
    parametros = []
    for nome, ano, operador in (
        ("ano_inicio", ano_inicio, ">="),
        ("ano_fim", ano_fim, "<="),
    ):
        if ano is None:
            continue
        if isinstance(ano, bool) or not isinstance(ano, Integral):
            raise TypeError(f"{nome} deve ser um número inteiro ou None")
        predicados.append(f"{nome} {operador} ?")
        parametros.append(int(ano))
    if ano_inicio is not None and ano_fim is not None and ano_inicio > ano_fim:
        raise ValueError("ano_inicio não pode ser maior que ano_fim")
    return predicados, parametros


def _obter_por_ano(
    mart: str,
    coluna_ano: str,
    colunas: str,
    ano_inicio: int | None,
    ano_fim: int | None,
) -> pd.DataFrame:
    predicados, parametros = _validar_intervalo(ano_inicio, ano_fim)
    # Os identificadores são constantes internas; somente valores são parâmetros.
    predicados = [
        predicado.replace("ano_inicio", coluna_ano).replace("ano_fim", coluna_ano)
        for predicado in predicados
    ]
    where = f" WHERE {' AND '.join(predicados)}" if predicados else ""
    return _consultar(
        f"SELECT {colunas} FROM marts.{mart}{where} ORDER BY {coluna_ano}",
        parametros,
    )


def obter_filmes_por_ano(
    ano_inicio: int | None = None, ano_fim: int | None = None
) -> pd.DataFrame:
    """Consulta filmes por ano de lançamento, opcionalmente dentro de um intervalo."""
    return _obter_por_ano(
        _MART_01,
        "release_year",
        "release_year, total_movies",
        ano_inicio,
        ano_fim,
    )


def _obter_por_genero(mart: str, ordenacao: str, genero: str | None) -> pd.DataFrame:
    if genero is not None and not isinstance(genero, str):
        raise TypeError("genero deve ser texto ou None")
    where = " WHERE genero = ?" if genero is not None else ""
    parametros = [genero] if genero is not None else []
    return _consultar(
        f"SELECT * FROM marts.{mart}{where} ORDER BY {ordenacao} DESC, genero",
        parametros,
    )


def obter_nota_tmdb_por_genero(genero: str | None = None) -> pd.DataFrame:
    """Consulta a nota média TMDB por gênero, com filtro opcional parametrizado."""
    return _obter_por_genero(_MART_02, "nota_media_tmdb", genero)


def obter_votos_tmdb_por_genero(genero: str | None = None) -> pd.DataFrame:
    """Consulta os votos TMDB por gênero, com filtro opcional parametrizado."""
    return _obter_por_genero(_MART_03, "total_votos_tmdb", genero)


def obter_distribuicao_notas() -> pd.DataFrame:
    """Consulta a distribuição já agregada das notas MovieLens."""
    return _consultar(f"SELECT * FROM marts.{_MART_04} ORDER BY rating")


def obter_avaliacoes_por_ano(
    ano_inicio: int | None = None, ano_fim: int | None = None
) -> pd.DataFrame:
    """Consulta avaliações por ano UTC, opcionalmente dentro de um intervalo."""
    return _obter_por_ano(
        _MART_05,
        "ano_avaliacao",
        "ano_avaliacao, total_avaliacoes",
        ano_inicio,
        ano_fim,
    )


def obter_nota_media_por_ano(
    ano_inicio: int | None = None, ano_fim: int | None = None
) -> pd.DataFrame:
    """Consulta volume e nota média por ano UTC, sem recalcular a MART."""
    return _obter_por_ano(
        _MART_06,
        "ano_avaliacao",
        "ano_avaliacao, total_avaliacoes, nota_media",
        ano_inicio,
        ano_fim,
    )


def obter_filmes_mais_avaliados(top_n: int = 20) -> pd.DataFrame:
    """Consulta o Top 10 ou Top 20, ordenando pelo volume já publicado."""
    if top_n not in (10, 20):
        raise ValueError("top_n deve ser 10 ou 20")
    return _consultar(
        f"SELECT * FROM marts.{_MART_07} ORDER BY total_avaliacoes DESC LIMIT ?",
        [top_n],
    )


def _validar_ano_comparacao(ano: int, nome: str) -> int:
    if isinstance(ano, bool) or not isinstance(ano, Integral):
        raise TypeError(f"{nome} deve ser um ano inteiro")
    ano = int(ano)
    if not 1 <= ano <= 9999:
        raise ValueError(f"{nome} deve estar entre 1 e 9999")
    return ano


def obter_anos_ranking_anual() -> pd.DataFrame:
    """Lista os anos realmente disponíveis na MART 11 em ordem crescente."""
    return _consultar(
        f"SELECT DISTINCT ano_avaliacao FROM marts.{_MART_11} ORDER BY ano_avaliacao"
    )


def obter_filmes_mais_avaliados_no_ano(ano: int, top_n: int = 20) -> pd.DataFrame:
    """Consulta o Top anual publicado, preservando ordem e grão da MART 11."""
    ano = _validar_ano_comparacao(ano, "ano")
    if isinstance(top_n, bool) or not isinstance(top_n, Integral):
        raise TypeError("top_n deve ser um número inteiro")
    if top_n not in (10, 20):
        raise ValueError("top_n deve ser 10 ou 20")

    return _consultar(
        f"SELECT ano_avaliacao, movieId, tmdbId, titulo, total_avaliacoes, "
        f"nota_media_movielens, ranking FROM marts.{_MART_11} "
        "WHERE ano_avaliacao = ? AND ranking <= ? ORDER BY ranking",
        [ano, int(top_n)],
    )


def obter_filme_mais_avaliado_no_ano(ano: int) -> pd.DataFrame:
    """Consulta o primeiro colocado anual e seu pôster nos metadados TMDB."""
    ano = _validar_ano_comparacao(ano, "ano")
    return _consultar(
        f"SELECT m.ano_avaliacao, m.movieId, m.tmdbId, m.titulo, "
        f"m.total_avaliacoes, m.nota_media_movielens, m.ranking, f.poster_path "
        f"FROM marts.{_MART_11} m "
        "LEFT JOIN refined.filmes f ON m.tmdbId = f.id "
        "WHERE m.ano_avaliacao = ? AND m.ranking = 1",
        [ano],
    )


def montar_url_poster_tmdb(poster_path: object) -> str | None:
    """Monta a URL oficial apenas para caminhos relativos válidos do TMDB."""
    if not isinstance(poster_path, str):
        return None
    caminho = poster_path.strip()
    if (
        not caminho.startswith("/")
        or caminho.startswith("//")
        or any(caractere.isspace() or ord(caractere) < 32 for caractere in caminho)
        or "/" in caminho[1:]
        or "\\" in caminho
    ):
        return None
    nome_arquivo = caminho[1:]
    if not nome_arquivo or nome_arquivo in {".", ".."}:
        return None
    return f"https://image.tmdb.org/t/p/w500/{quote(nome_arquivo, safe='._-')}"


def obter_poster_tmdb(poster_path: object) -> bytes | None:
    """Baixa e valida o pôster; falhas de rede retornam ``None``."""
    url = montar_url_poster_tmdb(poster_path)
    if url is None:
        return None

    requisicao = Request(url, headers={"User-Agent": "MovieAnalytics/1.0"})
    try:
        with urlopen(requisicao, timeout=_TIMEOUT_POSTER_SEGUNDOS) as resposta:
            status = (
                resposta.status if hasattr(resposta, "status") else resposta.getcode()
            )
            if status != 200:
                return None
            content_type = resposta.headers.get("Content-Type", "")
            if not content_type.lower().startswith("image/"):
                return None
            conteudo = resposta.read(_TAMANHO_MAXIMO_POSTER_BYTES + 1)
    except (HTTPError, URLError, TimeoutError, OSError, HTTPException, ValueError):
        return None

    if not conteudo or len(conteudo) > _TAMANHO_MAXIMO_POSTER_BYTES:
        return None
    try:
        with Image.open(BytesIO(conteudo)) as imagem:
            if imagem.format not in {"JPEG", "PNG", "WEBP", "GIF"}:
                return None
            imagem.verify()
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError):
        return None
    return conteudo


def obter_comparacao_ranking_anual(
    ano_a: int, ano_b: int, top_n: int = 20
) -> pd.DataFrame:
    """Consulta o Top anual de dois anos, mantendo o grão e a ordem da MART."""
    ano_a = _validar_ano_comparacao(ano_a, "ano_a")
    ano_b = _validar_ano_comparacao(ano_b, "ano_b")
    if ano_a == ano_b:
        raise ValueError("ano_a e ano_b devem ser diferentes")
    if isinstance(top_n, bool) or not isinstance(top_n, Integral):
        raise TypeError("top_n deve ser um número inteiro")
    if top_n not in (10, 20):
        raise ValueError("top_n deve ser 10 ou 20")

    return _consultar(
        f"SELECT ano_avaliacao, movieId, tmdbId, titulo, total_avaliacoes, "
        f"nota_media_movielens, ranking FROM marts.{_MART_11} "
        "WHERE ano_avaliacao IN (?, ?) AND ranking <= ? "
        "ORDER BY ano_avaliacao, ranking",
        [ano_a, ano_b, int(top_n)],
    )


def obter_usuarios_mais_ativos() -> pd.DataFrame:
    """Consulta os usuários do Top 20 já publicado."""
    return _consultar(f"SELECT * FROM marts.{_MART_08} ORDER BY total_avaliacoes DESC")


def obter_distribuicao_usuarios() -> pd.DataFrame:
    """Consulta as sete faixas publicadas na ordem oficial."""
    return _consultar(
        f"SELECT * FROM marts.{_MART_09} "
        "ORDER BY CASE faixa_avaliacoes "
        "WHEN '1' THEN 1 WHEN '2-10' THEN 2 WHEN '11-30' THEN 3 "
        "WHEN '31-100' THEN 4 WHEN '101-500' THEN 5 "
        "WHEN '501-1000' THEN 6 WHEN '>1000' THEN 7 ELSE 8 END"
    )


def obter_nota_movielens_por_genero(genero: str | None = None) -> pd.DataFrame:
    """Consulta a nota MovieLens por gênero, com filtro opcional parametrizado."""
    return _obter_por_genero(_MART_10, "nota_media_movielens", genero)


def _estilizar_figura(
    figura: go.Figure,
    *,
    titulo: str,
    eixo_x: str,
    eixo_y: str,
    mart: str,
    vazia: bool,
) -> go.Figure:
    """Aplica rótulos, layout, origem e estado vazio a um gráfico."""
    figura.update_layout(
        title=titulo,
        xaxis_title=eixo_x,
        yaxis_title=eixo_y,
        template="plotly_white",
        hovermode="closest",
        separators=".,",
        font={"family": "Arial, sans-serif", "size": 14, "color": "#25364A"},
        title_font={
            "family": "Arial, sans-serif",
            "size": 20,
            "color": "#17324D",
        },
        colorway=[
            "#2F6B7C",
            "#315F85",
            "#597B69",
            "#806A8A",
            "#A66A4F",
            "#527C8A",
            "#8C6D4F",
            "#5F7391",
            "#6F855F",
            "#9A6676",
            "#274C63",
            "#4B8796",
            "#718B7D",
            "#9A7B4A",
            "#705F86",
            "#486577",
            "#7E8E9C",
            "#885D45",
            "#637E6B",
            "#8A6F63",
        ],
        paper_bgcolor="white",
        plot_bgcolor="white",
        margin={"t": 96, "b": 70, "l": 86, "r": 30},
        title_x=0.01,
        title_xanchor="left",
    )
    figura.update_xaxes(
        showgrid=False,
        zeroline=False,
        linecolor="#E5EBF1",
        tickfont={"size": 13, "color": "#66788A"},
        title_font={"size": 14, "color": "#25364A"},
    )
    figura.update_yaxes(
        showgrid=True,
        gridcolor="#E5EBF1",
        gridwidth=1,
        zeroline=False,
        linecolor="#E5EBF1",
        tickfont={"size": 13, "color": "#66788A"},
        title_font={"size": 14, "color": "#25364A"},
        automargin=True,
    )
    figura.add_annotation(
        text=f"Origem: marts.{mart}",
        xref="paper",
        yref="paper",
        x=1,
        y=1.12,
        xanchor="right",
        showarrow=False,
        font={"size": 11, "color": "#66788A"},
    )
    if vazia:
        figura.add_annotation(
            text="Sem dados para os filtros selecionados.",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font={"size": 14, "color": "#52616b"},
        )
    return figura


def _customdata(df: pd.DataFrame, colunas: Sequence[str]) -> list[list[object]]:
    """Converte colunas auxiliares em listas, mantendo nulos como nulos."""
    return (
        df[list(colunas)]
        .astype(object)
        .where(df[list(colunas)].notna(), None)
        .values.tolist()
    )


def _grafico_barras(
    df: pd.DataFrame,
    *,
    categoria: str,
    medida: str,
    titulo: str,
    eixo_x: str,
    eixo_y: str,
    mart: str,
    orientacao: str,
    hovertemplate: str,
    custom_columns: Sequence[str] = (),
    destaque_genero: str | None = None,
    formato_medida: str = ",.0f",
) -> go.Figure:
    """Cria gráfico de barras sem filtrar linhas nem substituir valores nulos."""
    categorias = df[categoria].tolist()
    medidas = df[medida].tolist()
    trace = {
        "name": f"marts.{mart}",
        "hovertemplate": hovertemplate,
    }
    if custom_columns:
        trace["customdata"] = _customdata(df, custom_columns)
    if orientacao == "h":
        trace.update(x=medidas, y=categorias, orientation="h")
        figura = go.Figure(data=[go.Bar(**trace)])
        figura.update_xaxes(tickformat=formato_medida)
        figura.update_yaxes(
            categoryorder="array", categoryarray=categorias, autorange="reversed"
        )
    else:
        trace.update(x=categorias, y=medidas)
        figura = go.Figure(data=[go.Bar(**trace)])
        figura.update_yaxes(tickformat=formato_medida)
    figura.update_traces(marker_color="#315f85", showlegend=False)
    if destaque_genero is not None and categoria == "genero":
        colors = [
            "#17324d" if nome == destaque_genero else "#9db4c5" for nome in categorias
        ]
        figura.data[0].marker.color = colors
    figura = _estilizar_figura(
        figura,
        titulo=titulo,
        eixo_x=eixo_x,
        eixo_y=eixo_y,
        mart=mart,
        vazia=df.empty,
    )
    if orientacao == "h":
        figura.update_layout(height=max(400, min(560, 100 + len(categorias) * 23)))
        figura.update_xaxes(showgrid=True, gridcolor="#E5EBF1")
        figura.update_yaxes(showgrid=False)
    else:
        figura.update_layout(height=390)
        figura.update_yaxes(showgrid=True, gridcolor="#E5EBF1")
    return figura


def criar_grafico_filmes_por_ano(df: pd.DataFrame) -> go.Figure:
    """Cria barras verticais de filmes lançados por ano."""
    return _grafico_barras(
        df,
        categoria="release_year",
        medida="total_movies",
        titulo="Filmes por ano de lançamento",
        eixo_x="Ano de lançamento",
        eixo_y="Quantidade de filmes",
        mart=_MART_01,
        orientacao="v",
        hovertemplate="Ano: %{x}<br>Filmes: %{y:,.0f}<extra></extra>",
    )


def criar_grafico_nota_tmdb_por_genero(
    df: pd.DataFrame, destaque_genero: str | None = None
) -> go.Figure:
    """Cria barras horizontais da média TMDB e pode destacar um gênero."""
    return _grafico_barras(
        df,
        categoria="genero",
        medida="nota_media_tmdb",
        titulo="Nota média TMDB por gênero",
        eixo_x="Nota média TMDB",
        eixo_y="Gênero",
        mart=_MART_02,
        orientacao="h",
        hovertemplate=(
            "Gênero: %{y}<br>Nota média: %{x:.2f}"
            "<br>Filmes: %{customdata[0]:,.0f}<extra></extra>"
        ),
        custom_columns=("total_filmes",),
        destaque_genero=destaque_genero,
        formato_medida=".2f",
    )


def criar_grafico_votos_tmdb_por_genero(
    df: pd.DataFrame, destaque_genero: str | None = None
) -> go.Figure:
    """Cria barras horizontais de votos TMDB, destacando sem excluir gêneros."""
    return _grafico_barras(
        df,
        categoria="genero",
        medida="total_votos_tmdb",
        titulo="Votos TMDB por gênero",
        eixo_x="Quantidade de votos TMDB",
        eixo_y="Gênero",
        mart=_MART_03,
        orientacao="h",
        hovertemplate=(
            "Gênero: %{y}<br>Votos TMDB: %{x:,.0f}"
            "<br>Filmes: %{customdata[0]:,.0f}<extra></extra>"
        ),
        custom_columns=("total_filmes",),
        destaque_genero=destaque_genero,
    )


def criar_grafico_distribuicao_notas(df: pd.DataFrame) -> go.Figure:
    """Cria barras verticais da distribuição de notas e percentuais."""
    return _grafico_barras(
        df,
        categoria="rating",
        medida="total_avaliacoes",
        titulo="Distribuição das avaliações MovieLens",
        eixo_x="Nota MovieLens",
        eixo_y="Quantidade de avaliações",
        mart=_MART_04,
        orientacao="v",
        hovertemplate=(
            "Nota: %{x:.1f}<br>Avaliações: %{y:,.0f}"
            "<br>Participação: %{customdata[0]:.2f}%<extra></extra>"
        ),
        custom_columns=("percentual",),
    )


def _grafico_linha(
    df: pd.DataFrame,
    *,
    medida: str,
    titulo: str,
    eixo_y: str,
    mart: str,
    hovertemplate: str,
) -> go.Figure:
    """Cria uma série anual mantendo lacunas para valores nulos."""
    trace = {
        "x": df["ano_avaliacao"].tolist(),
        "y": df[medida].tolist(),
        "mode": "lines+markers",
        "connectgaps": False,
        "name": f"marts.{mart}",
        "hovertemplate": hovertemplate,
    }
    if medida == "nota_media":
        trace["customdata"] = _customdata(df, ("total_avaliacoes",))
    figura = go.Figure(data=[go.Scatter(**trace)])
    figura.update_traces(
        line={"color": "#2F6B7C", "width": 2.5},
        marker={"color": "#2F6B7C", "size": 7},
    )
    figura.update_layout(showlegend=False)
    figura.update_xaxes(tickformat="d")
    figura.update_yaxes(tickformat=",.0f" if medida == "total_avaliacoes" else ".3f")
    return _estilizar_figura(
        figura,
        titulo=titulo,
        eixo_x="Ano da avaliação (UTC)",
        eixo_y=eixo_y,
        mart=mart,
        vazia=df.empty,
    )


def criar_grafico_avaliacoes_por_ano(df: pd.DataFrame) -> go.Figure:
    """Cria a série temporal do volume de avaliações por ano UTC."""
    return _grafico_linha(
        df,
        medida="total_avaliacoes",
        titulo="Avaliações MovieLens por ano",
        eixo_y="Quantidade de avaliações",
        mart=_MART_05,
        hovertemplate="Ano UTC: %{x}<br>Avaliações: %{y:,.0f}<extra></extra>",
    )


def criar_grafico_nota_media_por_ano(df: pd.DataFrame) -> go.Figure:
    """Cria a série temporal da nota média das avaliações por ano UTC."""
    return _grafico_linha(
        df,
        medida="nota_media",
        titulo="Nota média MovieLens por ano",
        eixo_y="Nota média MovieLens",
        mart=_MART_06,
        hovertemplate=(
            "Ano UTC: %{x}<br>Avaliações: %{customdata:,.0f}"
            "<br>Nota média: %{y:.3f}<extra></extra>"
        ),
    )


def criar_grafico_filmes_mais_avaliados(df: pd.DataFrame) -> go.Figure:
    """Cria barras horizontais do Top de filmes na ordem da MART."""
    return _grafico_barras(
        df,
        categoria="titulo",
        medida="total_avaliacoes",
        titulo="Filmes com mais avaliações MovieLens",
        eixo_x="Quantidade de avaliações",
        eixo_y="Filme",
        mart=_MART_07,
        orientacao="h",
        hovertemplate=(
            "Filme: %{y}<br>Avaliações: %{x:,.0f}"
            "<br>Nota média MovieLens: %{customdata[2]:.2f}"
            "<br>movieId: %{customdata[0]}"
            "<br>tmdbId: %{customdata[1]}<extra></extra>"
        ),
        custom_columns=("movieId", "tmdbId", "nota_media_movielens"),
    )


def criar_grafico_filmes_mais_avaliados_no_ano(df: pd.DataFrame) -> go.Figure:
    """Cria o ranking anual horizontal, sem fundir títulos ou movieIds."""
    dados = df.copy()
    anos = dados["ano_avaliacao"].dropna().unique().tolist()
    titulo_grafico = (
        f"Filmes mais avaliados em {int(anos[0])}"
        if len(anos) == 1
        else "Filmes mais avaliados no ano"
    )
    rotulos = []
    for _, filme in dados.iterrows():
        titulo = filme["titulo"]
        if pd.isna(titulo) or not str(titulo).strip():
            titulo = f"Sem título (movieId {filme['movieId']})"
        rotulos.append(f"{int(filme['ranking']):02d} · {titulo}")
    dados["rotulo_ranking"] = rotulos

    figura = _grafico_barras(
        dados,
        categoria="rotulo_ranking",
        medida="total_avaliacoes",
        titulo=titulo_grafico,
        eixo_x="Quantidade de avaliações",
        eixo_y="Filme · posição no ranking",
        mart=_MART_11,
        orientacao="h",
        hovertemplate=(
            "Posição: %{customdata[4]}<br>Filme: %{customdata[0]}"
            "<br>Avaliações: %{x:,.0f}"
            "<br>Nota média MovieLens: %{customdata[3]:.3f}"
            "<br>movieId: %{customdata[1]}"
            "<br>tmdbId: %{customdata[2]}<extra></extra>"
        ),
        custom_columns=(
            "titulo",
            "movieId",
            "tmdbId",
            "nota_media_movielens",
            "ranking",
        ),
    )
    if not dados.empty:
        cores = [
            "#17324D" if posicao == 0 else "#2F6B7C" if posicao < 3 else "#8AA6B8"
            for posicao in range(len(dados))
        ]
        figura.data[0].marker.color = cores
    return figura


def criar_grafico_comparacao_ranking_anual(
    df: pd.DataFrame, ano_a: int, ano_b: int
) -> go.Figure:
    """Compara as posições anuais sem substituir anos ausentes por zero."""
    ano_a = _validar_ano_comparacao(ano_a, "ano_a")
    ano_b = _validar_ano_comparacao(ano_b, "ano_b")
    if ano_a == ano_b:
        raise ValueError("ano_a e ano_b devem ser diferentes")

    figura = go.Figure()
    if not df.empty:
        for movie_id in df["movieId"].drop_duplicates().tolist():
            filme = df.loc[df["movieId"] == movie_id].sort_values("ano_avaliacao")
            customdata = (
                filme[["titulo", "tmdbId", "total_avaliacoes", "nota_media_movielens"]]
                .astype(object)
                .where(
                    filme[
                        [
                            "titulo",
                            "tmdbId",
                            "total_avaliacoes",
                            "nota_media_movielens",
                        ]
                    ].notna(),
                    None,
                )
                .values.tolist()
            )
            titulo = filme["titulo"].iloc[0]
            titulo_legenda = str(titulo) if pd.notna(titulo) else "Sem título"
            nome = f"{titulo_legenda} (movieId {movie_id})"
            figura.add_trace(
                go.Scatter(
                    x=filme["ano_avaliacao"].tolist(),
                    y=filme["ranking"].tolist(),
                    customdata=customdata,
                    mode="lines+markers" if len(filme) > 1 else "markers",
                    connectgaps=False,
                    name=nome,
                    hovertemplate=(
                        "Ano UTC: %{x}<br>Ranking: %{y}"
                        "<br>Filme: %{customdata[0]}"
                        "<br>tmdbId: %{customdata[1]}"
                        "<br>Avaliações: %{customdata[2]:,.0f}"
                        "<br>Nota média MovieLens: %{customdata[3]:.3f}"
                        "<extra></extra>"
                    ),
                )
            )
    figura.update_xaxes(tickmode="array", tickvals=[ano_a, ano_b])
    figura.update_yaxes(autorange="reversed", dtick=1)
    figura.update_traces(
        line={"width": 1.8},
        marker={"size": 8},
        showlegend=False,
    )
    figura.update_layout(
        height=max(430, min(590, 270 + df["movieId"].nunique() * 16)),
        hoverlabel={"bgcolor": "#FFFFFF", "font": {"color": "#25364A", "size": 13}},
    )
    return _estilizar_figura(
        figura,
        titulo="Comparação do ranking anual de filmes MovieLens",
        eixo_x="Ano da avaliação (UTC)",
        eixo_y="Posição no ranking",
        mart=_MART_11,
        vazia=df.empty,
    )


def criar_grafico_usuarios_mais_ativos(df: pd.DataFrame) -> go.Figure:
    """Cria barras posicionais; mantém userId e nota no hover."""
    dados = df.copy()
    dados["posicao_ranking"] = range(1, len(dados) + 1)
    figura = _grafico_barras(
        dados,
        categoria="posicao_ranking",
        medida="total_avaliacoes",
        titulo="Usuários mais ativos no MovieLens",
        eixo_x="Quantidade de avaliações",
        eixo_y="Posição no ranking",
        mart=_MART_08,
        orientacao="h",
        hovertemplate=(
            "Posição: %{y}<br>Avaliações: %{x:,.0f}"
            "<br>userId: %{customdata[0]}"
            "<br>Nota média: %{customdata[1]:.2f}<extra></extra>"
        ),
        custom_columns=("userId", "nota_media_usuario"),
    )
    if not dados.empty:
        cores = [
            "#17324D" if posicao == 0 else "#2F6B7C" if posicao < 3 else "#8AA6B8"
            for posicao in range(len(dados))
        ]
        figura.data[0].marker.color = cores
    return figura


def criar_grafico_distribuicao_usuarios(df: pd.DataFrame) -> go.Figure:
    """Cria barras verticais das sete faixas de atividade dos usuários."""
    return _grafico_barras(
        df,
        categoria="faixa_avaliacoes",
        medida="total_usuarios",
        titulo="Distribuição da atividade dos usuários",
        eixo_x="Faixa de avaliações por usuário",
        eixo_y="Quantidade de usuários",
        mart=_MART_09,
        orientacao="v",
        hovertemplate=(
            "Faixa: %{x}<br>Usuários: %{y:,.0f}"
            "<br>Percentual: %{customdata[0]:.2f}%<extra></extra>"
        ),
        custom_columns=("percentual_usuarios",),
    )


def criar_grafico_nota_movielens_por_genero(
    df: pd.DataFrame, destaque_genero: str | None = None
) -> go.Figure:
    """Cria barras horizontais da média MovieLens por gênero."""
    return _grafico_barras(
        df,
        categoria="genero",
        medida="nota_media_movielens",
        titulo="Nota média MovieLens por gênero",
        eixo_x="Nota média MovieLens",
        eixo_y="Gênero",
        mart=_MART_10,
        orientacao="h",
        hovertemplate=(
            "Gênero: %{y}<br>Nota média MovieLens: %{x:.3f}"
            "<br>Filmes: %{customdata[0]:,.0f}"
            "<br>Avaliações: %{customdata[1]:,.0f}<extra></extra>"
        ),
        custom_columns=("total_filmes", "total_avaliacoes"),
        destaque_genero=destaque_genero,
        formato_medida=".3f",
    )
