-- Pergunta de negócio: quantos votos TMDB os filmes acumulam em cada gênero?
-- Grão do resultado final: uma linha por gênero extraído.
-- CTE filmes_elegiveis: uma linha por filme (id) com vote_count não nulo.
-- CTE generos_extraidos: uma linha por par filme (id) e gênero extraído.
-- Filmes multigênero contribuem com seu vote_count em cada gênero associado;
-- portanto, totais entre gêneros podem contar os mesmos votos mais de uma vez.
WITH filmes_elegiveis AS (
    SELECT
        id,
        vote_count,
        genres
    FROM refined.filmes
    WHERE vote_count IS NOT NULL
),
generos_extraidos AS (
    SELECT
        id,
        vote_count,
        TRIM(
            REPLACE(
                REPLACE(genero, '''name'': ''', ''),
                '''',
                ''
            )
        ) AS genero
    FROM filmes_elegiveis,
    UNNEST(
        REGEXP_EXTRACT_ALL(
            genres,
            '''name'': ''([^'']+)'''
        )
    ) AS t(genero)
)
SELECT
    genero,
    COUNT(DISTINCT id) AS total_filmes,
    SUM(vote_count) AS total_votos_tmdb
FROM generos_extraidos
WHERE genero <> ''
GROUP BY genero
ORDER BY total_votos_tmdb DESC;