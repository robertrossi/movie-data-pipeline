# Fontes de dados

A fonte de referência do projeto é [The Movies Dataset — Rounak Banik](https://www.kaggle.com/datasets/rounakbanik/the-movies-dataset). O README identifica que o conjunto reúne dados associados ao TMDB e ao MovieLens/GroupLens; o projeto não é proprietário desses dados.

O código em `pipeline/ingestao.py` define exatamente cinco arquivos e seus destinos:

| Arquivo | Conteúdo descrito no projeto | Tabela `raw` |
|---|---|---|
| `movies_metadata.csv` | Metadados dos filmes. | `raw.filmes` |
| `ratings.csv` | Avaliações de filmes feitas por usuários MovieLens. | `raw.avaliacoes` |
| `credits.csv` | Créditos, elenco e equipe. | `raw.creditos` |
| `keywords.csv` | Palavras-chave associadas aos filmes. | `raw.palavras_chave` |
| `links.csv` | Identificadores que relacionam filmes MovieLens a identificadores externos. | `raw.links` |

O processo requer que esses arquivos estejam em `raw/`. Arquivos como `ratings_small.csv` e `links_small.csv` não são incluídos na lista de ingestão atual.

## Referências relacionadas

- Lista efetiva de arquivos: `pipeline/ingestao.py`, constante `ARQUIVOS_TABELAS`.
- Regras de leitura: `pipeline/ingestao.py` usa UTF-8, `dtype=str`, `keep_default_na=False` e `na_values=[""]`.
- Estrutura de destino e execução: [Dicionário de dados](dicionario.md) e [Execução](../operacao/execucao.md).
