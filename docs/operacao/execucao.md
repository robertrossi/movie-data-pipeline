# Execução do pipeline

Execute as etapas na ordem abaixo, a partir da raiz do projeto. A ingestão substitui tabelas RAW correspondentes; a transformação substitui refined/rejected; a publicação completa substitui o schema MART.

```powershell
uv run python -m pipeline.ingestao
uv run python -m pipeline.transformacao
uv run python -m pipeline.marts
```

Para publicar somente algumas MARTs, informe os números:

```powershell
uv run python -m pipeline.marts --only 05 06
```

O modo seletivo preserva as demais tabelas MART e valida as tabelas refined referenciadas pelos SQLs escolhidos. Sem `--only`, a publicação substitui o schema `marts` em transação.

## Aplicações

Depois que as MARTs estiverem publicadas, inicie o dashboard:

```powershell
uv run streamlit run app.py
```

Gere e abra o relatório HTML:

```powershell
uv run python relatorio.py
Start-Process .\relatorio.html
```

Os comandos de pipeline escrevem no banco selecionado. Confirme o caminho do banco antes de executá-los; para detalhes, consulte [Banco e snapshot](banco-snapshot.md).
