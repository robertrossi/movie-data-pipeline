# Auditoria metodológica geral — Cinema Analytics

**Data:** 2 de novembro de 2026<br>
**Banco:** DuckDB `movie_data`, arquivo `C:/Users/rober/Desktop/projetoedj/movie-data-pipeline/movie_data.duckdb`<br>
**Versão retornada pela MCP:** `v1.5.6`<br>
**Acesso e histórico:** a auditoria inicial foi feita com consultas somente leitura por MCP DuckDB. Em 2 de novembro de 2026, as MARTs 05 e 06 foram republicadas seletivamente; a auditoria pós-publicação usou conexão DuckDB somente leitura e consultas `SELECT`.

> **Atualização pós-publicação — 2 de novembro de 2026:** a regra oficial para os indicadores 05 e 06 é UTC (`AT TIME ZONE 'UTC'`). As MARTs `marts.avaliacoes_movielens_ao_longo_do_tempo` e `marts.nota_media_movielens_ao_longo_do_tempo` foram republicadas seletivamente, com 23 linhas cada. A auditoria posterior confirmou o intervalo de 1995 a 2017 e zero diferenças em cada direção de `EXCEPT ALL` para ambos os indicadores. As outras oito MARTs foram preservadas. O resultado anterior de 44 linhas divergentes por indicador corresponde ao estado pré-publicação.

## Resultado consolidado

| Indicador | Relatório | Parecer | Consistência com `marts` nesta auditoria |
|---:|---|---|---|
| 01 — Filmes lançados por ano | [indicador-01-auditoria.md](indicador-01-auditoria.md) | APROVADO COM RESSALVAS | Recalculado: 17 linhas; 0 diferenças |
| 02 — Nota média TMDB por gênero | [indicador-02-auditoria.md](indicador-02-auditoria.md) | APROVADO COM RESSALVAS | Recalculado: 20 linhas; 0 diferenças |
| 03 — Votos TMDB por gênero | [indicador-03-auditoria.md](indicador-03-auditoria.md) | APROVADO COM RESSALVAS | Recalculado: 20 linhas; 0 diferenças |
| 04 — Distribuição de notas MovieLens | [indicador-04-auditoria.md](indicador-04-auditoria.md) | APROVADO | Recalculado: 10 linhas; 0 diferenças |
| 05 — Avaliações MovieLens ao longo do tempo | [indicador-05-auditoria.md](indicador-05-auditoria.md) | APROVADO | 23 linhas; 1995–2017; 0 diferenças em cada direção |
| 06 — Nota média MovieLens ao longo do tempo | [indicador-06-auditoria.md](indicador-06-auditoria.md) | APROVADO | 23 linhas; 1995–2017; 0 diferenças em cada direção |
| 07 — Filmes mais avaliados MovieLens | [indicador-07-auditoria.md](indicador-07-auditoria.md) | APROVADO | Recalculado: 20 linhas; 0 diferenças |
| 08 — Usuários mais ativos | [indicador-08-auditoria.md](indicador-08-auditoria.md) | APROVADO | Recalculado: 20 linhas; 0 diferenças |
| 09 — Distribuição de avaliações por usuário | [indicador-09-auditoria.md](indicador-09-auditoria.md) | APROVADO COM RESSALVAS | Recalculado: 8 linhas; 0 diferenças |
| 10 — Nota média MovieLens por gênero | [indicador-10-auditoria.md](indicador-10-auditoria.md) | APROVADO COM RESSALVAS | Evidência e parecer do relatório anterior considerados; sem novo teste da mart nesta etapa |

**Contagem dos pareceres:** 5 aprovados, 5 aprovados com ressalvas, 0 reprovados.

Na auditoria inicial, os indicadores 01–09 foram comparados com as MARTs. Depois da adoção de UTC, as MARTs 05 e 06 foram atualizadas seletivamente e comparadas de novo com as consultas oficiais. Para cada indicador, ambas as direções de `EXCEPT ALL` retornaram zero diferenças. As outras oito MARTs foram preservadas. O indicador 10 foi tratado conforme o escopo anterior: seu relatório e parecer metodológico foram considerados, sem nova comparação com a MART.

