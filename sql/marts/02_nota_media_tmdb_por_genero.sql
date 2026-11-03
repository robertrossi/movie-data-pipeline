-- Pergunta de negócio: qual é a nota média TMDB dos filmes elegíveis em cada gênero?
-- Grão do resultado final: uma linha por gênero extraído.
-- CTE filmes_elegiveis: uma linha por filme (id), limitada a vote_count >= 50
-- e vote_average não nulo.
-- CTE generos_extraidos: uma linha por par filme (id) e gênero extraído.
-- Cada filme pode pertencer a vários gêneros e contribuir uma vez em cada grupo;
-- por isso, a contagem distinta de filmes e os grupos por gênero não são aditivos.
-- A média é simples entre as notas dos filmes elegíveis de cada gênero, sem ponderação
-- pelo número de votos TMDB.
WITH filmes_elegiveis AS (
    SELECT
        id,
        vote_average,
        genres
    FROM refined.filmes
    WHERE vote_count >= 50
      AND vote_average IS NOT NULL
),
generos_extraidos AS (
    SELECT
        id,
        vote_average,
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
    ROUND(AVG(vote_average), 2) AS nota_media_tmdb
FROM generos_extraidos
WHERE genero <> ''
GROUP BY genero
ORDER BY nota_media_tmdb DESC;