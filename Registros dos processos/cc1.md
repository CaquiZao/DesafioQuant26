# Integração da Sinapse no Bloco 3 (Remoção do Equal-Weight)

Este documento foi preparado em formato de prompt, pronto para você copiar e colar para o Claude Code (ou para que eu mesmo o execute, caso você aprove e me dê o sinal verde na sequência).

***

## Prompt para o Claude Code:

Você deve atuar como Engenheiro Quantitativo Sênior e refatorar o **Motor de Backtest (Bloco 3)** do projeto SINAPSE. O motor atual foi construído com uma lógica provisória para testar uma estratégia *equal-weight* com rebalanceamento mensal, mas a nossa estratégia real (Sinapse) opera de forma diária e a matriz de pesos oficiais já está sendo gerada pelo Bloco 5.

Sua tarefa é modificar o arquivo `fase 3 - backtest\src\s3_backtest.py` para consumir o output real da Sinapse e simplificar/corrigir a mecânica de cálculo de P&L diário.

### 1. Contexto das Mudanças
O arquivo `df_weights_sinapse.parquet` gerado pelo Bloco 5 possui o seguinte formato:
- **Índice:** Datas diárias.
- **Colunas:** Tickers das ações + a coluna especial `IBOV_SYNTHETIC` (que representa o hedge vendido de Ibovespa).
- **Valores:** Pesos percentuais da carteira (positivos para LONG, negativos para SHORT).
- **Atenção:** O *lag* de D+1 já foi aplicado nativamente no output do Bloco 5. Portanto, o peso que aparece no dia $T$ no parquet já é o peso que deve ser multiplicado pelo retorno do dia $T$.

### 2. Instruções de Refatoração no `s3_backtest.py`

#### A. Remoção da lógica antiga
- Delete a função `gerar_pesos_equal_weight` e `carregar_universo_mensal`.
- Delete as lógicas de agrupamento mensal e a função `mes_seguinte` (todo o loop complexo de "mês de decisão" vs "mês de execução" em `rodar_motor`).
- O motor não será mais "mensal", ele será uma multiplicação matricial diária direta.

#### B. Novos Inputs
- O script deve carregar o arquivo `df_weights_sinapse.parquet` (este é o output do Bloco 5 que está sendo gerado na pasta raiz `data` ou no diretório base). Atualize as constantes de caminhos de acordo com o output gerado na Fase 5.
  - O caminho dos retornos geralmente é `../data/precos/retornos_diarios.parquet` ou equivalente.
  - O caminho dos pesos novos é o destino salvo por `exec_s5.py` (normalmente `../data/df_weights_sinapse.parquet`).

#### C. O novo `rodar_motor` (Motor Diário)
A função `rodar_motor` deverá ser reescrita para aceitar o DataFrame diário de pesos e o DataFrame diário de retornos:
1. **Alinhamento de Datas e Colunas:** Garanta que `df_weights` e `df_returns` compartilhem as mesmas datas.
2. **Tratamento do `IBOV_SYNTHETIC`:** O arquivo de retornos (`df_returns`) não possui a coluna `IBOV_SYNTHETIC`. O script precisará baixar/calcular o retorno diário do Ibovespa e injetá-lo no `df_returns` sob a coluna `IBOV_SYNTHETIC` para que a multiplicação matricial funcione sem dar KeyError.
3. **Cálculo de Giro (Turnover):** 
   - `df_mudanca = df_weights.fillna(0).diff().abs()`
   - `giro_diario = df_mudanca.sum(axis=1)`
   - *Custo de transação:* `custo_diario = giro_diario * custo_por_giro`
4. **Cálculo do P&L (Retorno Diário):**
   - `pnl_bruto = (df_weights * df_returns.fillna(0)).sum(axis=1)`
   - `retorno_estrategia = pnl_bruto - custo_diario`
5. **Retorno da Função:** Apenas a série `retorno_estrategia`. (A tabela de cobertura não fará mais sentido como estava, pode simplificar ou remover).

#### D. Teste de Sanidade e Comparativo
- Como a nossa estratégia real possui o *hedge* de Ibovespa (Beta-Neutro), **a curva da Sinapse NÃO DEVE ter alta correlação com o Ibovespa**. Pelo contrário, queremos ver o alfa descorrelacionado.
- Atualize os textos de "Teste de Sanidade" no final do script (`main`) para refletir que agora estamos rodando a estratégia real de *market-neutral*, e que a correlação esperada com o mercado é próxima de zero.

### 3. Validação
Após escrever o código, certifique-se de que a matemática matricial `(Pesos * Retornos)` está rodando corretamente de forma vetorizada, o que deixará o script incrivelmente mais rápido do que o loop anterior.

### Arquivos Alvo
- `fase 3 - backtest\src\s3_backtest.py`

Execute estas mudanças usando as melhores práticas de código limpo.
