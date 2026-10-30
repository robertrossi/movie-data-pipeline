"""Transformação de `raw` para `refined` — Cinema Analytics Pipeline.

Especificação aplicada (Aula 2 — “Ler o dado ≠ confiar no dado”):

Escopo e nomes
--------------
Transforma `raw.filmes`, `raw.avaliacoes` e `raw.links` em tabelas homônimas
no schema `refined`, e isola em `rejected.filmes` os três registros malformados
e todas as ocorrências dos 13 IDs com duplicidade divergente.
`raw.creditos` e `raw.palavras_chave` ficam fora desta etapa. Os nomes originais
das colunas são preservados; colunas sem tipo explicitamente definido
permanecem VARCHAR.

Tipos de destino
----------------
* filmes: id BIGINT; budget e revenue DECIMAL(18,2); release_date DATE;
  vote_average e popularity DOUBLE; vote_count BIGINT.
* avaliacoes: userId, movieId e timestamp BIGINT; rating DOUBLE. timestamp
  permanece Unix em segundos.
* links: movieId e tmdbId BIGINT; imdbId VARCHAR.

Conversões e nulos
------------------
Um valor nulo legítimo é preservado onde permitido. Um valor não nulo que não
possa ser convertido bloqueia a transformação, exceto nos registros designados
para rejeição (os três registros malformados e todas as ocorrências dos 13 IDs
divergentes); não se converte erro em NULL nem se fabricam correções.
filmes.id, avaliacoes.userId, avaliacoes.movieId e
links.movieId não podem ser nulos. Outros nulos são preservados conforme a
origem e a política de nulidade da especificação. budget e revenue iguais a
zero permanecem zero. genres continua VARCHAR; a decomposição fica para etapa
posterior.

Duplicidades
------------
Em filmes, linhas integralmente idênticas são removidas, mantendo uma ocorrência.
Todas as ocorrências dos 13 IDs com conteúdo divergente identificados na
especificação são preservadas em rejected.filmes e excluídas de refined.filmes;
nenhuma versão é escolhida. Conflitos em outros IDs continuam bloqueando a
transformação. Em avaliacoes, duplicidades na chave composta (userId, movieId)
interrompem a transformação. Em links, duplicidades de movieId interrompem a
transformação, enquanto tmdbId repetido é permitido.

Evidências RAW registradas na especificação
-------------------------------------------
Volumes: filmes 45.466; avaliacoes 26.024.289; links 45.843. Filmes contém 30
registros excedentes em relação aos IDs distintos, 16 IDs com ocorrências
integralmente idênticas (incluindo o ID 141971, que aparece três vezes) e 13 IDs
divergentes: 4912, 10991, 12600, 13209, 14788, 15028, 22649, 69234, 77221,
84198, 109962, 110428 e 132641. As divergências observadas estão em popularity
e, para 10991 e 15028, também em vote_count. Todas as ocorrências desses IDs
são rejeitadas, não sendo escolhida uma versão. Há três registros com
indícios de desalinhamento, problema distinto dos IDs divergentes. Os registros
source_rowid 19730 e 29503 falham em id, budget e release_date; o 35587 falha
em id, budget, popularity e release_date. budget tem
três valores não conversíveis; revenue tem três valores vazios (nulos legítimos)
e três inválidos associados aos registros desalinhados; release_date tem 87
nulos e três valores inválidos associados aos desalinhamentos. Existem 36.573
budget zero e 38.052 revenue zero. genres contém listas serializadas em texto.
avaliacoes tem 270.896 usuários e 45.115 filmes distintos, sem duplicidade da
chave composta ou valor inválido em rating/timestamp; rating vai de 0,5 a 5,0
e timestamp é Unix em segundos. links não tem movieId duplicado, tem 219
tmdbId nulos, 29 tmdbId associados a vários movieId e 161 tmdbId sem filme
correspondente. Essas evidências orientam validações e não autorizam correções.

Execução, atomicidade e aceitação
--------------------------------
Verifica-se a presença das três tabelas RAW antes de transformar. Se faltarem,
todas são listadas e a execução termina com código 1, orientando a ingestão.
As três tabelas refined e `rejected.filmes` são criadas/substituídas com CREATE
OR REPLACE, nunca append, dentro de uma única transação DuckDB. Antes de rejeitar,
os source_rowid malformados são conferidos contra os valores esperados e os 13
IDs divergentes são confirmados como conflitos; qualquer divergência interrompe
a transformação. Esses registros são omitidos das validações por linha e de
refined.filmes, sem alteração em RAW. Se qualquer validação ou etapa de
publicação falhar, a transação é revertida; nenhuma alteração parcial fica
persistida. A execução informa contagens de entrada e saída, linhas idênticas
removidas, nulos preservados por coluna e quantidade e motivos dos rejeitados,
além de reportar inconsistências com tabela, coluna, valor e localizador do
registro. Mensagens de terminal usam UTF-8.

Premissas e limitações
---------------------
Os três registros desalinhados e os IDs divergentes não são corrigidos
arbitrariamente. Os source_rowid 19730, 29503 e 35587 são localizadores físicos
da versão atual da tabela; seus registros são validados por conteúdo antes do
isolamento e esses localizadores não são IDs permanentes do CSV. ratings_small.csv
e links_small.csv aparecem na lista
original de indicadores, mas a ingestão da Aula 1 usa ratings.csv e links.csv;
esta transformação segue as tabelas efetivamente ingeridas, sem alterar a
ingestão. `source_rowid` usa o pseudocampo físico `rowid` do DuckDB apenas como
localizador temporário durante a transação de validação. Não corresponde à
linha original do CSV e não tem garantia de estabilidade entre transações.
"""

