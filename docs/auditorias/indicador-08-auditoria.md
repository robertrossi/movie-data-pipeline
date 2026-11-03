# Auditoria metodológica — Indicador 08

**Indicador:** usuários mais ativos no MovieLens<br>
**SQL auditado:** `sql/marts/08_usuarios_mais_ativos.sql`<br>
**Tabela comparada:** `marts.usuarios_mais_ativos`<br>
**Parecer:** **APROVADO**

## Pergunta, grão e metodologia

A consulta lista os 20 `userId` com maior número de avaliações e a média dos ratings de cada um. A origem tem grão de avaliação; a agregação é uma linha por usuário; a tabela final contém os 20 maiores grupos. `COUNT(*)` mede avaliações e `ROUND(AVG(rating), 2)` calcula média simples entre suas avaliações. Não há JOINs ou CTEs.

## Consultas executadas e resultados

### Recálculo e comparação com a tabela materializada

```sql
WITH por_usuario AS (
  SELECT userId, COUNT(*) AS total_avaliacoes,
    ROUND(AVG(rating), 2) AS nota_media_usuario
  FROM refined.avaliacoes GROUP BY userId
), esperado AS (
  SELECT * FROM por_usuario
  ORDER BY total_avaliacoes DESC LIMIT 20
), diferencas AS (
  (SELECT * FROM esperado EXCEPT ALL
   SELECT * FROM marts.usuarios_mais_ativos)
  UNION ALL
  (SELECT * FROM marts.usuarios_mais_ativos EXCEPT ALL
   SELECT * FROM esperado)
)
SELECT (SELECT COUNT(*) FROM esperado) AS linhas_esperadas,
  (SELECT COUNT(*) FROM marts.usuarios_mais_ativos) AS linhas_mart,
  (SELECT COUNT(*) FROM diferencas) AS diferencas,
  (SELECT MIN(total_avaliacoes) FROM esperado) AS corte_20,
  (SELECT COUNT(*) FROM por_usuario) AS grupos_usuario;
```

**Resultado:** 20 linhas esperadas e 20 materializadas; **0 diferenças**; 270.896 grupos de usuário na origem; corte do Top 20: **4.785** avaliações.

### Nulos, usuários e limite Top 20

Foi ordenada a quantidade por usuário com `ROW_NUMBER()` e verificada a contagem do 20º e 21º lugar, o número de usuários no corte, nulos de `userId` e IDs distintos.

```sql
WITH pu AS (
  SELECT userId, COUNT(*) AS n FROM refined.avaliacoes GROUP BY userId
), ranked AS (
  SELECT userId, n, ROW_NUMBER() OVER (ORDER BY n DESC) AS rn FROM pu
)
SELECT MAX(n) FILTER (WHERE rn = 20) AS vigesimo,
  MAX(n) FILTER (WHERE rn = 21) AS vigesimo_primeiro,
  COUNT(*) FILTER (WHERE n = (SELECT n FROM ranked WHERE rn = 20)) AS empate_corte,
  (SELECT COUNT(*) FROM refined.avaliacoes WHERE userId IS NULL) AS linhas_userId_nulo,
  (SELECT COUNT(DISTINCT userId) FROM refined.avaliacoes) AS users_distintos
FROM ranked;
```

**Resultado:** 20º lugar = **4.785**, 21º = **4.707**, apenas **1** usuário na contagem do corte; nenhum `userId` nulo e **270.896** usuários distintos.

Também se verificou duplicidade de avaliação para o mesmo usuário e filme:

```sql
WITH pares AS (
  SELECT userId, movieId, COUNT(*) AS n
  FROM refined.avaliacoes GROUP BY userId, movieId
)
SELECT COUNT(*) FILTER (WHERE n > 1) AS pares_usuario_filme_duplicados,
  SUM(n - 1) FILTER (WHERE n > 1) AS registros_excedentes
FROM pares;
```

Resultado: **0 pares `(userId, movieId)` duplicados**. `registros_excedentes` retornou NULL porque não havia pares a somar.

### Resultado materializado

Consulta executada: `SELECT userId, total_avaliacoes, nota_media_usuario FROM marts.usuarios_mais_ativos ORDER BY total_avaliacoes DESC, userId;`.

| userId | Avaliações | Média |
|---:|---:|---:|
| 45811 | 18.276 | 3,20 |
| 8659 | 9.279 | 3,28 |
| 270123 | 7.638 | 2,60 |
| 179792 | 7.515 | 3,21 |
| 228291 | 7.410 | 3,22 |
| 243443 | 6.320 | 1,58 |
| 98415 | 6.094 | 2,80 |
| 229879 | 6.024 | 3,50 |
| 98787 | 5.814 | 2,44 |
| 172224 | 5.701 | 3,75 |
| 230417 | 5.619 | 0,86 |
| 70648 | 5.356 | 3,01 |
| 194690 | 5.206 | 2,47 |
| 107720 | 5.169 | 2,40 |
| 24025 | 4.946 | 3,21 |
| 165352 | 4.921 | 1,14 |
| 101276 | 4.834 | 2,86 |
| 243331 | 4.834 | 3,04 |
| 74275 | 4.815 | 2,99 |
| 41190 | 4.785 | 3,22 |

A auditoria do indicador 04 confirmou que todos os ratings são não nulos e estão no domínio de 0,5 a 5,0 em incrementos de 0,5.

## Avaliação metodológica e limitações

- O agrupamento por `userId` preserva uma linha por usuário; não há usuários nulos nem pares repetidos usuário/filme no conjunto observado.
- A média simples é a média de todas as notas dadas pelo usuário. A classificação “mais ativo” usa exclusivamente quantidade de avaliações, não recência, tempo de participação ou diversidade de filmes.
- Não há empate atravessando o limite do Top 20. Há dois usuários com 4.834 avaliações dentro do Top 20; a ordenação entre eles pode variar, mas ambos estão acima do corte e a população não muda.
- A mart corresponde exatamente ao recálculo.

## Parecer

**APROVADO.** Grão, contagem, média e seleção Top 20 estão consistentes, sem nulos de usuário ou duplicidade usuário/filme observada. A leitura do ranking como volume bruto de atividade é inerente à pergunta definida.
