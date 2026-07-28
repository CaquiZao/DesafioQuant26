# Implementação do Bloco 5: Gestão de Risco e Construção da Carteira

Este plano detalha a construção do **Bloco 5**, focado na gestão de risco e geração dos pesos (`df_weights`) para o backtest institucional da estratégia SINAPSE. O plano inclui a correção da polaridade matemática documentada e a introdução da variável de AUM para testar os impactos de liquidez (10% do ADTV).

## User Review Required

> [!WARNING]
> **Assimetria Direcional:** O requisito "Só operamos no sentido Empresa Grande -> Empresa Pequena" normalmente é imposto na criação do próprio grafo (Bloco 4 ou extração da IA), já que depende da capitalização de mercado e cobertura de analistas das duas pontas do elo. O Bloco 5 assumirá que os Z-scores recebidos do Bloco 4 já respeitam essa assimetria. Caso seja necessário filtrar a assimetria no Bloco 5, precisaremos de dados de Market Cap no `sinal_sinapse.parquet`. Por favor, confirme se o filtro de Grande -> Pequena deve ser feito no Bloco 5 (exigindo base de Market Cap) ou se já está garantido na construção do Grafo.

## Open Questions

> [!IMPORTANT]
> **Janela de Volatilidade:** Para o *Vol-Targeting* (alvo de 12%), o padrão institucional costuma ser calcular a volatilidade teórica da carteira usando os últimos 60 dias (como citado no guia original). Podemos confirmar o uso de uma janela móvel de 60 dias (`window=60`) sobre retornos diários para o escalonamento da alavancagem?
>
> **Beta do IBOV:** Para zerar o Beta do portfólio (Beta-Neutra), precisamos do beta histórico recente de cada ativo em relação ao IBOV. Vamos aproveitar a regressão rolling de 252 dias do Bloco 4 (que já calcula betas) e repassar os betas para o Bloco 5 através do arquivo parquet, ou o Bloco 5 deve recalcular os betas de 252 dias independentemente?

## Proposed Changes

### 1. Documentação e Parâmetros Base

#### [MODIFY] [guia_de_implementacaoBLOCOS.md](file:///c:/Users/kakam/OneDrive/Documentos/PROJETOS/DesafioQuant26/guia_de_implementacaoBLOCOS.md)
*   **Correção da Polaridade:** Ajustar a Seção do Bloco 5 para refletir a matemática correta da física do sinal.
    *   **Z-Score Positivo alto:** Ação esperada de subida = COMPRA (LONG)
    *   **Z-Score Negativo alto:** Ação esperada de queda = VENDA A DESCOBERTO (SHORT)

#### [MODIFY] [PARAMETROS.md](file:///c:/Users/kakam/OneDrive/Documentos/PROJETOS/DesafioQuant26/PARAMETROS.md)
*   **AUM (Assets Under Management):** Transformar o tamanho do fundo em um parâmetro livre, crucial para ativar de forma realista a trava de 10% do ADTV (Volume Médio Diário Negociado).
    *   **Valor Padrão:** R$ 100.000.000,00 (100 milhões).
    *   **Testes de Capacidade Planejados:** R$ 20 milhões e R$ 300 milhões.

---

### 2. Motor de Construção de Carteira (Bloco 5)

#### [NEW] [fase 5 - construcao da carteira/src/s5_portfolio_builder.py](file:///c:/Users/kakam/OneDrive/Documentos/PROJETOS/DesafioQuant26/fase%205%20-%20construcao%20da%20carteira/src/s5_portfolio_builder.py)
Este será o script central do bloco 5. Ele fará o pipeline sequencial de transformações a partir do `sinal_sinapse.parquet`:
1.  **Ingestão e Ranqueamento Direcional:**
    *   Sinal `> 0` (cauda superior) → Alocações na ponta **LONG**.
    *   Sinal `< 0` (cauda inferior) → Alocações na ponta **SHORT**.
2.  **Vol-Targeting:**
    *   Cálculo da volatilidade móvel (ex: 60 dias) da alocação bruta.
    *   Redução ou alavancagem para buscar 12% de volatilidade anualizada, aplicando um escalar inversamente proporcional (Volatilidade Alvo / Volatilidade Realizada).
3.  **Travas e Limites Institucionais (Otimização Iterativa):**
    *   Limite de **5% por nome** (ação individual).
    *   Agrupamento por setor (`mapeamento_setores.csv`) e aplicação do limite máximo absoluto de **25% de exposição por setor**.
    *   Cálculo de Volume em BRL baseado na média de volume (ADTV de 21 dias) importada do COTAHIST.
    *   Trava de liquidez restritiva: Posição Financeira (Peso % × `AUM`) **≤** `10% × ADTV`. (Se o limite for excedido, o peso é "tesourado").
4.  **Hedge Beta-Neutro Dinâmico:**
    *   Cálculo do Beta agregado (ponderado) da carteira em relação ao IBOV.
    *   Inclusão de uma nova coluna/ativo chamado `IBOV_SYNTHETIC` (ou equivalente como BOVA11/FUT), cujo peso no dia é exatamente `-1 * (Soma (Peso_i * Beta_i))` para garantir que o *Beta de Mercado* do fundo zere.
5.  **Execução Institucional:**
    *   Geração do output final: matriz de alocação de capital `df_weights_final.parquet`.
    *   O motor assumirá que o *Lag de execução (t+1)* será comandado nativamente no motor do Bloco 3, conforme previsto no Guia de Implementação, ou aplicará o shift(1) no output, garantindo rigor e pagando os spreads.

---

### 3. Validação e Testes Unitários

#### [NEW] [fase 5 - construcao da carteira/tests/test_s5_portfolio_builder.py](file:///c:/Users/kakam/OneDrive/Documentos/PROJETOS/DesafioQuant26/fase%205%20-%20construcao%20da%20carteira/tests/test_s5_portfolio_builder.py)
Implementação de testes com `pytest` (usando *mocks* e dados estáticos) para validar toda a infraestrutura matemática de travas:
*   `test_polaridade_zscore`: Confirma se Z-Scores positivos geram pesos > 0, e negativos pesos < 0.
*   `test_limite_peso_ativo`: Garante que nenhum ativo ultrapassa |5%|.
*   `test_limite_peso_setorial`: Garante que a soma do valor absoluto (ou líquido) de ativos num setor nunca excede 25%.
*   `test_trava_liquidez_adtv`: Avalia três cenários injetando diferentes AUMs (20M, 100M, 300M). Deve provar que com R$ 300M o *clipping* das caudas (*small caps*) é severo, e em 20M os pesos fluem normalmente.
*   `test_beta_neutrality`: Confirma matematicamente que o produto escalar `sum(Peso * Beta) + Peso_IBOV` resulta em 0 (com margem de erro razoável `1e-6`).

## Verification Plan

### Automated Tests
*   Rodar `pytest fase 5 - construcao da carteira/tests/test_s5_portfolio_builder.py -v`.

### Manual Verification
*   Revisão da lógica matemática no pull request pelo analista-chefe.
*   Injeção do output final `df_weights_final.parquet` gerado no ambiente, verificando colunas (Tickers + IBOV) e índices (datas).
