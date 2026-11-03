"""Gera uma versao HTML estatica do dashboard Cinema Analytics."""

from __future__ import annotations

from datetime import datetime
from html import escape
from pathlib import Path
from typing import Callable

import pandas as pd
import plotly.graph_objects as go

import painel

_ARQUIVO_SAIDA = Path(__file__).resolve().with_name("relatorio.html")
_GRAFICOS: list[str] = []


def _intervalo_padrao(
    dados: pd.DataFrame,
    coluna: str,
    preferido: tuple[int, int] | None = None,
) -> tuple[int, int] | None:
    """Reproduz o valor inicial do seletor anual correspondente no dashboard."""
    if dados.empty:
        return None
    menor = int(dados[coluna].min())
    maior = int(dados[coluna].max())
    if menor == maior:
        return menor, maior
    if preferido is not None:
        inicio = max(menor, preferido[0])
        fim = min(maior, preferido[1])
        if inicio <= fim:
            return inicio, fim
    return menor, maior


def _grafico(
    dados: pd.DataFrame,
    criar: Callable[..., go.Figure],
    *,
    primeiro: bool = False,
    argumentos: dict[str, object] | None = None,
) -> str:
    """Converte uma figura existente em HTML usando um ID estável."""
    div_id = f"g{len(_GRAFICOS) + 1:02d}"
    _GRAFICOS.append(div_id)
    figura = criar(dados, **(argumentos or {}))
    altura_atual = int(figura.layout.height or 0)
    figura.update_layout(height=max(altura_atual, 480), autosize=True)
    return figura.to_html(
        full_html=False,
        include_plotlyjs="cdn" if primeiro else False,
        div_id=div_id,
    )


def _cartao_grafico(titulo: str, grafico: str) -> str:
    return f'<article class="chart-card"><h3>{escape(titulo)}</h3>{grafico}</article>'


