# Indicador 06 — Evolução da nota média MovieLens

A seção metodológica abaixo reproduz as informações registradas para este indicador em `indicadores.md`.

## Definição e evidências metodológicas

- **Nome:** MovieLens Average Rating Over Time.
- **Objetivo de negócio:** Acompanhar a evolução da nota média das avaliações submetidas pelos usuários ao longo do tempo.
- **Tabelas e colunas utilizadas:** `refined.avaliacoes`: `timestamp`, `rating`, `userId`.
- **Granularidade:** Ano de registro da avaliação.
- **Regra de cálculo:** Calcular a média de `rating` por ano de registro da avaliação.
- **Resultado exploratório:** Entre 1996 e 2017, as médias anuais variaram aproximadamente de 3,43 a 3,63. Em 1995, a média foi 3,75, mas baseada em apenas quatro avaliações.
- **Destaques:** A menor média observada no período principal foi 3,427 em 2004; a maior foi 3,626 em 2013.
- **Classificação:** **Dá, mas...**
- **Justificativa da classificação:** A média anual é calculável, mas representa as avaliações submetidas naquele ano, e não a qualidade dos filmes lançados naquele ano.
- **Ressalvas:** Recomenda-se utilizar 1996–2016 como período principal. 1995 possui volume insuficiente e 2017 é incompleto. Diferenças anuais não devem ser interpretadas automaticamente como mudanças na qualidade do cinema.

## Auditoria

[Auditoria metodológica do indicador 06](../auditorias/indicador-06-auditoria.md)

## Consulta SQL correspondente

Arquivo fonte: `sql/marts/06_nota_media_movielens_ao_longo_do_tempo.sql`.

```sql
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
```
