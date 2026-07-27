# Solução Arquitetural: Eliminação do Survivorship Bias

Este documento registra a análise e a decisão arquitetural tomada para o módulo `s1_precos.py` do projeto SINAPSE, focada em resolver o problema de viés de sobrevivência (Survivorship Bias) sem comprometer a qualidade dos ajustes de proventos.

## 1. O Problema Identificado

O script `s2_universo.py` mapeou corretamente **253 tickers** que tiveram alta liquidez em algum momento da janela do backtest (2016-2025). No entanto, o `s1_precos.py`, ao tentar baixar esses dados do Yahoo Finance, obteve sucesso em apenas **166 tickers**. 

Isso significa que **87 tickers** falharam, dividindo-se em três categorias:
1. **Rate Limiting / Erro de API:** Ações ativas que o Yahoo falhou em entregar por excesso de requisições.
2. **Tickers Renomeados:** Empresas que mudaram de código (ex: `BVMF3` → `B3SA3`, `KROT3` → `COGN3`). O Yahoo só mantém o histórico sob o ticker novo.
3. **Ações Deslistadas / Falências:** Empresas que saíram da bolsa (ex: `LAME4`, `MPLU3`). O Yahoo simplesmente apaga o histórico dessas empresas.

Ignorar essas 87 ações criaria um **Survivorship Bias (Viés de Sobrevivência)** grave: o backtest simularia a estratégia apenas com as empresas que "sobreviveram" e deram certo, inflando artificialmente os resultados e invalidando o estudo quantitativo.

## 2. O Desafio dos Preços Brutos (COTAHIST)

A solução óbvia seria abandonar o Yahoo Finance e extrair todos os preços do **COTAHIST** (base oficial da B3, que contém 100% dos dados, vivos ou mortos). 

O problema é que o COTAHIST fornece **preços brutos**. A estratégia SINAPSE é baseada na propagação de choques via regressão OLS. Preços brutos sofrem quedas artificiais em dias de eventos corporativos, gerando **choques falsos**:
- **Splits (Desdobramentos):** Uma queda de -50% a -80% num único dia. Destruiria a regressão OLS.
- **Dividendos:** Uma queda leve (~1% a 5%). Causa ruído na regressão, mas é parcialmente absorvido pelo índice setorial e não tem direcionalidade concentrada.

Tentamos buscar os dados de proventos na base aberta da CVM para ajustar os dividendos manualmente. Contudo:
- O endpoint antigo da CVM (`PROV_DINHEIRO`) foi descontinuado.
- Os dados da CVM focam na "Data de Aprovação", mas o ajuste financeiro exige a **Data-Ex** (dia em que a ação fica ex-direitos), dado que não está prontamente tabular na base da CVM.

## 3. A Solução: Arquitetura Híbrida Inteligente

Como a busca por preços 100% ajustados da B3 exigiria a contratação de provedores pagos (como Economatica ou Bloomberg), adotaremos uma **solução híbrida** que extrai o melhor dos dois mundos.

O novo `s1_precos.py` funcionará em duas etapas:

### Etapa 1: Ações "Vivas" (Yahoo Finance)
Para a grande maioria do dataset (~166 ações), usaremos o Yahoo Finance.
- **Por quê?** O Yahoo já fornece a série `Adj Close` matematicamente perfeita, ajustada retroativamente para todos os splits e dividendos.
- **Como:** Implementaremos um sistema de *retry* com atraso (delay) para garantir que ações ativas (como `JBSS3`) não falhem por rate-limiting.

### Etapa 2: Ações "Mortas" / Faltantes (COTAHIST + Heurística)
Para as ações que o Yahoo Finance rejeitar (deslistadas ou renomeadas), faremos o resgate diretamente dos arquivos COTAHIST locais.
- **O Problema dos Splits:** Aplicaremos uma **heurística de detecção de splits**. O algoritmo rastreará retornos diários que correspondam a frações exatas típicas de desdobramento (-50%, -66.6%, -75%, -80%, etc.) em dias onde o IBOVESPA não sofreu crash equivalente. Ao detectar, multiplicará toda a série de preços anterior pelo fator de correção (ex: x0.5).
- **O Problema dos Dividendos:** Para essa minoria de ações deslistadas, os dividendos **não serão ajustados**. Aceitaremos esse leve ruído.

### Por que essa solução é robusta?
1. **Zero Survivorship Bias:** Toda ação líquida do universo estará no backtest, mesmo que tenha falido.
2. **Proteção contra Choques Falsos Graves:** O tratamento heurístico dos splits impede que quedas artificiais de -50% contaminem o grafo de regressão.
3. **Pragmatismo Analítico:** Ações prestes a falir (maioria das deslistadas) raramente pagam dividendos expressivos nos anos finais. O ruído residual de dividendos na série dessas ações é facilmente absorvido pelo modelo de Rolling OLS de 252 dias e pelo beta setorial.

> [!TIP]
> **Resumo Acadêmico para Defesa:** "Utilizamos o Yahoo Finance para a série ajustada primária e o COTAHIST para a reconstrução de empresas deslistadas (com correção heurística de splits), garantindo 100% de cobertura do universo sem viés de sobrevivência."