def _renderizar_relatorio() -> str:
    """Consulta as MARTs e compõe as quatro seções do dashboard."""
    _GRAFICOS.clear()
    primeiro_grafico = True

    def adicionar(
        dados: pd.DataFrame,
        criar: Callable[..., go.Figure],
        *,
        argumentos: dict[str, object] | None = None,
    ) -> str:
        nonlocal primeiro_grafico
        conteudo = _grafico(
            dados,
            criar,
            primeiro=primeiro_grafico,
            argumentos=argumentos,
        )
        primeiro_grafico = False
        return conteudo

    filmes_ano_base = painel.obter_filmes_por_ano()
    intervalo_filmes = _intervalo_padrao(filmes_ano_base, "release_year", (2000, 2016))
    filmes_ano = (
        painel.obter_filmes_por_ano(
            ano_inicio=intervalo_filmes[0], ano_fim=intervalo_filmes[1]
        )
        if intervalo_filmes is not None
        else filmes_ano_base
    )

    avaliacoes_base = painel.obter_avaliacoes_por_ano()
    intervalo_avaliacoes = _intervalo_padrao(avaliacoes_base, "ano_avaliacao")
    if intervalo_avaliacoes is None:
        avaliacoes_ano = avaliacoes_base
        nota_ano = painel.obter_nota_media_por_ano()
    else:
        avaliacoes_ano = painel.obter_avaliacoes_por_ano(
            ano_inicio=intervalo_avaliacoes[0], ano_fim=intervalo_avaliacoes[1]
        )
        nota_ano = painel.obter_nota_media_por_ano(
            ano_inicio=intervalo_avaliacoes[0], ano_fim=intervalo_avaliacoes[1]
        )

    distribuicao_notas = painel.obter_distribuicao_notas()
    visao_geral = "".join(
        (
            _cartao_grafico(
                "Filmes por ano de lançamento",
                adicionar(filmes_ano, painel.criar_grafico_filmes_por_ano),
            ),
            _cartao_grafico(
                "Distribuição das avaliações MovieLens",
                adicionar(distribuicao_notas, painel.criar_grafico_distribuicao_notas),
            ),
            _cartao_grafico(
                "Avaliações MovieLens por ano",
                adicionar(avaliacoes_ano, painel.criar_grafico_avaliacoes_por_ano),
            ),
            _cartao_grafico(
                "Nota média MovieLens por ano",
                adicionar(nota_ano, painel.criar_grafico_nota_media_por_ano),
            ),
        )
    )

    nota_tmdb = painel.obter_nota_tmdb_por_genero()
    votos_tmdb = painel.obter_votos_tmdb_por_genero()
    nota_movielens = painel.obter_nota_movielens_por_genero()
    generos = "".join(
        (
            _cartao_grafico(
                "Nota média TMDB por gênero",
                adicionar(nota_tmdb, painel.criar_grafico_nota_tmdb_por_genero),
            ),
            _cartao_grafico(
                "Votos TMDB por gênero",
                adicionar(votos_tmdb, painel.criar_grafico_votos_tmdb_por_genero),
            ),
            _cartao_grafico(
                "Nota média MovieLens por gênero",
                adicionar(
                    nota_movielens, painel.criar_grafico_nota_movielens_por_genero
                ),
            ),
        )
    )

    anos_ranking_df = painel.obter_anos_ranking_anual()
    anos_ranking = (
        sorted({int(ano) for ano in anos_ranking_df["ano_avaliacao"].dropna()})
        if not anos_ranking_df.empty
        else []
    )
    filmes_ranking = ""
    comparacao = ""
    destaque = '<p class="empty-state">Ranking anual indisponível.</p>'
    if anos_ranking:
        ano_ranking = anos_ranking[-1]
        ranking_anual = painel.obter_filmes_mais_avaliados_no_ano(
            ano=ano_ranking, top_n=20
        )
        filmes_ranking = _cartao_grafico(
            f"Top 20 filmes mais avaliados em {ano_ranking}",
            adicionar(ranking_anual, painel.criar_grafico_filmes_mais_avaliados_no_ano),
        )

        filme_top = painel.obter_filme_mais_avaliado_no_ano(ano_ranking)
        if not filme_top.empty:
            linha = filme_top.iloc[0]
            titulo = linha["titulo"]
            if pd.isna(titulo) or not str(titulo).strip():
                titulo = f"Filme (movieId {int(linha['movieId'])})"
            media = linha["nota_media_movielens"]
            media_texto = f"{float(media):.2f}" if pd.notna(media) else "—"
            destaque = (
                '<div class="highlight-card">'
                '<span class="eyebrow">Destaque do ano</span>'
                f"<h3>{escape(str(titulo))}</h3>"
                f"<p>{int(linha['total_avaliacoes']):,} avaliações · "
                f"Nota média MovieLens {media_texto}</p></div>"
            )

    ranking_historico = painel.obter_filmes_mais_avaliados(top_n=20)
    grafico_historico = _cartao_grafico(
        "Top 20 histórico",
        adicionar(ranking_historico, painel.criar_grafico_filmes_mais_avaliados),
    )

    if len(anos_ranking) >= 2:
        ano_a, ano_b = anos_ranking[-2:]
        comparacao_df = painel.obter_comparacao_ranking_anual(
            ano_a=ano_a, ano_b=ano_b, top_n=20
        )
        comparacao = _cartao_grafico(
            f"Comparação do Top 20: {ano_a} e {ano_b}",
            adicionar(
                comparacao_df,
                painel.criar_grafico_comparacao_ranking_anual,
                argumentos={"ano_a": ano_a, "ano_b": ano_b},
            ),
        )

    series = "".join(
        (
            _cartao_grafico(
                "Avaliações MovieLens por ano",
                adicionar(avaliacoes_ano, painel.criar_grafico_avaliacoes_por_ano),
            ),
            _cartao_grafico(
                "Nota média MovieLens por ano",
                adicionar(nota_ano, painel.criar_grafico_nota_media_por_ano),
            ),
        )
    )

    filmes = (
        f'<div class="feature-grid">{filmes_ranking}{destaque}</div>'
        f'<div class="chart-grid chart-grid--secondary">'
        f"{grafico_historico}{comparacao}</div>"
        '<h3 class="section-subtitle">Evolução das avaliações</h3>'
        f'<div class="chart-grid">{series}</div>'
    )

    usuarios_ativos = painel.obter_usuarios_mais_ativos()
    distribuicao_usuarios = painel.obter_distribuicao_usuarios()
    tabela_usuarios = distribuicao_usuarios[
        ["faixa_avaliacoes", "total_usuarios", "percentual_usuarios"]
    ].to_html(
        index=False,
        border=0,
        classes="data-table",
        formatters={"percentual_usuarios": lambda valor: f"{valor:.2f}%"},
        escape=True,
    )
    usuarios = "".join(
        (
            _cartao_grafico(
                "Usuários mais ativos",
                adicionar(usuarios_ativos, painel.criar_grafico_usuarios_mais_ativos),
            ),
            _cartao_grafico(
                "Distribuição da atividade dos usuários",
                adicionar(
                    distribuicao_usuarios,
                    painel.criar_grafico_distribuicao_usuarios,
                ),
            ),
            '<article class="table-card table-card-wide">'
            "<h3>Usuários por faixa de avaliações</h3>"
            f"{tabela_usuarios}</article>",
        )
    )

    geracao = datetime.now().astimezone().strftime("%d/%m/%Y %H:%M")
    return f"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light">
  <title>Cinema Analytics — Relatório</title>
  <style>
    :root {{ color-scheme: light; --bg:#F5F7FA; --surface:#FFFFFF; --teal:#2F6B7C;
      --navy:#17324D; --ink:#25364A; --muted:#66788A; --line:#E5EBF1; }}
    * {{ box-sizing: border-box; }}
    body {{ margin:0; background:var(--bg); color:var(--ink);
      font-family:Arial, sans-serif; }}
    main {{ width:min(1720px, calc(100% - 40px)); margin:24px auto 56px; }}
    .cinema-banner {{ position:relative; isolation:isolate; overflow:hidden;
      min-height:176px; margin:0 0 28px; padding:36px clamp(40px, 7vw, 84px);
      border:1px solid rgba(229,235,241,.18); border-radius:16px;
      background:linear-gradient(112deg,#17324D,#243544 68%,#224B57);
      box-shadow:0 12px 30px rgba(23,50,77,.12); }}
    .cinema-banner::after {{ position:absolute; z-index:-1; inset:0; content:"";
      background-image:radial-gradient(rgba(255,255,255,.2) .55px,transparent .8px),
        repeating-linear-gradient(115deg,transparent 0 38px,rgba(255,255,255,.025) 39px 40px);
      background-size:5px 5px,auto; opacity:.2; }}
    .perforation {{ position:absolute; top:14px; bottom:14px; width:13px;
      background:radial-gradient(ellipse 4px 6px at center,rgba(218,229,235,.58) 0 72%,transparent 78%) center top/13px 25px repeat-y;
      opacity:.62; }}
    .perforation.left {{ left:12px; }} .perforation.right {{ right:12px; }}
    .eyebrow {{ margin:0 0 8px; color:#9ac3ca; font-size:11px;
      font-weight:700; letter-spacing:.16em; text-transform:uppercase; }}
    .cinema-banner h1 {{ margin:0; color:#fff; font-size:clamp(30px,4vw,44px);
      letter-spacing:-.035em; line-height:1.1; }}
    .cinema-banner > p:not(.eyebrow) {{ margin:10px 0 0; color:#FFFFFF;
      font-size:16px; line-height:1.5; }}
    .accent {{ position:absolute; right:7%; bottom:0; width:22%; height:3px;
      border-radius:3px 3px 0 0; background:var(--teal); }}
    section.report-section {{ margin:0 0 36px; }}
    h2 {{ margin:0 0 16px; color:var(--navy); font-size:24px; }}
    .section-subtitle {{ margin:28px 0 14px; color:var(--navy); font-size:19px; }}
    .chart-grid {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:20px; }}
    .feature-grid {{ display:grid; grid-template-columns:minmax(0,1.85fr) minmax(260px,1fr);
      align-items:stretch; gap:20px; }}
    .genre-grid {{ grid-template-columns:repeat(6,minmax(0,1fr)); }}
    .genre-grid > .chart-card:nth-child(-n+2) {{ grid-column:span 3; }}
    .genre-grid > .chart-card:nth-child(3) {{ grid-column:2/span 4; }}
    .chart-grid--secondary {{ margin-top:20px; }}
    .chart-card,.table-card,.highlight-card {{ min-width:0;
      border:1px solid var(--line); border-radius:12px; background:var(--surface);
      box-shadow:0 1px 5px rgba(23,50,77,.035); }}
    .chart-card {{ overflow:visible; padding:10px 10px 2px; }}
    .chart-card h3,.table-card h3 {{ margin:4px 8px 0; color:var(--navy); font-size:16px; }}
    .chart-card .plotly-graph-div {{ width:100% !important; min-width:0; }}
    .highlight-card {{ margin:14px 0 18px; padding:18px 22px; }}
    .feature-grid .highlight-card {{ display:flex; flex-direction:column; justify-content:center;
      margin:0; }}
    .highlight-card h3 {{ margin:4px 0; color:var(--navy); }}
    .highlight-card p {{ margin:0; color:var(--muted); }}
    .table-card {{ padding:18px; }}
    .table-card-wide {{ grid-column:1 / -1; }}
    .data-table {{ width:100%; margin-top:12px; border-collapse:collapse; }}
    .data-table th,.data-table td {{ padding:10px 12px; border-bottom:1px solid var(--line);
      text-align:left; }}
    .data-table th {{ color:var(--muted); font-size:13px; }}
    .empty-state {{ padding:20px; border-radius:10px; background:var(--surface); color:var(--muted); }}
    footer {{ padding-top:18px; border-top:1px solid var(--line); color:var(--muted);
      font-size:13px; text-align:right; }}
    @media (max-width:760px) {{
      main {{ width:calc(100% - 28px); margin-top:14px; }}
      .chart-grid,.feature-grid {{ grid-template-columns:1fr; gap:12px; }}
      .genre-grid > .chart-card:nth-child(-n+3) {{ grid-column:auto; }}
      .table-card-wide {{ grid-column:auto; }}
      .cinema-banner {{ min-height:150px; margin-bottom:22px; padding:28px 38px; border-radius:12px; }}
      .perforation.left {{ left:8px; }} .perforation.right {{ right:8px; }}
      h2 {{ font-size:21px; }}
    }}
  </style>
</head>
<body>
  <main>
    <header class="cinema-banner" aria-label="Cinema Analytics">
      <span class="perforation left" aria-hidden="true"></span>
      <span class="perforation right" aria-hidden="true"></span>
      <p class="eyebrow">Movie Data · Film Analytics</p>
      <h1>Cinema Analytics</h1>
      <p>Uma exploração analítica do universo cinematográfico</p>
      <span class="accent" aria-hidden="true"></span>
    </header>
    <section class="report-section"><h2>Visão geral</h2>
      <div class="chart-grid">{visao_geral}</div></section>
    <section class="report-section"><h2>Gêneros</h2>
      <div class="chart-grid genre-grid">{generos}</div></section>
    <section class="report-section"><h2>Filmes e avaliações</h2>{filmes}</section>
    <section class="report-section"><h2>Usuários</h2>
      <div class="chart-grid">{usuarios}</div></section>
    <footer>Dados de {escape(geracao)}</footer>
  </main>
</body>
</html>"""


def main() -> None:
    """Gera o arquivo HTML na raiz do projeto."""
    conteudo = _renderizar_relatorio()
    _ARQUIVO_SAIDA.write_text(conteudo, encoding="utf-8", newline="\n")
    tamanho_kb = _ARQUIVO_SAIDA.stat().st_size / 1024
    print(
        f"Relatório gerado: {_ARQUIVO_SAIDA} "
        f"({tamanho_kb:.1f} KB; {len(_GRAFICOS)} gráficos)."
    )


if __name__ == "__main__":
    main()
