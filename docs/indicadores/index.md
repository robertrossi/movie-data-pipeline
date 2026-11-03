# Indicadores de negócio

As 11 MARTs estão definidas nas consultas SQL numeradas de `sql/marts/`. Cada página abaixo combina a seção metodológica correspondente de `indicadores.md` com o conteúdo integral da consulta SQL de produção. O SQL foi inserido diretamente a partir do arquivo fonte, sem alterar sua lógica.

| Nº | Indicador | Granularidade | Pergunta de negócio |
|---|---|---|---|
| 01 | [Quantidade de filmes por ano de lançamento](indicador-01.md) | Ver descrição na consulta SQL. | Pergunta não registrada no comentário SQL. |
| 02 | [Nota média TMDB por gênero](indicador-02.md) | Ver descrição na consulta SQL. | Pergunta não registrada no comentário SQL. |
| 03 | [Quantidade de votos TMDB por gênero](indicador-03.md) | Ver descrição na consulta SQL. | Pergunta não registrada no comentário SQL. |
| 04 | [Distribuição das avaliações MovieLens](indicador-04.md) | Ver descrição na consulta SQL. | Pergunta não registrada no comentário SQL. |
| 05 | [Evolução da quantidade de avaliações MovieLens](indicador-05.md) | Ver descrição na consulta SQL. | Pergunta não registrada no comentário SQL. |
| 06 | [Evolução da nota média MovieLens](indicador-06.md) | Ver descrição na consulta SQL. | Pergunta não registrada no comentário SQL. |
| 07 | [Filmes com maior número de avaliações MovieLens](indicador-07.md) | Ver descrição na consulta SQL. | Pergunta não registrada no comentário SQL. |
| 08 | [Usuários mais ativos](indicador-08.md) | Ver descrição na consulta SQL. | Pergunta não registrada no comentário SQL. |
| 09 | [Distribuição da quantidade de avaliações por usuário](indicador-09.md) | Ver descrição na consulta SQL. | Pergunta não registrada no comentário SQL. |
| 10 | [Nota média MovieLens por gênero](indicador-10.md) | Ver descrição na consulta SQL. | Pergunta não registrada no comentário SQL. |
| 11 | [Filmes com maior número de avaliações MovieLens por ano](indicador-11.md) | Ver descrição na consulta SQL. | Pergunta não registrada no comentário SQL. |

## Ressalvas transversais registradas

- As notas TMDB e MovieLens são métricas distintas.
- Filmes multigênero participam de cada gênero associado; totais entre gêneros não são aditivos.
- Os resultados descrevem os registros disponíveis no dataset e na base de avaliações, não necessariamente o universo de filmes ou espectadores.
- A página do indicador 11 não atribui auditoria individual inexistente; apresenta apenas as evidências disponíveis no documento metodológico e no SQL.
