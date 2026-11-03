-- Pergunta de negócio: quantas avaliações MovieLens foram registradas em cada ano?
-- Grão do resultado final: uma linha por ano UTC de avaliação, derivado do timestamp Unix.
-- Cada linha de refined.avaliacoes representa uma avaliação e é contada no seu ano.
SELECT
    EXTRACT(
        YEAR FROM TO_TIMESTAMP(timestamp) AT TIME ZONE 'UTC'
    ) AS ano_avaliacao,
    COUNT(*) AS total_avaliacoes
FROM refined.avaliacoes
GROUP BY
    EXTRACT(YEAR FROM TO_TIMESTAMP(timestamp) AT TIME ZONE 'UTC')
ORDER BY
    ano_avaliacao;
