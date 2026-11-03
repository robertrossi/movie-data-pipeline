-- Pergunta de negócio: qual foi o volume e a nota média das avaliações em cada ano?
-- Grão do resultado final: uma linha por ano UTC de avaliação, derivado do timestamp Unix.
-- Cada linha de refined.avaliacoes é uma avaliação; AVG(rating) é a média simples
-- de todas as avaliações do ano, e total_avaliacoes informa o respectivo volume.
SELECT
    EXTRACT(
        YEAR FROM TO_TIMESTAMP(timestamp) AT TIME ZONE 'UTC'
    ) AS ano_avaliacao,
    COUNT(*) AS total_avaliacoes,
    ROUND(AVG(rating), 3) AS nota_media
FROM refined.avaliacoes
GROUP BY
    EXTRACT(YEAR FROM TO_TIMESTAMP(timestamp) AT TIME ZONE 'UTC')
ORDER BY
    ano_avaliacao;
