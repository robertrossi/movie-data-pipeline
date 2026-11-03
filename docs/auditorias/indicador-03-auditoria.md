# Auditoria metodológica — Indicador 03

**Indicador:** quantidade de votos TMDB por gênero<br>
**SQL auditado:** `sql/marts/03_quantidade_votos_tmdb_por_genero.sql`<br>
**Tabela comparada:** `marts.quantidade_votos_tmdb_por_genero`<br>
**Parecer:** **APROVADO COM RESSALVAS**

## Pergunta, grão e metodologia

A pergunta é quantos votos TMDB os filmes acumulam em cada gênero. A origem é `refined.filmes`, com uma linha por `id` TMDB. A consulta inclui `vote_count IS NOT NULL`, expande a lista de gêneros e soma `vote_count` por gênero. O resultado tem uma linha por gênero e conta filmes distintos por `id`.

Não há JOINs nem ponderação: `vote_count` já representa o total de votos TMDB no filme. Filmes multigênero contribuem com todos os seus votos em cada gênero correspondente. Assim, tanto `total_filmes` quanto `total_votos_tmdb` não são aditivos entre gêneros.

## Consultas executadas e resultados

### Recálculo e comparação com a tabela materializada

O SQL do indicador foi reproduzido como `esperado`, incluindo o filtro de votos não nulos e a regex de gênero; o resultado foi comparado com a mart via `EXCEPT ALL` nos dois sentidos.

```sql
WITH filmes_elegiveis AS (
  SELECT id, vote_count, genres FROM refined.filmes
  WHERE vote_count IS NOT NULL
), generos_extraidos AS (
  SELECT id, vote_count,
    TRIM(REPLACE(REPLACE(genero, '''name'': ''', ''), '''', '')) AS genero
  FROM filmes_elegiveis,
  UNNEST(REGEXP_EXTRACT_ALL(genres, '''name'': ''([^'']+)''')) AS t(genero)
), esperado AS (
  SELECT genero, COUNT(DISTINCT id) AS total_filmes,
    SUM(vote_count) AS total_votos_tmdb
  FROM generos_extraidos WHERE genero <> '' GROUP BY genero
), diferencas AS (
  (SELECT * FROM esperado EXCEPT ALL
   SELECT * FROM marts.quantidade_votos_tmdb_por_genero)
  UNION ALL
  (SELECT * FROM marts.quantidade_votos_tmdb_por_genero EXCEPT ALL
   SELECT * FROM esperado)
)
SELECT (SELECT COUNT(*) FROM esperado) AS linhas_esperadas,
  (SELECT COUNT(*) FROM marts.quantidade_votos_tmdb_por_genero) AS linhas_mart,
  (SELECT COUNT(*) FROM diferencas) AS diferencas,
  (SELECT COUNT(*) FROM filmes_elegiveis) AS filmes_vote_count_nao_nulo,
  (SELECT SUM(vote_count) FROM filmes_elegiveis) AS soma_vote_count_catalogo,
  (SELECT COUNT(*) FROM generos_extraidos WHERE genero <> '') AS pares_filme_genero;
```

**Resultado:** 20 linhas esperadas e 20 na mart; **0 diferenças**; 45.417 filmes com `vote_count` não nulo; soma desses `vote_count` no catálogo: **4.993.591**; **90.967** pares filme/gênero extraídos.

### Valores, chaves e integridade da expansão

Consulta executada:

```sql
WITH gx AS (
  SELECT f.id, f.vote_count,
    TRIM(REPLACE(REPLACE(genero, '''name'': ''', ''), '''', '')) AS genero
  FROM refined.filmes f,
  UNNEST(REGEXP_EXTRACT_ALL(f.genres, '''name'': ''([^'']+)''')) AS t(genero)
  WHERE f.vote_count IS NOT NULL
), pares AS (
  SELECT id, genero, COUNT(*) AS n FROM gx GROUP BY id, genero
)
SELECT
  (SELECT COUNT(*) FROM refined.filmes WHERE vote_count IS NULL) AS vote_count_nulo,
  (SELECT COUNT(*) FROM refined.filmes WHERE vote_count < 0) AS vote_count_negativo,
  (SELECT COUNT(*) FROM refined.filmes WHERE vote_count = 0) AS vote_count_zero,
  (SELECT COUNT(*) FROM refined.filmes WHERE vote_count > 0) AS vote_count_positivo,
  (SELECT MIN(vote_count) FROM refined.filmes WHERE vote_count IS NOT NULL) AS minimo,
  (SELECT MAX(vote_count) FROM refined.filmes) AS maximo,
  (SELECT COUNT(*) FROM gx WHERE genero = '') AS generos_vazios,
  (SELECT COUNT(*) FROM pares WHERE n > 1) AS pares_duplicados,
  (SELECT COUNT(DISTINCT id) FROM gx) AS filmes_com_genero,
  (SELECT COUNT(*) FROM refined.filmes f WHERE f.vote_count IS NOT NULL
    AND NOT REGEXP_MATCHES(COALESCE(f.genres,''), '''name'': ''([^'']+)'''))
    AS sem_genero_extraivel;
```

