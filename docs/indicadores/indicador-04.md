# Indicador 04 — Distribuição das avaliações MovieLens

A seção metodológica abaixo reproduz as informações registradas para este indicador em `indicadores.md`.

## Definição e evidências metodológicas

- **Nome:** MovieLens Rating Distribution.
- **Objetivo de negócio:** Compreender a distribuição das notas atribuídas pelos usuários MovieLens.
- **Tabelas e colunas utilizadas:** `refined.avaliacoes`: `rating`.
- **Granularidade:** Nota atribuída.
- **Regra de cálculo:** Contar as avaliações por valor de `rating` e calcular sua participação percentual sobre o total.
- **Resultado exploratório:** Foram analisadas 26.024.289 avaliações, distribuídas entre notas de 0,5 a 5,0, em incrementos de 0,5.
- **Destaques:** A nota 4,0 representa 26,89% das avaliações; 3,0 representa 20,20%; e 5,0 representa 14,65%. No total, 49,88% das avaliações são iguais ou superiores a 4,0 e 82,05% são iguais ou superiores a 3,0.
- **Classificação:** **Dá, mas...**
- **Justificativa da classificação:** A distribuição é calculável e a qualidade dos valores de avaliação foi validada.
- **Ressalvas:** Os resultados representam exclusivamente as avaliações presentes na base MovieLens, não a opinião de todos os espectadores.

## Auditoria

[Auditoria metodológica do indicador 04](../auditorias/indicador-04-auditoria.md)

## Consulta SQL correspondente

Arquivo fonte: `sql/marts/04_distribuicao_notas_movielens.sql`.

```sql
-- Pergunta de negócio: como as avaliações MovieLens se distribuem por nota?
-- Grão do resultado final: uma linha por valor de rating.
-- Cada linha de refined.avaliacoes representa uma avaliação; percentual usa o total
-- de avaliações da tabela como denominador.
SELECT
    rating,
    COUNT(*) AS total_avaliacoes,
    ROUND(
        COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (),
        2
    ) AS percentual
FROM refined.avaliacoes
GROUP BY rating
ORDER BY rating;
```
