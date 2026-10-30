"""Ingestão fiel dos cinco CSVs definidos para a camada raw.

Os nomes de arquivo e tabela são literais para formar o vocabulário usado nas
consultas seguintes. Todos os arquivos são verificados antes de abrir o banco
para impedir uma ingestão parcial. A leitura usa UTF-8 declarado e texto em
todas as colunas, pois conversões e correções pertencem à etapa refined.
Somente campos vazios são nulos: os valores textuais como "NA" e "NULL" não
devem ser reinterpretados pelos valores padrão de NA do pandas. Cada tabela é
substituída para que reexecutar o script produza o mesmo estado. As contagens
impressas vêm do banco, que é a conferência do que foi efetivamente gravado.
"""

import sys

import pandas as pd

from pipeline import db

ARQUIVOS_TABELAS = (
    ("movies_metadata.csv", "filmes"),
    ("ratings.csv", "avaliacoes"),
    ("credits.csv", "creditos"),
    ("keywords.csv", "palavras_chave"),
    ("links.csv", "links"),
)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    faltantes = [arquivo for arquivo, _ in ARQUIVOS_TABELAS if not (db.PASTA_RAW / arquivo).is_file()]
    if faltantes:
        print(f"Arquivos ausentes em {db.PASTA_RAW}:")
        for arquivo in faltantes:
            print(f"- {arquivo}")
        sys.exit(1)

    con = db.conectar()
    total = 0
    try:
        db.criar_schema(con, "raw")
        for arquivo, tabela in ARQUIVOS_TABELAS:
            df = pd.read_csv(
                db.PASTA_RAW / arquivo,
                encoding="utf-8",
                dtype=str,
                keep_default_na=False,
                na_values=[""],
            )
            quantidade = db.gravar(con, df, "raw", tabela)
            total += quantidade
            print(f"raw.{tabela}: {quantidade:,}".replace(",", "."))
        print(f"Total: {total:,}".replace(",", "."))
    finally:
        con.close()


if __name__ == "__main__":
    main()
