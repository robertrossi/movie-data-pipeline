-- Pergunta de negócio: quais usuários fizeram mais avaliações e qual sua nota média?
-- Grão do resultado final: uma linha por userId, ordenada pelo volume e limitada aos 20.
-- Cada linha de refined.avaliacoes é uma avaliação; as métricas são agregadas por usuário.
SELECT
    userId,
    COUNT(*) AS total_avaliacoes,
    ROUND(AVG(rating), 2) AS nota_media_usuario
FROM refined.avaliacoes
GROUP BY
    userId
ORDER BY
    total_avaliacoes DESC
LIMIT 20;