from __future__ import annotations

import sys

from pipeline import db


RAW_TABLES = ("filmes", "avaliacoes", "links")

FILM_RAW_COLUMNS = (
    "adult",
    "belongs_to_collection",
    "budget",
    "genres",
    "homepage",
    "id",
    "imdb_id",
    "original_language",
    "original_title",
    "overview",
    "popularity",
    "poster_path",
    "production_companies",
    "production_countries",
    "release_date",
    "revenue",
    "runtime",
    "spoken_languages",
    "status",
    "tagline",
    "title",
    "video",
    "vote_average",
    "vote_count",
)

MALFORMED_FILM_REJECTION_REASONS: dict[int, str] = {
    19730: "Deslocamento de colunas; falhas de conversão em id, budget, release_date",
    29503: "Deslocamento de colunas; falhas de conversão em id, budget, release_date",
    35587: "Deslocamento de colunas; falhas de conversão em id, budget, popularity, release_date",
}

DIVERGENT_FILM_REJECTION_REASONS: dict[str, str] = {
    "4912": "Conflito de duplicidade com conteúdo divergente (id=4912)",
    "10991": "Conflito de duplicidade com conteúdo divergente (id=10991)",
    "12600": "Conflito de duplicidade com conteúdo divergente (id=12600)",
    "13209": "Conflito de duplicidade com conteúdo divergente (id=13209)",
    "14788": "Conflito de duplicidade com conteúdo divergente (id=14788)",
    "15028": "Conflito de duplicidade com conteúdo divergente (id=15028)",
    "22649": "Conflito de duplicidade com conteúdo divergente (id=22649)",
    "69234": "Conflito de duplicidade com conteúdo divergente (id=69234)",
    "77221": "Conflito de duplicidade com conteúdo divergente (id=77221)",
    "84198": "Conflito de duplicidade com conteúdo divergente (id=84198)",
    "109962": "Conflito de duplicidade com conteúdo divergente (id=109962)",
    "110428": "Conflito de duplicidade com conteúdo divergente (id=110428)",
    "132641": "Conflito de duplicidade com conteúdo divergente (id=132641)",
}

MALFORMED_FILM_ROWIDS = tuple(MALFORMED_FILM_REJECTION_REASONS)
DIVERGENT_FILM_IDS = tuple(DIVERGENT_FILM_REJECTION_REASONS)

