# Auditoria metodológica — Indicador 10

**Indicador:** nota média MovieLens por gênero<br>
**SQL auditado:** `sql/marts/10_nota_media_movielens_por_genero.sql`<br>
**Data da auditoria:** 2 de novembro de 2026<br>
**Parecer:** **APROVADO COM RESSALVAS**

## 1. Objetivo e escopo

Esta auditoria avaliou a integridade do grão, das chaves e dos relacionamentos entre `refined.avaliacoes`, `refined.links` e `refined.filmes`; a extração e expansão de gêneros; e a fórmula da média por gênero. O grão MovieLens é `movieId`. Filmes multigênero participam de cada gênero armazenado, e filmes MovieLens distintos não devem ser consolidados quando compartilham um `tmdbId`.

Os valores de nota usados são `rating` de MovieLens. Os metadados TMDB entram para localizar os gêneros; `vote_average` e `vote_count` TMDB não são combinados com os ratings MovieLens.

As verificações previamente realizadas de ausência de duplicidades em `refined.links.movieId` e `refined.filmes.id` foram consideradas concluídas e não repetidas. A auditoria foi investigativa: não alterou SQL, dados ou tabelas e não executou o pipeline.

## 2. Ambiente e método

- **Conexão:** MCP do DuckDB configurada para o arquivo `C:/Users/rober/Desktop/projetoedj/movie-data-pipeline/movie_data.duckdb`.
- **Identificação retornada pela conexão:** `current_database() = movie_data`.
- **Versão:** `v1.5.6`.
- **Modo de acesso:** somente leitura, conforme a configuração da MCP.
- **Acesso aos dados:** exclusivamente por consultas MCP DuckDB. Todas as consultas de auditoria foram operações `SELECT`.

Consulta de identificação executada:

```sql
SELECT current_database() AS banco_conectado, version() AS versao_duckdb;
```

Resultado: `movie_data`, `v1.5.6`.

## 3. Implementação SQL examinada

A consulta auditada executa estas etapas:

1. `avaliacoes_por_filme`: agrupa `refined.avaliacoes` por `movieId`, usando `COUNT(*) AS total_avaliacoes` e `AVG(rating) AS nota_media`.
2. `filmes_com_avaliacoes`: junta os resultados a `refined.links` por `movieId` e a `refined.filmes` por `links.tmdbId = filmes.id`, com `INNER JOIN`; exige `tmdbId IS NOT NULL`.
3. `generos_extraidos`: expande `genres` com `UNNEST(REGEXP_EXTRACT_ALL(genres, '''name'': ''([^'']+)'''))`, e limpa o texto com `TRIM(REPLACE(REPLACE(genero, '''name'': ''', ''), '''', ''))`.
4. O resultado agrupa por gênero, calcula `COUNT(DISTINCT movieId)`, soma avaliações e calcula `ROUND(SUM(nota_media * total_avaliacoes) / SUM(total_avaliacoes), 3)`.

Como a CTE inicial contém uma média por `movieId`, o produto pela quantidade de ratings e a divisão pela soma dessas quantidades tornam a média por gênero equivalente à média direta de cada rating MovieLens associado ao gênero. Cada `movieId` mantém seu próprio peso; `movieId`s diferentes que compartilham `tmdbId` não são consolidados.

O SQL declara uma linha por gênero no resultado; um filme multigênero gera uma linha para cada par filme/gênero. Portanto, as contagens e somas entre gêneros não são aditivas.

## 4. Evidências e resultados

### 4.1 Cobertura dos relacionamentos

Foram considerados todos os `movieId` distintos em `refined.avaliacoes`. A verificação usou `LEFT JOIN` para contar as etapas de cobertura sem descartar antecipadamente os IDs:

