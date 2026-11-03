-- Pergunta de negócio: qual é o volume, a quantidade de filmes e a nota média MovieLens por gênero?
-- Grão do resultado final: uma linha por gênero extraído.
-- CTE avaliacoes_por_filme: uma linha por movieId, com volume e média simples das avaliações.
-- CTE filmes_com_avaliacoes: uma linha por movieId após os vínculos; links tem no máximo
-- uma linha por movieId e filmes tem uma linha por id, então as junções não multiplicam
-- avaliações. movieIds diferentes podem apontar para o mesmo tmdbId, mas permanecem
-- filmes MovieLens distintos no grão desta análise.
-- CTE generos_extraidos: uma linha por par movieId e gênero. Filmes multigênero
-- contribuem em cada gênero, então totais entre gêneros não são aditivos.
-- A nota por gênero é média ponderada pelo total de avaliações de cada movieId,
-- evitando dar o mesmo peso a filmes com volumes de avaliação diferentes.
WITH avaliacoes_por_filme AS (
    SELECT
        movieId,
        COUNT(*) AS total_avaliacoes,
        AVG(rating) AS nota_media
    FROM refined.avaliacoes
    GROUP BY movieId
),
filmes_com_avaliacoes AS (
    SELECT
        a.movieId,
        a.total_avaliacoes,
        a.nota_media,
        f.id AS tmdbId,
        f.genres
    FROM avaliacoes_por_filme a
    INNER JOIN refined.links l
        ON a.movieId = l.movieId
    INNER JOIN refined.filmes f
        ON l.tmdbId = f.id
    WHERE l.tmdbId IS NOT NULL
),
generos_extraidos AS (
    SELECT
        movieId,
        total_avaliacoes,
        nota_media,
        TRIM(
            REPLACE(
                REPLACE(genero, '''name'': ''', ''),
                '''',
                ''
            )
        ) AS genero
    FROM filmes_com_avaliacoes,
    UNNEST(
        REGEXP_EXTRACT_ALL(
            genres,
            '''name'': ''([^'']+)'''
        )
    ) AS t(genero)
)
SELECT
    genero,
    COUNT(DISTINCT movieId) AS total_filmes,
    SUM(total_avaliacoes) AS total_avaliacoes,
    ROUND(
        SUM(nota_media * total_avaliacoes)
        / SUM(total_avaliacoes),
        3
    ) AS nota_media_movielens
FROM generos_extraidos
WHERE genero <> ''
GROUP BY genero
ORDER BY nota_media_movielens DESC;