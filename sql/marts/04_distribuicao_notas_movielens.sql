-- Pergunta de negócio: como as avaliações MovieLens se distribuem por nota?
-- Grão do resultado final: uma linha por valor de rating.
-- Cada linha de refined.avaliacoes representa uma avaliação; percentual usa o total
-- de avaliações da tabela como denominador.
SELECT
    rating,
    COUNT(*) AS total_avaliacoes,
    ROUND(
        COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (),
        2
    ) AS percentual
FROM refined.avaliacoes
GROUP BY rating
ORDER BY rating;