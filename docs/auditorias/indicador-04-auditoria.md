# Auditoria metodológica — Indicador 04

**Indicador:** distribuição das notas MovieLens<br>
**SQL auditado:** `sql/marts/04_distribuicao_notas_movielens.sql`<br>
**Tabela comparada:** `marts.distribuicao_notas_movielens`<br>
**Parecer:** **APROVADO**

## Pergunta, grão e metodologia

A consulta mostra como os ratings MovieLens se distribuem por valor de nota. Cada linha de `refined.avaliacoes` representa uma avaliação; o resultado tem uma linha por valor distinto de `rating`. `COUNT(*)` conta as avaliações em cada valor, e o percentual usa como denominador todas as linhas da tabela:

\[
\text{percentual}_r = 100 \times \frac{\text{contagem de avaliações com rating }r}{\text{total de avaliações}}
\]

Não há JOIN nem CTE. A unidade contada é uma avaliação, não um filme ou usuário.

## Consultas executadas e resultados

### Recálculo e comparação com a mart

```sql
WITH esperado AS (
  SELECT rating, COUNT(*) AS total_avaliacoes,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS percentual
  FROM refined.avaliacoes GROUP BY rating
), diferencas AS (
  (SELECT * FROM esperado EXCEPT ALL
   SELECT * FROM marts.distribuicao_notas_movielens)
  UNION ALL
  (SELECT * FROM marts.distribuicao_notas_movielens EXCEPT ALL
   SELECT * FROM esperado)
)
SELECT (SELECT COUNT(*) FROM esperado) AS notas_distintas,
  (SELECT COUNT(*) FROM marts.distribuicao_notas_movielens) AS linhas_mart,
  (SELECT COUNT(*) FROM diferencas) AS diferencas,
  (SELECT SUM(total_avaliacoes) FROM esperado) AS total_avaliacoes,
  (SELECT SUM(percentual) FROM marts.distribuicao_notas_movielens) AS soma_percentuais;
```

**Resultado:** 10 notas, 10 linhas materializadas, **0 diferenças**, total de **26.024.289** avaliações. A soma dos percentuais arredondados é **99,99000000000001%** (99,99% na precisão exibida).

### Nulos e domínio dos ratings

```sql
SELECT COUNT(*) AS total_linhas, COUNT(rating) AS ratings_validos,
  COUNT(*) - COUNT(rating) AS ratings_nulos,
  MIN(rating) AS minimo, MAX(rating) AS maximo,
  COUNT(*) FILTER (WHERE rating < 0.5 OR rating > 5) AS fora_escala,
  COUNT(*) FILTER (WHERE rating * 2 <> ROUND(rating * 2)) AS fora_incremento_0_5,
  COUNT(DISTINCT rating) AS valores_distintos
FROM refined.avaliacoes;
```

**Resultado:** 26.024.289 linhas e ratings válidos; **0** nulos; mínimo 0,5, máximo 5,0; **0** fora da escala 0,5–5; **0** fora dos incrementos de 0,5; 10 valores distintos.

### Distribuição materializada

Consulta executada: `SELECT rating, total_avaliacoes, percentual FROM marts.distribuicao_notas_movielens ORDER BY rating;`.

| Rating | Avaliações | Percentual |
|---:|---:|---:|
| 0,5 | 404.897 | 1,56% |
| 1,0 | 843.310 | 3,24% |
| 1,5 | 403.607 | 1,55% |
| 2,0 | 1.762.440 | 6,77% |
| 2,5 | 1.255.358 | 4,82% |
| 3,0 | 5.256.722 | 20,20% |
| 3,5 | 3.116.213 | 11,97% |
| 4,0 | 6.998.802 | 26,89% |
| 4,5 | 2.170.441 | 8,34% |
| 5,0 | 3.812.499 | 14,65% |

## Avaliação metodológica e limitações

- Todos os ratings são não nulos, pertencem ao domínio esperado e usam incrementos de 0,5; não há registro inválido que precise de tratamento adicional nesta consulta.
- O denominador é o total de avaliações da tabela, coerente com a interpretação. Os percentuais somam 99,99% por arredondamento individual a duas casas; não é perda de registros.
- A distribuição descreve volume de avaliações, sem ajustar por usuário, filme ou data. Isso é coerente com a pergunta e não deve ser interpretado como distribuição de notas por filme ou por usuário.
- O recálculo corresponde integralmente à tabela materializada.

## Parecer

**APROVADO.** O grão, a contagem, o denominador percentual e a mart são consistentes; não foram encontrados nulos ou ratings fora do domínio. A diferença de 0,01 ponto percentual no total exibido decorre do arredondamento.
