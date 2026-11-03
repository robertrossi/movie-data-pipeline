# Instalação

O projeto requer Python 3.13 ou superior compatível com as dependências e uv. A partir da raiz do repositório, sincronize o ambiente:

```powershell
uv sync
```

Os cinco arquivos de origem devem ser disponibilizados em `raw/` antes da ingestão. A lista e os nomes das tabelas correspondentes estão em [Fontes de dados](../dados/fontes.md). O repositório não inclui os CSVs.

Para preparar especificamente a documentação local neste ambiente de desenvolvimento:

```powershell
uv sync --all-groups
```

## Arquivos de dependências

- `pyproject.toml` declara requisitos do projeto e o grupo de desenvolvimento, incluindo MkDocs Material.
- `uv.lock` registra as versões resolvidas.
