# Auditoria metodológica — Indicador 05

**Indicador:** avaliações MovieLens ao longo do tempo<br>
**SQL auditado:** `sql/marts/05_avaliacoes_movielens_ao_longo_do_tempo.sql`<br>
**Tabela comparada:** `marts.avaliacoes_movielens_ao_longo_do_tempo`<br>
**Parecer:** **APROVADO**

> **Atualização pós-publicação — 2 nov. 2026:** a classificação anual oficial usa UTC por meio de `TO_TIMESTAMP(timestamp) AT TIME ZONE 'UTC'`. A publicação seletiva atualizou `marts.avaliacoes_movielens_ao_longo_do_tempo`, que contém **23 linhas** para **1995–2017**. Na auditoria posterior, `EXCEPT ALL` retornou **0 diferenças** em referência → MART e **0** em MART → referência. A publicação seletiva preservou as outras oito MARTs. O resultado pré-publicação, com 44 diferenças, fica registrado abaixo como histórico.

## Pergunta, grão e metodologia

A consulta conta avaliações MovieLens por ano UTC, convertendo `timestamp` (epoch em segundos) com `TO_TIMESTAMP(timestamp) AT TIME ZONE 'UTC'` e extraindo o ano. O grão de origem é uma avaliação por linha; o grão de saída é um ano de avaliação. Não há JOINs ou agregações além da contagem anual.

## Consultas executadas e resultados

### Recálculo e comparação com a mart

```sql
WITH esperado AS (
  SELECT EXTRACT(YEAR FROM TO_TIMESTAMP(timestamp) AT TIME ZONE 'UTC') AS ano_avaliacao,
    COUNT(*) AS total_avaliacoes
  FROM refined.avaliacoes
  GROUP BY EXTRACT(YEAR FROM TO_TIMESTAMP(timestamp) AT TIME ZONE 'UTC')
), diferencas AS (
  (SELECT * FROM esperado EXCEPT ALL
   SELECT * FROM marts.avaliacoes_movielens_ao_longo_do_tempo)
  UNION ALL
  (SELECT * FROM marts.avaliacoes_movielens_ao_longo_do_tempo EXCEPT ALL
   SELECT * FROM esperado)
)
SELECT (SELECT COUNT(*) FROM esperado) AS anos_esperados,
  (SELECT COUNT(*) FROM marts.avaliacoes_movielens_ao_longo_do_tempo) AS anos_mart,
  (SELECT COUNT(*) FROM diferencas) AS diferencas,
  (SELECT SUM(total_avaliacoes) FROM esperado) AS total_avaliacoes,
  (SELECT MIN(ano_avaliacao) FROM esperado) AS primeiro_ano,
  (SELECT MAX(ano_avaliacao) FROM esperado) AS ultimo_ano;
```

**Resultado:** 23 anos recalculados e 23 na mart; **0 diferenças**; total **26.024.289**; primeiro ano 1995 e último 2017.

### Qualidade do timestamp

```sql
SELECT COUNT(*) AS total_linhas, COUNT(timestamp) AS timestamps_nao_nulos,
  COUNT(*) - COUNT(timestamp) AS timestamps_nulos,
  COUNT(*) FILTER (WHERE timestamp < 0) AS timestamps_negativos,
  MIN(timestamp) AS timestamp_minimo, MAX(timestamp) AS timestamp_maximo,
  MIN(TO_TIMESTAMP(timestamp)) AS instante_minimo,
  MAX(TO_TIMESTAMP(timestamp)) AS instante_maximo
FROM refined.avaliacoes;
```

**Resultado:** 26.024.289 timestamps, todos não nulos e não negativos. Epoch mínimo **789.652.004**, máximo **1.501.829.870**; instantes apresentados pela MCP: `1995-01-09 09:46:44-02:00` e `2017-08-04 03:57:50-03:00`.

### Fuso horário aplicado

Consulta executada: `SELECT current_setting('TimeZone') AS timezone_sessao;`. Resultado: **`America/Sao_Paulo`**.

Foi comparado o ano extraído diretamente de `TO_TIMESTAMP(timestamp)` com o ano UTC explícito:

