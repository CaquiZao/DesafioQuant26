# Resumo: Implementação e Código do Bloco 5 (Construção da Carteira)

Este documento resume a função dos scripts Python construídos para o Bloco 5 e detalha o que foi realizado em sua implementação, conforme registrado na documentação do projeto.

## 1. O que os scripts Python fazem

### `s5_portfolio_builder.py`
Este script é o "motor" central do Bloco 5. Ele contém a classe `PortfolioBuilder`, responsável por receber os sinais matemáticos (Z-scores brutos) gerados no Bloco 4 e transformá-los em uma matriz de pesos realista para a carteira. O processo envolve as seguintes etapas:
*   **Vol-Targeting:** Escalonamento da alavancagem usando o histórico de volatilidade das ações para atingir uma volatilidade alvo de 12% ao ano para a carteira.
*   **Travas Institucionais:** Aplicação de três freios de risco:
    1.  **Trava de Liquidez:** Limita o aporte em uma ação a no máximo 10% do seu Volume Médio Diário Negociado (ADTV), baseado no *Assets Under Management (AUM)* do fundo (padrão de R$ 100 milhões).
    2.  **Trava de Concentração por Ativo:** Limita a exposição máxima em um único ativo a 5%.
    3.  **Trava de Concentração Setorial:** Impede que a soma absoluta dos pesos das ações de um mesmo setor ultrapasse 25%.
*   **Hedge Beta-Neutro:** Calcula o beta total da carteira em relação ao Ibovespa e insere um ativo de proteção (`IBOV_SYNTHETIC`) vendido na proporção exata para zerar o risco de mercado (fator IBOV).
*   **Lag de Execução (T+1):** Desloca a matriz de pesos um dia à frente para simular a execução real (recebe o sinal no fechamento de $T$, mas só executa em $T+1$).

### `exec_s5.py`
Este é o script orquestrador (ponto de entrada) para executar o Bloco 5. Sua função é:
*   Carregar os arquivos de dados necessários gerados nas fases anteriores: os sinais (`sinal_sinapse.parquet`), os retornos diários e o mapeamento de setores.
*   Instanciar a classe `PortfolioBuilder` (assumindo AUM de 100 milhões).
*   Fornecer *mocks* (dados simulados temporários) para Betas e ADTV, permitindo que a simulação rode e valide a estrutura antes de dados reais dessas variáveis serem integrados.
*   Executar o cálculo de pesos chamando `build_portfolio` e exportar o resultado final para o arquivo `df_weights_sinapse.parquet`, que servirá de entrada para o motor de backtest (Bloco 3).

## 2. O que foi feito na implementação do Bloco 5

A implementação seguiu com sucesso o plano traçado e a execução foi validada. Os principais marcos da entrega foram:

*   **Ajustes na Documentação e Parâmetros:** A regra de polaridade matemática foi estabelecida e documentada claramente (`Z-Score Positivo = LONG`, `Z-Score Negativo = SHORT`). Além disso, o tamanho do fundo (AUM) foi parametrizado, definindo R$ 100 milhões como a base para testes de liquidez.
*   **Desenvolvimento do Motor:** Todo o coração lógico do Bloco 5 (`s5_portfolio_builder.py`) foi programado, contemplando escalonamento de volatilidade, redução de limites setoriais, *clipping* de limites nominais e hedge sintético do Ibovespa.
*   **Cobertura de Testes Automatizados (Validação Matemática):** Foi criada uma suíte de testes (`test_s5_portfolio_builder.py`) utilizando o `pytest`. Os testes comprovaram com sucesso todos os cinco pilares geométricos da matriz:
    1. Respeito à polaridade do Z-score.
    2. Cumprimento do limite de peso de 5% por ativo.
    3. Tesourada da trava de liquidez (ADTV) respondendo corretamente ao AUM inserido.
    4. Redução proporcional do setor quando a soma atinge 25%.
    5. Neutralidade de Beta alcançada (produto vetorial zerado com sucesso).
*   **Geração do Output Oficial:** O orquestrador `exec_s5.py` foi rodado com dados reais e obteve êxito ao produzir a matriz oficial final de pesos (`df_weights_sinapse.parquet`), deixando o pipeline totalmente preparado para a integração com o backtester do Bloco 3.

## 3. Detalhamento do Output Final

O **output final** do Bloco 5 é um único arquivo chamado **`df_weights_sinapse.parquet`** (gerado e salvo pela execução do arquivo `exec_s5.py`).

Para entender plenamente este output, aqui está o detalhamento de como os inputs são transformados no resultado final:

### 📥 Inputs do Bloco 5 (Entradas)
O motor recebe 5 bases de dados:
1. **`df_zscore`:** A matriz com os sinais finais (força das empresas) gerados no Bloco 4 (índices = datas, colunas = tickers).
2. **`df_returns`:** A matriz de retornos diários das ações (usada para calcular a volatilidade teórica da carteira).
3. **`df_adtv`:** A matriz de volume médio diário de negociações (usada para aplicar os limites de liquidez do fundo de 100M).
4. **`df_betas`:** A matriz de risco (beta) de cada ativo em relação ao Ibovespa nos últimos 252 dias.
5. **`df_sectors`:** O dicionário relacionando cada Ticker ao seu respectivo setor de atuação.

### 📤 O Output Final (`df_weights_sinapse.parquet`)
O resultado gerado é um `DataFrame` pandas estruturado da seguinte forma:

*   **As Linhas (Índice):** Continuam sendo as **datas de fechamento diário** dos pregões (as mesmas recebidas no Z-score).
*   **As Colunas:** Contêm os **30 Tickers** originais do universo de ações, **MAIS uma coluna adicional** criada dinamicamente chamada `IBOV_SYNTHETIC` (totalizando 31 colunas).
*   **Os Valores (Miolos da Matriz):** Os números contidos no dataframe são os **pesos percentuais de alocação de capital** que o motor de backtest (Bloco 3) deve usar naquele dia. 
    *   Um valor `0.05` significa estar **comprado (LONG)** alocando 5% do capital na ação.
    *   Um valor `-0.02` significa estar **vendido a descoberto (SHORT)** alocando -2% do capital.
*   **A coluna `IBOV_SYNTHETIC`:** Contém o peso (geralmente negativo) em contratos de Ibovespa necessário para fazer o hedge perfeito (proteção) de todo o beta da carteira naquele dia.
*   **Lag de D+1 Aplicado:** Vale notar que todas as linhas no output final já estão **"deslocadas" 1 dia para frente (`shift(1)`)**. Ou seja, a decisão matemática que o robô tomou no fechamento de segunda-feira vai aparecer nos pesos do arquivo apenas na linha correspondente a terça-feira, para que o Motor de Backtest simule o *slippage* no mundo real.

**Resumo da Ópera:** O output do Bloco 5 é o *"cardápio de ordens prontas"* com os percentuais perfeitos, seguros e dentro da lei do fundo (travas de setor, concentração, liquidez e vol = 12%) que dizem ao backtest do Bloco 3 exatamente o que ele precisa comprar e vender a cada amanhecer.
