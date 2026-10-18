# Odontograma: guia de uso (versão 4.0)

O odontograma fica na tela **Prontuário** do `SISTEMA_CLINICA.html`, logo abaixo
dos dados do paciente.

## Como ler a tela

- As duas arcadas aparecem como se você olhasse para dentro da boca do paciente
  (vista oclusal): a Maxila (arcada superior) em cima e a Mandíbula (arcada
  inferior) embaixo.
- O lado direito do paciente fica à esquerda da tela, e o lado esquerdo, à
  direita, como o dentista vê o paciente de frente.
- A cor do número indica o grupo do dente: laranja para incisivos, verde para
  caninos, roxo para pré-molares e azul para molares.

## Estados e marcações

| O que aparece no dente | Significado |
|---|---|
| Esmalte branco, sem cor | Hígido (saudável) |
| Dente tingido com a cor do estado | Cárie, restaurado, canal tratado, selante, coroa, prótese, implante ou fratura (legenda abaixo do odontograma) |
| Contorno tracejado azul | Dente com atendimento registrado (prontuário ou agenda) |
| Ponto colorido no dente | Há uma observação registrada |
| Letras ao lado do número (ex.: OV) | Faces afetadas: M (mesial), D (distal), O (oclusal/incisal), V (vestibular), L (lingual/palatina) |
| Dente esmaecido e tracejado | Ausente |

## Como usar

- Passe o mouse sobre um dente: ele é destacado, e o painel ao lado mostra o
  nome completo, o estado, as faces, o atendimento e a observação.
- Clique no dente (ou navegue até ele com **Tab** e pressione **Enter**) para abrir o
  formulário de edição: estado clínico, faces afetadas e observação.
- O botão **+ Registrar dente** abre o mesmo formulário, com a escolha do dente em uma lista.
- A opção **Permanentes / Decíduos (leite)** alterna entre 32 e 20 dentes. Para
  pacientes com menos de 13 anos, a dentição decídua é exibida automaticamente.
- O botão **Ver em grade** mostra a visualização anterior (quadrados em linha), e o
  botão **Ver arcada 3D** volta para a nova.
- O botão **Imprimir** gera o relatório do odontograma, com o detalhamento por dente.

## Notação FDI (por que 11, 12... e não 1 a 32)

O sistema usa a notação FDI (norma ISO 3950), padrão no Brasil. O adulto tem
32 dentes, e cada um é identificado por dois dígitos.

**1º dígito: quadrante** (do ponto de vista do paciente)

| Quadrante | Região | Permanentes | Decíduos |
|---|---|---|---|
| 1 / 5 | Superior direito | 11 a 18 | 51 a 55 |
| 2 / 6 | Superior esquerdo | 21 a 28 | 61 a 65 |
| 3 / 7 | Inferior esquerdo | 31 a 38 | 71 a 75 |
| 4 / 8 | Inferior direito | 41 a 48 | 81 a 85 |

**2º dígito: posição** (do meio da boca para o fundo)

| Dígito | Permanente | Decíduo |
|---|---|---|
| 1 | Incisivo central | Incisivo central |
| 2 | Incisivo lateral | Incisivo lateral |
| 3 | Canino | Canino |
| 4 | Primeiro pré-molar | Primeiro molar |
| 5 | Segundo pré-molar | Segundo molar |
| 6 | Primeiro molar | — |
| 7 | Segundo molar | — |
| 8 | Terceiro molar (siso) | — |

Exemplos: 16 = primeiro molar superior direito; 36 = primeiro molar
inferior esquerdo; 51 = incisivo central superior direito de leite.

A numeração de 1 a 32 (Sistema Universal) é usada principalmente nos EUA:
começa no siso superior direito e percorre as arcadas em sequência. Ela não indica a
região do dente pelo número e não é o padrão brasileiro.

## Observações

- Os dados ficam apenas na memória do navegador. Ao recarregar a página, o
  odontograma volta ao estado inicial, assim como todo o restante da versão de
  demonstração.
- Na impressão, a arcada aparece sem a inclinação 3D.
