# Auditoria metodológica — Indicador 02

**Indicador:** nota média TMDB por gênero<br>
**SQL auditado:** `sql/marts/02_nota_media_tmdb_por_genero.sql`<br>
**Tabela comparada:** `marts.nota_media_tmdb_por_genero`<br>
**Parecer:** **APROVADO COM RESSALVAS**

## Pergunta, grão e metodologia

A pergunta é qual a nota média (`vote_average`) dos filmes TMDB elegíveis em cada gênero. A origem é `refined.filmes`, cujo grão é uma linha por `id` TMDB. A CTE `filmes_elegiveis` seleciona `vote_count >= 50` e `vote_average IS NOT NULL`. A extração de gênero expande cada filme para pares `(id, genero)`, e o resultado tem uma linha por gênero.

O cálculo é a média simples das notas dos filmes que pertencem a cada gênero, arredondada a duas casas. Não pondera por `vote_count`: a interpretação é “média das notas TMDB dos filmes elegíveis”, não a média de votos individuais. Um filme multigênero aparece integralmente em cada gênero; logo, totais por gênero não são aditivos. Não há JOINs.

Esta é uma escolha de unidade de análise: cada filme elegível tem peso igual, ainda que a nota TMDB de um filme possa resumir volumes de votos diferentes. Uma média ponderada por `vote_count` responderia a outra pergunta. No conjunto auditado, a diferença máxima entre essas duas fórmulas foi aproximadamente 0,591 ponto entre os gêneros.

## Consultas executadas e resultados

### Recálculo da consulta e comparação com a mart

Foi executada a consulta do indicador como CTE `esperado`, com os mesmos filtros e a mesma extração. O resultado foi comparado à mart usando `EXCEPT ALL` nos dois sentidos:

```sql
WITH filmes_elegiveis AS (
  SELECT id, vote_average, genres FROM refined.filmes
  WHERE vote_count >= 50 AND vote_average IS NOT NULL
), generos_extraidos AS (
  SELECT id, vote_average,
    TRIM(REPLACE(REPLACE(genero, '''name'': ''', ''), '''', '')) AS genero
  FROM filmes_elegiveis,
  UNNEST(REGEXP_EXTRACT_ALL(genres, '''name'': ''([^'']+)''')) AS t(genero)
), esperado AS (
  SELECT genero, COUNT(DISTINCT id) AS total_filmes,
    ROUND(AVG(vote_average), 2) AS nota_media_tmdb
  FROM generos_extraidos WHERE genero <> '' GROUP BY genero
), diferencas AS (
  (SELECT * FROM esperado EXCEPT ALL
   SELECT * FROM marts.nota_media_tmdb_por_genero)
  UNION ALL
  (SELECT * FROM marts.nota_media_tmdb_por_genero EXCEPT ALL
   SELECT * FROM esperado)
)
SELECT (SELECT COUNT(*) FROM esperado) AS linhas_esperadas,
  (SELECT COUNT(*) FROM marts.nota_media_tmdb_por_genero) AS linhas_mart,
  (SELECT COUNT(*) FROM diferencas) AS diferencas,
  (SELECT COUNT(*) FROM filmes_elegiveis) AS filmes_elegiveis,
  (SELECT COUNT(*) FROM generos_extraidos WHERE genero <> '') AS pares_filme_genero;
```

**Resultado:** 20 linhas recalculadas, 20 linhas materializadas, **0 diferenças**, **9.137** filmes elegíveis e **23.044** pares filme/gênero extraídos.

### Chaves, elegibilidade, valores e expansão

Consulta executada:

```sql
WITH elegiveis AS (
  SELECT * FROM refined.filmes
  WHERE vote_count >= 50 AND vote_average IS NOT NULL
), gx AS (
  SELECT id, TRIM(REPLACE(REPLACE(genero, '''name'': ''', ''), '''', '')) AS genero
  FROM elegiveis,
  UNNEST(REGEXP_EXTRACT_ALL(genres, '''name'': ''([^'']+)''')) AS t(genero)
), pares AS (
  SELECT id, genero, COUNT(*) AS n FROM gx GROUP BY id, genero
)
SELECT
  (SELECT COUNT(*) FROM refined.filmes) AS filmes_total,
  (SELECT COUNT(id) FROM refined.filmes) AS ids_nao_nulos,
  (SELECT COUNT(DISTINCT id) FROM refined.filmes) AS ids_distintos,
  (SELECT COUNT(*) FROM elegiveis) AS elegiveis_vote_count50_e_nota,
  (SELECT COUNT(*) FROM refined.filmes WHERE vote_count IS NULL) AS vote_count_nulo,
  (SELECT COUNT(*) FROM refined.filmes WHERE vote_count < 0) AS vote_count_negativo,
  (SELECT COUNT(*) FROM refined.filmes WHERE vote_average IS NULL) AS vote_average_nulo,
  (SELECT COUNT(*) FROM refined.filmes WHERE vote_average < 0 OR vote_average > 10)
    AS nota_fora_escala_0_10,
  (SELECT COUNT(*) FROM elegiveis WHERE genres IS NULL OR genres = '')
    AS elegiveis_genres_nulos_ou_vazios,
  (SELECT COUNT(*) FROM elegiveis e WHERE NOT REGEXP_MATCHES(
    COALESCE(e.genres, ''), '''name'': ''([^'']+)''')) AS elegiveis_sem_genero,
  (SELECT COUNT(*) FROM gx WHERE genero = '') AS generos_vazios,
  (SELECT COUNT(*) FROM pares WHERE n > 1) AS pares_duplicados;
```