```sql
WITH avaliados AS (
  SELECT DISTINCT movieId FROM refined.avaliacoes
), cobertura AS (
  SELECT a.movieId, l.movieId AS link_movieId, l.tmdbId, f.id AS filme_id
  FROM avaliados a
  LEFT JOIN refined.links l ON a.movieId = l.movieId
  LEFT JOIN refined.filmes f ON l.tmdbId = f.id
)
SELECT COUNT(*) AS total_movieId,
  COUNT(*) FILTER (WHERE link_movieId IS NOT NULL) AS com_link,
  COUNT(*) FILTER (WHERE tmdbId IS NOT NULL) AS com_tmdbId,
  COUNT(*) FILTER (WHERE filme_id IS NOT NULL) AS com_filme,
  COUNT(*) FILTER (WHERE link_movieId IS NULL) AS sem_link,
  COUNT(*) FILTER (WHERE link_movieId IS NOT NULL AND tmdbId IS NULL) AS link_sem_tmdbId,
  COUNT(*) FILTER (WHERE tmdbId IS NOT NULL AND filme_id IS NULL) AS tmdb_sem_filme
FROM cobertura;
```

| Verificação | `movieId` | Percentual dos 45.115 IDs avaliados |
|---|---:|---:|
| Total de `movieId` avaliados | 45.115 | 100,00% |
| Com correspondência em `links` | 45.115 | 100,00% |
| Com `tmdbId` não nulo | 44.902 | 99,53% |
| Com correspondência em `filmes` | 44.715 | 99,11% |
| Sem link | 0 | 0,00% |
| Com link, mas sem `tmdbId` | 213 | 0,47% |
| Com `tmdbId`, mas sem filme correspondente | 187 | 0,41% |

Os `INNER JOINs` excluem 213 IDs com `tmdbId` nulo e 187 sem filme correspondente: **400 `movieId` (0,89%)** não chegam à tabela de filmes. O efeito é uma limitação de cobertura da cadeia `avaliacoes.movieId → links.movieId → links.tmdbId → filmes.id`.

### 4.2 Qualidade das avaliações e peso

Consulta executada:

```sql
SELECT COUNT(*) AS total_registros,
  COUNT(rating) AS ratings_nao_nulos,
  COUNT(*) - COUNT(rating) AS ratings_nulos,
  COUNT(*) FILTER (WHERE rating < 0.5 OR rating > 5) AS fora_intervalo_0_5_5,
  MIN(rating) AS rating_minimo,
  MAX(rating) AS rating_maximo,
  AVG(rating) AS media_registros_validos
FROM refined.avaliacoes;
```

| Medida | Resultado |
|---|---:|
| Registros (`COUNT(*)`) | 26.024.289 |
| Ratings não nulos (`COUNT(rating)`) | 26.024.289 |
| Ratings nulos | 0 |
| Fora do intervalo 0,5–5,0 | 0 |
| Mínimo / máximo | 0,5 / 5,0 |
| Média global observada | 3,5280903543608817 |

Também foi comparado o peso por filme:

```sql
WITH avaliacoes_por_filme AS (
  SELECT movieId, COUNT(*) AS total_avaliacoes,
    COUNT(rating) AS ratings_validos, AVG(rating) AS nota_media
  FROM refined.avaliacoes GROUP BY movieId
)
SELECT COUNT(*) AS movieIds,
  COUNT(*) FILTER (WHERE total_avaliacoes <> ratings_validos) AS filmes_com_peso_divergente,
  SUM(total_avaliacoes) AS soma_peso_count_star,
  SUM(ratings_validos) AS soma_ratings_validos,
  SUM(total_avaliacoes - ratings_validos) AS diferenca_peso_vs_validos
FROM avaliacoes_por_filme;
```

Resultado: **45.115** filmes MovieLens; **0** com divergência entre `COUNT(*)` e `COUNT(rating)`; ambas as somas são **26.024.289**, diferença **0**. Assim, o peso efetivamente corresponde aos ratings válidos neste banco. Se houvesse nulos, `AVG(rating)` os ignoraria, enquanto `COUNT(*)` os contaria; a auditoria não encontrou esse caso.

### 4.3 Extração e integridade dos gêneros

