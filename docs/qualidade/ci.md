# Integração contínua

O workflow `.github/workflows/ci.yml` executa verificações em Pull Requests direcionados à branch `main`. Ele usa Ubuntu 24.04, Python 3.13.5 e uv 0.13.6, com permissão `contents: read`.

As etapas são:

1. Instalar dependências travadas: `uv sync --locked --all-groups`.
2. Executar testes e cobertura: `uv run --locked pytest --cov`.
3. Executar lint: `uv run --locked ruff check .`.
4. Conferir formatação: `uv run --locked ruff format --check .`.

O workflow é CI de qualidade; ele não publica o site MkDocs nem altera o relatório HTML. O README registra que a primeira execução após o PR #16 concluiu com sucesso em 51 segundos.
