# Testes e qualidade

A suíte usa pytest; a cobertura é produzida por pytest-cov. A configuração de cobertura em `pyproject.toml` mede os módulos `pipeline`, `painel` e `relatorio` e mostra linhas ausentes. As interfaces visuais `app.py` e `ui.py` não integram essa métrica.

```powershell
uv run pytest --cov
uv run ruff check .
uv run ruff format --check .
```

O README registra uma validação de referência com 75 testes aprovados, 94% de cobertura e duração de 23,92 segundos, com duas advertências. Essa execução ocorreu com um ambiente alternativo e Plotly 5.24.1, em vez da versão 7.1.0 resolvida no lockfile; portanto, não deve ser apresentada como validação da suíte no ambiente exato de `uv.lock`. Ruff check e Ruff format check foram registrados como aprovados em execução anterior. O README registra ainda que a primeira execução da CI terminou em 51 segundos.

Esses números são históricos e não foram reexecutados durante a construção destas páginas.