# Snapshot dos valores observados que identifica cada registro esperado. O teste
# integral evita rejeitar uma linha diferente caso o DuckDB reutilize um rowid.
EXPECTED_REJECTED_FILM_RECORDS = {
    19730: {
        "adult": " - Written by Ørnås",
        "belongs_to_collection": "0.065736",
        "budget": "/ff9qCepilowshEtG2GYWwzt2bs4.jpg",
        "genres": "[{'name': 'Carousel Productions', 'id': 11176}, {'name': 'Vision View Entertainment', 'id': 11602}, {'name': 'Telescene Film Group Productions', 'id': 29812}]",
        "homepage": "[{'iso_3166_1': 'CA', 'name': 'Canada'}, {'iso_3166_1': 'LU', 'name': 'Luxembourg'}, {'iso_3166_1': 'GB', 'name': 'United Kingdom'}, {'iso_3166_1': 'US', 'name': 'United States of America'}]",
        "id": "1997-08-20",
        "imdb_id": "0",
        "original_language": "104.0",
        "original_title": "[{'iso_639_1': 'en', 'name': 'English'}]",
        "overview": "Released",
        "popularity": None,
        "poster_path": "Midnight Man",
        "production_companies": "False",
        "production_countries": "6.0",
        "release_date": "1",
        "revenue": None,
        "runtime": None,
        "spoken_languages": None,
        "status": None,
        "tagline": None,
        "title": None,
        "video": None,
        "vote_average": None,
        "vote_count": None,
    },
    29503: {
        "adult": " Rune Balot goes to a casino connected to the October corporation to try to wrap up her case once and for all.",
        "belongs_to_collection": "1.931659",
        "budget": "/zV8bHuSL6WXoD6FWogP9j4x80bL.jpg",
        "genres": "[{'name': 'Aniplex', 'id': 2883}, {'name': 'GoHands', 'id': 7759}, {'name': 'BROSTA TV', 'id': 7760}, {'name': 'Mardock Scramble Production Committee', 'id': 7761}, {'name': 'Sentai Filmworks', 'id': 33751}]",
        "homepage": "[{'iso_3166_1': 'US', 'name': 'United States of America'}, {'iso_3166_1': 'JP', 'name': 'Japan'}]",
        "id": "2012-09-29",
        "imdb_id": "0",
        "original_language": "68.0",
        "original_title": "[{'iso_639_1': 'ja', 'name': '日本語'}]",
        "overview": "Released",
        "popularity": None,
        "poster_path": "Mardock Scramble: The Third Exhaust",
        "production_companies": "False",
        "production_countries": "7.0",
        "release_date": "12",
        "revenue": None,
        "runtime": None,
        "spoken_languages": None,
        "status": None,
        "tagline": None,
        "title": None,
        "video": None,
        "vote_average": None,
        "vote_count": None,
    },
    35587: {
        "adult": " Avalanche Sharks tells the story of a bikini contest that turns into a horrifying affair when it is hit by a shark avalanche.",
        "belongs_to_collection": "2.185485",
        "budget": "/zaSf5OG7V8X8gqFvly88zDdRm46.jpg",
        "genres": "[{'name': 'Odyssey Media', 'id': 17161}, {'name': 'Pulser Productions', 'id': 18012}, {'name': 'Rogue State', 'id': 18013}, {'name': 'The Cartel', 'id': 23822}]",
        "homepage": "[{'iso_3166_1': 'CA', 'name': 'Canada'}]",
        "id": "2014-01-01",
        "imdb_id": "0",
        "original_language": "82.0",
        "original_title": "[{'iso_639_1': 'en', 'name': 'English'}]",
        "overview": "Released",
        "popularity": "Beware Of Frost Bites",
        "poster_path": "Avalanche Sharks",
        "production_companies": "False",
        "production_countries": "4.3",
        "release_date": "22",
        "revenue": None,
        "runtime": None,
        "spoken_languages": None,
        "status": None,
        "tagline": None,
        "title": None,
        "video": None,
        "vote_average": None,
        "vote_count": None,
    },
}

TARGET_TYPES = {
    "filmes": {
        "id": "BIGINT",
        "budget": "DECIMAL(18,2)",
        "revenue": "DECIMAL(18,2)",
        "release_date": "DATE",
        "vote_average": "DOUBLE",
        "popularity": "DOUBLE",
        "vote_count": "BIGINT",
    },
    "avaliacoes": {
        "userId": "BIGINT",
        "movieId": "BIGINT",
        "rating": "DOUBLE",
        "timestamp": "BIGINT",
    },
    "links": {
        "movieId": "BIGINT",
        "tmdbId": "BIGINT",
        "imdbId": "VARCHAR",
    },
}

