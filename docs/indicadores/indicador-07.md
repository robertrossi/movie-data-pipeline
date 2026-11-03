# Indicador 07 — Filmes com maior número de avaliações MovieLens

A seção metodológica abaixo reproduz as informações registradas para este indicador em `indicadores.md`.

## Definição e evidências metodológicas

- **Nome:** Most Rated Movies (MovieLens).
- **Objetivo de negócio:** Identificar os filmes que concentram o maior volume de avaliações na base MovieLens.
- **Tabelas e colunas utilizadas:** `refined.avaliacoes`: `movieId` e `rating`; `refined.links`: `movieId` e `tmdbId`; `refined.filmes`: `id` e `title`.
- **Relacionamentos necessários:** Relacionar `avaliacoes.movieId` a `links.movieId` e, quando houver correspondência, `links.tmdbId` a `filmes.id`.
- **Granularidade:** `movieId` MovieLens.
- **Regra de cálculo:** Contar as avaliações por `movieId`, ordenar em ordem decrescente e apresentar a média das notas como informação complementar.
- **Resultado exploratório:** Forrest Gump liderou o ranking, com 91.921 avaliações e média 4,05. Em seguida aparecem The Shawshank Redemption, com 91.082 avaliações e média 4,43, e Pulp Fiction, com 87.901 avaliações e média 4,17.
- **Classificação:** **Dá, mas...**
- **Justificativa da classificação:** A contagem é calculável por `movieId`, e o enriquecimento com título TMDB funcionou para os 20 primeiros registros apresentados.
- **Ressalvas:** A ordenação é baseada na quantidade de avaliações, não na média. Diferentes `movieId`s não devem ser consolidados automaticamente, mesmo quando compartilham o mesmo `tmdbId`. O indicador mede volume de avaliações na base, não popularidade mundial.

## Auditoria

[Auditoria metodológica do indicador 07](../auditorias/indicador-07-auditoria.md)

## Consulta SQL correspondente

Arquivo fonte: `sql/marts/07_filmes_mais_avaliados_movielens.sql`.

```sql
-- Pergunta de negócio: quais filmes têm mais avaliações MovieLens e quais são suas notas?
-- Grão do resultado final: uma linha por movieId, ordenada pelo total de avaliações;
-- o resultado é limitado aos 20 primeiros.
-- CTE avaliacoes_por_filme: uma linha por movieId, com volume e média das avaliações.
-- refined.links: no máximo uma linha por movieId; refined.filmes: uma linha por id.
-- As junções usam essas chaves únicas, preservando uma linha por movieId e não
-- multiplicando o volume nem alterando a média calculada na CTE. tmdbId repetido
-- entre movieIds não causa multiplicação porque a ligação parte de movieId.
WITH avaliacoes_por_filme AS (
    SELECT
        movieId,
        COUNT(*) AS total_avaliacoes,
        ROUND(AVG(rating), 2) AS nota_media_movielens
    FROM refined.avaliacoes
    GROUP BY movieId
)
SELECT
    a.movieId,
    l.tmdbId,
    f.title AS titulo,
    a.total_avaliacoes,
    a.nota_media_movielens
FROM avaliacoes_por_filme a
LEFT JOIN refined.links l
    ON a.movieId = l.movieId
LEFT JOIN refined.filmes f
    ON l.tmdbId = f.id
ORDER BY
    a.total_avaliacoes DESC
LIMIT 20;
```
