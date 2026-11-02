# Evidências de Validação da Transformação de Dados

**Projeto:** Movie Data Pipeline  
**Banco de dados:** `movie_data.duckdb`  
**Camadas avaliadas:** `raw`, `refined` e `rejected`  
**Status:** Validações executadas com sucesso

---

## 1. Objetivo

Este documento registra as evidências obtidas durante a validação da transformação dos dados da camada `raw` para a camada `refined`, conforme as regras estabelecidas em `specs/transformacao.md`.

O objetivo é verificar:

- A publicação correta das tabelas transformadas.
- A preservação das tabelas de origem.
- O tratamento de duplicidades e registros inconsistentes.
- A aplicação dos tipos de dados definidos.
- A preservação dos valores durante as conversões.
- O armazenamento dos registros rejeitados.

As consultas foram executadas diretamente no DuckDB, em modo de leitura, sem modificar os dados.

## 2. Conferência das contagens

Foi executada uma consulta para comparar a quantidade de registros nas tabelas de origem, destino e rejeição.

| Tabela | Registros esperados | Registros encontrados |
|---|---:|---:|
| `raw.filmes` | 45.466 | 45.466 |
| `refined.filmes` | 45.420 | 45.420 |
| `raw.avaliacoes` | 26.024.289 | 26.024.289 |
| `refined.avaliacoes` | 26.024.289 | 26.024.289 |
| `raw.links` | 45.843 | 45.843 |
| `refined.links` | 45.843 | 45.843 |
| `rejected.filmes` | 29 | 29 |

**Resultado:** todas as contagens corresponderam aos valores esperados.

### 2.1. Reconciliação de filmes

A diferença entre a quantidade de registros em `raw.filmes` e `refined.filmes` é explicada pelos registros rejeitados e pelas duplicidades integralmente idênticas removidas.

| Componente | Registros |
|---|---:|
| Registros originais | 45.466 |
| Registros rejeitados | 29 |
| Ocorrências duplicadas idênticas removidas | 17 |
| Registros publicados em refined | 45.420 |

A reconciliação fecha:

`45.466 - 29 - 17 = 45.420`

## 3. Integridade das chaves nas tabelas RAW

Foi verificada a quantidade total de registros e a quantidade de chaves distintas nas três tabelas de origem.

| Tabela | Total | Chaves distintas | Ocorrências excedentes |
|---|---:|---:|---:|
| `raw.filmes` | 45.466 | 45.436 | 30 |
| `raw.avaliacoes` | 26.024.289 | 26.024.289 | 0 |
| `raw.links` | 45.843 | 45.843 | 0 |

### 3.1. Interpretação

- `raw.filmes`: foram identificados 29 IDs repetidos, sendo que um deles aparece três vezes. Isso resulta em 30 ocorrências excedentes.
- `raw.avaliacoes`: não foram encontradas duplicidades na chave composta `(userId, movieId)`.
- `raw.links`: não foram encontradas duplicidades na chave `movieId`.

**Resultado:** as características de unicidade observadas durante a investigação da camada RAW foram confirmadas.

## 4. Validação dos registros rejeitados

A tabela `rejected.filmes` contém 29 registros, divididos em duas categorias.

| Categoria | Quantidade |
|---|---:|
| Conflitos de duplicidade com conteúdo divergente | 26 |
| Registros malformados por deslocamento de colunas | 3 |
| **Total** | **29** |

### 4.1. Conflitos de duplicidade

Foram rejeitadas todas as ocorrências dos 13 IDs que apresentavam conteúdos divergentes:

| ID | Ocorrências rejeitadas |
|---:|---:|
| 4912 | 2 |
| 10991 | 2 |
| 12600 | 2 |
| 13209 | 2 |
| 14788 | 2 |
| 15028 | 2 |
| 22649 | 2 |
| 69234 | 2 |
| 77221 | 2 |
| 84198 | 2 |
| 109962 | 2 |
| 110428 | 2 |
| 132641 | 2 |
| **Total** | **26** |

### 4.2. Registros malformados

Também foram identificados três registros com deslocamento de colunas, associados a falhas de conversão:

- `1997-08-20`
- `2012-09-29`
- `2014-01-01`

Os três registros foram preservados na tabela de rejeição.

**Resultado:** os 29 registros rejeitados foram encontrados e classificados de acordo com os motivos previstos na especificação.

## 5. Ausência dos IDs conflitantes na camada refined

Foi executada uma consulta para verificar se os 13 IDs com conteúdo divergente estavam ausentes de `refined.filmes`.

**Resultado encontrado:** zero registros.

Isso confirma que nenhuma das ocorrências dos 13 IDs conflitantes foi publicada na camada refined.

## 6. Validação dos tipos de dados

Foi consultado o catálogo `information_schema.columns` para verificar os tipos efetivamente publicados.

### 6.1. Tabela `refined.filmes`

| Coluna | Tipo esperado | Tipo encontrado |
|---|---|---|
| `id` | BIGINT | BIGINT |
| `budget` | DECIMAL(18,2) | DECIMAL(18,2) |
| `revenue` | DECIMAL(18,2) | DECIMAL(18,2) |
| `release_date` | DATE | DATE |
| `popularity` | DOUBLE | DOUBLE |
| `vote_average` | DOUBLE | DOUBLE |
| `vote_count` | BIGINT | BIGINT |
| Demais colunas | VARCHAR | VARCHAR |

