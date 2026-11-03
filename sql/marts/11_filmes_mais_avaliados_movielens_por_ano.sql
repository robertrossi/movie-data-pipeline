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
