# Auditoria metodológica — Indicador 06

**Indicador:** volume e nota média MovieLens por ano<br>
**SQL auditado:** `sql/marts/06_nota_media_movielens_ao_longo_do_tempo.sql`<br>
**Tabela comparada:** `marts.nota_media_movielens_ao_longo_do_tempo`<br>
**Parecer:** **APROVADO**

> **Atualização pós-publicação — 2 nov. 2026:** a classificação anual oficial usa UTC por meio de `TO_TIMESTAMP(timestamp) AT TIME ZONE 'UTC'`. A publicação seletiva atualizou `marts.nota_media_movielens_ao_longo_do_tempo`, que contém **23 linhas** para **1995–2017**. Na auditoria posterior, `EXCEPT ALL` retornou **0 diferenças** em referência → MART e **0** em MART → referência. A publicação seletiva preservou as outras oito MARTs. O resultado pré-publicação, com 44 diferenças, fica registrado abaixo como histórico.

## Pergunta, grão e metodologia

A consulta informa o total de avaliações e a média aritmética de `rating` por ano UTC da avaliação. Cada linha de origem representa uma avaliação; o ano é extraído de `TO_TIMESTAMP(timestamp) AT TIME ZONE 'UTC'`. Não há JOIN. O volume é `COUNT(*)`; a média é `ROUND(AVG(rating), 3)`.

## Consultas executadas e resultados

### Recálculo e comparação com a mart

```sql
WITH esperado AS (
  SELECT EXTRACT(YEAR FROM TO_TIMESTAMP(timestamp) AT TIME ZONE 'UTC') AS ano_avaliacao,
    COUNT(*) AS total_avaliacoes, ROUND(AVG(rating), 3) AS nota_media
  FROM refined.avaliacoes
  GROUP BY EXTRACT(YEAR FROM TO_TIMESTAMP(timestamp) AT TIME ZONE 'UTC')
), diferencas AS (
  (SELECT * FROM esperado EXCEPT ALL
   SELECT * FROM marts.nota_media_movielens_ao_longo_do_tempo)
  UNION ALL
  (SELECT * FROM marts.nota_media_movielens_ao_longo_do_tempo EXCEPT ALL
   SELECT * FROM esperado)
)
SELECT (SELECT COUNT(*) FROM esperado) AS anos_esperados,
  (SELECT COUNT(*) FROM marts.nota_media_movielens_ao_longo_do_tempo) AS anos_mart,
  (SELECT COUNT(*) FROM diferencas) AS diferencas,
  (SELECT SUM(total_avaliacoes) FROM esperado) AS total_avaliacoes,
  (SELECT MIN(ano_avaliacao) FROM esperado) AS primeiro_ano,
  (SELECT MAX(ano_avaliacao) FROM esperado) AS ultimo_ano;
```

**Resultado:** 23 anos recalculados e 23 na mart; **0 diferenças**; 26.024.289 avaliações no total; anos de 1995 a 2017.

### Comparação de ano local com ano UTC

O fuso retornado por `current_setting('TimeZone')` na conexão MCP é `America/Sao_Paulo` (ver evidência detalhada no relatório do indicador 05). Executou-se a seguinte comparação entre ano da sessão e ano UTC:

```sql
WITH por_local AS (
  SELECT EXTRACT(YEAR FROM TO_TIMESTAMP(timestamp)) AS ano,
    COUNT(*) AS n_local, ROUND(AVG(rating), 3) AS media_local
  FROM refined.avaliacoes GROUP BY 1
), por_utc AS (
  SELECT EXTRACT(YEAR FROM TO_TIMESTAMP(timestamp) AT TIME ZONE 'UTC') AS ano,
    COUNT(*) AS n_utc, ROUND(AVG(rating), 3) AS media_utc
  FROM refined.avaliacoes GROUP BY 1
)
SELECT COUNT(*) FILTER (WHERE COALESCE(l.n_local,0) <> COALESCE(u.n_utc,0))
    AS anos_contagens_divergentes,
  COUNT(*) FILTER (WHERE l.media_local IS DISTINCT FROM u.media_utc)
    AS anos_medias_arredondadas_divergentes,
  MAX(ABS(COALESCE(l.media_local,0)-COALESCE(u.media_utc,0)))
    AS diferenca_maxima_media,
  SUM(ABS(COALESCE(l.n_local,0)-COALESCE(u.n_utc,0)))
    AS soma_diferencas_abs_contagens
FROM por_local l FULL JOIN por_utc u USING (ano);
```

