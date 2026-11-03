# Indicador 03 — Quantidade de votos TMDB por gênero

A seção metodológica abaixo reproduz as informações registradas para este indicador em `indicadores.md`.

## Definição e evidências metodológicas

- **Nome:** TMDB Votes by Genre.
- **Objetivo de negócio:** Identificar o volume de votos registrados pelo TMDB para os filmes de cada gênero.
- **Tabelas e colunas utilizadas:** `refined.filmes`: `id`, `genres` e `vote_count`.
- **Granularidade:** Gênero.
- **Regra de cálculo:** Somar `vote_count` por gênero para os filmes com valor preenchido, incluindo filmes com zero votos.
- **Resultado exploratório:** Foram identificados 45.417 valores preenchidos em `vote_count`, três valores nulos e 2.895 filmes com zero votos. A soma dos votos registrados é 4.993.591.
- **Destaques:** Drama apresentou 1.954.388 votos; Action, 1.708.201; Comedy, 1.437.285; Adventure, 1.433.777; e Thriller, 1.433.111.
- **Classificação:** **Dá, mas...**
- **Justificativa da classificação:** A soma pode ser calculada, mas filmes multigênero contribuem integralmente para cada gênero.
- **Ressalvas:** Os totais entre gêneros não são aditivos. O indicador mede o volume de votos registrado na base TMDB para os filmes disponíveis, não a popularidade mundial dos gêneros.

## Auditoria

[Auditoria metodológica do indicador 03](../auditorias/indicador-03-auditoria.md)

## Consulta SQL correspondente

Arquivo fonte: `sql/marts/03_quantidade_votos_tmdb_por_genero.sql`.

```sql
-- Pergunta de negócio: quantos votos TMDB os filmes acumulam em cada gênero?
-- Grão do resultado final: uma linha por gênero extraído.
-- CTE filmes_elegiveis: uma linha por filme (id) com vote_count não nulo.
-- CTE generos_extraidos: uma linha por par filme (id) e gênero extraído.
-- Filmes multigênero contribuem com seu vote_count em cada gênero associado;
-- portanto, totais entre gêneros podem contar os mesmos votos mais de uma vez.
WITH filmes_elegiveis AS (
    SELECT
        id,
        vote_count,
        genres
    FROM refined.filmes
    WHERE vote_count IS NOT NULL
),
generos_extraidos AS (
    SELECT
        id,
        vote_count,
        TRIM(
            REPLACE(
                REPLACE(genero, '''name'': ''', ''),
                '''',
                ''
            )
        ) AS genero
    FROM filmes_elegiveis,
    UNNEST(
        REGEXP_EXTRACT_ALL(
            genres,
            '''name'': ''([^'']+)'''
        )
    ) AS t(genero)
)
SELECT
    genero,
    COUNT(DISTINCT id) AS total_filmes,
    SUM(vote_count) AS total_votos_tmdb
FROM generos_extraidos
WHERE genero <> ''
GROUP BY genero
ORDER BY total_votos_tmdb DESC;
```
