# Dicionário de dados

O dicionário abaixo apresenta os campos e tipos explicitamente documentados em `specs/transformacao.md` e confirmados em `pipeline/transformacao.py`. Na camada `raw`, todos os campos são lidos como texto (`VARCHAR`). Na camada `refined`, somente os campos listados recebem tipos específicos; os demais permanecem `VARCHAR`.

## Filmes

| Coluna | Tipo refined | Descrição disponível |
|---|---|---|
| `adult` | `VARCHAR` | Indicador de conteúdo adulto conforme a origem. |
| `belongs_to_collection` | `VARCHAR` | Informação serializada de coleção. |
| `budget` | `DECIMAL(18,2)` | Orçamento; zero é preservado como zero. |
| `genres` | `VARCHAR` | Lista de gêneros serializada em texto; permanece sem decomposição na transformação. |
| `homepage` | `VARCHAR` | Página associada ao filme, quando presente. |
| `id` | `BIGINT` | Identificador TMDB usado para relacionar metadados. |
| `imdb_id` | `VARCHAR` | Identificador IMDb da origem. |
| `original_language` | `VARCHAR` | Idioma original registrado. |
| `original_title` | `VARCHAR` | Título original. |
| `overview` | `VARCHAR` | Sinopse. |
| `popularity` | `DOUBLE` | Métrica de popularidade da origem. |
| `poster_path` | `VARCHAR` | Caminho do pôster usado pelo dashboard para buscar imagem TMDB. |
| `production_companies` | `VARCHAR` | Companhias de produção serializadas. |
| `production_countries` | `VARCHAR` | Países de produção serializados. |
| `release_date` | `DATE` | Data de lançamento, nulos legítimos são preservados. |
| `revenue` | `DECIMAL(18,2)` | Receita; zero é preservado como zero. |
| `runtime` | `VARCHAR` | Duração conforme a origem. |
| `spoken_languages` | `VARCHAR` | Idiomas falados serializados. |
| `status` | `VARCHAR` | Status do registro do filme. |
| `tagline` | `VARCHAR` | Frase de divulgação. |
| `title` | `VARCHAR` | Título usado para exibição. |
| `video` | `VARCHAR` | Valor de origem referente a vídeo. |
| `vote_average` | `DOUBLE` | Nota TMDB. |
| `vote_count` | `BIGINT` | Quantidade de votos TMDB. |

## Avaliações MovieLens

| Coluna | Tipo refined | Descrição |
|---|---|---|
| `userId` | `BIGINT` | Identificador do usuário MovieLens. |
| `movieId` | `BIGINT` | Identificador do filme MovieLens. |
| `rating` | `DOUBLE` | Nota registrada pelo usuário. |
| `timestamp` | `BIGINT` | Unix timestamp em segundos; permanece inteiro na camada refined. |

## Links MovieLens e metadados

| Coluna | Tipo refined | Descrição |
|---|---|---|
| `movieId` | `BIGINT` | Identificador MovieLens; chave validada como única em `refined.links`. |
| `imdbId` | `VARCHAR` | Identificador IMDb conforme a origem. |
| `tmdbId` | `BIGINT` | Identificador TMDB; pode ser nulo ou repetido. |

## Tabelas de rejeição

`rejected.filmes` preserva as 24 colunas originais de `raw.filmes` como `VARCHAR` e acrescenta `source_table` (`VARCHAR`), `source_rowid` (`BIGINT`) e `rejection_reason` (`VARCHAR`). `source_rowid` é um localizador físico validado por conteúdo, não o número da linha do CSV nem uma chave permanente.

## Campos sem dicionário detalhado

`raw.creditos` e `raw.palavras_chave` são carregadas como texto, mas o projeto não fornece um dicionário de campo documentado para elas, e ambas ficam fora da transformação refined atual. O mesmo se aplica a detalhes semânticos dos subcampos serializados em `genres`, créditos e palavras-chave.
