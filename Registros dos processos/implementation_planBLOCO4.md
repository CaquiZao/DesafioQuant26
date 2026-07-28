# Construção do Bloco 4 (Sinal da Sinapse)

A execução do Bloco 4 é a materialização matemática da nossa tese de investimentos. Seguindo rigorosamente o calendário estabelecido (`planejamento.pdf`) e as diretrizes arquiteturais do arquivo `Bloco444.txt`, o objetivo é calcular os "choques limpos" das ações âncoras (grandes), propagar a energia desse choque pelos elos do Grafo (vizinhos menores) e devolver um sinal normalizado para o Motor de Backtest (Bloco 3).

## User Review Required

> [!IMPORTANT]
> Aprovação Arquitetural: Confirme se a estrutura de dados e as fórmulas abaixo representam com fidelidade a tese da **assimetria** exigida pelos professores e descrita no PDF de planejamento.

## Open Questions

> [!WARNING]
> 1. Vocês já possuem alguma planilha pronta (ou rascunho) com os ~30 elos que criaremos no arquivo `grafo_manual_base.csv`? 
> 2. O cálculo da regressão linear para isolar o Choque Limpo usará uma janela móvel de quantos dias para estimar os Betas (ex: 252 dias úteis)? (Isso deve bater com o nosso `PARAMETROS.md`).

---

## Proposed Changes

Vamos criar um novo diretório chamado `fase 4 - sinal da sinapse` na raiz do projeto para abrigar a lógica matemática da estratégia.

### [NEW] [fase 4 - sinal da sinapse/grafo_manual_base.csv](file:///c:/Users/kakam/OneDrive/Documentos/PROJETOS/DesafioQuant26/fase%204%20-%20sinal%20da%20sinapse/grafo_manual_base.csv)

Este arquivo representará o **Passo 4.1: Construção do Grafo Manual (Sem IA)**. 
- **Detalhe do Planejamento:** 23/07 | Zero IA. Planilha à mão.
- **Formato:** Estrutura base para a Prova de Conceito antes de escalarmos via IA. 
- **Colunas:** `[empresa_A, empresa_B, tipo_de_elo, forca, direcao]`
- **O que precisa ter lá:** ~30 elos óbvios (ex: Petrobras $\leftrightarrow$ Fornecedoras; Vale $\leftrightarrow$ Logística; Varejo $\leftrightarrow$ Shoppings; Bancos $\leftrightarrow$ Devedores Listados).

---

### [NEW] [fase 4 - sinal da sinapse/src/s4_sinapse_sinal.py](file:///c:/Users/kakam/OneDrive/Documentos/PROJETOS/DesafioQuant26/fase%204%20-%20sinal%20da%20sinapse/src/s4_sinapse_sinal.py)

Este será o motor matemático do nosso sinal, e processará em lote os passos 4.2 a 4.4 do planejamento.

#### Passo 4.2: Cálculo do "Choque Limpo" (A Regressão)
- **Detalhe do Planejamento:** 23/07
- O código iterará sobre o universo e aplicará a regressão matemática proposta no Bloco444:
  `Retorno_A = alpha + beta1 * Retorno_Ibovespa + beta2 * Retorno_Setor + resíduo (ε)`
- **O Gatilho:** O resíduo `(ε)` será extraído isoladamente para a Empresa A. Este resíduo é o nosso **choque verdadeiro/limpo**, livre da "maré" da bolsa e do setor.

#### Passo 4.3: Propagação e Montagem do Sinal
- **Detalhe do Planejamento:** 24/07
- Um join (merge de dados Pandas) será feito entre os "Choques Limpos" computados no 4.2 e a tabela de conexões do `grafo_manual_base.csv`.
- Será aplicada a equação mestre da estratégia em loop para toda Empresa B (a empresa desatendida/vizinha):
  `sinal_bruto_B = Choque_limpo_A * forca_do_elo * direcao_prevista`
- **Nota Estrutural:** O código garantirá assimetria direcional (só calculamos propagações da Grande $\rightarrow$ Pequena, nunca o contrário).

#### Passo 4.4: Limpeza do Sinal (Rank e Winsorização)
- **Detalhe do Planejamento:** 24/07 | Ordena, corta extremos
- A matriz de sinais gerada no passo anterior conterá ruídos. A coluna `sinal_bruto_B` passará por uma winsorização matemática:
  - Corte transversal de 2% (p1 e p99) para evitar distorção da carteira por outliers irreais.
- Conversão da intensidade do sinal em um *z-score transversal* para o ranking diário/mensal de operações.

---

### Output Final do Bloco
O código irá exportar todos os resultados para o arquivo `data/sinal_sinapse.parquet`. Este é o artefato final que o Bloco 3 (Motor de Backtest Genérico) irá ingerir para testar a rentabilidade (P&L) gerada pela tese de vocês.

## Verification Plan

### Testes Matemáticos e Verificação
1. **Teste do Choque Limpo:** Iremos buscar na base histórica uma data em que sabemos que ocorreu um desastre com a Vale (ex: Brumadinho em jan/2019). Analisaremos se o `s4_sinapse_sinal.py` conseguiu captar corretamente um choque idiossincrático (resíduo) gigantesco na Vale neste exato dia.
2. **Teste da Assimetria:** Confirmaremos empiricamente através da saída do pipeline que um choque idêntico em uma empresa satélite pequena não retorna "energia" de volta para a âncora grande.
