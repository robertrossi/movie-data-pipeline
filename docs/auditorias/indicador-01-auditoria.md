# Auditoria metodológica — Indicador 01

**Indicador:** filmes lançados por ano, de 2000 a 2016<br>
**SQL auditado:** `sql/marts/01_filmes_lancados_por_ano.sql`<br>
**Tabela comparada:** `marts.filmes_lancados_por_ano`<br>
**Parecer:** **APROVADO COM RESSALVAS**

## Pergunta, grão e metodologia

A consulta responde quantos registros de filme em `refined.filmes` têm `release_date` em cada ano civil de 2000 a 2016, inclusive. O grão de origem é uma linha por filme TMDB (`id`); o resultado tem uma linha por ano (`release_year`). A auditoria confirmou 45.420 linhas, todos com `id` não nulo e distintos. O indicador não usa JOINs.

O SQL exclui datas nulas e filtra o intervalo semiaberto `[2000-01-01, 2017-01-01)`, que inclui todos os dias de 2000 a 2016 sem incluir 2017. `COUNT(*)` conta cada filme elegível uma vez. Foram comparados os resultados recalculados da fonte com a tabela materializada usando `EXCEPT ALL` nas duas direções.

## Consultas executadas e evidências

### Consistência com a tabela materializada

```sql
WITH esperado AS (
  SELECT EXTRACT(YEAR FROM release_date) AS release_year, COUNT(*) AS total_movies
  FROM refined.filmes
  WHERE release_date IS NOT NULL
    AND release_date >= DATE '2000-01-01'
    AND release_date < DATE '2017-01-01'
  GROUP BY EXTRACT(YEAR FROM release_date)
), diferencas AS (
  (SELECT * FROM esperado EXCEPT ALL
   SELECT * FROM marts.filmes_lancados_por_ano)
  UNION ALL
  (SELECT * FROM marts.filmes_lancados_por_ano EXCEPT ALL
   SELECT * FROM esperado)
)
SELECT (SELECT COUNT(*) FROM esperado) AS linhas_esperadas,
  (SELECT COUNT(*) FROM marts.filmes_lancados_por_ano) AS linhas_mart,
  (SELECT COUNT(*) FROM diferencas) AS diferencas_entre_esperado_e_mart,
  (SELECT MIN(release_year) FROM marts.filmes_lancados_por_ano) AS primeiro_ano,
  (SELECT MAX(release_year) FROM marts.filmes_lancados_por_ano) AS ultimo_ano;
```

**Resultado:** 17 linhas esperadas, 17 na mart, **0 diferenças**, anos mínimo e máximo 2000 e 2016.

### Unicidade das chaves, nulos e cobertura temporal

```sql
SELECT COUNT(*) AS filmes_total, COUNT(id) AS ids_nao_nulos,
  COUNT(*) - COUNT(id) AS ids_nulos, COUNT(DISTINCT id) AS ids_distintos,
  COUNT(*) FILTER (WHERE release_date IS NULL) AS datas_nulas,
  COUNT(*) FILTER (WHERE release_date < DATE '2000-01-01'
    OR release_date >= DATE '2017-01-01') AS fora_periodo,
  COUNT(*) FILTER (WHERE release_date >= DATE '2000-01-01'
    AND release_date < DATE '2017-01-01') AS dentro_periodo
FROM refined.filmes;
```

**Resultado:** 45.420 filmes; 45.420 IDs não nulos e distintos; 0 IDs nulos; 87 datas nulas; 21.891 datas fora do período e 23.442 dentro do período.

### Resultado materializado por ano

```sql
SELECT release_year, total_movies
FROM marts.filmes_lancados_por_ano ORDER BY release_year;
```

| Ano | Filmes | Ano | Filmes |
|---:|---:|---:|---:|
| 2000 | 787 | 2009 | 1.585 |
| 2001 | 862 | 2010 | 1.501 |
| 2002 | 901 | 2011 | 1.665 |
| 2003 | 882 | 2012 | 1.720 |
| 2004 | 992 | 2013 | 1.886 |
| 2005 | 1.123 | 2014 | 1.973 |
| 2006 | 1.268 | 2015 | 1.904 |
| 2007 | 1.319 | 2016 | 1.604 |
| 2008 | 1.470 |  |  |

## Avaliação metodológica e limitações

- A chave `refined.filmes.id` está completa e sem duplicidade segundo a consulta executada (`COUNT(*) = COUNT(id) = COUNT(DISTINCT id)`), portanto `COUNT(*)` não duplica filmes por chave.
- Não há JOINs, agregações incompatíveis ou valores inválidos envolvidos no cálculo além da exclusão explícita de `release_date IS NULL`.
- As 87 datas nulas são excluídas. O período também é intencionalmente limitado a 2000–2016; 21.891 registros com data fora dele não pertencem ao indicador.
- A consulta conta filmes no catálogo TMDB com data elegível, independentemente de haver avaliação MovieLens. Isso é coerente com a pergunta de lançamentos e não mede popularidade, cobertura MovieLens ou filmes únicos após deduplicação externa ao `id`.
- A comparação integral confirma que a tabela materializada corresponde à consulta atual.

## Parecer

**APROVADO COM RESSALVAS.** Cálculo, grão anual, filtro de datas, chave e tabela materializada são consistentes. A ressalva é de escopo e cobertura: 87 filmes sem data não são contabilizados, e o resultado deliberadamente cobre apenas os anos de 2000 a 2016.
