# Indicadores de negócio — Cinema Analytics Pipeline

## Critério de leitura

Este documento registra os dez indicadores selecionados e explorados para o Cinema Analytics Pipeline.

A classificação utiliza a nomenclatura **Dá**, **Dá, mas...** e **Não dá**. Neste documento, os indicadores foram considerados viáveis, mas apresentam ressalvas relacionadas à cobertura, representatividade, granularidade ou interpretação dos dados.

As evidências foram obtidas por consultas exploratórias executadas manualmente no DuckDB sobre as tabelas da camada `refined`.

## Evidências comprovadas

### Estrutura e qualidade dos dados

- `refined.filmes`: 45.420 registros, 45.420 IDs distintos e nenhum ID nulo. A tabela possui 87 datas de lançamento ausentes. As datas preenchidas vão de 1874-12-09 a 2020-12-16.
- `refined.filmes`: `vote_average` possui 45.417 valores preenchidos. Foram identificados 9.137 filmes com pelo menos 50 votos TMDB.
- `refined.filmes`: a extração dos gêneros identificou 42.978 filmes, 90.976 associações filme–gênero e 20 gêneros distintos. Outros 2.442 filmes não possuem gênero identificável.
- `refined.avaliacoes`: 26.024.289 avaliações, 270.896 usuários distintos e 45.115 `movieId`s distintos. Não há avaliações inválidas, identificadores ausentes ou pares `userId`/`movieId` duplicados. As notas variam de 0,5 a 5,0.
- `refined.avaliacoes`: os timestamps não possuem valores nulos. O período registrado vai de janeiro de 1995 a agosto de 2017.
- `refined.links`: 45.843 registros e 45.843 `movieId`s distintos. Existem 219 `tmdbId`s nulos e 29 `tmdbId`s duplicados, associados a múltiplos `movieId`s.
- O relacionamento entre avaliações, links e filmes manteve a quantidade original de avaliações, sem multiplicação de linhas. Das 26.024.289 avaliações, 25.974.454 encontram correspondência em `refined.filmes`, representando cobertura de 99,81%.

### Decisões metodológicas gerais

- Filmes multigênero participam integralmente de cada gênero ao qual estão associados. Portanto, os totais entre gêneros não são exclusivos nem devem ser somados como se representassem grupos distintos.
- Os indicadores TMDB utilizam informações registradas na base TMDB disponibilizada pelo dataset, não representando necessariamente o universo mundial de filmes ou espectadores.
- Os indicadores MovieLens representam o comportamento observado na base de avaliações, não o comportamento de todos os espectadores.
- A tabela `refined.links` preserva a granularidade MovieLens por `movieId`. Diferentes `movieId`s que apontam para o mesmo `tmdbId` não são consolidados automaticamente em indicadores cuja unidade de análise é `movieId`.
- Os indicadores devem apresentar suas limitações de cobertura e período sempre que isso afetar a interpretação.

---

## 1. Quantidade de filmes por ano de lançamento

- **Nome:** Movies Released by Year (TMDB).
- **Objetivo de negócio:** Acompanhar a distribuição anual dos filmes presentes no catálogo TMDB, considerando seu ano de lançamento.
- **Tabelas e colunas utilizadas:** `refined.filmes`: `id`, `release_date` e `status`.
- **Granularidade:** Ano de lançamento.
- **Regra de cálculo:** Contar os filmes por ano de `release_date`, utilizando as datas válidas e os registros presentes na camada refined.
- **Resultado exploratório:** Foram identificadas 45.420 linhas, das quais 87 possuem data de lançamento ausente. Entre os anos de 2000 e 2016, a quantidade anual variou de 787 filmes em 2000 a 1.973 em 2014. Em 2016 foram registrados 1.604 filmes e, em 2017, 532.
- **Classificação:** **Dá, mas...**
- **Justificativa da classificação:** O indicador é calculável, mas a cobertura temporal apresenta uma queda expressiva a partir de 2017. A análise do campo `status` não explicou essa redução.
- **Ressalvas:** O período principal recomendado para apresentação é 2000–2016. O indicador descreve o catálogo disponível, não a produção cinematográfica mundial. Não se deve interpretar a queda a partir de 2017 como redução real da produção de filmes.

## 2. Nota média TMDB por gênero

