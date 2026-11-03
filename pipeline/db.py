"""Conexão e gravação do banco do pipeline.

`PASTA_RAW` e o caminho padrão do DuckDB são ancorados na raiz do projeto para
que chamadas feitas de outros diretórios encontrem os mesmos dados. O caminho
do banco pode ser substituído explicitamente por `MOVIE_DATA_DB_PATH`.
Este módulo só oferece operações genéricas de banco: as etapas decidem como
ler, tipar e nomear os dados, evitando regras de negócio escondidas aqui.
`conectar` não mantém conexão global; quem abriu a conexão também a fecha.
`gravar` substitui a tabela e consulta a contagem persistida, para que o
resultado reflita o banco e reexecuções não dupliquem linhas.
"""

import os
from pathlib import Path

import duckdb

PASTA_RAW = Path(__file__).resolve().parent.parent / "raw"
_ARQUIVO_BANCO = Path(__file__).resolve().parent.parent / "movie_data.duckdb"


def _caminho_banco() -> Path:
    """Retorna o caminho configurado ou o banco padrão ancorado no projeto."""
    configurado = os.environ.get("MOVIE_DATA_DB_PATH")
    if configurado and configurado.strip():
        return Path(configurado).expanduser()
    return _ARQUIVO_BANCO


def conectar(*, must_exist=False, read_only=False):
    """Abre o banco configurado; pode exigir existência e acesso somente leitura.

    ``must_exist=True`` impede que uma execução destinada a atualizar dados
    crie silenciosamente um banco vazio por erro de caminho ou arquivo ausente.
    ``read_only=True`` abre o arquivo sem permitir alterações. Nesse modo, a
    existência do banco também é obrigatória, para evitar a criação acidental
    de um arquivo vazio para consultas.
    """
    arquivo_banco = _caminho_banco()
    if (must_exist or read_only) and not arquivo_banco.is_file():
        raise FileNotFoundError(f"Banco DuckDB não encontrado: {arquivo_banco}")
    if read_only:
        return duckdb.connect(str(arquivo_banco), read_only=True)
    return duckdb.connect(str(arquivo_banco))


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