### 6.2. Tabela `refined.avaliacoes`

| Coluna | Tipo esperado | Tipo encontrado |
|---|---|---|
| `userId` | BIGINT | BIGINT |
| `movieId` | BIGINT | BIGINT |
| `rating` | DOUBLE | DOUBLE |
| `timestamp` | BIGINT | BIGINT |

### 6.3. Tabela `refined.links`

| Coluna | Tipo esperado | Tipo encontrado |
|---|---|---|
| `movieId` | BIGINT | BIGINT |
| `tmdbId` | BIGINT | BIGINT |
| `imdbId` | VARCHAR | VARCHAR |

**Resultado:** todos os tipos de dados encontrados corresponderam aos tipos definidos na especificação.

## 7. Comparação dos valores entre RAW e refined

Foram executadas consultas de comparação entre os dados originais e os dados transformados.

As comparações utilizaram as chaves correspondentes e, quando necessário, a deduplicação dos registros integralmente idênticos da origem.

A comparação de valores utilizou `IS DISTINCT FROM`, permitindo identificar diferenças inclusive quando envolvem valores nulos.

### 7.1. Filmes

| Coluna | Registros comparados | Divergências |
|---|---:|---:|
| `budget` | 45.420 | 0 |
| `revenue` | 45.420 | 0 |
| `release_date` | 45.420 | 0 |

A primeira tentativa de comparação de `budget` e `revenue` retornou 45.437 linhas, devido à multiplicação de registros no relacionamento com os IDs duplicados da origem.

A consulta foi corrigida com a deduplicação dos registros RAW antes do relacionamento. A comparação passou a retornar exatamente 45.420 registros, sem divergências.

### 7.2. Avaliações

| Coluna | Registros comparados | Divergências |
|---|---:|---:|
| `rating` | 26.024.289 | 0 |
| `userId` | 26.024.289 | 0 |
| `movieId` | 26.024.289 | 0 |

A correspondência foi realizada utilizando a chave composta `(userId, movieId)`.

**Resultado:** não foram encontradas diferenças nos valores comparados.

### 7.3. Links

| Coluna | Registros comparados | Divergências |
|---|---:|---:|
| `movieId` | 45.843 | 0 |
| `tmdbId` | 45.843 | 0 |
| `imdbId` | 45.843 | 0 |

A correspondência foi realizada pela chave `movieId`.

**Resultado:** não foram encontradas divergências, inclusive na preservação dos valores nulos de `tmdbId`.

## 8. Preservação dos valores nulos

Durante a execução da transformação, o script apresentou a quantidade de valores nulos preservados em cada coluna das tabelas refined.

Entre os resultados observados:

| Tabela | Coluna | Nulos preservados |
|---|---|---:|
| `filmes` | `belongs_to_collection` | 40.934 |
| `filmes` | `homepage` | 37.649 |
| `filmes` | `overview` | 954 |
| `filmes` | `release_date` | 87 |
| `filmes` | `revenue` | 3 |
| `filmes` | `runtime` | 260 |
| `filmes` | `tagline` | 25.025 |
| `avaliacoes` | Todas as colunas | 0 |
| `links` | `tmdbId` | 219 |

Os valores nulos legítimos foram preservados conforme as regras definidas na especificação. Os zeros de `budget` e `revenue` também foram mantidos como valores numéricos, não sendo tratados automaticamente como ausência de informação.

## 9. Conclusão

Com base nas consultas executadas e nos resultados registrados, a transformação dos dados apresentou conformidade com as regras verificadas da especificação `specs/transformacao.md`.

As evidências demonstram que:

1. As tabelas RAW mantiveram suas contagens originais.
2. As tabelas refined foram publicadas com as contagens esperadas.
3. Os registros inconsistentes foram preservados na camada rejected.
4. Os conflitos de duplicidade foram tratados conforme as regras definidas.
5. Os tipos de dados publicados correspondem aos tipos especificados.
6. Os valores comparados entre RAW e refined não apresentaram divergências.
7. Os valores nulos legítimos foram preservados.

**Conclusão:** as verificações realizadas foram aprovadas, fornecendo evidências de integridade e consistência para a transformação dos dados.

---

## 10. Escopo e limitações das evidências

Este documento registra as verificações efetivamente executadas durante a validação.

Não foram realizados, nesta etapa:

- Testes automatizados com pytest.
- Comparação integral de todas as colunas de todas as tabelas.
- Validação individual de todos os valores de `timestamp`.
- Validação semântica do conteúdo serializado de `genres`.
- Validação de integridade referencial completa entre `filmes`, `avaliacoes` e `links`.

Essas atividades não devem ser consideradas aprovadas apenas com base nos resultados registrados neste documento.

**Referências:**
- `specs/transformacao.md` — especificação da transformação.
- `pipeline/transformacao.py` — implementação executada.
- `docs/evidencias-transformacao.md` — registro das evidências desta validação.