| Verificação | Resultado |
|---|---:|
| Filmes no catálogo / IDs não nulos e distintos | 45.420 / 45.420 |
| `vote_count` nulo / negativo | 3 / 0 |
| `vote_count = 0` / positivo | 2.895 / 42.522 |
| `vote_count` mínimo / máximo | 0 / 14.075 |
| Filmes com gênero extraído | 42.975 |
| Sem gênero extraível entre os com `vote_count` não nulo | 2.442 |
| Gêneros vazios / pares `(id, genero)` duplicados | 0 / 0 |

O grão de origem está completo e sem duplicidade observada: `COUNT(*)`, `COUNT(id)` e `COUNT(DISTINCT id)` são 45.420. A extração usa exatamente `REGEXP_EXTRACT_ALL(genres, '''name'': ''([^'']+)''')` e a limpeza `TRIM(REPLACE(REPLACE(...)))`. Não há duplicação de par filme/gênero.

### Resultado da mart e não aditividade

Consulta executada: `SELECT genero, total_filmes, total_votos_tmdb FROM marts.quantidade_votos_tmdb_por_genero ORDER BY total_votos_tmdb DESC;`.

| Gênero | Filmes | Votos TMDB |
|---|---:|---:|
| Drama | 20.234 | 1.954.388 |
| Action | 6.589 | 1.708.201 |
| Comedy | 13.174 | 1.437.285 |
| Adventure | 3.486 | 1.433.777 |
| Thriller | 7.616 | 1.433.111 |
| Science Fiction | 3.040 | 981.838 |
| Fantasy | 2.307 | 769.068 |
| Crime | 4.302 | 757.309 |
| Family | 2.764 | 670.078 |
| Romance | 6.727 | 645.012 |
| Horror | 4.669 | 471.124 |
| Animation | 1.928 | 452.427 |
| Mystery | 2.463 | 408.976 |
| War | 1.321 | 159.200 |
| History | 1.398 | 150.095 |
| Music | 1.596 | 108.327 |
| Western | 1.042 | 78.521 |
| Documentary | 3.929 | 50.441 |
| TV Movie | 764 | 15.936 |
| Foreign | 1.618 | 12.900 |

Consulta de totais da mart: `SELECT COUNT(*) AS generos, SUM(total_filmes) AS soma_filmes_por_genero, SUM(total_votos_tmdb) AS soma_votos_por_genero, MIN(total_votos_tmdb) AS min_votos_genero, MAX(total_votos_tmdb) AS max_votos_genero FROM marts.quantidade_votos_tmdb_por_genero;`.

Resultado: 20 gêneros; soma de filmes por gênero **90.967**; soma de votos por gênero **13.698.014**; menor total por gênero **12.900** e maior **1.954.388**. A soma de votos por gênero supera os 4.993.591 votos somados uma vez por filme porque filmes multigênero aparecem em vários grupos; isso é esperado e não é erro de agregação.

## Avaliação metodológica e limitações

- O uso de `COUNT(DISTINCT id)` representa corretamente a quantidade de filmes TMDB por gênero. A chave `id` foi verificada e não há pares filme/gênero repetidos.
- `SUM(vote_count)` mede votos TMDB associados aos filmes de cada gênero, e não avaliações MovieLens. Não se deve interpretar o resultado como número de usuários ou de ratings MovieLens.
- Três filmes têm `vote_count` nulo e são excluídos; 2.442 filmes com contagem não nula não têm gênero extraível. A consulta não lhes atribui um grupo.
- `vote_count = 0` ocorre em 2.895 filmes e é incluído, corretamente sob o filtro `IS NOT NULL`; zero significa nenhum voto contado, não dado ausente.
- As somas entre gêneros não são aditivas por causa da associação multigênero.
- A comparação integral confirma consistência da mart com a consulta atual.

## Parecer

**APROVADO COM RESSALVAS.** Cálculo, grão, expansão e mart são consistentes, sem duplicidades de pares ou contagens negativas. As ressalvas são a exclusão de três `vote_count` nulos, 2.442 filmes sem gênero extraível e a não aditividade esperada dos votos entre gêneros.
