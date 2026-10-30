# Especificação de Transformação — Cinema Analytics Pipeline

## 1. Objetivo

Definir as regras de transformação da camada `raw` para a camada `refined`, seguindo a metodologia — "Ler o dado ≠ confiar no dado".

Esta especificação é a fonte de verdade para a implementação. Nenhuma regra de negócio deve ser criada ou presumida pelo código sem estar documentada.

## 2. Escopo

Serão transformadas as seguintes tabelas:

| Origem | Destino | Justificativa |
|---|---|---|
| `raw.filmes` | `refined.filmes` | Indicadores de orçamento, receita, gêneros e avaliações TMDB. |
| `raw.avaliacoes` | `refined.avaliacoes` | Indicadores baseados nas avaliações MovieLens. |
| `raw.links` | `refined.links` | Relacionamento entre identificadores MovieLens e TMDB. |

Ficam fora do escopo desta versão:

- `raw.creditos`: não é utilizada nos dez indicadores atuais.
- `raw.palavras_chave`: não é utilizada nos dez indicadores atuais.

O escopo poderá ser revisto caso novos indicadores exijam essas tabelas.

## 3. Nomes das colunas

Preservar integralmente os nomes originais das colunas, em inglês.

Não realizar renomeações nas três tabelas transformadas.

## 4. Tipos de dados

### 4.1. `filmes`

| Coluna | Tipo de destino |
|---|---|
| `id` | BIGINT |
| `budget` | DECIMAL(18,2) |
| `revenue` | DECIMAL(18,2) |
| `release_date` | DATE |
| `vote_average` | DOUBLE |
| `popularity` | DOUBLE |
| `vote_count` | BIGINT |
| Demais colunas | VARCHAR |

### 4.2. `avaliacoes`

| Coluna | Tipo de destino |
|---|---|
| `userId` | BIGINT |
| `movieId` | BIGINT |
| `rating` | DOUBLE |
| `timestamp` | BIGINT |

O campo `timestamp` será mantido como Unix timestamp, sem conversão para data/hora nesta etapa.

### 4.3. `links`

| Coluna | Tipo de destino |
|---|---|
| `movieId` | BIGINT |
| `tmdbId` | BIGINT |
| `imdbId` | VARCHAR |

Os campos não listados permanecem como VARCHAR.

## 5. Falhas de conversão

A transformação deverá interromper sua execução quando encontrar um valor não nulo que não possa ser convertido para o tipo definido, exceto nos três registros de `raw.filmes` designados para rejeição na seção 9.1. As falhas desses três registros serão registradas como motivo da rejeição e não bloquearão a transformação dos demais registros.

Regras:

- Não converter silenciosamente valores inválidos para `NULL`.
- Informar a tabela, a coluna, os valores problemáticos e os registros correspondentes.
- Preservar os valores nulos legítimos quando permitidos pela política de nulidade.
- Não fabricar valores para corrigir registros inválidos.

As conversões devem distinguir valores originalmente nulos de valores não nulos inválidos.

## 6. Duplicidades

### 6.1. `filmes`

Chave: `id`.

- Remover duplicatas integralmente idênticas, mantendo uma ocorrência e contabilizando as removidas.
- Rejeitar integralmente todas as ocorrências dos 13 IDs divergentes enumerados na seção 8.2, preservando-as em `rejected.filmes` conforme a seção 9.1 e excluindo-as de `refined.filmes`.
- Validar os conflitos antes da publicação das tabelas.
- Não selecionar arbitrariamente a primeira, a última, a maior ou a menor ocorrência.
- Duplicidades conflitantes em registros não designados para rejeição continuam impedindo a transformação e devem ser reportadas.

### 6.2. `avaliacoes`

Chave composta: (`userId`, `movieId`).

- Interromper a transformação caso existam duplicidades nessa combinação.
- Informar os registros conflitantes.

### 6.3. `links`

Chave: `movieId`.

- Interromper a transformação caso existam duplicidades de `movieId`.
- Permitir valores repetidos em `tmdbId`, pois um mesmo identificador TMDB pode estar associado a mais de um `movieId` MovieLens.

## 7. Tratamento de valores nulos

### 7.1. `filmes`

- `id`: nulo não permitido; interromper a transformação.
- `release_date`: preservar nulos legítimos.
- `revenue`: preservar nulos legítimos.
- `vote_average`: preservar nulos legítimos.
- `vote_count`: preservar nulos legítimos.
- Demais colunas: preservar os nulos da origem.

### 7.2. `avaliacoes`

- `userId` e `movieId`: nulos não permitidos; interromper a transformação.
- Demais colunas: preservar nulos legítimos.

### 7.3. `links`

- `movieId`: nulo não permitido; interromper a transformação.
- `tmdbId`: preservar nulos.
- `imdbId`: preservar conforme a origem.

### 7.4. Valores zero

Os valores zero de `budget` e `revenue` devem ser preservados como zero.

Não interpretar automaticamente zero como ausência de informação.