```sql
WITH anos AS (
  SELECT EXTRACT(YEAR FROM TO_TIMESTAMP(timestamp)) AS ano_sessao,
    EXTRACT(YEAR FROM TO_TIMESTAMP(timestamp) AT TIME ZONE 'UTC') AS ano_utc
  FROM refined.avaliacoes
)
SELECT COUNT(*) FILTER (WHERE ano_sessao <> ano_utc) AS registros_com_ano_divergente,
  COUNT(DISTINCT ano_sessao) AS anos_sessao,
  COUNT(DISTINCT ano_utc) AS anos_utc,
  MIN(ano_utc) AS primeiro_ano_utc,
  MAX(ano_utc) AS ultimo_ano_utc
FROM anos;
```

Resultado: **7.394 avaliações** têm ano local diferente do ano UTC; ambas as classificações contêm 23 anos, 1995–2017.

Para localizar o efeito anual, executou-se agrupamento por ano em cada referencial e `FULL JOIN` pelas colunas `ano`, exibindo apenas contagens diferentes. A coluna abaixo é `contagem_sessao_local - contagem_utc`:

| Ano | Diferença local − UTC | Ano | Diferença local − UTC |
|---:|---:|---:|---:|
| 1996 | +210 | 2007 | +135 |
| 1997 | −158 | 2008 | −153 |
| 1998 | −52 | 2009 | +164 |
| 1999 | +231 | 2010 | −212 |
| 2000 | +42 | 2011 | +173 |
| 2001 | +236 | 2012 | +28 |
| 2002 | +216 | 2013 | −181 |
| 2003 | +15 | 2014 | −32 |
| 2004 | +5 | 2015 | +277 |
| 2005 | −566 | 2016 | +311 |
| 2006 | +67 | 2017 | −756 |

### Resultado materializado antes da republicação (histórico)

Os valores abaixo documentam a MART anterior à adoção/materialização da regra UTC e não representam o resultado atual. A MART republicada foi comparada com a consulta UTC: 23 linhas, 1995–2017, zero diferenças em cada direção de `EXCEPT ALL`.

Consulta executada: `SELECT ano_avaliacao, total_avaliacoes FROM marts.avaliacoes_movielens_ao_longo_do_tempo ORDER BY ano_avaliacao;`.

| Ano | Avaliações | Ano | Avaliações |
|---:|---:|---:|---:|
| 1995 | 4 | 2007 | 1.096.238 |
| 1996 | 1.733.473 | 2008 | 1.210.914 |
| 1997 | 763.774 | 2009 | 994.098 |
| 1998 | 329.668 | 2010 | 982.811 |
| 1999 | 1.231.494 | 2011 | 835.433 |
| 2000 | 2.034.072 | 2012 | 793.738 |
| 2001 | 1.239.954 | 2013 | 634.597 |
| 2002 | 910.875 | 2014 | 586.062 |
| 2003 | 1.079.526 | 2015 | 1.913.997 |
| 2004 | 1.202.086 | 2016 | 2.095.272 |
| 2005 | 1.850.023 | 2017 | 1.294.536 |
| 2006 | 1.211.644 |  |  |

## Avaliação metodológica e limitações

- A contagem preserva o grão de avaliação e inclui todas as 26.024.289 linhas. Não foram encontrados timestamps nulos ou negativos, e não há JOINs que possam multiplicar ou excluir linhas.
- A MART atual é exatamente consistente com a consulta oficial UTC: zero divergências nas duas direções de `EXCEPT ALL`.
- **Evidência histórica:** antes da republicação, a sessão em `America/Sao_Paulo` classificava 7.394 avaliações em ano diferente de UTC e a MART antiga divergia em 44 linhas no `EXCEPT ALL` bidirecional. Essa diferença foi resolvida pela atualização seletiva.
- A sazonalidade temporal não é ajustada por volume de usuários ativos, quantidade de filmes disponíveis ou outros fatores; a consulta descreve contagem bruta de avaliações por ano.

## Parecer

**APROVADO.** A consulta UTC preserva o grão e cobre todas as avaliações. A MART foi republicada seletivamente e coincide exatamente com a referência: 23 linhas, anos de 1995 a 2017 e zero diferenças nas duas direções de `EXCEPT ALL`. As demais oito MARTs foram preservadas.
