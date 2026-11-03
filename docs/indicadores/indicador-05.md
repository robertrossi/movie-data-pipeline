# Indicador 05 — Evolução da quantidade de avaliações MovieLens

A seção metodológica abaixo reproduz as informações registradas para este indicador em `indicadores.md`.

## Definição e evidências metodológicas

- **Nome:** MovieLens Ratings Over Time.
- **Objetivo de negócio:** Acompanhar a evolução anual do volume de avaliações registradas pelos usuários MovieLens.
- **Tabelas e colunas utilizadas:** `refined.avaliacoes`: `timestamp`, `userId` e `rating`.
- **Granularidade:** Ano de registro da avaliação.
- **Regra de cálculo:** Converter o timestamp Unix para data e contar as avaliações por ano.
- **Resultado exploratório:** Foram analisadas 26.024.289 avaliações, sem timestamps nulos. O período vai de janeiro de 1995 a agosto de 2017.
- **Destaques:** 1996 registrou 1.733.473 avaliações; 2000, 2.034.072; 2015, 1.913.997; e 2016, 2.095.272.
- **Classificação:** **Dá, mas...**
- **Justificativa da classificação:** O volume anual é calculável, mas varia conforme a quantidade de usuários ativos e a intensidade de participação de cada usuário.
- **Ressalvas:** 1995 é um período residual, com apenas quatro avaliações. 2017 está incompleto, pois os registros terminam em agosto. O aumento do volume não deve ser interpretado isoladamente como crescimento de popularidade dos filmes.

## Auditoria

[Auditoria metodológica do indicador 05](../auditorias/indicador-05-auditoria.md)

## Consulta SQL correspondente

Arquivo fonte: `sql/marts/05_avaliacoes_movielens_ao_longo_do_tempo.sql`.

```sql
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
```