- **Nome:** Average TMDB Rating by Genre.
- **Objetivo de negócio:** Comparar as notas médias registradas pelo TMDB entre os gêneros cinematográficos.
- **Tabelas e colunas utilizadas:** `refined.filmes`: `id`, `genres`, `vote_average` e `vote_count`.
- **Granularidade:** Gênero.
- **Regra de cálculo:** Calcular a média simples de `vote_average` por gênero, considerando filmes com pelo menos 50 votos TMDB e gênero identificável.
- **Resultado exploratório:** Foram identificados 9.137 filmes com pelo menos 50 votos. Desses, 9.131 possuem gênero identificável. Foram extraídas 23.044 associações entre filmes e gêneros, distribuídas em 20 gêneros.
- **Destaques:** Documentary apresentou média 7,26; History, 6,91; War, 6,88; Drama, 6,65; e Horror, 5,83.
- **Classificação:** **Dá, mas...**
- **Justificativa da classificação:** A média é calculável, mas cada filme recebe o mesmo peso, independentemente da quantidade de votos. Filmes multigênero participam integralmente de cada categoria.
- **Ressalvas:** Os grupos não são exclusivos. O gênero Foreign possui apenas três filmes elegíveis, portanto sua média deve ser interpretada com cautela. O filtro de 50 votos reduz a influência de filmes com pouca participação, mas não torna a amostra representativa de todos os filmes.

## 3. Quantidade de votos TMDB por gênero

- **Nome:** TMDB Votes by Genre.
- **Objetivo de negócio:** Identificar o volume de votos registrados pelo TMDB para os filmes de cada gênero.
- **Tabelas e colunas utilizadas:** `refined.filmes`: `id`, `genres` e `vote_count`.
- **Granularidade:** Gênero.
- **Regra de cálculo:** Somar `vote_count` por gênero para os filmes com valor preenchido, incluindo filmes com zero votos.
- **Resultado exploratório:** Foram identificados 45.417 valores preenchidos em `vote_count`, três valores nulos e 2.895 filmes com zero votos. A soma dos votos registrados é 4.993.591.
- **Destaques:** Drama apresentou 1.954.388 votos; Action, 1.708.201; Comedy, 1.437.285; Adventure, 1.433.777; e Thriller, 1.433.111.
- **Classificação:** **Dá, mas...**
- **Justificativa da classificação:** A soma pode ser calculada, mas filmes multigênero contribuem integralmente para cada gênero.
- **Ressalvas:** Os totais entre gêneros não são aditivos. O indicador mede o volume de votos registrado na base TMDB para os filmes disponíveis, não a popularidade mundial dos gêneros.

## 4. Distribuição das avaliações MovieLens

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

## 5. Evolução da quantidade de avaliações MovieLens

- **Nome:** MovieLens Ratings Over Time.
- **Objetivo de negócio:** Acompanhar a evolução anual do volume de avaliações registradas pelos usuários MovieLens.
- **Tabelas e colunas utilizadas:** `refined.avaliacoes`: `timestamp`, `userId` e `rating`.
- **Granularidade:** Ano de registro da avaliação.
- **Regra de cálculo:** Converter o timestamp Unix para data e contar as avaliações por ano.
- **Resultado exploratório:** Foram analisadas 26.024.289 avaliações, sem timestamps nulos. O período vai de janeiro de 1995 a agosto de 2017.
- **Destaques:** 1996 registrou 1.733.473 avaliações; 2000, 2.034.072; 2015, 1.913.997; e 2016, 2.095.272.
- **Classificação:** **Dá, mas...**
- **Justificativa da classificação:** O volume anual é calculável, mas varia conforme a quantidade de usuários ativos e a intensidade de participação de cada usuário.
- **Ressalvas:** 1995 é um período residual, com apenas quatro avaliações. 2017 está incompleto, pois os registros terminam em agosto. O aumento do volume não deve ser interpretado isoladamente como crescimento de popularidade dos filmes.

## 6. Evolução da nota média MovieLens

