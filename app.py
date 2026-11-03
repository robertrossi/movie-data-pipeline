"""Interface Streamlit do Movie Analytics, em português."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

import pandas as pd
import streamlit as st

import painel
from pipeline import db

_LOGGER = logging.getLogger(__name__)

st.set_page_config(
    page_title="Movie Analytics",
    page_icon="🎬",
    layout="wide",
)


def _preparar_banco_dashboard() -> None:
    """Seleciona e verifica o banco antes de executar consultas das abas."""
    try:
        conexao = db.conectar(must_exist=True, read_only=True)
        conexao.close()
    except Exception as erro:  # noqa: BLE001
        _LOGGER.exception("Falha ao preparar o banco do dashboard")
        st.error(f"Não foi possível preparar o banco do dashboard: {erro}")
        st.stop()


_preparar_banco_dashboard()

st.markdown(
    """
    <style>
      .cinema-banner {
        position: relative;
        isolation: isolate;
        overflow: hidden;
        box-sizing: border-box;
        min-height: 176px;
        margin: .4rem 0 1.7rem;
        padding: clamp(1.6rem, 4vw, 2.8rem) clamp(2.8rem, 7vw, 5.2rem);
        border: 1px solid rgba(229, 235, 241, .18);
        border-radius: 16px;
        background:
          linear-gradient(112deg, rgba(23, 50, 77, .98), rgba(36, 53, 68, .97) 68%, rgba(34, 75, 87, .96)),
          #17324D;
        box-shadow: 0 12px 30px rgba(23, 50, 77, .12);
      }
      .cinema-banner::after {
        position: absolute;
        z-index: -1;
        inset: 0;
        background-image:
          radial-gradient(rgba(255, 255, 255, .2) .55px, transparent .8px),
          repeating-linear-gradient(115deg, transparent 0 38px, rgba(255, 255, 255, .025) 39px 40px);
        background-size: 5px 5px, auto;
        content: "";
        opacity: .2;
        pointer-events: none;
      }
      .cinema-banner__perforations {
        position: absolute;
        top: 14px;
        bottom: 14px;
        width: 13px;
        background: radial-gradient(ellipse 4px 6px at center, rgba(218, 229, 235, .58) 0 72%, transparent 78%)
          center top / 13px 25px repeat-y;
        opacity: .62;
      }
      .cinema-banner__perforations--left { left: 12px; }
      .cinema-banner__perforations--right { right: 12px; }
      .cinema-banner__content { position: relative; z-index: 1; }
      .cinema-banner__eyebrow {
        margin: 0 0 .55rem;
        color: #9ac3ca;
        font-size: .72rem;
        font-weight: 700;
        letter-spacing: .16em;
        text-transform: uppercase;
      }
      .cinema-banner__title {
        margin: 0;
        color: #FFFFFF !important;
        font-size: clamp(1.85rem, 4vw, 2.75rem);
        font-weight: 700;
        letter-spacing: -.035em;
        line-height: 1.1;
      }
      .cinema-banner__subtitle {
        margin: .65rem 0 0;
        color: #d4dde5;
        font-size: clamp(.95rem, 1.7vw, 1.08rem);
        line-height: 1.5;
      }
      .cinema-banner__accent {
        position: absolute;
        right: 7%;
        bottom: 0;
        width: 22%;
        height: 3px;
        border-radius: 3px 3px 0 0;
        background: #2F6B7C;
      }
      @media (max-width: 640px) {
        .cinema-banner {
          min-height: 150px;
          margin-bottom: 1.25rem;
          padding: 1.5rem 2.35rem;
          border-radius: 12px;
        }
        .cinema-banner__perforations--left { left: 8px; }
        .cinema-banner__perforations--right { right: 8px; }
      }
    </style>
    <section class="cinema-banner" aria-label="Cinema Analytics">
      <span class="cinema-banner__perforations cinema-banner__perforations--left" aria-hidden="true"></span>
      <span class="cinema-banner__perforations cinema-banner__perforations--right" aria-hidden="true"></span>
      <div class="cinema-banner__content">
        <p class="cinema-banner__eyebrow">Movie Data · Film Analytics</p>
        <h1 class="cinema-banner__title">Cinema Analytics</h1>
        <p class="cinema-banner__subtitle">Uma exploração analítica do universo cinematográfico</p>
      </div>
      <span class="cinema-banner__accent" aria-hidden="true"></span>
    </section>
    """,
    unsafe_allow_html=True,
)


def _carregar_dados(
    indicador: str,
    funcao: Callable[..., pd.DataFrame],
    **argumentos: Any,
) -> pd.DataFrame | None:
    """Consulta a camada analítica e apresenta erros no contexto do indicador."""
    try:
        return funcao(**argumentos)
    except Exception:  # noqa: BLE001
        _LOGGER.exception("Falha ao consultar o indicador %s", indicador)
        st.error(f"Não foi possível carregar esta análise ({indicador}).")
        return None


def _intervalo_ano(
    dados: pd.DataFrame | None,
    *,
    coluna: str,
    rotulo: str,
    chave: str,
    periodo_principal: tuple[int, int] | None = None,
) -> tuple[int, int] | None:
    """Mostra um seletor de intervalo baseado nos anos presentes na MART."""
    if dados is None or dados.empty:
        st.info(f"Não há anos disponíveis para o filtro de {rotulo.lower()}.")
        return None

    menor = int(dados[coluna].min())
    maior = int(dados[coluna].max())
    if menor == maior:
        st.caption(f"{rotulo}: {menor}")
        return menor, maior

    padrao = (menor, maior)
    if periodo_principal is not None:
        inicio = max(menor, periodo_principal[0])
        fim = min(maior, periodo_principal[1])
        if inicio <= fim:
            padrao = (inicio, fim)

    return st.slider(
        rotulo,
        min_value=menor,
        max_value=maior,
        value=padrao,
        key=chave,
    )


def _mostrar_grafico(
    indicador: str,
    dados: pd.DataFrame | None,
    criar_grafico: Callable[..., Any],
    *,
    chave: str,
    argumentos_grafico: dict[str, Any] | None = None,
) -> None:
    """Renderiza uma figura e mantém falhas isoladas no indicador correspondente."""
    if dados is None:
        return
    try:
        figura = criar_grafico(dados, **(argumentos_grafico or {}))
        st.plotly_chart(figura, width="stretch", key=chave)
    except Exception:  # noqa: BLE001
        _LOGGER.exception("Falha ao montar o gráfico do indicador %s", indicador)
        st.error(f"Não foi possível exibir esta análise ({indicador}).")


@st.cache_data(ttl=6 * 60 * 60, show_spinner=False)
def _obter_poster_cacheado(poster_path: str | None) -> bytes | None:
    """Guarda o pôster por seis horas para evitar downloads em cada rerun."""
    return painel.obter_poster_tmdb(poster_path)


aba_geral, aba_generos, aba_filmes, aba_usuarios = st.tabs(
    ["Visão geral", "Gêneros", "Filmes e avaliações", "Usuários"]
)

with aba_geral:
    st.header("Visão geral")
    st.caption("Panorama do catálogo, das notas e da atividade MovieLens.")

    dados_ano_lancamento = _carregar_dados("01", painel.obter_filmes_por_ano)
    dados_anos_avaliacao = _carregar_dados("05", painel.obter_avaliacoes_por_ano)

    filtro_lancamento, filtro_avaliacao, _ = st.columns([1, 1, 2])
    with filtro_lancamento:
        intervalo_lancamento = _intervalo_ano(
            dados_ano_lancamento,
            coluna="release_year",
            rotulo="Ano de lançamento",
            chave="geral_intervalo_lancamento",
            periodo_principal=(2000, 2016),
        )
    with filtro_avaliacao:
        intervalo_avaliacao = _intervalo_ano(
            dados_anos_avaliacao,
            coluna="ano_avaliacao",
            rotulo="Ano da avaliação (UTC)",
            chave="geral_intervalo_avaliacao",
        )

    if intervalo_lancamento is None:
        filmes_por_ano = dados_ano_lancamento
    else:
        filmes_por_ano = _carregar_dados(
            "01",
            painel.obter_filmes_por_ano,
            ano_inicio=intervalo_lancamento[0],
            ano_fim=intervalo_lancamento[1],
        )

    if intervalo_avaliacao is None:
        avaliacoes_por_ano = dados_anos_avaliacao
        nota_media_por_ano = _carregar_dados("06", painel.obter_nota_media_por_ano)
    else:
        avaliacoes_por_ano = _carregar_dados(
            "05",
            painel.obter_avaliacoes_por_ano,
            ano_inicio=intervalo_avaliacao[0],
            ano_fim=intervalo_avaliacao[1],
        )
        nota_media_por_ano = _carregar_dados(
            "06",
            painel.obter_nota_media_por_ano,
            ano_inicio=intervalo_avaliacao[0],
            ano_fim=intervalo_avaliacao[1],
        )

    linha_1 = st.columns(2)
    with linha_1[0]:
        _mostrar_grafico(
            "01",
            filmes_por_ano,
            painel.criar_grafico_filmes_por_ano,
            chave="grafico_01_geral",
        )
    with linha_1[1]:
        distribuicao_notas = _carregar_dados("04", painel.obter_distribuicao_notas)
        _mostrar_grafico(
            "04",
            distribuicao_notas,
            painel.criar_grafico_distribuicao_notas,
            chave="grafico_04_geral",
        )

    linha_2 = st.columns(2)
    with linha_2[0]:
        _mostrar_grafico(
            "05",
            avaliacoes_por_ano,
            painel.criar_grafico_avaliacoes_por_ano,
            chave="grafico_05_geral",
        )
    with linha_2[1]:
        _mostrar_grafico(
            "06",
            nota_media_por_ano,
            painel.criar_grafico_nota_media_por_ano,
            chave="grafico_06_geral",
        )

with aba_generos:
    st.header("Gêneros")
    st.caption(
        "Explore como os gêneros se comportam em diferentes métricas de avaliação."
    )
    nota_tmdb = _carregar_dados("02", painel.obter_nota_tmdb_por_genero)
    votos_tmdb = _carregar_dados("03", painel.obter_votos_tmdb_por_genero)
    nota_movielens = _carregar_dados("10", painel.obter_nota_movielens_por_genero)

    conjuntos = [
        set(dados["genero"].dropna().astype(str))
        for dados in (nota_tmdb, votos_tmdb, nota_movielens)
        if dados is not None and not dados.empty
    ]
    generos = sorted(set.union(*conjuntos)) if conjuntos else []
    opcoes_genero = ["Todos os gêneros"] + generos
    filtro_genero, _ = st.columns([1, 3])
    with filtro_genero:
        genero_selecionado = st.selectbox(
            "Gênero a destacar",
            options=opcoes_genero,
            help="O destaque mantém todas as barras para comparação.",
            key="genero_a_destacar",
        )
    destaque_genero = (
        None if genero_selecionado == "Todos os gêneros" else genero_selecionado
    )

    st.subheader("Visão do TMDB")
    linha_generos_tmdb = st.columns(2)
    with linha_generos_tmdb[0]:
        _mostrar_grafico(
            "02",
            nota_tmdb,
            painel.criar_grafico_nota_tmdb_por_genero,
            chave="grafico_02_generos",
            argumentos_grafico={"destaque_genero": destaque_genero},
        )
    with linha_generos_tmdb[1]:
        _mostrar_grafico(
            "03",
            votos_tmdb,
            painel.criar_grafico_votos_tmdb_por_genero,
            chave="grafico_03_generos",
            argumentos_grafico={"destaque_genero": destaque_genero},
        )
    st.divider()
    st.subheader("Visão do MovieLens")
    _mostrar_grafico(
        "10",
        nota_movielens,
        painel.criar_grafico_nota_movielens_por_genero,
        chave="grafico_10_generos",
        argumentos_grafico={"destaque_genero": destaque_genero},
    )
    st.caption("Notas TMDB e MovieLens são métricas distintas.")

with aba_filmes:
    st.header("Filmes e avaliações")
    st.caption("Rankings anuais, comparação entre anos e evolução das avaliações.")
    anos_ranking_df = _carregar_dados("11", painel.obter_anos_ranking_anual)
    anos_ranking = (
        sorted({int(ano) for ano in anos_ranking_df["ano_avaliacao"].dropna()})
        if anos_ranking_df is not None and not anos_ranking_df.empty
        else []
    )

    st.subheader("Filmes mais avaliados")
    st.caption("Descubra quais filmes receberam mais avaliações no ano selecionado.")
    if not anos_ranking:
        st.info("Não há ranking anual disponível.")
    else:
        filtros_ranking_ano = st.columns([1, 1, 2])
        with filtros_ranking_ano[0]:
            ano_ranking = st.selectbox(
                "Ano",
                options=anos_ranking,
                index=len(anos_ranking) - 1,
                key="ranking_filmes_ano",
            )
        with filtros_ranking_ano[1]:
            top_n_anual = st.selectbox(
                "Quantidade",
                options=[10, 20],
                index=1,
                format_func=lambda quantidade: f"Top {quantidade}",
                key="ranking_filmes_top_n",
            )
        ranking_anual = _carregar_dados(
            "11",
            painel.obter_filmes_mais_avaliados_no_ano,
            ano=ano_ranking,
            top_n=top_n_anual,
        )
        if ranking_anual is not None:
            if ranking_anual.empty:
                st.info("Não há filmes avaliados neste ano.")
            else:
                grafico_ranking, destaque_filme = st.columns([1.85, 1])
                with grafico_ranking:
                    _mostrar_grafico(
                        "11",
                        ranking_anual,
                        painel.criar_grafico_filmes_mais_avaliados_no_ano,
                        chave="grafico_11_ranking_anual",
                    )
                with destaque_filme:
                    filme_destaque = _carregar_dados(
                        "11", painel.obter_filme_mais_avaliado_no_ano, ano=ano_ranking
                    )
                    if filme_destaque is not None and filme_destaque.empty:
                        st.info("Não há filme em destaque para este ano.")
                    elif filme_destaque is not None:
                        filme = filme_destaque.iloc[0]
                        poster_path_bruto = filme["poster_path"]
                        poster_path = (
                            None
                            if pd.isna(poster_path_bruto)
                            else str(poster_path_bruto)
                        )
                        poster = _obter_poster_cacheado(poster_path)
                        if poster is not None:
                            st.image(poster, width=240)
                            st.caption("Pôster: TMDB")
                        else:
                            with st.container(
                                width=240,
                                height=360,
                                border=True,
                                vertical_alignment="center",
                            ):
                                st.markdown("## 🎬", text_alignment="center")
                                st.caption("Pôster indisponível")

                        titulo_destaque = filme["titulo"]
                        if pd.isna(titulo_destaque) or not str(titulo_destaque).strip():
                            titulo_destaque = f"Filme (movieId {int(filme['movieId'])})"
                        st.subheader(str(titulo_destaque))
                        st.metric(
                            "Avaliações neste ano",
                            f"{int(filme['total_avaliacoes']):,}".replace(",", "."),
                        )
                        nota_destaque = filme["nota_media_movielens"]
                        nota_formatada = (
                            f"{float(nota_destaque):.2f}"
                            if pd.notna(nota_destaque)
                            else "—"
                        )
                        st.metric("Nota média MovieLens", nota_formatada)

    with st.expander("Ranking histórico, todos os anos"):
        st.caption("Filmes com mais avaliações no conjunto completo de dados.")
        filtro_top_historico, _ = st.columns([1, 3])
        with filtro_top_historico:
            top_n_historico = st.selectbox(
                "Quantidade",
                options=[10, 20],
                index=1,
                format_func=lambda quantidade: f"Top {quantidade}",
                key="top_filmes",
            )
        filmes_top = _carregar_dados(
            "07", painel.obter_filmes_mais_avaliados, top_n=top_n_historico
        )
        _mostrar_grafico(
            "07",
            filmes_top,
            painel.criar_grafico_filmes_mais_avaliados,
            chave="grafico_07_filmes",
        )

    st.divider()
    st.subheader("Comparação entre anos")
    st.caption("Compare os filmes mais avaliados em dois anos diferentes.")
    if len(anos_ranking) < 2:
        st.info("São necessários dois anos com avaliações para comparar.")
    else:
        seletores_comparacao = st.columns([1, 1, 1, 1])
        with seletores_comparacao[0]:
            ano_a = st.selectbox(
                "Primeiro ano",
                options=anos_ranking,
                index=len(anos_ranking) - 2,
                key="ranking_anual_ano_a",
            )
        with seletores_comparacao[1]:
            ano_b = st.selectbox(
                "Segundo ano",
                options=anos_ranking,
                index=len(anos_ranking) - 1,
                key="ranking_anual_ano_b",
            )
        with seletores_comparacao[2]:
            top_n_comparacao = st.selectbox(
                "Quantidade",
                options=[10, 20],
                index=1,
                format_func=lambda quantidade: f"Top {quantidade}",
                key="ranking_anual_top_n",
            )

        if ano_a == ano_b:
            st.info("Escolha dois anos diferentes para comparar.")
        else:
            comparacao_anual = _carregar_dados(
                "11",
                painel.obter_comparacao_ranking_anual,
                ano_a=ano_a,
                ano_b=ano_b,
                top_n=top_n_comparacao,
            )
            if comparacao_anual is not None:
                if comparacao_anual.empty:
                    st.info("Não há filmes para comparar nos anos selecionados.")
                else:
                    _mostrar_grafico(
                        "11",
                        comparacao_anual,
                        painel.criar_grafico_comparacao_ranking_anual,
                        chave="grafico_11_comparacao_anual",
                        argumentos_grafico={"ano_a": ano_a, "ano_b": ano_b},
                    )

    st.divider()
    st.subheader("Evolução das avaliações")
    dados_anos_filmes = _carregar_dados("05", painel.obter_avaliacoes_por_ano)
    filtro_periodo_filmes, _ = st.columns([1, 3])
    with filtro_periodo_filmes:
        intervalo_filmes = _intervalo_ano(
            dados_anos_filmes,
            coluna="ano_avaliacao",
            rotulo="Intervalo de avaliação (UTC)",
            chave="filmes_intervalo_avaliacao",
        )
    if intervalo_filmes is None:
        avaliacoes_filmes = dados_anos_filmes
        nota_filmes = _carregar_dados("06", painel.obter_nota_media_por_ano)
    else:
        avaliacoes_filmes = _carregar_dados(
            "05",
            painel.obter_avaliacoes_por_ano,
            ano_inicio=intervalo_filmes[0],
            ano_fim=intervalo_filmes[1],
        )
        nota_filmes = _carregar_dados(
            "06",
            painel.obter_nota_media_por_ano,
            ano_inicio=intervalo_filmes[0],
            ano_fim=intervalo_filmes[1],
        )

    linha_temporal = st.columns(2)
    with linha_temporal[0]:
        _mostrar_grafico(
            "05",
            avaliacoes_filmes,
            painel.criar_grafico_avaliacoes_por_ano,
            chave="grafico_05_filmes",
        )
    with linha_temporal[1]:
        _mostrar_grafico(
            "06",
            nota_filmes,
            painel.criar_grafico_nota_media_por_ano,
            chave="grafico_06_filmes",
        )

with aba_usuarios:
    st.header("Usuários")
    st.caption("Explore o volume de avaliações e sua distribuição entre usuários.")

    usuarios = _carregar_dados("08", painel.obter_usuarios_mais_ativos)
    distribuicao_usuarios = _carregar_dados("09", painel.obter_distribuicao_usuarios)
    st.subheader("Usuários mais ativos")
    _mostrar_grafico(
        "08",
        usuarios,
        painel.criar_grafico_usuarios_mais_ativos,
        chave="grafico_08_usuarios",
    )

    st.divider()
    st.subheader("Distribuição da atividade")
    _mostrar_grafico(
        "09",
        distribuicao_usuarios,
        painel.criar_grafico_distribuicao_usuarios,
        chave="grafico_09_usuarios",
    )
    st.caption("Passe o cursor nas barras para consultar o percentual por faixa.")

    st.divider()
    st.subheader("Detalhamento por faixa")
    if distribuicao_usuarios is None:
        st.info("A distribuição de usuários está indisponível.")
    elif distribuicao_usuarios.empty:
        st.info("A MART não contém faixas de usuários para exibir.")
    else:
        st.dataframe(
            distribuicao_usuarios[
                ["faixa_avaliacoes", "total_usuarios", "percentual_usuarios"]
            ],
            hide_index=True,
            width="stretch",
            column_config={
                "faixa_avaliacoes": st.column_config.TextColumn("Faixa"),
                "total_usuarios": st.column_config.NumberColumn(
                    "Usuários", format="localized"
                ),
                "percentual_usuarios": st.column_config.NumberColumn(
                    "Percentual", format="%.2f%%"
                ),
            },
        )
        st.caption("Percentual sobre o total de usuários.")
