# Camadas de dados

| Schema | Responsabilidade | Observações documentadas |
|---|---|---|
| `raw` | Receber os cinco CSVs ingeridos. | A ingestão lê colunas como texto e converte somente campos vazios em nulos. |
| `refined` | Publicar filmes, avaliações e links após conversões e validações. | Nomes de coluna são preservados; campos sem tipo explícito permanecem `VARCHAR`. |
| `rejected` | Isolar ocorrências de filmes que não seguem as regras definidas. | `rejected.filmes` conserva colunas originais e acrescenta metadados de origem e motivo. |
| `marts` | Armazenar os resultados das consultas analíticas. | Uma consulta SQL numerada define cada tabela MART. |

## Materialização

- A ingestão substitui as tabelas `raw` correspondentes, sem append.
- A transformação substitui `refined.filmes`, `refined.avaliacoes`, `refined.links` e `rejected.filmes` atomicamente.
- A publicação completa substitui o schema `marts` dentro de uma transação. Com `--only NN ...`, somente os indicadores selecionados são substituídos e as demais MARTs são preservadas.

As regras completas de tipos, nulidade, duplicidades e rejeição estão em `specs/transformacao.md`; um resumo está em [Transformação](../dados/transformacao.md).
