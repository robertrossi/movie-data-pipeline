
"""Conexão e gravação do banco do pipeline.

`PASTA_RAW` e o arquivo DuckDB são ancorados na raiz do projeto para que
chamadas feitas de outros diretórios sempre encontrem os mesmos dados.
Este módulo só oferece operações genéricas de banco: as etapas decidem como
ler, tipar e nomear os dados, evitando regras de negócio escondidas aqui.
`conectar` não mantém conexão global; quem abriu a conexão também a fecha.
`gravar` substitui a tabela e consulta a contagem persistida, para que o
resultado reflita o banco e reexecuções não dupliquem linhas.
"""

from pathlib import Path

import duckdb

PASTA_RAW = Path(__file__).resolve().parent.parent / "raw"
_ARQUIVO_BANCO = Path(__file__).resolve().parent.parent / "movie_data.duckdb"


def conectar():
    """Abre ou cria o banco na raiz do projeto; o chamador fecha a conexão."""
    return duckdb.connect(str(_ARQUIVO_BANCO))


def criar_schema(con, nome):
    """Cria o schema quando necessário, tratando o argumento como identificador."""
    identificador = '"' + nome.replace('"', '""') + '"'
    con.execute(f"CREATE SCHEMA IF NOT EXISTS {identificador}")


def gravar(con, df, schema, tabela):
    """Substitui uma tabela pelo DataFrame e retorna a contagem lida do DuckDB.

    O registro temporário só existe durante a instrução e é removido mesmo se
    a gravação falhar, para não deixar objetos auxiliares na conexão.
    """
    identificador_schema = '"' + schema.replace('"', '""') + '"'
    identificador_tabela = '"' + tabela.replace('"', '""') + '"'
    nome_registro = "_pipeline_dataframe_gravar"
    con.register(nome_registro, df)
    try:
        con.execute(
            f"CREATE OR REPLACE TABLE {identificador_schema}.{identificador_tabela} "
            f"AS SELECT * FROM {nome_registro}"
        ).fetchall()

        resultado = con.execute(
            f"SELECT count(*) FROM {identificador_schema}.{identificador_tabela}"
        ).fetchall()
        return resultado[0][0]
    finally:
        con.unregister(nome_registro)