## 8. Evidências levantadas na camada RAW

### 8.1. Volumes

| Tabela | Registros |
|---|---:|
| `raw.filmes` | 45.466 |
| `raw.avaliacoes` | 26.024.289 |
| `raw.links` | 45.843 |

### 8.2. Filmes

- Foram identificados 30 registros excedentes em relação à quantidade de IDs distintos.
- Existem 16 IDs com ocorrências integralmente idênticas, incluindo o ID `141971`, que aparece três vezes.
- Existem 13 IDs com conteúdos divergentes: `4912`, `10991`, `12600`, `13209`, `14788`, `15028`, `22649`, `69234`, `77221`, `84198`, `109962`, `110428` e `132641`.
- Nas ocorrências divergentes, as diferenças observadas estão em `popularity` e, para os IDs `10991` e `15028`, também em `vote_count`.
- Foram identificados três registros com indícios de desalinhamento entre colunas.
- Os 13 IDs com registros divergentes e os três registros com indícios de desalinhamento são problemas distintos; não se deve presumir que correspondam aos mesmos registros.
- `budget` apresenta três valores não conversíveis.
- `revenue` apresenta três valores vazios, correspondentes a nulos legítimos, e três valores inválidos associados aos registros desalinhados.
- `release_date` apresenta 87 nulos e três valores inválidos associados aos registros desalinhados.
- Existem 36.573 registros com `budget = 0`.
- Existem 38.052 registros com `revenue = 0`.
- A coluna `genres` contém listas serializadas em texto; sua interpretação será definida na etapa pertinente aos indicadores.

### 8.3. Avaliações MovieLens

- 26.024.289 registros.
- 270.896 usuários distintos.
- 45.115 filmes distintos.
- Nenhuma duplicidade identificada na combinação (`userId`, `movieId`).
- Nenhum valor inválido identificado em `rating` ou `timestamp`.
- `rating` varia de 0,5 a 5,0.
- `timestamp` contém valores Unix em segundos.

### 8.4. Links

- 45.843 registros.
- Nenhuma duplicidade de `movieId`.
- 219 registros sem `tmdbId`.
- 29 valores de `tmdbId` associados a mais de um `movieId`.
- 161 registros com `tmdbId` sem correspondência em `raw.filmes`.

Essas evidências devem orientar as validações, mas não autorizam correções automáticas dos dados.

## 9. Saída e execução

A transformação deverá:

1. Criar ou substituir as tabelas `refined.filmes`, `refined.avaliacoes`, `refined.links` e `rejected.filmes`.
2. Utilizar `CREATE OR REPLACE`, nunca append.
3. Não modificar as tabelas da camada RAW.
4. Informar a quantidade de registros antes e depois da transformação.
5. Informar a quantidade de duplicatas idênticas removidas.
6. Informar a quantidade de valores nulos preservados por coluna.
7. Gerar relatórios das inconsistências que impedirem a execução.
8. Exibir mensagens no terminal utilizando UTF-8.
9. Informar a quantidade de registros rejeitados e seus motivos.

A publicação de `refined.filmes`, `refined.avaliacoes`, `refined.links` e o isolamento em `rejected.filmes` deverão ser atômicos. Se todas as etapas forem concluídas, as três tabelas refined e a tabela de rejeitados deverão ser publicadas; se ocorrer uma falha, nenhuma alteração parcial deverá permanecer persistida. A implementação deverá utilizar um mecanismo transacional compatível com DuckDB para garantir esse comportamento.

### 9.1 Registros rejeitados

Os `source_rowid` 19730, 29503 e 35587 identificam os registros malformados na versão atual de `raw.filmes`. Antes do isolamento, deve-se conferir que cada localizador ainda corresponde ao registro esperado. São localizadores físicos do DuckDB, não identificadores permanentes do CSV.

Os três registros apresentam deslocamento de colunas e falhas de conversão. Eles não serão corrigidos, reconstruídos, excluídos ou modificados na camada RAW. Serão isolados em `rejected.filmes` e excluídos da publicação de `refined.filmes`. Os demais registros poderão prosseguir, desde que atendam às demais regras desta especificação.

A estrutura lógica de `rejected.filmes` será:

- `source_table` (`VARCHAR`): tabela de origem, `raw.filmes`.
- `source_rowid` (`BIGINT`): identificador de origem usado para localizar o registro.
- `rejection_reason` (`VARCHAR`): classificação geral de deslocamento de colunas e falhas de conversão registradas individualmente por registro: `source_rowid` 19730 — `id`, `budget`, `release_date`; `source_rowid` 29503 — `id`, `budget`, `release_date`; `source_rowid` 35587 — `id`, `budget`, `popularity`, `release_date`.
- As 24 colunas originais de `raw.filmes`, todas como `VARCHAR`, com nomes e valores originais preservados, inclusive `NULL`s: `adult`, `belongs_to_collection`, `budget`, `genres`, `homepage`, `id`, `imdb_id`, `original_language`, `original_title`, `overview`, `popularity`, `poster_path`, `production_companies`, `production_countries`, `release_date`, `revenue`, `runtime`, `spoken_languages`, `status`, `tagline`, `title`, `video`, `vote_average` e `vote_count`.