**Resultado:** contagens diferem em **22** anos; a média arredondada difere em **1** ano; maior diferença absoluta entre médias arredondadas: **0,0009999999999998899** (aproximadamente 0,001); soma das diferenças absolutas das contagens por ano: **4.220**. No indicador 05, a comparação por registro mostrou que **7.394** timestamps trocam de ano entre fuso local e UTC.

### Resultado materializado antes da republicação (histórico)

Os valores abaixo documentam a MART anterior à adoção/materialização da regra UTC e não representam o resultado atual. A MART republicada foi comparada com a consulta UTC: 23 linhas, 1995–2017, zero diferenças em cada direção de `EXCEPT ALL`.

Consulta executada: `SELECT ano_avaliacao, total_avaliacoes, nota_media FROM marts.nota_media_movielens_ao_longo_do_tempo ORDER BY ano_avaliacao;`.

| Ano | Avaliações | Média | Ano | Avaliações | Média |
|---:|---:|---:|---:|---:|---:|
| 1995 | 4 | 3,750 | 2007 | 1.096.238 | 3,464 |
| 1996 | 1.733.473 | 3,554 | 2008 | 1.210.914 | 3,527 |
| 1997 | 763.774 | 3,592 | 2009 | 994.098 | 3,491 |
| 1998 | 329.668 | 3,523 | 2010 | 982.811 | 3,510 |
| 1999 | 1.231.494 | 3,617 | 2011 | 835.433 | 3,536 |
| 2000 | 2.034.072 | 3,578 | 2012 | 793.738 | 3,586 |
| 2001 | 1.239.954 | 3,536 | 2013 | 634.597 | 3,626 |
| 2002 | 910.875 | 3,484 | 2014 | 586.062 | 3,596 |
| 2003 | 1.079.526 | 3,472 | 2015 | 1.913.997 | 3,575 |
| 2004 | 1.202.086 | 3,427 | 2016 | 2.095.272 | 3,537 |
| 2005 | 1.850.023 | 3,432 | 2017 | 1.294.536 | 3,555 |
| 2006 | 1.211.644 | 3,460 |  |  |  |

A auditoria do indicador 04 confirmou zero ratings nulos e domínio válido; portanto `AVG(rating)` considera todas as linhas desta fonte. A soma das contagens anuais é 26.024.289.

## Avaliação metodológica e limitações

- A média é a média simples de ratings individuais, apropriada para “nota média das avaliações” por ano. Não é média de médias por filme nem por usuário.
- `COUNT(*)` e `AVG(rating)` usam a mesma população no conjunto auditado, pois não há ratings nulos. Não há JOINs, perdas ou multiplicações.
- A MART atual reproduz exatamente a expressão SQL oficial UTC: zero divergências nas duas direções de `EXCEPT ALL`.
- **Evidência histórica:** antes da republicação, a sessão em `America/Sao_Paulo` classificava 7.394 avaliações em ano diferente de UTC; 22 contagens anuais e uma média arredondada diferiam. A MART antiga divergia em 44 linhas no `EXCEPT ALL` bidirecional. Essa diferença foi resolvida pela atualização seletiva.
- A média anual é descritiva; mudanças de composição de usuários, filmes avaliados ou atividade não são ajustadas.

## Parecer

**APROVADO.** A média aritmética e o volume estão corretamente calculados sob o critério UTC explícito. A MART foi republicada seletivamente e coincide exatamente com a referência: 23 linhas, anos de 1995 a 2017 e zero diferenças nas duas direções de `EXCEPT ALL`. As demais oito MARTs foram preservadas.