## Síntese por indicador

1. **Indicador 01:** a tabela tem 45.420 filmes com `id` não nulo e distinto. O resultado de 2000–2016 contém 17 anos e 23.442 filmes com data dentro do intervalo; 87 datas são nulas. A materialização coincide. A ressalva é o escopo temporal deliberado e a exclusão de datas nulas.
2. **Indicador 02:** 9.137 filmes satisfazem `vote_count >= 50` e `vote_average IS NOT NULL`; geram 23.044 pares filme/gênero em 20 gêneros. A média simples por filme e a mart coincidem. Três `vote_count` e três `vote_average` são nulos; seis filmes elegíveis não têm gênero extraível. A métrica não pondera pela quantidade de votos TMDB.
3. **Indicador 03:** 45.417 filmes têm `vote_count` não nulo; 42.975 têm gênero extraível e geram 90.967 pares. Os 20 grupos coincidem com a mart. Três contagens de votos são nulas; 2.442 filmes sem gênero extraível não entram. Totais entre gêneros não são aditivos por multigênero.
4. **Indicador 04:** 26.024.289 avaliações têm rating não nulo em dez valores entre 0,5 e 5,0, em incrementos de 0,5. A distribuição de dez linhas coincide com a mart. Percentuais arredondados somam 99,99%.
5. **Indicador 05:** 26.024.289 timestamps, sem nulos ou negativos, cobrem 1995–2017. O ano é classificado explicitamente em UTC. A MART tem 23 linhas e coincide exatamente com a consulta de referência: zero diferenças em ambas as direções de `EXCEPT ALL`.
6. **Indicador 06:** a consulta e a MART UTC têm 23 linhas, cobrindo 1995–2017, com 26.024.289 avaliações na soma anual. As duas direções de `EXCEPT ALL` retornaram zero diferenças. A publicação seletiva preservou as demais oito MARTs.
7. **Indicador 07:** os 20 filmes com mais ratings coincidem com a mart, mantêm `movieId` e têm `tmdbId` e título. Não há empate entre as posições 20 e 21 (57.070 versus 56.827 avaliações); nenhum problema de JOIN foi observado.
8. **Indicador 08:** o Top 20 de usuários coincide com a mart. Há 270.896 usuários sem `userId` nulo e sem duplicidade de par usuário/filme. O corte não tem empate com o 21º usuário (4.785 versus 4.707 avaliações).
9. **Indicador 09:** oito faixas classificam uma vez cada um dos 270.896 usuários e coincidem com a mart. As duas menores faixas têm 13 e 1 usuários, mas exibem 0,00% após arredondamento; `10000+` significa estritamente acima de 10.000 na expressão atual.
10. **Indicador 10:** o relatório anterior encontrou média ponderada metodologicamente correta, igualdade com a média direta nos 20 gêneros, pares sem duplicidade e grão `movieId` preservado. Suas ressalvas — cobertura de relacionamento e gêneros ausentes — são compatíveis com limitações observadas nas fontes TMDB e com a extração de gêneros dos indicadores 02 e 03. Os denominadores diferem: o indicador 10 considera somente filmes com avaliações MovieLens e correspondência por `links`; os indicadores 02 e 03 partem do catálogo TMDB e usam outros filtros. Portanto, suas contagens de gêneros ausentes não devem ser comparadas diretamente.

## Problemas recorrentes e riscos metodológicos

### Referência UTC nos indicadores temporais

Nos indicadores 05 e 06, `TO_TIMESTAMP(timestamp) AT TIME ZONE 'UTC'` fixa explicitamente o calendário UTC e remove a dependência do fuso da sessão. Após a republicação seletiva, ambas as MARTs coincidem com as consultas de referência nas duas direções de `EXCEPT ALL`. O resultado pré-publicação tinha 44 linhas divergentes por indicador; essa pendência foi encerrada.

### Gêneros multivalorados e cobertura de metadados

