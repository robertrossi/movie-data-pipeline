# Indicador 08 — Usuários mais ativos

A seção metodológica abaixo reproduz as informações registradas para este indicador em `indicadores.md`.

## Definição e evidências metodológicas

- **Nome:** Most Active Users (MovieLens).
- **Objetivo de negócio:** Identificar os usuários que mais contribuíram com avaliações na base MovieLens.
- **Tabelas e colunas utilizadas:** `refined.avaliacoes`: `userId`, `movieId` e `rating`.
- **Granularidade:** Usuário (`userId`).
- **Regra de cálculo:** Contar as avaliações por usuário, calcular a média das notas e ordenar pela quantidade de avaliações em ordem decrescente.
- **Resultado exploratório:** O usuário 45811 lidera o ranking, com 18.276 avaliações e média 3,20. O segundo colocado possui 9.279 avaliações.
- **Classificação:** **Dá, mas...**
- **Justificativa da classificação:** A atividade pode ser medida diretamente pela quantidade de avaliações associadas a cada usuário.
- **Ressalvas:** Os identificadores são anônimos. O ranking representa a atividade histórica registrada na base, não atividade atual ou comportamento geral de espectadores. A média de notas é complementar e não interfere na classificação.

## Auditoria

[Auditoria metodológica do indicador 08](../auditorias/indicador-08-auditoria.md)

## Consulta SQL correspondente

Arquivo fonte: `sql/marts/08_usuarios_mais_ativos.sql`.

```sql
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
```
