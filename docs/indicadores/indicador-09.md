# Indicador 09 — Distribuição da quantidade de avaliações por usuário

A seção metodológica abaixo reproduz as informações registradas para este indicador em `indicadores.md`.

## Definição e evidências metodológicas

- **Nome:** Ratings per User Distribution (MovieLens).
- **Objetivo de negócio:** Entender a distribuição da atividade dos usuários e identificar a concentração de avaliações em diferentes níveis de participação.
- **Tabelas e colunas utilizadas:** `refined.avaliacoes`: `userId` e `rating`.
- **Granularidade:** Usuário, agrupado em faixas de quantidade de avaliações.
- **Regra de cálculo:** Contar as avaliações por usuário e classificar cada usuário nas seguintes faixas: 1; 2–10; 11–30; 31–100; 101–500; 501–1.000; mais de 1.000 avaliações.
- **Resultado exploratório:** Foram identificados 270.896 usuários. O mínimo foi uma avaliação, a média foi 96,07, a mediana foi 30 e o máximo foi 18.276 avaliações.
- **Distribuição observada:**
  - 1 avaliação: 5.084 usuários (1,88%).
  - 2 a 10: 38.704 usuários (14,29%).
  - 11 a 30: 93.016 usuários (34,34%).
  - 31 a 100: 70.515 usuários (26,03%).
  - 101 a 500: 54.125 usuários (19,98%).
  - 501 a 1.000: 6.950 usuários (2,57%).
  - Mais de 1.000: 2.502 usuários (0,92%).
- **Classificação:** **Dá, mas...**
- **Justificativa da classificação:** A distribuição é calculável e evidencia assimetria na participação dos usuários.
- **Ressalvas:** A média é superior à mediana devido à concentração de avaliações em usuários muito ativos. As faixas são agrupamentos analíticos definidos para facilitar a interpretação, não categorias oficiais do MovieLens. O percentual total apresentado pode chegar a 100,01% devido ao arredondamento.

## Auditoria

[Auditoria metodológica do indicador 09](../auditorias/indicador-09-auditoria.md)

## Consulta SQL correspondente

Arquivo fonte: `sql/marts/09_distribuicao_avaliacoes_por_usuario.sql`.

```sql
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
```
