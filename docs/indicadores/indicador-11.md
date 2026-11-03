# Indicador 11 — Filmes com maior número de avaliações MovieLens por ano

A seção metodológica abaixo reproduz as informações registradas para este indicador em `indicadores.md`.

## Definição e evidências metodológicas

- **Nome:** Most Rated Movies by Year (MovieLens).
- **Objetivo de negócio:** Comparar, em cada ano, os filmes que concentraram mais avaliações submetidas na base MovieLens.
- **Fontes:** `refined.avaliacoes` (`movieId`, `rating`, `timestamp`), `refined.links` (`movieId`, `tmdbId`) e `refined.filmes` (`id`, `title`).
- **Relacionamentos:** Agregar as avaliações antes de relacionar `movieId` a `links.movieId` e `links.tmdbId` a `filmes.id`. As junções são `LEFT JOIN`; ausência de vínculo ou metadado não elimina o par ano/filme.
- **Grão:** Uma linha por combinação de ano UTC de avaliação e `movieId` MovieLens. O mesmo filme aparece em anos distintos quando recebe avaliações em anos distintos. `tmdbId` e título são atributos descritivos e não definem o grão.
- **Colunas:** `ano_avaliacao` é o ano UTC extraído do timestamp Unix; `movieId` identifica o filme na base MovieLens; `tmdbId` e `titulo` vêm dos metadados TMDB e podem ser nulos; `total_avaliacoes` conta os ratings do par ano/filme; `nota_media_movielens` é a média aritmética dos ratings MovieLens do par, sem arredondamento na MART; `ranking` é a posição anual.
- **Regra de cálculo:** Converter `timestamp` com `TO_TIMESTAMP(timestamp) AT TIME ZONE 'UTC'`, agrupar por ano e `movieId`, contar as avaliações e calcular `AVG(rating)`. O ranking usa `ROW_NUMBER()` particionado por ano, por `total_avaliacoes` decrescente e `movieId` crescente como desempate determinístico.
- **Escopo:** A MART contém todos os pares filme/ano com avaliações, e não somente o Top 20. A interface pode aplicar um corte para apresentação sem perder a posição relativa ou o histórico completo.
- **Limitações:** O volume mede avaliações MovieLens submetidas em cada ano UTC; não é o ano de lançamento, a popularidade mundial ou uma medida de qualidade. A média reflete os ratings observados naquele par e pode ter amostras pequenas. IDs sem correspondência TMDB continuam na MART com metadados nulos. Diferentes `movieId`s permanecem separados mesmo que apontem ao mesmo `tmdbId`.

## Auditoria

Não há auditoria individual para este indicador em `docs/auditorias/`; esta página usa as evidências de `indicadores.md`, os comentários e a consulta SQL correspondente.

## Consulta SQL correspondente

Arquivo fonte: `sql/marts/11_filmes_mais_avaliados_movielens_por_ano.sql`.

```sql
-- Pergunta de negócio: quais filmes receberam mais avaliações MovieLens em cada ano?
-- Grão do resultado: uma linha por ano UTC de avaliação e movieId.
-- A nota média é a média simples das avaliações MovieLens do filme naquele ano,
-- sem arredondamento. Os metadados TMDB são descritivos e podem estar ausentes.
-- refined.links.movieId e refined.filmes.id preservam o grão nas junções.
WITH avaliacoes_por_ano_filme AS (
    SELECT
        EXTRACT(
            YEAR FROM TO_TIMESTAMP(timestamp) AT TIME ZONE 'UTC'
        ) AS ano_avaliacao,
        movieId,
        COUNT(*) AS total_avaliacoes,
        AVG(rating) AS nota_media_movielens
    FROM refined.avaliacoes
    GROUP BY
        EXTRACT(YEAR FROM TO_TIMESTAMP(timestamp) AT TIME ZONE 'UTC'),
        movieId
),
ranking_anual AS (
    SELECT
        ano_avaliacao,
        movieId,
        total_avaliacoes,
        nota_media_movielens,
        ROW_NUMBER() OVER (
            PARTITION BY ano_avaliacao
            ORDER BY total_avaliacoes DESC, movieId ASC
        ) AS ranking
    FROM avaliacoes_por_ano_filme
)
SELECT
    r.ano_avaliacao,
    r.movieId,
    l.tmdbId,
    f.title AS titulo,
    r.total_avaliacoes,
    r.nota_media_movielens,
    r.ranking
FROM ranking_anual r
LEFT JOIN refined.links l
    ON r.movieId = l.movieId
LEFT JOIN refined.filmes f
    ON l.tmdbId = f.id
ORDER BY
    r.ano_avaliacao,
    r.ranking;
```
