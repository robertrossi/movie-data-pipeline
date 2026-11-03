# Indicador 02 — Nota média TMDB por gênero

A seção metodológica abaixo reproduz as informações registradas para este indicador em `indicadores.md`.

## Definição e evidências metodológicas

- **Nome:** Average TMDB Rating by Genre.
- **Objetivo de negócio:** Comparar as notas médias registradas pelo TMDB entre os gêneros cinematográficos.
- **Tabelas e colunas utilizadas:** `refined.filmes`: `id`, `genres`, `vote_average` e `vote_count`.
- **Granularidade:** Gênero.
- **Regra de cálculo:** Calcular a média simples de `vote_average` por gênero, considerando filmes com pelo menos 50 votos TMDB e gênero identificável.
- **Resultado exploratório:** Foram identificados 9.137 filmes com pelo menos 50 votos. Desses, 9.131 possuem gênero identificável. Foram extraídas 23.044 associações entre filmes e gêneros, distribuídas em 20 gêneros.
- **Destaques:** Documentary apresentou média 7,26; History, 6,91; War, 6,88; Drama, 6,65; e Horror, 5,83.
- **Classificação:** **Dá, mas...**
- **Justificativa da classificação:** A média é calculável, mas cada filme recebe o mesmo peso, independentemente da quantidade de votos. Filmes multigênero participam integralmente de cada categoria.
- **Ressalvas:** Os grupos não são exclusivos. O gênero Foreign possui apenas três filmes elegíveis, portanto sua média deve ser interpretada com cautela. O filtro de 50 votos reduz a influência de filmes com pouca participação, mas não torna a amostra representativa de todos os filmes.

## Auditoria

[Auditoria metodológica do indicador 02](../auditorias/indicador-02-auditoria.md)

## Consulta SQL correspondente

Arquivo fonte: `sql/marts/02_nota_media_tmdb_por_genero.sql`.

```sql
-- Pergunta de negócio: qual é a nota média TMDB dos filmes elegíveis em cada gênero?
-- Grão do resultado final: uma linha por gênero extraído.
-- CTE filmes_elegiveis: uma linha por filme (id), limitada a vote_count >= 50
-- e vote_average não nulo.
-- CTE generos_extraidos: uma linha por par filme (id) e gênero extraído.
-- Cada filme pode pertencer a vários gêneros e contribuir uma vez em cada grupo;
-- por isso, a contagem distinta de filmes e os grupos por gênero não são aditivos.
-- A média é simples entre as notas dos filmes elegíveis de cada gênero, sem ponderação
-- pelo número de votos TMDB.
WITH filmes_elegiveis AS (
    SELECT
        id,
        vote_average,
        genres
    FROM refined.filmes
    WHERE vote_count >= 50
      AND vote_average IS NOT NULL
),
generos_extraidos AS (
    SELECT
        id,
        vote_average,
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
    ROUND(AVG(vote_average), 2) AS nota_media_tmdb
FROM generos_extraidos
WHERE genero <> ''
GROUP BY genero
ORDER BY nota_media_tmdb DESC;
```
