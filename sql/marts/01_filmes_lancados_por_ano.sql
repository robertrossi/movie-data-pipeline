-- Pergunta de negócio: quantos filmes foram lançados em cada ano, entre 2000 e 2016?
-- Grão do resultado final: uma linha por ano de lançamento (release_year).
-- Fonte refined.filmes: cada linha representa um filme; COUNT(*) conta os filmes
-- com data de lançamento válida dentro do intervalo definido na consulta.
SELECT
    EXTRACT(YEAR FROM release_date) AS release_year,
    COUNT(*) AS total_movies
FROM refined.filmes
WHERE release_date IS NOT NULL
  AND release_date >= DATE '2000-01-01'
  AND release_date < DATE '2017-01-01'
GROUP BY
    EXTRACT(YEAR FROM release_date)
ORDER BY
    release_year;