As verificações aplicaram exatamente a expressão regular e a limpeza do SQL auditado:

```sql
REGEXP_EXTRACT_ALL(genres, '''name'': ''([^'']+)''')
TRIM(REPLACE(REPLACE(genero, '''name'': ''', ''), '''', ''))
```

Os CTEs de base reproduziram a agregação por `movieId` e os dois `INNER JOINs` do indicador. O resumo da expansão retornou:

| Medida | Resultado |
|---|---:|
| Filmes após os JOINs | 44.715 |
| Linhas extraídas | 89.831 |
| Filmes com ao menos um gênero extraído | 42.331 |
| Pares distintos `movieId`/gênero | 89.831 |
| Linhas de gênero vazias ou nulas | 0 |

Foi agrupado por `(movieId, genero)` e contada a ocorrência de pares repetidos. Resultado: **0 pares duplicados**, **0 ocorrências excedentes** e **0 pares vazios**. Portanto, a expansão preserva uma linha por combinação filme/gênero.

Verificações de `genres` entre os 44.715 filmes após os JOINs:

| Condição | Resultado |
|---|---:|
| `genres IS NULL` | 0 |
| `genres = ''` | 0 |
| Sem correspondência à expressão regular de gênero | 2.384 |

Uma consulta de amostra retornou `genres = '[]'` para os primeiros filmes sem correspondência. Uma amostra dos filmes com gênero confirmou que o padrão captura nomes armazenados: para `movieId = 1`, o texto continha Animation, Comedy e Family, e a extração capturou os três; para `movieId = 2`, capturou Adventure, Fantasy e Family. Os 2.384 casos sem extração não entram nos grupos.

Os 42.331 filmes com gênero extraível correspondem a **94,67%** dos 44.715 que passaram pelos JOINs e **93,83%** dos 45.115 IDs avaliados.

### 4.4 Integridade do grão e cardinalidade dos JOINs

Consulta executada para comparar linhas e IDs distintos em cada etapa:

```sql
WITH avaliacoes_por_filme AS (
  SELECT movieId, COUNT(*) AS total_avaliacoes, AVG(rating) AS nota_media
  FROM refined.avaliacoes GROUP BY movieId
), apos_link AS (
  SELECT a.movieId, a.total_avaliacoes, a.nota_media, l.tmdbId
  FROM avaliacoes_por_filme a
  INNER JOIN refined.links l ON a.movieId = l.movieId
), apos_filme AS (
  SELECT a.movieId, a.total_avaliacoes, a.nota_media, a.tmdbId, f.genres
  FROM apos_link a
  INNER JOIN refined.filmes f ON a.tmdbId = f.id
  WHERE a.tmdbId IS NOT NULL
)
SELECT
  (SELECT COUNT(*) FROM avaliacoes_por_filme) AS linhas_agregadas,
  (SELECT COUNT(DISTINCT movieId) FROM avaliacoes_por_filme) AS movieIds_agregados,
  (SELECT COUNT(*) FROM apos_link) AS linhas_apos_links,
  (SELECT COUNT(DISTINCT movieId) FROM apos_link) AS movieIds_apos_links,
  (SELECT COUNT(*) FROM apos_filme) AS linhas_apos_filmes,
  (SELECT COUNT(DISTINCT movieId) FROM apos_filme) AS movieIds_apos_filmes,
  (SELECT COUNT(*) FROM apos_link WHERE tmdbId IS NULL) AS tmdb_nulo_apos_link,
  (SELECT COUNT(DISTINCT tmdbId) FROM apos_filme) AS tmdbIds_distintos;
```

| Etapa | Linhas | `movieId` distintos |
|---|---:|---:|
| Agregação inicial por `movieId` | 45.115 | 45.115 |
| Após o JOIN com `links` | 45.115 | 45.115 |
| Após o JOIN com `filmes` e `tmdbId` não nulo | 44.715 | 44.715 |

