# Auditoria metodológica — Indicador 09

**Indicador:** distribuição de usuários por quantidade de avaliações<br>
**SQL:** `sql/marts/09_distribuicao_avaliacoes_por_usuario.sql`<br>
**MART:** `marts.distribuicao_avaliacoes_por_usuario`<br>
**Data da revisão e publicação seletiva:** 3 de novembro de 2026<br>
**Parecer:** **APROVADO**

## Pergunta, grão e regra de negócio

A pergunta é como os usuários se distribuem por faixas de quantidade acumulada de avaliações. `avaliacoes_por_usuario` agrega a tabela `refined.avaliacoes` por `userId`, produzindo uma linha por usuário. `usuarios_classificados` atribui a cada linha exatamente uma faixa conforme `indicadores.md`: `1`, `2-10`, `11-30`, `31-100`, `101-500`, `501-1000` e `>1000`.

As faixas são disjuntas e cobrem todos os inteiros positivos: 1; 2–10; 11–30; 31–100; 101–500; 501–1.000; e todo valor maior que 1.000. Como cada usuário agrupado tem pelo menos uma avaliação, nenhum volume fica sem faixa. O percentual de cada categoria usa o total de usuários classificados como denominador e é arredondado a duas casas somente depois do cálculo.

## Distribuição recalculada

Consulta somente leitura executada sobre `refined.avaliacoes`, com as faixas da definição oficial:

| Faixa | Usuários | Percentual | Mínimo observado | Máximo observado |
|---|---:|---:|---:|---:|
| 1 | 5.084 | 1,88% | 1 | 1 |
| 2-10 | 38.704 | 14,29% | 2 | 10 |
| 11-30 | 93.016 | 34,34% | 11 | 30 |
| 31-100 | 70.515 | 26,03% | 31 | 100 |
| 101-500 | 54.125 | 19,98% | 101 | 500 |
| 501-1000 | 6.950 | 2,57% | 501 | 1.000 |
| >1000 | 2.502 | 0,92% | 1.001 | 18.276 |
| **Total** | **270.896** | **100,01%** | **1** | **18.276** |

O total percentual exibido é 100,01% porque cada percentual é arredondado individualmente a duas casas; antes do arredondamento, as participações usam o mesmo denominador de 270.896 usuários. Portanto, a soma apresentada não representa usuários extras nem erro de denominador.

## Comparação com a distribuição anterior

A distribuição anterior foi calculada com faixas diferentes e estava na MART antes da publicação seletiva de 3 de novembro de 2026. A tabela abaixo preserva o registro histórico da versão anterior; ela não representa o estado atual da MART:

| Faixa anterior | Usuários | Percentual anterior |
|---|---:|---:|
| 01-10 | 43.788 | 16,16% |
| 11-50 | 124.729 | 46,04% |
| 51-100 | 38.802 | 14,32% |
| 101-500 | 54.125 | 19,98% |
| 501-1000 | 6.950 | 2,57% |
| 1001-5000 | 2.488 | 0,92% |
| 5001-10000 | 13 | 0,00% |
| 10000+ | 1 | 0,00% |
| **Total** | **270.896** | **99,99%** |

As mudanças são redistribuições por limites de faixa, não mudanças na população. Por exemplo, a faixa anterior `01-10` passa a ser dividida em 5.084 usuários com uma avaliação e 38.704 com 2–10. A faixa `>1000` reúne os 2.488 usuários antes em `1001-5000`, os 13 antes em `5001-10000` e o usuário acima de 10.000.

## Validações de população e classificação

Consultas `SELECT` confirmaram:

- **270.896** usuários na agregação e **270.896** usuários somados nas novas faixas;
- **0** avaliações com `userId` nulo;
- **0** usuários sem faixa;
- **0** usuários classificados em quantidade diferente de uma faixa;
- mínimo de **1** e máximo de **18.276** avaliações por usuário;
- percentuais recalculados pela expressão `ROUND(total_usuarios * 100.0 / total_usuarios_geral, 2)`.

Antes da republicação, a consulta esperada tinha 7 linhas enquanto a MART antiga tinha 8. Naquela comparação, `EXCEPT ALL` encontrou **5 linhas em referência → MART** e **6 em MART → referência**. Esse resultado descreve somente o estado pré-publicação; a validação após a publicação está registrada a seguir.

### Publicação seletiva e validação pós-publicação

Em 3 de novembro de 2026, foi executado `python -m pipeline.marts --only 09`. O executor atualizou exclusivamente `marts.distribuicao_avaliacoes_por_usuario`; não executou `DROP SCHEMA` e preservou as outras nove MARTs. A MART publicada tem **7 linhas**, soma **270.896 usuários** e soma **100,01%** após arredondamento individual. Consulta e MART foram comparadas usando `EXCEPT ALL` nos dois sentidos: **0 diferenças em referência → MART** e **0 diferenças em MART → referência**.

O inventário posterior confirmou as dez MARTs presentes. As outras nove mantiveram as contagens previamente auditadas: 17, 20, 20, 10, 23, 23, 20, 20 e 20 linhas, conforme seus indicadores.

## Avaliação metodológica

A divergência confirmada entre a lista de faixas de `indicadores.md` e a versão anterior do SQL foi corrigida no SQL para obedecer à definição oficial. Não foram alterados população, grão, medida ou denominador. O indicador continua medindo volume acumulado por usuário, não recência, duração de participação ou intensidade por período.

A soma das porcentagens arredondadas pode variar de 100% por arredondamento individual. Nesta distribuição corrigida soma 100,01%; na anterior, 99,99%. As contagens devem ser apresentadas junto dos percentuais.

## Parecer

**APROVADO.** O SQL implementa as sete faixas oficiais, classifica exatamente uma vez cada um dos 270.896 usuários, calcula percentuais corretos sobre a população total e coincide exatamente com a MART publicada: ambas as direções de `EXCEPT ALL` retornaram zero diferenças. A soma de 100,01% decorre do arredondamento individual. As outras nove MARTs foram preservadas.
