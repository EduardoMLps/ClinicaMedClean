# RH, comissões e contracheque (versão 5.2)

Este documento descreve as regras usadas pelo `SISTEMA_CLINICA.html` no módulo
RH, nos totais dos relatórios e no contracheque.

## 1. Colaboradores

| Campo | Regra |
|---|---|
| Nome e cargo | Obrigatórios |
| CPF | Opcional; quando informado, os dígitos verificadores são conferidos e não pode haver CPF repetido |
| Dependentes para o IRRF | Número inteiro de 0 a 20 |
| Vínculo | CLT, Autônomo (comissão), Prestador PJ ou Estágio |
| Salário fixo | Valor mensal; obrigatório para funcionário CLT que não seja dentista |
| Comissão (%) | De 0 a 100; padrão de 25% para dentistas; outros cargos ficam com 0% |
| Admissão | Obrigatória e não pode ser data futura |
| Desligamento | Opcional; não pode ser anterior à admissão |

- Ao cadastrar um dentista, ou ao mudar o cargo de alguém para Dentista, o
  sistema o inclui na lista de profissionais da Agenda.
- Ao marcar um colaborador como Inativo sem informar a data, o desligamento é
  registrado na data de hoje. Uma data de desligamento já passada torna o
  colaborador inativo automaticamente; uma data futura (aviso prévio) o mantém
  ativo até lá.
- A aba **Colaboradores** tem busca por nome, cargo ou CPF e filtro por
  situação (ativos, inativos ou todos).

## 2. Comissão dos dentistas

- **Base:** valor cobrado dos atendimentos com status **Concluído** e
  **pagos** no período, atribuídos ao dentista. A partir da versão 5.2 o valor é
  gravado no momento do recebimento, então mudar o preço de um procedimento
  depois não altera comissões já calculadas.
- **Percentual:** o do cadastro do dentista; se não houver, o padrão da clínica
  (25%), alterável na aba **Colaboradores**.
- **Exemplo:** produção paga de R$ 24.350,00 em setembro gera comissão de
  R$ 6.087,50 (25%).
- Atendimentos agendados, cancelados, faltas ou não pagos não geram comissão.

## 3. Totais nos relatórios

Os relatórios diário, semanal, mensal e anual mostram:

| Linha | Cálculo |
|---|---|
| Recebido | Soma das receitas pagas no período |
| Despesas | Despesas do Financeiro, exceto a categoria Comissões |
| Comissões dos dentistas | Soma das comissões de todos os dentistas no período |
| Resultado líquido | Recebido − Despesas − Comissões |

A categoria Comissões é excluída das despesas para que a comissão não seja
descontada duas vezes quando a folha já tiver sido lançada no Financeiro.

## 4. Folha do mês

A aba **Comissões e folha** mostra, para o mês escolhido:

| Indicador | Cálculo |
|---|---|
| Salários do mês | Salários proporcionais aos dias trabalhados |
| FGTS | 8% da remuneração dos funcionários CLT |
| Custo total de pessoal | Comissões + salários + FGTS |
| Provisão de 13º e férias | Reserva mensal sugerida para CLT: 1/12 de 13º mais 1/12 de férias com 1/3, com FGTS (7/36 do salário × 1,08) |

**Quem entra na folha:** colaboradores já admitidos até o fim do mês e não
desligados antes do início do mês. Dentistas aparecem sempre que tiverem
comissão no mês.

**Salário proporcional:** o mês é tratado como comercial, de 30 dias. Quem foi
admitido em 15/09 recebe 16 dias (R$ 3.000,00 vira R$ 1.600,00); quem foi
desligado em 10/08 recebe 10 dias em agosto e nada a partir de setembro.

O botão **Lançar folha no Financeiro** cria, para o mês escolhido:

- uma despesa na categoria **Comissões** para cada dentista com comissão;
- uma despesa na categoria **Pessoal** para cada salário (já proporcional);
- uma despesa na categoria **Pessoal** para o FGTS de cada funcionário CLT.

