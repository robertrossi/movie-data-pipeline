-- Pergunta de negócio: como os usuários se distribuem por faixa de quantidade de avaliações?
-- Grão do resultado final: uma linha por faixa_avaliacoes.
-- CTE avaliacoes_por_usuario: uma linha por userId, com sua quantidade de avaliações.
-- CTE usuarios_classificados: uma linha por userId, com a faixa atribuída à quantidade.
-- Cada usuário entra em uma única faixa; percentual usa o total de usuários classificados.
WITH avaliacoes_por_usuario AS (
    SELECT
        userId,
        COUNT(*) AS total_avaliacoes
    FROM refined.avaliacoes
    GROUP BY userId
),
usuarios_classificados AS (
    SELECT
        userId,
        total_avaliacoes,
        CASE
            WHEN total_avaliacoes = 1 THEN '1'
            WHEN total_avaliacoes BETWEEN 2 AND 10 THEN '2-10'
            WHEN total_avaliacoes BETWEEN 11 AND 30 THEN '11-30'
            WHEN total_avaliacoes BETWEEN 31 AND 100 THEN '31-100'
            WHEN total_avaliacoes BETWEEN 101 AND 500 THEN '101-500'
            WHEN total_avaliacoes BETWEEN 501 AND 1000 THEN '501-1000'
            ELSE '>1000'
        END AS faixa_avaliacoes
    FROM avaliacoes_por_usuario
)
SELECT
    faixa_avaliacoes,
    COUNT(*) AS total_usuarios,
    ROUND(
        COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (),
        2
    ) AS percentual_usuarios
FROM usuarios_classificados
GROUP BY faixa_avaliacoes
ORDER BY
    MIN(total_avaliacoes);
