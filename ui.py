"""Abre a interface local do DuckDB para explorar o banco do pipeline.

O caminho absoluto evita abrir um banco vazio dependendo do diretório atual.
O arquivo é conferido antes da conexão porque `duckdb.connect` cria bancos
ausentes, o que poderia parecer uma ingestão válida. A extensão UI roda enquanto
a conexão vive, então o processo aguarda Ctrl+C e fecha a conexão para encerrar
o servidor e liberar o lock do arquivo. O stdout é UTF-8 para mensagens legíveis
no Prompt de Comando do Windows.
"""

import sys
import time
from pathlib import Path

import duckdb

ARQUIVO_BANCO = Path(__file__).resolve().parent / "movie_data.duckdb"


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    if not ARQUIVO_BANCO.is_file():
        print("Banco movie_data.duckdb não encontrado. Rode a ingestão antes.")
        sys.exit(1)

    con = duckdb.connect(str(ARQUIVO_BANCO))
    try:
        con.execute("INSTALL ui")
        con.execute("LOAD ui")
        con.execute("CALL start_ui()")
        print("Interface DuckDB: http://localhost:4213")
        print("Ctrl+C para encerrar")
        while True:
            try:
                # Mantém a conexão viva enquanto a extensão atende o navegador.
                time.sleep(1)
            except KeyboardInterrupt:
                break
    finally:
        con.close()


if __name__ == "__main__":
    main()
