# Banco DuckDB e snapshot

O caminho padrão local é `movie_data.duckdb` na raiz do projeto. `pipeline/db.py` também aceita `MOVIE_DATA_DB_PATH`, que tem prioridade sobre os padrões. No Streamlit Community Cloud, o caminho padrão do dashboard é `data/movie_data_snapshot.duckdb`.

`app.py` verifica o banco antes de apresentar as abas e abre uma conexão DuckDB com `read_only=True`. As funções de consulta em `painel.py` também usam acesso de leitura. A conexão genérica usada pelas etapas do pipeline não é somente leitura, pois essas etapas precisam criar e substituir tabelas.

O trecho abaixo reproduz a abertura read-only implementada em `pipeline/db.py`:

```python
return duckdb.connect(str(arquivo_banco), read_only=True)
```

O snapshot foi preparado para as consultas atuais do dashboard: contém as 11 MARTs e `refined.filmes` com `id` e `poster_path`, necessários ao destaque de pôsteres. Ele não substitui o banco completo para ingestão e transformação.

`pipeline/snapshot.py` implementa também um mecanismo opcional de download com `MOVIE_DATA_SNAPSHOT_URL` e `MOVIE_DATA_SNAPSHOT_SHA256`; esse mecanismo só é ativado quando as duas variáveis estão configuradas. O caminho padrão documentado para o Streamlit Cloud, contudo, é o snapshot local versionado em `data/`.