| Verificação | Resultado |
|---|---:|
| Filmes no catálogo | 45.420 |
| IDs não nulos / distintos | 45.420 / 45.420 |
| Filmes elegíveis (`vote_count >= 50` e nota não nula) | 9.137 |
| `vote_count` nulo / negativo | 3 / 0 |
| `vote_average` nulo | 3 |
| `vote_average` fora da escala 0–10 | 0 |
| Elegíveis com `genres` nulo ou string vazia | 0 |
| Elegíveis sem gênero extraível | 6 |
| Gêneros vazios / pares duplicados `(id, genero)` | 0 / 0 |

A tabela `refined.filmes.id` tem uma chave por linha no conjunto observado (45.420 não nulos e distintos). Os gêneros foram extraídos com o mesmo padrão do SQL: `REGEXP_EXTRACT_ALL(genres, '''name'': ''([^'']+)''')`, com a limpeza por `TRIM(REPLACE(REPLACE(...)))`. Não há expansão duplicada de um mesmo filme dentro do mesmo gênero.

### Resultado materializado

Consulta executada: `SELECT genero, total_filmes, nota_media_tmdb FROM marts.nota_media_tmdb_por_genero ORDER BY nota_media_tmdb DESC;`.

| Gênero | Filmes | Nota média TMDB |
|---|---:|---:|
| Documentary | 201 | 7,26 |
| History | 347 | 6,91 |
| War | 277 | 6,88 |
| Drama | 4.218 | 6,65 |
| Animation | 674 | 6,65 |
| Music | 281 | 6,62 |
| Western | 154 | 6,60 |
| Foreign | 3 | 6,50 |
| Crime | 1.341 | 6,47 |
| Romance | 1.492 | 6,45 |
| Mystery | 724 | 6,37 |
| Adventure | 1.357 | 6,27 |
| Fantasy | 857 | 6,25 |
| Family | 929 | 6,23 |
| Comedy | 3.263 | 6,20 |
| Thriller | 2.534 | 6,18 |
| Action | 2.036 | 6,17 |
| Science Fiction | 995 | 6,10 |
| TV Movie | 70 | 6,00 |
| Horror | 1.291 | 5,83 |

## Avaliação metodológica e limitações

- A contagem de filmes usa `COUNT(DISTINCT id)`, apropriada para o grão por filme dentro de cada gênero. A unicidade observada de `id` e ausência de pares duplicados sustentam que a expansão não infla uma contagem por gênero.
- `AVG(vote_average)` concede peso igual a cada filme elegível. Isso é coerente com a interpretação declarada, mas não equivale a média ponderada por votos, nem descreve os ratings MovieLens.
- O corte mínimo de 50 votos exclui filmes com menos votos e os três filmes com `vote_count` nulo. Os três `vote_average` nulos também são inelegíveis; os resultados não especificam a interseção entre esses nulos. O critério é explícito e deve acompanhar a interpretação.
- Seis filmes elegíveis não tiveram gênero extraível pela regex. Isso reduz a cobertura de gênero; os grupos não representam todos os filmes elegíveis.
- A expansão distribui cada filme integralmente por todos os gêneros extraídos. Os grupos não são exclusivos; somar suas quantidades não produz uma contagem única de filmes.
- Há gêneros com poucos filmes (por exemplo, Foreign com 3), tornando suas médias menos estáveis. Isso é limitação interpretativa, não erro do cálculo.
- O recálculo da fonte e a mart coincidem integralmente.

## Parecer

**APROVADO COM RESSALVAS.** A extração, a agregação e a mart são consistentes; não foram encontrados valores fora da escala, duplicação de pares ou problema de cardinalidade. As ressalvas são o corte de elegibilidade (`vote_count >= 50`), seis filmes elegíveis sem gênero extraível e a interpretação de média simples por filme, que não pondera a quantidade de votos TMDB.
