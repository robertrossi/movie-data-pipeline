# Módulos Python

| Módulo | Responsabilidade documentada no código |
|---|---|
| `pipeline/db.py` | Localiza `raw/` e o DuckDB, abre conexões, cria schemas e substitui tabelas. Suporta `MOVIE_DATA_DB_PATH` e conexão somente leitura. |
| `pipeline/ingestao.py` | Confere os CSVs obrigatórios e os carrega no schema `raw`. |
| `pipeline/transformacao.py` | Valida a entrada RAW, aplica conversões, verifica chaves e duplicidades e publica `refined`/`rejected` atomicamente. |
| `pipeline/marts.py` | Descobre os SQLs numerados, cria as MARTs por CTAS e publica transacionalmente, completa ou seletivamente. |
| `pipeline/snapshot.py` | Provisiona um snapshot remoto validado por SHA-256 quando as variáveis de ambiente correspondentes estão configuradas. |
| `painel.py` | Consulta MARTs, fornece funções analíticas e constrói figuras Plotly; também monta URLs e obtém bytes dos pôsteres TMDB. |
| `app.py` | Inicializa o dashboard Streamlit, verifica o banco em modo somente leitura e apresenta as quatro abas. |
| `relatorio.py` | Consulta o painel e gera `relatorio.html`, um relatório estático com gráficos Plotly. |
| `ui.py` | Abre uma interface local de exploração do DuckDB usando a extensão `ui`; não é a entrada do dashboard Streamlit. |

Os caminhos do banco e as regras de provisionamento estão em `pipeline/db.py` e `pipeline/snapshot.py`. Os detalhes de cada aba e do relatório estão em [Aplicações](../aplicacoes/dashboard.md).