Cada lançamento recebe uma referência interna (mês e colaborador). Clicar de
novo no botão não duplica os lançamentos.

O botão **Exportar folha (CSV)** gera o arquivo `folha-AAAA-MM.csv`, separado
por ponto e vírgula e com acentos compatíveis com o Excel, com uma linha por
colaborador e a linha de total.

## 5. Contracheque

| Item | Dentista (autônomo) | Funcionário CLT | Estágio | Prestador PJ |
|---|---|---|---|---|
| Documento | Recibo de pagamento a autônomo (RPA) | Recibo de pagamento de salário | Recibo de bolsa-estágio | Demonstrativo de pagamento |
| Proventos | Salário (se houver) e comissão do mês | Salário base ou proporcional | Bolsa | Valor fixo |
| INSS | 11% até o teto | Tabela progressiva de 2026 | Não há | Não há |
| IRRF | Tabela de 2026 | Tabela de 2026 | Tabela de 2026 | Sem retenção na folha |
| FGTS | Não se aplica | 8% (informativo, pago pela clínica) | Não se aplica | Não se aplica |

O contracheque traz: dados da clínica, competência e período (primeiro e último
dia do mês), nome, CPF, cargo, vínculo, admissão e desligamento, número de
dependentes, proventos e descontos com referência (dias ou atendimentos),
totais, valor líquido em número e por extenso, bases de INSS, IRRF e FGTS,
prazo de pagamento para CLT (até o 5º dia útil do mês seguinte, art. 459 da CLT)
e linhas de assinatura com local e data. Em telas estreitas, a tabela de
valores rola na horizontal.

**INSS 2026 (empregado):** 7,5% até R$ 1.621,00; 9% até R$ 2.902,84; 12% até
R$ 4.354,27; 14% até R$ 8.475,55 (teto). O cálculo é progressivo, faixa a faixa.

**IRRF 2026 (mensal):**

| Base de cálculo | Alíquota | Dedução |
|---|---|---|
| Até R$ 2.428,80 | Isento | - |
| Até R$ 2.826,65 | 7,5% | R$ 182,16 |
| Até R$ 3.751,05 | 15% | R$ 394,16 |
| Até R$ 4.664,68 | 22,5% | R$ 675,49 |
| Acima de R$ 4.664,68 | 27,5% | R$ 908,73 |

- Base pelas deduções legais: rendimento − INSS − R$ 189,59 por dependente.
- Base pelo desconto simplificado: rendimento − R$ 607,20.
- O sistema usa a base menor, ou seja, a opção mais favorável ao colaborador.
- Redução da Lei 15.270/2025: rendimento de até R$ 5.000,00 fica isento; entre
  R$ 5.000,01 e R$ 7.350,00 o imposto é reduzido em
  R$ 978,62 − 0,133145 × rendimento.

**Valores conferidos nos testes:** INSS de R$ 182,69 sobre R$ 2.300,00 (CLT);
R$ 781,51 sobre R$ 7.000,00 (CLT); R$ 191,13 sobre R$ 1.737,50 (autônomo).
IRRF de R$ 754,75 sobre R$ 7.000,00 (CLT, sem dependentes) e de R$ 650,48 com
2 dependentes.

## 6. Observações

- Os valores do contracheque são uma referência para conferência. A folha
  oficial (eSocial, DCTFWeb, guias de INSS, FGTS e IRRF) deve ser emitida pelo
  contador da clínica.
- Não estão incluídos: pensão alimentícia, horas extras, adicional noturno,
  vale-transporte, faltas, pagamento de férias e de 13º salário, rescisão e
  encargos patronais (que dependem do regime tributário da clínica).
- As tabelas precisam ser revisadas a cada reajuste anual.
- Como no restante do `SISTEMA_CLINICA.html`, os dados ficam só na memória do
  navegador e voltam ao estado inicial ao recarregar a página.

Fontes das tabelas: debit.com.br (Tabela INSS 2026) e calcularclt.com.br
(Tabela IRRF 2026), consultados em 02/10/2026.
