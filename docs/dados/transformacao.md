# Transformação de `raw` para `refined`

Esta página resume a especificação vigente em `specs/transformacao.md` e sua implementação em `pipeline/transformacao.py`. A especificação original permanece preservada; consulte-a para as regras completas e os critérios de aceite.

## Conversões e validações

- Filmes: `id` para `BIGINT`, orçamento e receita para `DECIMAL(18,2)`, data de lançamento para `DATE`, popularidade e nota TMDB para `DOUBLE`, contagem de votos para `BIGINT`; demais colunas permanecem `VARCHAR`.
- Avaliações: `userId`, `movieId` e `timestamp` para `BIGINT`; `rating` para `DOUBLE`.
- Links: `movieId` e `tmdbId` para `BIGINT`; `imdbId` permanece `VARCHAR`.
- Chaves obrigatórias nulas e falhas de conversão em registros elegíveis interrompem a publicação. Valores nulos legítimos são preservados conforme a política documentada; zero em `budget` e `revenue` continua zero.
- Duplicatas de filmes integralmente idênticas são reduzidas a uma ocorrência. Duplicatas no par (`userId`, `movieId`) e duplicatas de `movieId` em links bloqueiam a transformação. `tmdbId` repetido é permitido.

## Rejeições e atomicidade

A implementação verifica que os `source_rowid` configurados ainda correspondem aos registros malformados esperados e que os 13 IDs definidos ainda apresentam versões divergentes. Os três registros malformados e todas as ocorrências desses IDs divergentes são conservados em `rejected.filmes`; nenhuma versão conflitante é escolhida. As tabelas refined e rejected são publicadas em uma única transação, revertida se uma validação ou publicação falhar.

## Evolução do escopo dos indicadores

A especificação de transformação foi originalmente elaborada para atender a 10 indicadores. Posteriormente, o projeto evoluiu para 11 indicadores.

O indicador 11 utiliza as tabelas `refined.filmes`, `refined.avaliacoes` e `refined.links`, já contempladas na especificação original. Portanto, sua inclusão não exigiu novas tabelas refined nem alterações nas regras de transformação.

As tabelas de créditos e palavras-chave permanecem fora do escopo das 11 consultas SQL atuais.