REQUIRED_KEYS = {
    "filmes": ("id",),
    "avaliacoes": ("userId", "movieId"),
    "links": ("movieId",),
}

DUPLICATE_KEYS = {
    "avaliacoes": ("userId", "movieId"),
    "links": ("movieId",),
}


class TransformationError(Exception):
    """Erro de validação que impede publicar qualquer tabela refined."""


def _q(identifier: str) -> str:
    """Quote DuckDB identifier safely."""
    return '"' + identifier.replace('"', '""') + '"'


def _qualified(schema: str, table: str) -> str:
    return f"{_q(schema)}.{_q(table)}"


def _fetch_dicts(cursor) -> list[dict[str, object]]:
    names = [description[0] for description in cursor.description]
    return [dict(zip(names, row, strict=True)) for row in cursor.fetchall()]


def _existing_raw_tables(con) -> set[str]:
    rows = con.execute(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'raw' AND table_name IN (?, ?, ?)
        """,
        list(RAW_TABLES),
    ).fetchall()
    return {row[0] for row in rows}


def _column_names(con, table: str) -> list[str]:
    result = con.execute(f"DESCRIBE SELECT * FROM {_qualified('raw', table)}")
    return [row[0] for row in result.fetchall()]


def _check_expected_columns(columns_by_table: dict[str, list[str]]) -> None:
    errors = []
    for table, types in TARGET_TYPES.items():
        missing = sorted(set(types) - set(columns_by_table[table]))
        if missing:
            errors.append(f"raw.{table}: colunas esperadas ausentes: {', '.join(missing)}")
    missing_film_columns = sorted(
        set(FILM_RAW_COLUMNS) - set(columns_by_table["filmes"])
    )
    if missing_film_columns:
        errors.append(
            "raw.filmes: colunas originais esperadas ausentes: "
            + ", ".join(missing_film_columns)
        )
    if errors:
        raise TransformationError("\n".join(errors))


def _count_rows(con, schema: str, table: str) -> int:
    return con.execute(f"SELECT COUNT(*) FROM {_qualified(schema, table)}").fetchone()[0]


def _rowid_list_sql(rowids: tuple[int, ...] | list[int]) -> str:
    return ", ".join(str(int(rowid)) for rowid in rowids)


def _rowid_exclusion(alias: str, excluded_rowids: tuple[int, ...]) -> str:
    if not excluded_rowids:
        return ""
    prefix = f"{alias}." if alias else ""
    return f"{prefix}rowid NOT IN ({_rowid_list_sql(excluded_rowids)})"


def _film_exclusion(
    alias: str,
    excluded_rowids: tuple[int, ...] = (),
    excluded_ids: tuple[str, ...] = (),
) -> str:
    """Build the filter that removes designated rejected films from processing."""
    prefix = f"{alias}." if alias else ""
    exclusions = []
    if excluded_rowids:
        exclusions.append(_rowid_exclusion(alias, excluded_rowids))
    if excluded_ids:
        ids_sql = ", ".join(_sql_string(movie_id) for movie_id in excluded_ids)
        film_id = f"{prefix}{_q('id')}"
        exclusions.append(f"({film_id} IS NULL OR {film_id} NOT IN ({ids_sql}))")
    return " AND ".join(exclusions)


def _validate_rejected_film_locators(con) -> None:
    expected_rowids = tuple(EXPECTED_REJECTED_FILM_RECORDS)
    select_columns = ", ".join(f"{_q(column)}" for column in FILM_RAW_COLUMNS)
    sql = (
        f"SELECT rowid AS source_rowid, {select_columns} "
        f"FROM {_qualified('raw', 'filmes')} "
        f"WHERE rowid IN ({_rowid_list_sql(expected_rowids)})"
    )
    actual_rows = _fetch_dicts(con.execute(sql))
    actual_by_rowid = {row["source_rowid"]: row for row in actual_rows}
    problems = []

    for rowid, expected in EXPECTED_REJECTED_FILM_RECORDS.items():
        actual = actual_by_rowid.get(rowid)
        if actual is None:
            problems.append(f"source_rowid {rowid}: registro não encontrado")
            continue
        mismatches = {
            column: {"esperado": value, "encontrado": actual[column]}
            for column, value in expected.items()
            if actual[column] != value
        }
        if mismatches:
            problems.append(f"source_rowid {rowid}: valores divergentes {mismatches!r}")

    if problems:
        raise TransformationError(
            "Os localizadores físicos não correspondem aos registros malformados "
            "esperados; nenhum registro será isolado:\n- " + "\n- ".join(problems)
        )


def _validate_divergent_film_ids(con) -> None:
    """Confirm that each configured film ID still has divergent raw records."""
    ids_sql = ", ".join(_sql_string(movie_id) for movie_id in DIVERGENT_FILM_IDS)
    rows = con.execute(
        "SELECT id, COUNT(*) AS distinct_versions FROM ("
        "SELECT DISTINCT * FROM raw.filmes "
        f"WHERE id IN ({ids_sql})"
        ") AS distinct_records GROUP BY id"
    ).fetchall()
    versions_by_id = {row[0]: row[1] for row in rows}
    problems = [
        f"id {movie_id}: "
        + (
            f"encontradas {versions_by_id[movie_id]} versões distintas"
            if versions_by_id.get(movie_id, 0) > 1
            else f"conflito divergente não confirmado (versões distintas={versions_by_id.get(movie_id, 0)})"
        )
        for movie_id in DIVERGENT_FILM_IDS
        if versions_by_id.get(movie_id, 0) <= 1
    ]
    if problems:
        raise TransformationError(
            "Os IDs de filmes designados para rejeição não correspondem aos "
            "conflitos divergentes esperados; nenhuma tabela será publicada:\n- "
            + "\n- ".join(problems)
        )


def _conversion_and_null_issues(
    con,
    table: str,
    columns: list[str],
    excluded_rowids: tuple[int, ...] = (),
    excluded_ids: tuple[str, ...] = (),
) -> list[dict[str, object]]:
    """Find invalid casts and null required keys, including source row values."""
    raw = _qualified("raw", table)
    specs = TARGET_TYPES[table]
    record_columns = ", ".join(f"n.{_q(name)}" for name in columns)
    selections: list[str] = []

    for column in REQUIRED_KEYS[table]:
        quoted = _q(column)
        selections.append(
            "SELECT n.source_rowid, "
            f"'{column}' AS column_name, CAST(NULL AS VARCHAR) AS raw_value, "
            "'chave obrigatória nula' AS issue, "
            f"{record_columns} "
            f"FROM numbered AS n WHERE n.{quoted} IS NULL"
        )

    for column, target_type in specs.items():
        quoted = _q(column)
        if target_type == "VARCHAR":
            continue
        selections.append(
            "SELECT n.source_rowid, "
            f"'{column}' AS column_name, CAST(n.{quoted} AS VARCHAR) AS raw_value, "
            "'valor não conversível' AS issue, "
            f"{record_columns} "
            f"FROM numbered AS n "
            f"WHERE n.{quoted} IS NOT NULL "
            f"AND TRY_CAST(n.{quoted} AS {target_type}) IS NULL"
        )

    source_filter = (
        _film_exclusion(
            "", excluded_rowids=excluded_rowids, excluded_ids=excluded_ids
        )
        if table == "filmes"
        else _rowid_exclusion("", excluded_rowids)
    )
    source_where = f" WHERE {source_filter}" if source_filter else ""
    sql = (
        "WITH numbered AS MATERIALIZED ("
        f"SELECT rowid AS source_rowid, * FROM {raw}{source_where}"
        ") "
        + " UNION ALL ".join(selections)
        + " ORDER BY issue, column_name, source_rowid"
    )
    return _fetch_dicts(con.execute(sql))


def _duplicate_issues(
    con,
    table: str,
    columns: list[str],
    excluded_rowids: tuple[int, ...] = (),
    excluded_ids: tuple[str, ...] = (),
) -> list[dict[str, object]]:
    """Return full source records involved in prohibited duplicate keys."""
    if table == "filmes":
        key_columns = ("id",)
        excluded_filter = _film_exclusion(
            "", excluded_rowids=excluded_rowids, excluded_ids=excluded_ids
        )
        film_filters = [_q("id") + " IS NOT NULL"]
        if excluded_filter:
            film_filters.append(excluded_filter)
        distinct_source = (
            f"SELECT DISTINCT * FROM {_qualified('raw', table)} "
            f"WHERE {' AND '.join(film_filters)}"
        )
        duplicate_query = (
            f"SELECT {_q('id')} AS key_0, COUNT(*) AS occurrences "
            f"FROM ({distinct_source}) AS distinct_rows "
            f"GROUP BY {_q('id')} HAVING COUNT(*) > 1"
        )
    else:
        key_columns = DUPLICATE_KEYS.get(table, ())
        if not key_columns:
            return []
        keys_sql = ", ".join(
            f"{_q(name)} AS {_q(f'key_{index}')}"
            for index, name in enumerate(key_columns)
        )
        duplicate_query = (
            f"SELECT {keys_sql}, COUNT(*) AS occurrences "
            f"FROM {_qualified('raw', table)} GROUP BY "
            f"{', '.join(_q(name) for name in key_columns)} "
            "HAVING COUNT(*) > 1"
        )

    duplicates = con.execute(duplicate_query).fetchall()
    if not duplicates:
        return []

    key_aliases = [f"key_{index}" for index in range(len(key_columns))]
    join = " AND ".join(
        f"n.{_q(key)} IS NOT DISTINCT FROM d.{_q(alias)}"
        for key, alias in zip(key_columns, key_aliases, strict=True)
    )
    record_columns = ", ".join(f"n.{_q(name)}" for name in columns)
    source_filter = (
        _film_exclusion(
            "", excluded_rowids=excluded_rowids, excluded_ids=excluded_ids
        )
        if table == "filmes"
        else _rowid_exclusion("", excluded_rowids)
    )
    source_where = f" WHERE {source_filter}" if source_filter else ""
    sql = (
        "WITH numbered AS MATERIALIZED ("
        f"SELECT rowid AS source_rowid, * "
        f"FROM {_qualified('raw', table)}{source_where}"
        "), duplicate_keys AS ("
        f"{duplicate_query}"
        ") "
        f"SELECT n.source_rowid, d.occurrences, {record_columns} "
        "FROM numbered AS n JOIN duplicate_keys AS d ON "
        f"{join} ORDER BY {', '.join(f'n.{_q(key)}' for key in key_columns)}, n.source_rowid"
    )
    return _fetch_dicts(con.execute(sql))


def _identical_film_duplicates(
    con,
    excluded_rowids: tuple[int, ...] = (),
    excluded_ids: tuple[str, ...] = (),
) -> int:
    source_filter = _film_exclusion(
        "", excluded_rowids=excluded_rowids, excluded_ids=excluded_ids
    )
    source_where = f" WHERE {source_filter}" if source_filter else ""
    raw_count = con.execute(
        f"SELECT COUNT(*) FROM raw.filmes{source_where}"
    ).fetchone()[0]
    distinct_count = con.execute(
        "SELECT COUNT(*) FROM ("
        f"SELECT DISTINCT * FROM raw.filmes{source_where}"
        ") AS unique_rows"
    ).fetchone()[0]
    return raw_count - distinct_count


def _create_table_sql(table: str, columns: list[str]) -> str:
    expressions = []
    for column in columns:
        quoted = _q(column)
        target_type = TARGET_TYPES[table].get(column, "VARCHAR")
        expressions.append(f"CAST(src.{quoted} AS {target_type}) AS {quoted}")
    select = ", ".join(expressions)
    source = _qualified("raw", table)
    if table == "filmes":
        exclusion = _film_exclusion(
            "",
            excluded_rowids=MALFORMED_FILM_ROWIDS,
            excluded_ids=DIVERGENT_FILM_IDS,
        )
        source = f"(SELECT DISTINCT * FROM {source} WHERE {exclusion})"
    return (
        f"CREATE OR REPLACE TABLE {_qualified('refined', table)} AS "
        f"SELECT {select} FROM {source} AS src"
    )


def _create_rejected_films_sql() -> str:
    rowid_reason_cases = " ".join(
        f"WHEN src.rowid = {rowid} THEN {_sql_string(reason)}"
        for rowid, reason in MALFORMED_FILM_REJECTION_REASONS.items()
    )
    id_reason_cases = " ".join(
        f"WHEN src.{_q('id')} = {_sql_string(movie_id)} THEN {_sql_string(reason)}"
        for movie_id, reason in DIVERGENT_FILM_REJECTION_REASONS.items()
    )
    malformed_rowids_sql = _rowid_list_sql(MALFORMED_FILM_ROWIDS)
    divergent_ids_sql = ", ".join(
        _sql_string(movie_id) for movie_id in DIVERGENT_FILM_IDS
    )
    original_columns = ", ".join(
        f"CAST(src.{_q(column)} AS VARCHAR) AS {_q(column)}"
        for column in FILM_RAW_COLUMNS
    )
    return (
        f"CREATE OR REPLACE TABLE {_qualified('rejected', 'filmes')} AS "
        "SELECT CAST('raw.filmes' AS VARCHAR) AS source_table, "
        "CAST(src.rowid AS BIGINT) AS source_rowid, "
        f"CAST(CASE {rowid_reason_cases} {id_reason_cases} END AS VARCHAR) AS rejection_reason, "
        f"{original_columns} FROM {_qualified('raw', 'filmes')} AS src "
        f"WHERE src.rowid IN ({malformed_rowids_sql}) "
        f"OR src.{_q('id')} IN ({divergent_ids_sql}) ORDER BY src.rowid"
    )


def _sql_string(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _rejected_records(con) -> list[dict[str, object]]:
    return _fetch_dicts(
        con.execute(
            "SELECT source_rowid, rejection_reason "
            "FROM rejected.filmes ORDER BY source_rowid"
        )
    )


def _null_counts(
    con,
    table: str,
    columns: tuple[str, ...] | list[str],
    schema: str = "refined",
) -> dict[str, int]:
    expressions = ", ".join(
        f"COUNT(*) FILTER (WHERE {_q(column)} IS NULL) AS {_q(column)}"
        for column in columns
    )
    row = con.execute(
        f"SELECT {expressions} FROM {_qualified(schema, table)}"
    ).fetchone()
    return dict(zip(columns, row, strict=True))


def _record_text(issue: dict[str, object], columns: list[str]) -> str:
    record = {column: issue[column] for column in columns}
    return repr(record)


def _format_count(value: int) -> str:
    return f"{value:,}".replace(",", ".")


def _print_validation_issues(
    validation_issues: dict[str, list[dict[str, object]]],
    duplicate_issues: dict[str, list[dict[str, object]]],
    columns_by_table: dict[str, list[str]],
) -> None:
    for table, issues in validation_issues.items():
        for issue in issues:
            print(
                f"raw.{table}, source_rowid={issue['source_rowid']}, "
                f"coluna {issue['column_name']}: {issue['issue']}; "
                f"valor={issue['raw_value']!r}; "
                f"registro={_record_text(issue, columns_by_table[table])}"
            )
    for table, issues in duplicate_issues.items():
        for issue in issues:
            key = ", ".join(
                f"{name}={issue[name]!r}" for name in DUPLICATE_KEYS.get(table, ("id",))
            )
            if table == "filmes":
                key = f"id={issue['id']!r}"
            print(
                f"raw.{table}, chave duplicada ({key}), "
                f"source_rowid={issue['source_rowid']}, "
                f"ocorrências={issue['occurrences']}; "
                f"registro={_record_text(issue, columns_by_table[table])}"
            )


def _print_summary(
    before_counts: dict[str, int],
    after_counts: dict[str, int],
    identical_duplicates_removed: int,
    null_counts: dict[str, dict[str, int]],
    rejected_records: list[dict[str, object]],
    rejected_null_counts: dict[str, int],
) -> None:
    for table in RAW_TABLES:
        print(
            f"raw.{table}: {_format_count(before_counts[table])}; "
            f"refined.{table}: {_format_count(after_counts[table])}"
        )
        if table == "filmes":
            print(
                "Duplicatas integralmente idênticas removidas de "
                f"refined.filmes: {_format_count(identical_duplicates_removed)}"
            )
        for column, count in null_counts[table].items():
            print(
                f"Nulos preservados em refined.{table}.{column}: "
                f"{_format_count(count)}"
            )
    print(
        "Registros isolados em rejected.filmes: "
        f"{_format_count(len(rejected_records))}"
    )
    for record in rejected_records:
        print(
            f"rejected.filmes source_rowid={record['source_rowid']}: "
            f"{record['rejection_reason']}"
        )
    for column, count in rejected_null_counts.items():
        print(
            f"Nulos originais preservados em rejected.filmes.{column}: "
            f"{_format_count(count)}"
        )


def main() -> int:
    """Validate RAW inputs and atomically publish refined data and film rejections."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    con = None
    transaction_open = False
    published = False
    try:
        con = db.conectar()
        existing = _existing_raw_tables(con)
        missing = [table for table in RAW_TABLES if table not in existing]
        if missing:
            print("Tabelas RAW ausentes:")
            for table in missing:
                print(f"- raw.{table}")
            print("Execute o processo de ingestão antes da transformação.")
            return 1

        con.execute("BEGIN TRANSACTION")
        transaction_open = True

        columns_by_table = {table: _column_names(con, table) for table in RAW_TABLES}
        _check_expected_columns(columns_by_table)
        _validate_rejected_film_locators(con)
        _validate_divergent_film_ids(con)

        before_counts = {
            table: _count_rows(con, "raw", table) for table in RAW_TABLES
        }
        excluded_film_rowids = MALFORMED_FILM_ROWIDS
        excluded_film_ids = DIVERGENT_FILM_IDS
        identical_duplicates = _identical_film_duplicates(
            con,
            excluded_rowids=excluded_film_rowids,
            excluded_ids=excluded_film_ids,
        )
        validation_issues = {
            table: _conversion_and_null_issues(
                con,
                table,
                columns_by_table[table],
                excluded_rowids=(
                    excluded_film_rowids if table == "filmes" else ()
                ),
                excluded_ids=excluded_film_ids if table == "filmes" else (),
            )
            for table in RAW_TABLES
        }
        duplicate_issues = {
            table: _duplicate_issues(
                con,
                table,
                columns_by_table[table],
                excluded_rowids=(
                    excluded_film_rowids if table == "filmes" else ()
                ),
                excluded_ids=excluded_film_ids if table == "filmes" else (),
            )
            for table in RAW_TABLES
        }

        has_issues = any(validation_issues.values()) or any(duplicate_issues.values())
        if has_issues:
            _print_validation_issues(
                validation_issues, duplicate_issues, columns_by_table
            )
            if identical_duplicates:
                print(
                    "Duplicatas integralmente idênticas detectadas em "
                    f"raw.filmes: {_format_count(identical_duplicates)}; "
                    "não removidas porque a transformação foi interrompida."
                )
            con.execute("ROLLBACK")
            transaction_open = False
            return 1

        db.criar_schema(con, "refined")
        db.criar_schema(con, "rejected")
        for table in RAW_TABLES:
            con.execute(_create_table_sql(table, columns_by_table[table]))
        con.execute(_create_rejected_films_sql())

        after_counts = {
            table: _count_rows(con, "refined", table) for table in RAW_TABLES
        }
        null_counts = {
            table: _null_counts(con, table, columns_by_table[table])
            for table in RAW_TABLES
        }
        rejected_null_counts = _null_counts(
            con, "filmes", FILM_RAW_COLUMNS, schema="rejected"
        )
        rejected_records = _rejected_records(con)

        con.execute("COMMIT")
        transaction_open = False
        published = True
        _print_summary(
            before_counts,
            after_counts,
            identical_duplicates,
            null_counts,
            rejected_records,
            rejected_null_counts,
        )
        return 0
    except Exception as error:
        rollback_error = None
        if con is not None and transaction_open:
            try:
                con.execute("ROLLBACK")
            except Exception as rollback_exception:
                rollback_error = rollback_exception
        if published:
            print(f"As tabelas foram publicadas, mas houve falha ao relatar o resultado: {error}")
        elif rollback_error is not None:
            print(
                f"Falha na transformação: {error}; "
                f"também houve falha no ROLLBACK: {rollback_error}"
            )
        else:
            print(f"Falha na transformação; a transação foi revertida: {error}")
        return 1
    finally:
        if con is not None:
            con.close()


if __name__ == "__main__":
    raise SystemExit(main())