- **Nome:** MovieLens Average Rating Over Time.
- **Objetivo de negócio:** Acompanhar a evolução da nota média das avaliações submetidas pelos usuários ao longo do tempo.
- **Tabelas e colunas utilizadas:** `refined.avaliacoes`: `timestamp`, `rating`, `userId`.
- **Granularidade:** Ano de registro da avaliação.
- **Regra de cálculo:** Calcular a média de `rating` por ano de registro da avaliação.
- **Resultado exploratório:** Entre 1996 e 2017, as médias anuais variaram aproximadamente de 3,43 a 3,63. Em 1995, a média foi 3,75, mas baseada em apenas quatro avaliações.
- **Destaques:** A menor média observada no período principal foi 3,427 em 2004; a maior foi 3,626 em 2013.
- **Classificação:** **Dá, mas...**
- **Justificativa da classificação:** A média anual é calculável, mas representa as avaliações submetidas naquele ano, e não a qualidade dos filmes lançados naquele ano.
- **Ressalvas:** Recomenda-se utilizar 1996–2016 como período principal. 1995 possui volume insuficiente e 2017 é incompleto. Diferenças anuais não devem ser interpretadas automaticamente como mudanças na qualidade do cinema.

## 7. Filmes com maior número de avaliações MovieLens

- **Nome:** Most Rated Movies (MovieLens).
- **Objetivo de negócio:** Identificar os filmes que concentram o maior volume de avaliações na base MovieLens.
- **Tabelas e colunas utilizadas:** `refined.avaliacoes`: `movieId` e `rating`; `refined.links`: `movieId` e `tmdbId`; `refined.filmes`: `id` e `title`.
- **Relacionamentos necessários:** Relacionar `avaliacoes.movieId` a `links.movieId` e, quando houver correspondência, `links.tmdbId` a `filmes.id`.
- **Granularidade:** `movieId` MovieLens.
- **Regra de cálculo:** Contar as avaliações por `movieId`, ordenar em ordem decrescente e apresentar a média das notas como informação complementar.
- **Resultado exploratório:** Forrest Gump liderou o ranking, com 91.921 avaliações e média 4,05. Em seguida aparecem The Shawshank Redemption, com 91.082 avaliações e média 4,43, e Pulp Fiction, com 87.901 avaliações e média 4,17.
- **Classificação:** **Dá, mas...**
- **Justificativa da classificação:** A contagem é calculável por `movieId`, e o enriquecimento com título TMDB funcionou para os 20 primeiros registros apresentados.
- **Ressalvas:** A ordenação é baseada na quantidade de avaliações, não na média. Diferentes `movieId`s não devem ser consolidados automaticamente, mesmo quando compartilham o mesmo `tmdbId`. O indicador mede volume de avaliações na base, não popularidade mundial.

## 8. Usuários mais ativos

- **Nome:** Most Active Users (MovieLens).
- **Objetivo de negócio:** Identificar os usuários que mais contribuíram com avaliações na base MovieLens.
- **Tabelas e colunas utilizadas:** `refined.avaliacoes`: `userId`, `movieId` e `rating`.
- **Granularidade:** Usuário (`userId`).
- **Regra de cálculo:** Contar as avaliações por usuário, calcular a média das notas e ordenar pela quantidade de avaliações em ordem decrescente.
- **Resultado exploratório:** O usuário 45811 lidera o ranking, com 18.276 avaliações e média 3,20. O segundo colocado possui 9.279 avaliações.
- **Classificação:** **Dá, mas...**
- **Justificativa da classificação:** A atividade pode ser medida diretamente pela quantidade de avaliações associadas a cada usuário.
- **Ressalvas:** Os identificadores são anônimos. O ranking representa a atividade histórica registrada na base, não atividade atual ou comportamento geral de espectadores. A média de notas é complementar e não interfere na classificação.

## 9. Distribuição da quantidade de avaliações por usuário

- **Nome:** Ratings per User Distribution (MovieLens).
- **Objetivo de negócio:** Entender a distribuição da atividade dos usuários e identificar a concentração de avaliações em diferentes níveis de participação.
- **Tabelas e colunas utilizadas:** `refined.avaliacoes`: `userId` e `rating`.
- **Granularidade:** Usuário, agrupado em faixas de quantidade de avaliações.
- **Regra de cálculo:** Contar as avaliações por usuário e classificar cada usuário nas seguintes faixas: 1; 2–10; 11–30; 31–100; 101–500; 501–1.000; mais de 1.000 avaliações.
- **Resultado exploratório:** Foram identificados 270.896 usuários. O mínimo foi uma avaliação, a média foi 96,07, a mediana foi 30 e o máximo foi 18.276 avaliações.
- **Distribuição observada:**
  - 1 avaliação: 5.084 usuários (1,88%).
  - 2 a 10: 38.704 usuários (14,29%).
  - 11 a 30: 93.016 usuários (34,34%).
  - 31 a 100: 70.515 usuários (26,03%).
  - 101 a 500: 54.125 usuários (19,98%).
  - 501 a 1.000: 6.950 usuários (2,57%).
  - Mais de 1.000: 2.502 usuários (0,92%).
