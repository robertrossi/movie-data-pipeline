# Auditoria metodológica — Indicador 09

**Indicador:** distribuição de usuários por quantidade de avaliações<br>
**SQL auditado:** `sql/marts/09_distribuicao_avaliacoes_por_usuario.sql`<br>
**Tabela comparada:** `marts.distribuicao_avaliacoes_por_usuario`<br>
**Parecer:** **APROVADO COM RESSALVAS**

## Pergunta, grão e metodologia

A pergunta é como os usuários se distribuem por faixas de quantidade de avaliações. A primeira CTE agrega `refined.avaliacoes` por `userId`, produzindo uma linha por usuário com seu volume. A segunda atribui cada usuário a uma única faixa. O resultado final tem uma linha por faixa, conta usuários e calcula seu percentual sobre todos os usuários classificados. Não há JOINs.

As faixas codificadas são 1–10, 11–50, 51–100, 101–500, 501–1.000, 1.001–5.000, 5.001–10.000 e `ELSE '10000+'`. Como cada usuário surge de pelo menos uma linha agrupada, seu volume é >= 1; `ELSE` representa volumes acima de 10.000 na implementação atual.

## Consultas executadas e resultados

### Recálculo e comparação com a mart

```sql
WITH apu AS (
  SELECT userId, COUNT(*) AS total_avaliacoes
  FROM refined.avaliacoes GROUP BY userId
), uc AS (
  SELECT userId, total_avaliacoes,
    CASE
      WHEN total_avaliacoes BETWEEN 1 AND 10 THEN '01-10'
      WHEN total_avaliacoes BETWEEN 11 AND 50 THEN '11-50'
      WHEN total_avaliacoes BETWEEN 51 AND 100 THEN '51-100'
      WHEN total_avaliacoes BETWEEN 101 AND 500 THEN '101-500'
      WHEN total_avaliacoes BETWEEN 501 AND 1000 THEN '501-1000'
      WHEN total_avaliacoes BETWEEN 1001 AND 5000 THEN '1001-5000'
      WHEN total_avaliacoes BETWEEN 5001 AND 10000 THEN '5001-10000'
      ELSE '10000+'
    END AS faixa_avaliacoes
  FROM apu
), esperado AS (
  SELECT faixa_avaliacoes, COUNT(*) AS total_usuarios,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS percentual_usuarios
  FROM uc GROUP BY faixa_avaliacoes
), diferencas AS (
  (SELECT * FROM esperado EXCEPT ALL
   SELECT * FROM marts.distribuicao_avaliacoes_por_usuario)
  UNION ALL
  (SELECT * FROM marts.distribuicao_avaliacoes_por_usuario EXCEPT ALL
   SELECT * FROM esperado)
)
SELECT (SELECT COUNT(*) FROM esperado) AS faixas_esperadas,
  (SELECT COUNT(*) FROM marts.distribuicao_avaliacoes_por_usuario) AS faixas_mart,
  (SELECT COUNT(*) FROM diferencas) AS diferencas,
  (SELECT COUNT(*) FROM apu) AS total_usuarios,
  (SELECT SUM(total_usuarios) FROM marts.distribuicao_avaliacoes_por_usuario)
    AS usuarios_na_mart,
  (SELECT SUM(percentual_usuarios) FROM marts.distribuicao_avaliacoes_por_usuario)
    AS soma_percentuais;
```

**Resultado:** 8 faixas esperadas e 8 na mart; **0 diferenças**; **270.896** usuários classificados e somados; percentuais materializados somam **99,99000000000001%** (99,99% após arredondamento exibido).

### Cobertura e extremos dos volumes

Consulta executada sobre `apu` e a mesma expressão `CASE` das faixas:

```sql
WITH apu AS (
  SELECT userId, COUNT(*) AS n FROM refined.avaliacoes GROUP BY userId
), bandas AS (
  SELECT *, CASE
    WHEN n BETWEEN 1 AND 10 THEN '01-10'
    WHEN n BETWEEN 11 AND 50 THEN '11-50'
    WHEN n BETWEEN 51 AND 100 THEN '51-100'
    WHEN n BETWEEN 101 AND 500 THEN '101-500'
    WHEN n BETWEEN 501 AND 1000 THEN '501-1000'
    WHEN n BETWEEN 1001 AND 5000 THEN '1001-5000'
    WHEN n BETWEEN 5001 AND 10000 THEN '5001-10000'
    ELSE '10000+' END AS faixa
  FROM apu
)
SELECT COUNT(*) AS usuarios,
  COUNT(*) FILTER (WHERE userId IS NULL) AS userId_nulo,
  MIN(n) AS minimo_avaliacoes_usuario,
  MAX(n) AS maximo_avaliacoes_usuario,
  COUNT(*) FILTER (WHERE faixa IS NULL) AS sem_faixa,
  COUNT(DISTINCT faixa) AS faixas
FROM bandas;
```

**Resultado:** 270.896 usuários; 0 `userId` nulo; volumes mínimo e máximo 1 e 18.276; 0 sem faixa; 8 faixas observadas.

Verificaram-se também os volumes nos limites das faixas por usuário. Contagens nos valores 10, 11, 50, 51, 100, 101, 500, 501, 1.000, 1.001, 5.000, 5.001, 10.000 e acima de 10.000: **6.795; 4.412; 1.460; 1.267; 856; 689; 64; 41; 7; 6; 0; 0; 0; 1**, respectivamente. Assim, não há usuários com exatamente 5.000, 5.001, 10.000 nem acima de 10.000, exceto um acima do limite, com máximo geral 18.276.

### Resultado materializado

Consulta executada sobre `marts.distribuicao_avaliacoes_por_usuario`, ordenada pela ordem definida das faixas:

| Faixa | Usuários | Percentual |
|---|---:|---:|
| 01-10 | 43.788 | 16,16% |
| 11-50 | 124.729 | 46,04% |
| 51-100 | 38.802 | 14,32% |
| 101-500 | 54.125 | 19,98% |
| 501-1000 | 6.950 | 2,57% |
| 1001-5000 | 2.488 | 0,92% |
| 5001-10000 | 13 | 0,00% |
| 10000+ | 1 | 0,00% |

## Avaliação metodológica e limitações

- Cada usuário agregado é atribuído a uma única faixa; as faixas cobrem todos os volumes observados, de 1 a 18.276. Não há JOINs que alterem a cardinalidade.
- A proporção usa o total de usuários, não o total de avaliações, coerente com a pergunta sobre distribuição de usuários.
- O rótulo `10000+` tem uma ambiguidade de fronteira: o `CASE` anterior inclui 10.000 em `5001-10000`, então `10000+` significa estritamente acima de 10.000. Não há usuário com exatamente 10.000 no conjunto auditado, mas a definição do rótulo deve permanecer documentada ou ser clarificada se a população mudar.
- As duas faixas menores têm contagens positivas (13 e 1), mas exibem `0,00%` por arredondamento a duas casas. Isso pode ocultar visualmente uma proporção pequena; as contagens continuam corretas. As percentagens somam 99,99% por arredondamento.
- O indicador mede volume acumulado, não recência, duração de participação ou intensidade por período.
- A mart corresponde exatamente ao recálculo.

## Parecer

**APROVADO COM RESSALVAS.** A classificação em faixas, a contagem de usuários, o denominador percentual e a mart estão consistentes. Recomenda-se documentar que `10000+` significa `>10000` nesta implementação e considerar a apresentação de precisão suficiente para não exibir 0,00% quando há usuários na faixa.
