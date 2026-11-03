"""Executor transacional dos indicadores documentados na Aula 3.

Responsabilidade
----------------
Este módulo orquestra a publicação dos marts a partir das consultas SQL
versionadas no projeto. As regras de negócio e os cálculos dos indicadores
permanecem nos próprios arquivos SQL.

Descoberta e nomenclatura
-------------------------
A pasta ``sql/marts/`` é localizada relativamente a este módulo. Todos os
arquivos ``.sql`` dessa pasta são ordenados alfabeticamente antes da execução.
Cada arquivo deve iniciar com o prefixo numérico ``NN_``; o nome do destino é
o restante do nome do arquivo, sem a extensão. Destinos duplicados são
validados sem diferenciar maiúsculas e minúsculas antes da execução de SQL.

Entradas e publicação
---------------------
Antes da publicação, são obrigatórias as tabelas ``refined.filmes``,
``refined.avaliacoes`` e ``refined.links``. Cada consulta é lida integralmente;
apenas espaços em branco externos e, no máximo, um ponto e vírgula final são
removidos. O conteúdo restante da consulta é preservado e usado em uma
instrução CTAS para criar ``marts.<nome_do_destino>``.

Consistência e contagens
------------------------
Após cada CTAS, a quantidade de linhas é obtida diretamente da tabela criada.
Marts com zero linhas são rejeitados e causam falha na execução. A substituição
do schema ``marts`` e a criação de todos os seus objetos ocorrem em uma única
transação: ela só é confirmada se todos os marts forem criados com sucesso e
contiverem linhas. Qualquer falha provoca rollback, preservando o schema da
última execução bem-sucedida.

Saída
-----
Em caso de sucesso, imprime uma linha por mart no formato
``✓ marts.nome_da_tabela 20 linhas``, com milhares separados por ponto, seguida
do total de marts criados e da soma das linhas.

Modo seletivo
-------------
``--only NN ...`` atualiza somente os indicadores informados, preserva as
demais tabelas MART e valida apenas as tabelas refined referenciadas por esses
SQLs. Sem ``--only``, o schema marts inteiro continua sendo substituido.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import duckdb

from pipeline import db

_PASTA_MARTS = Path(__file__).resolve().parent.parent / "sql" / "marts"
_PREFIXO_NUMERICO = re.compile(r"^\d{2}_(.+)$")
_REFERENCIA_TABELA = re.compile(
    r"\b(?:FROM|JOIN)\s+([A-Za-z_]\w*)\.([A-Za-z_]\w*)", re.IGNORECASE
)


def _argumentos(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Publica tabelas MART do projeto.")
    parser.add_argument(
        "--only",
        nargs="+",
        metavar="NN",
        type=_indicador,
        help="publica somente os indicadores informados (ex.: --only 05 06)",
    )
    return parser.parse_args(argv)


def _indicador(valor: str) -> str:
    if not re.fullmatch(r"\d{1,2}", valor):
        raise argparse.ArgumentTypeError("o indicador deve ser numérico (ex.: 05)")
    return valor.zfill(2)


def _descobrir_arquivos() -> tuple[list[tuple[Path, str]], list[str]]:
    """Retorna os SQL ordenados e os problemas de nome encontrados."""
    if not _PASTA_MARTS.is_dir():
        return [], [f"Pasta de consultas não encontrada: {_PASTA_MARTS}"]

    arquivos = sorted(_PASTA_MARTS.glob("*.sql"), key=lambda arquivo: arquivo.name)
    if not arquivos:
        return [], [f"Nenhum arquivo .sql encontrado em {_PASTA_MARTS}"]

    problemas: list[str] = []
    destinos: dict[str, list[str]] = {}
    indicadores: dict[str, list[str]] = {}
    arquivos_validos: list[tuple[Path, str]] = []

    for arquivo in arquivos:
        correspondencia = _PREFIXO_NUMERICO.match(arquivo.stem)
        if correspondencia is None:
            problemas.append(
                f"{arquivo.name}: nome deve começar com prefixo numérico NN_."
            )
            continue

        destino = correspondencia.group(1)
        indicador = arquivo.stem[:2]
        if not destino:
            problemas.append(f"{arquivo.name}: nome de destino vazio.")
            continue

        destinos.setdefault(destino.casefold(), []).append(arquivo.name)
        indicadores.setdefault(indicador, []).append(arquivo.name)
        arquivos_validos.append((arquivo, destino))

    for destino, nomes in sorted(destinos.items()):
        if len(nomes) > 1:
            problemas.append(
                f"Destino duplicado '{destino}' nos arquivos: {', '.join(nomes)}"
            )

    for indicador, nomes in sorted(indicadores.items()):
        if len(nomes) > 1:
            problemas.append(
                f"Indicador {indicador} duplicado nos arquivos: {', '.join(nomes)}"
            )

    return arquivos_validos, problemas


def _tabelas_refined_ausentes(con) -> list[str]:
    esperadas = ("filmes", "avaliacoes", "links")
    existentes = {
        linha[0]
        for linha in con.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = ? AND table_name IN (?, ?, ?)",
            ["refined", *esperadas],
        ).fetchall()
    }
    return [f"refined.{tabela}" for tabela in esperadas if tabela not in existentes]


def _tabelas_origem_ausentes(con, arquivos) -> list[str]:
    """Valida apenas tabelas refined referenciadas nos SQLs selecionados."""
    necessarias: set[str] = set()
    for arquivo, _ in arquivos:
        consulta = arquivo.read_text(encoding="utf-8")
        necessarias.update(
            tabela
            for schema, tabela in _REFERENCIA_TABELA.findall(consulta)
            if schema.casefold() == "refined"
        )
    existentes = {
        linha[0]
        for linha in con.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'refined'"
        ).fetchall()
    }
    return [f"refined.{tabela}" for tabela in sorted(necessarias - existentes)]


def _selecionar_arquivos(arquivos, indicadores: list[str]):
    por_indicador = {
        arquivo.stem[:2]: (arquivo, destino) for arquivo, destino in arquivos
    }
    inexistentes = sorted(set(indicadores) - por_indicador.keys())
    if inexistentes:
        return [], [f"Indicadores não encontrados: {', '.join(inexistentes)}"]
    return [por_indicador[indicador] for indicador in dict.fromkeys(indicadores)], []


def _tabela_existe(con, destino: str) -> bool:
    return con.execute(
        "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
        "WHERE table_schema = 'marts' AND table_name = ?)",
        [destino],
    ).fetchone()[0]


def _identificador(nome: str) -> str:
    """Delimita um identificador DuckDB, escapando aspas internas."""
    return '"' + nome.replace('"', '""') + '"'


def main(argv=None) -> int:
    """Valida entradas e publica todos os marts em uma única transação."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    argumentos = _argumentos(argv)
    arquivos, problemas = _descobrir_arquivos()
    if problemas:
        print("Problemas nos arquivos SQL:")
        for problema in problemas:
            print(f"- {problema}")
        return 1

    seletiva = argumentos.only is not None
    if seletiva:
        arquivos, problemas = _selecionar_arquivos(arquivos, argumentos.only)
        if problemas:
            for problema in problemas:
                print(problema)
            return 1

    con = None
    transacao_aberta = False
    resultados: list[tuple[str, int]] = []
    try:
        con = db.conectar(must_exist=True)
        ausentes = (
            _tabelas_origem_ausentes(con, arquivos)
            if seletiva
            else _tabelas_refined_ausentes(con)
        )
        if ausentes:
            print("Tabelas de entrada ausentes:")
            for tabela in ausentes:
                print(f"- {tabela}")
            print("Execute: uv run python -m pipeline.transformacao")
            return 1

        con.execute("BEGIN TRANSACTION")
        transacao_aberta = True
        if not seletiva:
            con.execute("DROP SCHEMA IF EXISTS marts CASCADE")
        db.criar_schema(con, "marts")

        for arquivo, destino in arquivos:
            try:
                consulta = arquivo.read_text(encoding="utf-8").strip()
            except Exception as erro:
                raise RuntimeError(
                    f"Erro ao ler o arquivo {arquivo.name}: {erro}"
                ) from erro
            if consulta.endswith(";"):
                consulta = consulta[:-1].rstrip()

            tabela_sql = f"marts.{_identificador(destino)}"
            try:
                con.execute(f"CREATE OR REPLACE TABLE {tabela_sql} AS {consulta}")
                if not _tabela_existe(con, destino):
                    raise RuntimeError(f"Tabela marts.{destino} não foi criada")
                quantidade = con.execute(
                    f"SELECT COUNT(*) FROM {tabela_sql}"
                ).fetchone()[0]
            except Exception as erro:
                raise RuntimeError(f"Erro no arquivo {arquivo.name}: {erro}") from erro

            if quantidade == 0:
                raise RuntimeError(
                    f"Mart marts.{destino} criado com zero linhas "
                    f"(arquivo {arquivo.name}); execução interrompida."
                )
            resultados.append((destino, quantidade))

        con.execute("COMMIT")
        transacao_aberta = False

        total_linhas = sum(quantidade for _, quantidade in resultados)
        for destino, quantidade in resultados:
            print(f"✓ marts.{destino} {quantidade:,}".replace(",", ".") + " linhas")
        print(
            f"Concluído: {len(resultados)} marts, {total_linhas:,}".replace(",", ".")
            + " linhas no total."
        )
        return 0
    # Keep this broad so every failure during publication attempts a rollback.
    except Exception as erro:  # noqa: BLE001
        if con is not None and transacao_aberta:
            try:
                con.execute("ROLLBACK")
                transacao_aberta = False
            except duckdb.Error as erro_rollback:
                print(f"Falha ao reverter a transação: {erro_rollback}")
        print(erro)
        return 1
    finally:
        if con is not None:
            con.close()


if __name__ == "__main__":
    raise SystemExit(main())
