# Guia Técnico de Implementação: SINAPSE + ECO
Este guia detalha o que já foi construído no repositório, analisa as falhas arquiteturais do código existente em relação à nossa tese, e especifica tecnicamente como programar os blocos que faltam.

---

## Bloco 1 e 2: Universo e Preços (A Fundação de Dados)

### O que já temos (Status Atual)
Vocês já possuem a pasta `fase 2 - universo liquidez` rodando perfeitamente. O script `s2_universo.py` faz um excelente trabalho lendo o COTAHIST cru e filtrando as 100 ações mais líquidas por mês, expurgando BDRs, FIIs e ETFs corretamente pelo código BDI. Isso gera o nosso universo livre de *survivorship bias*.

### 🚨 ALERTA CRÍTICO: Falha no Bloco 1 (`s1_precos.py`)
No arquivo `fase 1 - preço ajustado\src\s1_precos.py`, vocês estão lendo os tickers do universo e usando a biblioteca **`yfinance`** (`yf.download`) para baixar a série de preços. 
**Isso destrói completamente o esforço do Bloco 2.** O Yahoo Finance **não possui** ou possui dados quebrados de empresas deslistadas (falidas ou adquiridas no passado). Ao consultar o Yahoo, as empresas mortas retornarão vazias e serão dropadas do backtest, reintroduzindo o *survivorship bias* (viés de sobrevivência) e garantindo a desclassificação na banca.

**O que precisa ser codado/corrigido:**
Vocês precisam reescrever o `s1_precos.py`. Em vez de usar `yfinance`, ele deve extrair os preços de fechamento (campo `PREULT`) **diretamente do COTAHIST**. O cálculo de ajuste por proventos (desdobramentos e dividendos) deve ser feito consumindo os dados oficiais da B3, ou, na impossibilidade técnica imediata, usar o `yfinance` apenas para ações vivas e aceitar que é necessário buscar a base de proventos históricos da B3 para fazer a matemática de ajuste de cotas (*Adjusted Close*).

---

## Bloco 3: Motor de Backtest (A Fazer)

### Como implementar
O motor de backtest não existe ainda. Ele deve ser um script (ex: `s3_motor_backtest.py`) que roda **independente de qualquer estratégia**. Ele precisa ser capaz de receber uma matriz de Pesos (Weights) e cuspir um P&L (Lucro/Prejuízo).

**Passo a passo técnico:**
1. **Entrada:** Um DataFrame `df_weights` onde o índice é a data (mensal) e as colunas são os tickers. Os valores (0.0 a 1.0) representam a alocação do capital.
2. **Lag de Execução:** Deslocar os pesos no tempo. Se o rebalanceamento é calculado no último pregão do mês $T$, a ordem de compra só é executada no fechamento do dia $T+1$ (para absorver slippage real). No código: `df_weights = df_weights.shift(1)`.
3. **Cálculo de P&L:** Multiplicar os pesos de $T+1$ pelos retornos diários do `retornos_diarios.parquet`. 
   `daily_pnl = (df_weights * df_retornos).sum(axis=1)`
4. **Métricas:** O script deve calcular o Retorno Anualizado, Volatilidade, Índice de Sharpe, e o *Maximum Drawdown* acumulado.

---

## Bloco 4: O Sinal da Sinapse (Já Implementado)

### O que já temos (Status Atual)
A lógica principal já existe no `fase 4 - sinal da sinapse\src\s4_sinapse_sinal.py`.
- Ele já usa a constante `JANELA_REGRESSAO_DIAS = 252` (dos parâmetros).
- Calcula o *Choque Limpo* rodando um `RollingOLS` das ações contra o Ibovespa e o Setor.
- Multiplica pela `força` e `direção` do `grafo_manual_base.csv`.
- Faz o *winsorize* (corta 1% em cada cauda, `WINSORIZATION_LIMIT = 0.02`) e gera o Z-Score transversal diário.

**O que precisa de atenção:**
O código atual varre `df_grafo.iterrows()` diáriamente, assumindo que as ligações do Grafo Manual (30 elos) são estáticas. Para a Fase 2 (IA com milhares de elos extraídos dos PDFs do IPE), o Grafo precisará ter a coluna `Data_em_que_virou_público`. O sinal de uma conexão A -> B **só pode começar a ser gerado** após a data em que o fato relevante foi publicado na CVM. Se propagar antes, ocorre *look-ahead bias*.

---

## Bloco 5: Construção da Carteira (A Fazer)

### Como implementar
Vocês devem criar o script `s5_portfolio_builder.py`. Ele pegará o Z-Score de sinal (criado pelo Bloco 4) e o transformará nos `df_weights` finais para jogar no Bloco 3 (Motor de Backtest).

**Passo a passo técnico (Lendo o PARAMETROS.md):**
1. **Rankeamento e Lado:** Z-Score Positivo alto: Ação esperada de subida = LONG. Z-Score Negativo alto: Ação esperada de queda = SHORT.
2. **Vol-Targeting:** A carteira deve ter volatilidade-alvo de 12% anualizada. O código calculará a volatilidade da carteira teórica nos últimos 60 dias. Se for 24%, ele cortará todos os pesos pela metade para bater nos 12%. Exposição Bruta não é mais estática 100%.
3. **Travas Institucionais (Otimização):**
   - Garantir que `abs(weight[ticker]) <= 0.05` (Travado em 5%).
   - Somar a exposição bruta de todos os tickers do mesmo setor, garantindo que não ultrapasse 25%.
   - **Liquidez:** Usar o COTAHIST original para checar o Volume em Reais. O tamanho financeiro da nossa posição (`Nosso AUM * abs(weight)`) tem que ser menor que 10% da média móvel do volume negociado nos últimos 21 dias.
4. **Beta-Neutro:** Calcular o Beta da carteira inteira contra o IBOV e aplicar um "Hedge de Ibovespa" automático via derivativos para que a carteira zere o fator de mercado local.

---

## Parte 2: O Cérbero Adaptado (BAB-BR) (Expansão Institucional a Fazer)

Como visto na tese, precisamos do piso da estratégia antes da IA brilhar. O código que vocês criarão para o BAB-BR compartilha toda a Fábrica (Blocos 1 a 3 e 5).

### Como implementar (s_cérbero_bab.py)
Em vez de ler o grafo da Sinapse, este script fará o ranqueamento estrutural clássico de Betting Against Beta:
1. Pega os mesmos 252 dias de histórico e calcula o Beta diário (sensibilidade de cada ação vs Ibovespa).
2. Rankeia o universo *point-in-time* no último dia de cada mês: 
   - Ações de Menor Beta (primeiro quintil) entram na carteira Long.
   - Ações de Maior Beta (último quintil) entram na carteira Short.
3. Alavanca a perna Long (baixo beta) e desalavanca a perna Short (alto beta) para que ambas tenham Betas Exatos de `1.0`. Isso gera a carteira puramente `Beta-Neutra` que captura o prêmio BAB original de Frazzini & Pedersen.
4. Adiciona o multiplicador do **Spread DI-Selic**. Quando o financiamento ficar escasso (curva estressa), as alavancagens caem, diminuindo a aposta na estratégia para o mês.
5. Joga tudo no motor do Bloco 5 para aplicar travas setoriais e Vol-Targeting.