Após os JOINs com filme há **44.698 `tmdbId` distintos**. Em consulta separada, entre os IDs avaliados com `tmdbId` não nulo, foram encontrados **29 `tmdbId` compartilhados**, associados a **59 `movieId`**; o máximo foi **3 `movieId` por `tmdbId`**. Esses IDs MovieLens permanecem distintos no grão. A diferença entre linhas e IDs distintos em cada etapa não indica multiplicação; as contagens coincidiram em todas as etapas.

As validações já fornecidas de unicidade em `links.movieId` e `filmes.id`, junto com essas cardinalidades, sustentam que os JOINs não multiplicam avaliações antes da expansão de gêneros.

### 4.5 Fórmula e comparação com a média direta

Para um gênero (g), o SQL calcula:

\[
\bar r_g = \frac{\sum_{m \in g} \bar r_m \times n_m}{\sum_{m \in g} n_m}
\]

onde \(\bar r_m\) é a média dos ratings do `movieId` \(m\), e \(n_m\) é seu total de ratings. Como não há rating nulo, `COUNT(*)` é igual à quantidade de ratings usados por `AVG(rating)`. Multiplicar a média do filme por sua contagem recupera a soma dos ratings do filme; a divisão pela soma das contagens equivale a calcular `AVG(rating)` diretamente sobre os ratings dos filmes daquele gênero.

Foi executada uma comparação por gênero entre `SUM(nota_media * total_avaliacoes) / SUM(total_avaliacoes)` e `AVG(rating)` direto, usando os mesmos JOINs e a mesma expansão regex. Resultado: **20 gêneros**, maior diferença absoluta entre médias **0,0** e **0 gêneros** com contagem divergente.

Resumo adicional retornado pela comparação: soma de avaliações por gênero **70.507.563** e soma de filmes por gênero **89.831**. Esses totais são maiores que os registros/filmes únicos porque filmes multigênero participam integralmente de cada grupo. Isso é esperado; totais entre gêneros não são aditivos e não representa inflação dentro de um gênero.

O SQL final auditado retornou os seguintes 20 grupos, ordenados pela média decrescente:

| Gênero | Filmes | Avaliações | Média MovieLens |
|---|---:|---:|---:|
| History | 1.388 | 1.020.854 | 3,807 |
| War | 1.301 | 1.037.340 | 3,788 |
| Documentary | 3.895 | 296.805 | 3,727 |
| Drama | 19.983 | 11.972.353 | 3,665 |
| Crime | 4.257 | 4.595.361 | 3,625 |
| Animation | 1.930 | 1.634.933 | 3,604 |
| Mystery | 2.435 | 2.363.096 | 3,587 |
| Western | 988 | 438.084 | 3,577 |
| Music | 1.544 | 857.355 | 3,532 |
| Thriller | 7.569 | 7.069.754 | 3,514 |
| Romance | 6.612 | 4.570.145 | 3,510 |
| Foreign | 1.609 | 44.877 | 3,484 |
| Adventure | 3.437 | 6.031.525 | 3,467 |
| Fantasy | 2.298 | 3.363.142 | 3,448 |
| Action | 6.516 | 7.244.860 | 3,437 |
| Science Fiction | 3.022 | 4.263.524 | 3,431 |
| Family | 2.747 | 3.066.295 | 3,426 |
| Comedy | 12.919 | 8.884.309 | 3,399 |
| TV Movie | 751 | 18.666 | 3,352 |
| Horror | 4.630 | 1.734.285 | 3,213 |

### 4.6 Efeito combinado das exclusões

Consulta executada com contagem de ratings por `movieId`, `LEFT JOIN` nas tabelas de relacionamento e classificação em: incluído; `tmdbId` nulo; `tmdbId` sem filme; sem gênero extraível.

| Situação | `movieId` | Avaliações |
|---|---:|---:|
| Incluído em algum gênero | 42.331 | 25.948.960 |
| Link ausente ou `tmdbId` nulo | 213 | 13.503 |
| `tmdbId` sem filme correspondente | 187 | 36.332 |
| Sem gênero extraível | 2.384 | 25.494 |
| **Total** | **45.115** | **26.024.289** |