Os indicadores 02, 03 e 10 expandem gêneros. Um filme multigênero participa de cada grupo, de modo que somas de filmes, ratings ou votos entre gêneros não representam totais exclusivos. Os indicadores TMDB 02–03 partem do catálogo de filmes; o indicador MovieLens 10 exige a cadeia de mapeamento `movieId → tmdbId → filme`, que exclui IDs sem correspondência completa. Também há filmes sem gênero extraível. Essas populações e filtros são diferentes; comparações diretas de totais entre esses indicadores seriam incorretas.

### Arredondamento e apresentação

Nos indicadores 04 e 09, percentuais são arredondados a duas casas e somam 99,99%, sem divergência de denominador. No indicador 09, as faixas de 13 e 1 usuários aparecem como 0,00%; a contagem deve ser lida junto do percentual. O indicador 02 arredonda notas TMDB a duas casas e o 06 a três, conforme definido nos SQLs.

### Métricas de volume e interpretação

Contagens de avaliações por ano, usuário ou filme são volumes brutos. Não ajustam por tempo de exposição, atividade de usuários ou composição de filmes. São corretas para as perguntas de contagem/ranking descritas, mas não devem ser interpretadas como qualidade, popularidade normalizada ou mudança causal. No indicador 02, a nota média TMDB é média simples por filme elegível, não média ponderada por votos; no indicador 10, a média MovieLens pondera pelo número de ratings válidos por filme, equivalente à média direta de avaliações dentro de cada gênero.

## Limitações gerais dos dados

- O catálogo `refined.filmes` contém 45.420 IDs distintos; há 87 datas de lançamento nulas e três valores nulos em cada um dos campos `vote_count` e `vote_average` (as interseções não foram medidas nesta auditoria).
- Em avaliações, foram observados 26.024.289 ratings sem nulos e no domínio MovieLens auditado; 45.115 `movieId` distintos e 270.896 usuários distintos.
- A cobertura MovieLens–TMDB não é completa: no indicador 10, 213 IDs têm `tmdbId` nulo e 187 não encontram filme correspondente. Entre os filmes que chegam a `refined.filmes`, parte não tem gênero extraível.
- O formato de `genres` é texto serializado; a regex auditada encontra os nomes esperados nos exemplos e não gerou pares repetidos nas verificações. Registros sem conteúdo de gênero não podem ser atribuídos a um grupo pela consulta atual.

## Recomendações

1. Manter a regra UTC nos indicadores 05 e 06 e repetir a comparação bidirecional `EXCEPT ALL` se a consulta ou sua materialização mudar.
2. Documentar a cobertura dos JOINs e a ausência de gênero no indicador 10, e evitar comparar seus totais diretamente com métricas TMDB que usam outra população.
3. Preservar a explicação de não aditividade em indicadores por gênero e a distinção entre média simples TMDB por filme e média MovieLens ponderada por avaliações.
4. Nos relatórios ou visualizações de percentuais, indicar arredondamento e evitar que uma faixa com usuários apareça como se estivesse vazia; clarificar o rótulo `10000+` para refletir o limite implementado (`>10000`).
5. Manter a faixa de anos e o tratamento de datas nulas do indicador 01 explícitos na descrição do indicador.
6. Em futuras validações de materialização, comparar também o indicador 10 com `marts.nota_media_movielens_por_genero`; essa verificação foi intencionalmente deixada fora desta rodada para não repetir sua auditoria.

## Conclusão sobre confiabilidade

Após a publicação seletiva e a auditoria pós-publicação, os indicadores 05 e 06 estão **APROVADOS**: cada MART contém 23 linhas de 1995 a 2017 e tem zero diferenças com a consulta UTC em ambas as direções de `EXCEPT ALL`. As outras oito MARTs foram preservadas. No conjunto de dez indicadores, cinco estão aprovados e cinco aprovados com ressalvas; nenhum foi reprovado. Permanecem as limitações documentadas de período, cobertura, multigênero e arredondamento dos indicadores correspondentes.