O isolamento dos registros rejeitados, a publicação das três tabelas refined e os relatórios correspondentes deverão fazer parte da mesma transação atômica.

#### 9.1.1 Conflitos de duplicidade divergente em `filmes`

Todas as ocorrências dos IDs `4912`, `10991`, `12600`, `13209`, `14788`, `15028`, `22649`, `69234`, `77221`, `84198`, `109962`, `110428` e `132641` devem ser rejeitadas integralmente. Nenhuma ocorrência desses IDs será publicada em `refined.filmes`, e nenhuma versão será escolhida como correta.

Todas essas ocorrências devem ser preservadas em `rejected.filmes`, com as 24 colunas originais de `raw.filmes` como `VARCHAR`, mantendo nomes, valores e `NULL`s, além dos metadados `source_table`, `source_rowid` e `rejection_reason` definidos na seção 9.1. O `rejection_reason` deve indicar conflito de duplicidade com conteúdo divergente. Essa rejeição é distinta da remoção de duplicatas integralmente idênticas: destas últimas, uma ocorrência permanece em `refined.filmes` e as demais são contabilizadas como removidas.

Os conflitos dos IDs listados devem ser validados antes da publicação. A rejeição deles e dos três registros malformados já definidos, junto à publicação das tabelas refined, permanece sujeita à atomicidade estabelecida na seção 9.

### 9.2 Ausência de tabelas RAW

Se alguma tabela de origem estiver ausente:

- Listar todas as tabelas faltantes.
- Orientar a execução do processo de ingestão.
- Encerrar a execução com código de saída 1.

### 9.3 Erros de transformação

Se houver falha de conversão, chave obrigatória nula ou conflito de duplicidade em registros não designados para rejeição na seção 9.1:

- Informar as inconsistências encontradas.
- Não concluir a transformação.
- Não produzir resultados parciais como se fossem válidos.

## 10. Critérios de aceitação

A transformação será considerada válida quando:

- As três tabelas de origem estiverem disponíveis.
- As conversões respeitarem os tipos definidos.
- Não houver falhas de conversão nos registros elegíveis para publicação; os três registros designados na seção 9.1 são rejeitados conforme aquela regra.
- Não houver chaves obrigatórias nulas.
- Não houver duplicidades conflitantes em registros elegíveis para publicação; todas as ocorrências dos 13 IDs divergentes designados na seção 9.1.1 devem ser rejeitadas.
- As duplicatas integralmente idênticas de `filmes` forem tratadas conforme a regra.
- As relações legítimas de `tmdbId` repetidos forem preservadas.
- As contagens de entrada, saída, duplicatas removidas e nulos preservados forem informadas.
- A execução for reprodutível, sem append.
- A camada RAW permanecer intacta.
- Os registros `source_rowid` 19730, 29503 e 35587 forem preservados em `rejected.filmes`, excluídos de `refined.filmes` e contabilizados com seus motivos.
- A publicação das tabelas refined e o isolamento dos rejeitados forem atômicos.

## 11. Premissas e limitações

- Os valores zero de orçamento e receita são preservados; não há decisão de negócio que permita interpretá-los como nulos.
- A coluna `timestamp` permanece como Unix timestamp em segundos.
- A coluna `genres` permanece como `VARCHAR` nesta etapa; sua decomposição será definida posteriormente, de acordo com os indicadores.
- Os registros divergentes e desalinhados não serão corrigidos arbitrariamente; as ocorrências dos 13 IDs divergentes enumerados na seção 8.2 serão rejeitadas conforme a seção 9.1, sem escolha de uma versão.
- A transformação deve reportar e interromper diante das inconsistências definidas nesta especificação, exceto pelos registros tratados conforme a seção 9.1.
- A lista original de indicadores menciona `ratings_small.csv` e `links_small.csv`, enquanto a ingestão da Aula 1 utiliza `ratings.csv` e `links.csv`. Esta versão seguirá as tabelas efetivamente ingeridas, sem alterar a ingestão silenciosamente.

## 12. Entregáveis

- Este documento de especificação.
- Implementação em `pipeline/transformacao.py`, com esta especificação documentada no docstring inicial.
- Relatórios de validação e execução.
- Lista final de premissas adotadas durante a implementação que não estejam explicitamente definidas nesta especificação.

---

RESTRIÇÕES PARA ESTA TAREFA:

1. Altere somente `specs/transformacao.md`.
2. Não implemente `pipeline/transformacao.py`.
3. Não execute transformações no DuckDB.
4. Não altere arquivos existentes.
5. Não invente regras adicionais.
6. Não resolva automaticamente as inconsistências pendentes.

Ao terminar, informe:
- Se o arquivo foi preenchido.
- Quais seções foram incluídas.
- Confirme que nenhum outro arquivo foi alterado.