- **Classificação:** **Dá, mas...**
- **Justificativa da classificação:** A distribuição é calculável e evidencia assimetria na participação dos usuários.
- **Ressalvas:** A média é superior à mediana devido à concentração de avaliações em usuários muito ativos. As faixas são agrupamentos analíticos definidos para facilitar a interpretação, não categorias oficiais do MovieLens. O percentual total apresentado pode chegar a 100,01% devido ao arredondamento.

## 10. Nota média MovieLens por gênero

- **Nome:** Average MovieLens Rating by Genre.
- **Objetivo de negócio:** Comparar as notas médias atribuídas pelos usuários MovieLens aos filmes de diferentes gêneros.
- **Tabelas e colunas utilizadas:** `refined.avaliacoes`: `movieId`, `userId` e `rating`; `refined.links`: `movieId` e `tmdbId`; `refined.filmes`: `id` e `genres`.
- **Relacionamentos necessários:** Relacionar `avaliacoes.movieId` a `links.movieId` e `links.tmdbId` a `filmes.id`. Extrair os gêneros dos filmes e associar as avaliações aos gêneros correspondentes.
- **Granularidade:** Gênero.
- **Regra de cálculo:** Calcular a média de `rating` por gênero, utilizando as avaliações dos filmes com correspondência na tabela de filmes e gênero identificável.
- **Resultado exploratório:** O relacionamento entre as avaliações e os filmes apresentou cobertura de 99,81%: 25.974.454 avaliações com filme correspondente, de um total de 26.024.289. Foram identificados 42.978 filmes com gênero, 90.976 associações filme–gênero e 20 gêneros distintos.
- **Destaques:** History apresentou média 3,807; War, 3,788; Documentary, 3,727; Drama, 3,665; e Horror, 3,213.
- **Classificação:** **Dá, mas...**
- **Justificativa da classificação:** A média pode ser calculada após os relacionamentos entre as três tabelas. A consulta preservou a granularidade das avaliações e não multiplicou registros nos relacionamentos.
- **Ressalvas:** Filmes multigênero participam integralmente de cada gênero. Portanto, as quantidades de avaliações não são aditivas entre categorias. As 49.835 avaliações sem correspondência em filmes e as avaliações de filmes sem gênero identificável não participam da agregação. A média representa as avaliações MovieLens, não a nota TMDB. Gêneros com menor volume de avaliações exigem cautela na interpretação.

---

## Resumo dos indicadores selecionados

| Nº | Indicador | Fonte principal |
|---:|---|---|
| 1 | Movies Released by Year | TMDB |
| 2 | Average TMDB Rating by Genre | TMDB |
| 3 | TMDB Votes by Genre | TMDB |
| 4 | MovieLens Rating Distribution | MovieLens |
| 5 | MovieLens Ratings Over Time | MovieLens |
| 6 | MovieLens Average Rating Over Time | MovieLens |
| 7 | Most Rated Movies | MovieLens + TMDB |
| 8 | Most Active Users | MovieLens |
| 9 | Ratings per User Distribution | MovieLens |
| 10 | Average MovieLens Rating by Genre | MovieLens + TMDB |

## Observações sobre o escopo

Os dez indicadores foram explorados manualmente no DuckDB. Os resultados e regras aqui registrados servem como base para a especificação da camada analítica.

A aprovação dos indicadores não significa que todas as etapas do pipeline estejam integralmente validadas. Permanecem fora do escopo desta exploração, entre outras atividades:

- Implementação e validação dos marts.
- Testes automatizados com pytest.
- Validação completa da integridade referencial.
- Formalização das regras de transformação em especificações técnicas.
- Implementação e validação do dashboard.

Essas atividades serão conduzidas nas próximas etapas do projeto.
