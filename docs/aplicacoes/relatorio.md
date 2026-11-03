# Relatório HTML

`relatorio.py` consulta as funções de `painel.py` e gera `relatorio.html` na raiz do projeto. O arquivo publicado é estático: contém quatro seções e 14 gráficos Plotly, usa identificadores estáveis para os gráficos e inclui a biblioteca Plotly uma vez via CDN.

Os gráficos preservam recursos como hover. Filtros dinâmicos, seletores de ano e gênero e pôsteres pertencem ao dashboard Streamlit e não estão disponíveis no relatório HTML. Os dados representados são os consultados no momento da geração.

- [Abrir o relatório publicado](https://robertrossi.github.io/movie-data-pipeline/relatorio.html)

Para gerar e abrir localmente:

```powershell
uv run python relatorio.py
Start-Process .\relatorio.html
```
