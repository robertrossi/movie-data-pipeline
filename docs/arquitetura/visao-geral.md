# Visão geral da arquitetura

O projeto separa a ingestão dos arquivos de origem, a validação e conversão dos dados, a publicação de indicadores analíticos e sua apresentação. A arquitetura usa schemas do DuckDB como camadas lógicas.

```mermaid
flowchart LR
    CSV["CSV locais"] --> ING["pipeline.ingestao"]
    ING --> RAW[("raw")]
    RAW --> TRANS["pipeline.transformacao"]
    TRANS --> REF[("refined")]
    TRANS --> REJ[("rejected")]
    REF --> MARTSQL["sql/marts/ · indicadores 01–11"]
    MARTSQL --> MARTS["pipeline.marts"]
    MARTS --> DBM[("marts")]
    DBM --> PANEL["painel.py · consultas e figuras"]
    PANEL --> STREAMLIT["app.py · dashboard"]
    PANEL --> REPORT["relatorio.py · relatório estático"]
```

O executor `pipeline.marts` lê os arquivos SQL e cria uma tabela por consulta no schema `marts`. O `painel.py` consulta as MARTs em modo somente leitura e fornece os dados e figuras ao dashboard Streamlit e ao gerador do relatório HTML.

## Páginas relacionadas

- [Fluxo de dados](fluxo-dados.md)
- [Camadas](camadas.md)
- [Módulos Python](modulos.md)
- [Indicadores](../indicadores/index.md)
