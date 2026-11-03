# Evidências da transformação

As evidências de validação existentes foram preservadas integralmente em [`docs/evidencias_transformacao.md`](../evidencias_transformacao.md). A página original registra contagens, tipos, nulos, rejeições e comparações de valores, além de explicitar quais verificações não foram realizadas.

## Resumo registrado

| Tabela | Registros documentados |
|---|---:|
| `raw.filmes` | 45.466 |
| `refined.filmes` | 45.420 |
| `raw.avaliacoes` e `refined.avaliacoes` | 26.024.289 |
| `raw.links` e `refined.links` | 45.843 |
| `rejected.filmes` | 29 |

O documento original informa 26 registros rejeitados por conflitos divergentes e três registros malformados. Também registra que a comparação corrigida das colunas avaliadas não encontrou divergências, mas declara que não foi feita comparação integral de todas as colunas nem validação referencial completa. Esses limites fazem parte da evidência e não devem ser ampliados além do que foi executado.
