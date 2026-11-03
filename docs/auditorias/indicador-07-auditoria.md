# Auditoria metodológica — Indicador 07

**Indicador:** filmes com mais avaliações MovieLens<br>
**SQL auditado:** `sql/marts/07_filmes_mais_avaliados_movielens.sql`<br>
**Tabela comparada:** `marts.filmes_mais_avaliados_movielens`<br>
**Parecer:** **APROVADO**

## Pergunta, grão e metodologia

A consulta lista os 20 `movieId` com maior número de avaliações MovieLens e apresenta `tmdbId`, título, volume e média MovieLens arredondada a duas casas. A agregação inicial é uma linha por `movieId`; depois, `LEFT JOIN`s opcionais enriquecem com `refined.links` e `refined.filmes`. O resultado pretendido e observado é uma linha por `movieId` entre os 20 mais avaliados.

O volume ordena os resultados. A média é `AVG(rating)` sobre as avaliações daquele filme, não a média TMDB. Os `LEFT JOIN`s mantêm no ranking MovieLens filmes sem correspondência de metadados, evitando que a cobertura TMDB altere quais filmes são mais avaliados.

## Consultas executadas e resultados

### Recálculo e comparação integral com a mart

```sql
WITH avaliacoes_por_filme AS (
  SELECT movieId, COUNT(*) AS total_avaliacoes,
    ROUND(AVG(rating), 2) AS nota_media_movielens
  FROM refined.avaliacoes GROUP BY movieId
), esperado AS (
  SELECT a.movieId, l.tmdbId, f.title AS titulo,
    a.total_avaliacoes, a.nota_media_movielens
  FROM avaliacoes_por_filme a
  LEFT JOIN refined.links l ON a.movieId = l.movieId
  LEFT JOIN refined.filmes f ON l.tmdbId = f.id
  ORDER BY a.total_avaliacoes DESC LIMIT 20
), diferencas AS (
  (SELECT * FROM esperado EXCEPT ALL
   SELECT * FROM marts.filmes_mais_avaliados_movielens)
  UNION ALL
  (SELECT * FROM marts.filmes_mais_avaliados_movielens EXCEPT ALL
   SELECT * FROM esperado)
)
SELECT (SELECT COUNT(*) FROM esperado) AS linhas_esperadas,
  (SELECT COUNT(*) FROM marts.filmes_mais_avaliados_movielens) AS linhas_mart,
  (SELECT COUNT(*) FROM diferencas) AS diferencas,
  (SELECT MIN(total_avaliacoes) FROM esperado) AS corte_20,
  (SELECT COUNT(*) FROM avaliacoes_por_filme) AS movieIds_avaliados;
```

**Resultado:** 20 linhas esperadas e 20 na mart; **0 diferenças**; corte do 20º lugar **57.070 avaliações**; 45.115 `movieId` agregados.

### Desempate no limite do Top 20

Foi ordenada a população agregada por contagem decrescente com `ROW_NUMBER`, medindo as contagens do 20º e 21º lugar e quantos filmes têm o valor do 20º.

```sql
WITH apf AS (
  SELECT movieId, COUNT(*) AS n FROM refined.avaliacoes GROUP BY movieId
), ordenados AS (
  SELECT movieId, n, ROW_NUMBER() OVER (ORDER BY n DESC) AS rn FROM apf
)
SELECT MAX(n) FILTER (WHERE rn = 20) AS vigesimo,
  MAX(n) FILTER (WHERE rn = 21) AS vigesimo_primeiro,
  COUNT(*) FILTER (WHERE n = (SELECT n FROM ordenados WHERE rn = 20))
    AS filmes_com_contagem_igual_corte
FROM ordenados;
```

**Resultado:** 20º = **57.070**, 21º = **56.827**, apenas **1** filme tem contagem igual ao corte. Não há empate atravessando o limite.

### Resultado materializado

Consulta executada: `SELECT movieId, tmdbId, titulo, total_avaliacoes, nota_media_movielens FROM marts.filmes_mais_avaliados_movielens ORDER BY total_avaliacoes DESC, movieId;`.

| movieId | tmdbId | Título | Avaliações | Média |
|---:|---:|---|---:|---:|
| 356 | 13 | Forrest Gump | 91.921 | 4,05 |
| 318 | 278 | The Shawshank Redemption | 91.082 | 4,43 |
| 296 | 680 | Pulp Fiction | 87.901 | 4,17 |
| 593 | 274 | The Silence of the Lambs | 84.078 | 4,15 |
| 2571 | 603 | The Matrix | 77.960 | 4,15 |
| 260 | 11 | Star Wars | 77.045 | 4,13 |
| 480 | 329 | Jurassic Park | 74.355 | 3,66 |
| 527 | 424 | Schindler's List | 67.662 | 4,27 |
| 110 | 197 | Braveheart | 66.512 | 4,02 |
| 1 | 862 | Toy Story | 66.008 | 3,89 |
| 1210 | 1892 | Return of the Jedi | 62.714 | 3,99 |
| 589 | 280 | Terminator 2: Judgment Day | 61.836 | 3,94 |
| 1196 | 1891 | The Empire Strikes Back | 61.672 | 4,14 |
| 2959 | 550 | Fight Club | 60.024 | 4,23 |
| 1198 | 85 | Raiders of the Lost Ark | 59.693 | 4,13 |
| 50 | 629 | The Usual Suspects | 59.271 | 4,30 |
| 2858 | 14 | American Beauty | 57.879 | 4,13 |
| 150 | 568 | Apollo 13 | 57.416 | 3,88 |
| 780 | 602 | Independence Day | 57.232 | 3,40 |
| 858 | 238 | The Godfather | 57.070 | 4,34 |

Consulta de integridade da mart:

```sql
SELECT COUNT(*) AS linhas, COUNT(DISTINCT movieId) AS movieIds,
  COUNT(*) FILTER (WHERE tmdbId IS NULL) AS tmdbId_nulo,
  COUNT(*) FILTER (WHERE titulo IS NULL) AS titulo_nulo,
  MIN(total_avaliacoes) AS min_avaliacoes,
  MAX(total_avaliacoes) AS max_avaliacoes
FROM marts.filmes_mais_avaliados_movielens;
```

Resultado: 20 linhas e 20 `movieId` distintos; 0 `tmdbId` nulo; 0 títulos nulos; mínimo 57.070 e máximo 91.921 avaliações.

## Avaliação metodológica e limitações

- A agregação inicial preserva uma linha por `movieId`; os `LEFT JOIN`s evitam perda de filmes por falta de metadados. As verificações anteriores de unicidade de `links.movieId` e `filmes.id`, junto à comparação integral sem diferenças, não indicam multiplicação no enriquecimento.
- Todos os 20 primeiros possuem `tmdbId` e título; a ausência de mapeamento em filmes fora do Top 20 não interfere na seleção devido aos `LEFT JOIN`s.
- Não há empate na contagem entre as posições 20 e 21. A ordenação entre eventuais empates internos não altera a população Top 20 observada.
- O ranking reflete volume bruto de ratings, não qualidade, período de exposição ou atividade normalizada por usuário. A nota é média simples de ratings do filme.
- A mart coincide exatamente com a consulta recalculada.

## Parecer

**APROVADO.** O grão, ranking, média, enriquecimento opcional e materialização estão consistentes; não há perda, multiplicação ou empate no corte Top 20 observado.
