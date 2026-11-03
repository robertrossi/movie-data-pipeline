# Indicador 01 — Quantidade de filmes por ano de lançamento

A seção metodológica abaixo reproduz as informações registradas para este indicador em `indicadores.md`.

## Definição e evidências metodológicas

- **Nome:** Movies Released by Year (TMDB).
- **Objetivo de negócio:** Acompanhar a distribuição anual dos filmes presentes no catálogo TMDB, considerando seu ano de lançamento.
- **Tabelas e colunas utilizadas:** `refined.filmes`: `id`, `release_date` e `status`.
- **Granularidade:** Ano de lançamento.
- **Regra de cálculo:** Contar os filmes por ano de `release_date`, utilizando as datas válidas e os registros presentes na camada refined.
- **Resultado exploratório:** Foram identificadas 45.420 linhas, das quais 87 possuem data de lançamento ausente. Entre os anos de 2000 e 2016, a quantidade anual variou de 787 filmes em 2000 a 1.973 em 2014. Em 2016 foram registrados 1.604 filmes e, em 2017, 532.
- **Classificação:** **Dá, mas...**
- **Justificativa da classificação:** O indicador é calculável, mas a cobertura temporal apresenta uma queda expressiva a partir de 2017. A análise do campo `status` não explicou essa redução.
- **Ressalvas:** O período principal recomendado para apresentação é 2000–2016. O indicador descreve o catálogo disponível, não a produção cinematográfica mundial. Não se deve interpretar a queda a partir de 2017 como redução real da produção de filmes.

## Auditoria

[Auditoria metodológica do indicador 01](../auditorias/indicador-01-auditoria.md)

## Consulta SQL correspondente

Arquivo fonte: `sql/marts/01_filmes_lancados_por_ano.sql`.

```sql
-- Pergunta de negócio: quantos filmes foram lançados em cada ano, entre 2000 e 2016?
-- Grão do resultado final: uma linha por ano de lançamento (release_year).
-- Fonte refined.filmes: cada linha representa um filme; COUNT(*) conta os filmes
-- com data de lançamento válida dentro do intervalo definido na consulta.
SELECT
    EXTRACT(YEAR FROM release_date) AS release_year,
    COUNT(*) AS total_movies
FROM refined.filmes
WHERE release_date IS NOT NULL
  AND release_date >= DATE '2000-01-01'
  AND release_date < DATE '2017-01-01'
GROUP BY
    EXTRACT(YEAR FROM release_date)
ORDER BY
    release_year;
```