No total, **75.329 avaliações** não são atribuídas a nenhum gênero, aproximadamente **0,29%** dos ratings. Os motivos são os filtros de correspondência e a ausência de gênero extraível.

## 5. Achados classificados

### Crítico

Nenhum problema crítico foi identificado. Não foi observada quebra do grão, multiplicação indevida por JOIN, consolidação de `movieId` distintos, duplicidade de pares filme/gênero nem erro na média ponderada.

### Relevante

1. **Cobertura da cadeia de relacionamento:** 400 `movieId` (0,89%) não chegam à tabela `filmes`: 213 têm `tmdbId` nulo e 187 não encontram correspondência. Consequência: 49.835 avaliações não entram na métrica. É uma limitação a documentar; a correção do SQL só seria necessária se o escopo pretendesse incluir esses filmes sem correspondência completa.
2. **Filmes sem gênero extraível:** 2.384 filmes correspondentes têm `genres = '[]'` na amostra e não entram em nenhum grupo, excluindo 25.494 avaliações. A limitação deve ser documentada. Os resultados não indicam que uma alteração da expressão regular recuperaria gêneros ausentes no dado armazenado.

### Informativo

1. **Multigênero:** filmes são integralmente atribuídos a cada gênero extraído. Por isso, somas entre gêneros não são aditivas. É característica metodológica esperada, a documentar.
2. **`tmdbId` compartilhado:** há `movieId` diferentes associados ao mesmo `tmdbId`; o indicador mantém a granularidade MovieLens e não os consolida. Não requer correção.
3. **Peso da média:** neste banco, não há nulos e `COUNT(*)` coincide com `COUNT(rating)`. A ponderação utilizada é válida para o conjunto auditado.

## 6. Parecer final

**APROVADO COM RESSALVAS.** A média ponderada está matematicamente correta e coincide com a média direta dos ratings para todos os 20 gêneros. O grão `movieId` é preservado pelos relacionamentos, os JOINs não multiplicam linhas antes da expansão, os pares `movieId`/gênero não se repetem e filmes multigênero são contabilizados em cada grupo correspondente.

As ressalvas são de cobertura: 400 IDs não obtêm correspondência completa em `refined.filmes`, e 2.384 filmes correspondentes não têm gênero extraível. Em conjunto, 75.329 ratings (aproximadamente 0,29%) ficam fora dos grupos. Essas limitações devem acompanhar a interpretação do indicador.

## Atualização da revisão metodológica — 3 de novembro de 2026

Foi repetida uma validação somente leitura da consulta de referência contra `marts.nota_media_movielens_por_genero`, usando as mesmas junções, expansão de gêneros e arredondamento. A consulta e a MART retornaram **20 linhas**, com **0 diferenças** em `referência EXCEPT ALL MART` e **0 diferenças** em `MART EXCEPT ALL referência`.

A equivalência entre a ponderação e a média direta foi confirmada para os 20 gêneros: diferença máxima absoluta **0,0** e nenhuma divergência nas contagens. As chaves continuam únicas (`links.movieId`: 45.843 linhas e 45.843 IDs; `filmes.id`: 45.420 linhas e 45.420 IDs). O grão de ratings agregados por `movieId` passou de 45.115 para 44.715 IDs após a correspondência com filme, sem multiplicação pelos JOINs.

As exclusões devem ser lidas em duas unidades: **400 `movieId`** não obtêm vínculo TMDB completo (213 com `tmdbId` nulo e 187 sem filme correspondente), enquanto **2.384 filmes vinculados** não têm gênero extraível. Juntas, essas condições deixam **75.329 ratings** sem atribuição a gênero, aproximadamente **0,29%** dos 26.024.289 ratings. Não se deve equiparar a contagem de filmes excluídos à contagem de ratings excluídos.
