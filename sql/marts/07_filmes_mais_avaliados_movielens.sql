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