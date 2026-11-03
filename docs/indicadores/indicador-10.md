# Indicador 10 — Nota média MovieLens por gênero

A seção metodológica abaixo reproduz as informações registradas para este indicador em `indicadores.md`.

## Definição e evidências metodológicas

- **Nome:** Average MovieLens Rating by Genre.
- **Objetivo de negócio:** Comparar as notas médias atribuídas pelos usuários MovieLens aos filmes de diferentes gêneros.
- **Tabelas e colunas utilizadas:** `refined.avaliacoes`: `movieId`, `userId` e `rating`; `refined.links`: `movieId` e `tmdbId`; `refined.filmes`: `id` e `genres`.
- **Relacionamentos necessários:** Relacionar `avaliacoes.movieId` a `links.movieId` e `links.tmdbId` a `filmes.id`. Extrair os gêneros dos filmes e associar as avaliações aos gêneros correspondentes.
- **Granularidade:** Gênero.
- **Regra de cálculo:** Calcular a média de `rating` por gênero, utilizando as avaliações dos filmes com correspondência na tabela de filmes e gênero identificável.
- **Resultado exploratório:** O relacionamento entre as avaliações e os filmes apresentou cobertura de 99,81%: 25.974.454 avaliações com filme correspondente, de um total de 26.024.289. Foram identificados 42.978 filmes com gênero, 90.976 associações filme–gênero e 20 gêneros distintos.
- **Destaques:** History apresentou média 3,807; War, 3,788; Documentary, 3,727; Drama, 3,665; e Horror, 3,213.
- **Classificação:** **Dá, mas...**
- **Justificativa da classificação:** A média pode ser calculada após os relacionamentos entre as três tabelas. A consulta preservou a granularidade das avaliações e não multiplicou registros nos relacionamentos.
- **Ressalvas:** Filmes multigênero participam integralmente de cada gênero. Portanto, as quantidades de avaliações não são aditivas entre categorias. As 49.835 avaliações sem correspondência em filmes e as avaliações de filmes sem gênero identificável não participam da agregação. A média representa as avaliações MovieLens, não a nota TMDB. Gêneros com menor volume de avaliações exigem cautela na interpretação.

---

## Auditoria

[Auditoria metodológica do indicador 10](../auditorias/indicador-10-auditoria.md)

## Consulta SQL correspondente

Arquivo fonte: `sql/marts/10_nota_media_movielens_por_genero.sql`.

```sql
-- Pergunta de negócio: qual é o volume, a quantidade de filmes e a nota média MovieLens por gênero?
-- Grão do resultado final: uma linha por gênero extraído.
-- CTE avaliacoes_por_filme: uma linha por movieId, com volume e média simples das avaliações.
-- CTE filmes_com_avaliacoes: uma linha por movieId após os vínculos; links tem no máximo
-- uma linha por movieId e filmes tem uma linha por id, então as junções não multiplicam
-- avaliações. movieIds diferentes podem apontar para o mesmo tmdbId, mas permanecem
-- filmes MovieLens distintos no grão desta análise.
-- CTE generos_extraidos: uma linha por par movieId e gênero. Filmes multigênero
-- contribuem em cada gênero, então totais entre gêneros não são aditivos.
-- A nota por gênero é média ponderada pelo total de avaliações de cada movieId,
-- evitando dar o mesmo peso a filmes com volumes de avaliação diferentes.
WITH avaliacoes_por_filme AS (
    SELECT
        movieId,
        COUNT(*) AS total_avaliacoes,
        AVG(rating) AS nota_media
    FROM refined.avaliacoes
    GROUP BY movieId
),
filmes_com_avaliacoes AS (
    SELECT
        a.movieId,
        a.total_avaliacoes,
        a.nota_media,
        f.id AS tmdbId,
        f.genres
    FROM avaliacoes_por_filme a
    INNER JOIN refined.links l
        ON a.movieId = l.movieId
    INNER JOIN refined.filmes f
        ON l.tmdbId = f.id
    WHERE l.tmdbId IS NOT NULL
),
generos_extraidos AS (
    SELECT
        movieId,
        total_avaliacoes,
        nota_media,
        TRIM(
            REPLACE(
                REPLACE(genero, '''name'': ''', ''),
                '''',
                ''
            )
        ) AS genero
    FROM filmes_com_avaliacoes,
    UNNEST(
        REGEXP_EXTRACT_ALL(
            genres,
            '''name'': ''([^'']+)'''
        )
    ) AS t(genero)
)
SELECT
    genero,
    COUNT(DISTINCT movieId) AS total_filmes,
    SUM(total_avaliacoes) AS total_avaliacoes,
    ROUND(
        SUM(nota_media * total_avaliacoes)
        / SUM(total_avaliacoes),
        3
    ) AS nota_media_movielens
FROM generos_extraidos
WHERE genero <> ''
GROUP BY genero
ORDER BY nota_media_movielens DESC;
```
