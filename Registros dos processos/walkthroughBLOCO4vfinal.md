# Conclusão do Bloco 4 (Sinal da Sinapse)

A fase de criação e propagação do Sinal da estratégia foi 100% estruturada e testada com dados reais, marcando a entrega completa do **Bloco 4**.

## O que foi construído

1. **Blindagem do Grafo Econômico (O Core da Estratégia):** 
   - A documentação e os critérios dos elos foram expandidos para incluir nuances de não-linearidade (`JBSS3 -> BRFS3`, `Petroleiras`, `Celulose`).
   - Adicionamos a Metodologia de Validação com fatos da CVM, covariância isolada de Beta e ITR.
   - O arquivo `grafo_manual_base.csv` foi totalmente reconstruído e limpo com 30 elos institucionais verificáveis.

2. **Ingestão de Dados (Fase 1 e 2):**
   - Atualizamos os extratores (`s1_precos.py` e `s1b_indices.py`) para puxarem dinamicamente todo o universo do nosso grafo e remover os antigos ETFs (implementando a decisão oficial de Índices Sintéticos).
   - Efetuamos o download maciço e real de 10 anos de pregão das empresas-alvo diretamente para arquivos `.parquet`.

3. **Motor Matemático (`s4_sinapse_sinal.py`):**
   - O código final do Bloco 4 foi programado em Python (Pandas e Statsmodels).
   - Implementou-se a **Regressão Móvel (Rolling OLS) de 252 dias** para isolar o Alfa idiossincrático (*Choque Limpo*).
   - O loop de propagação injeta e amortiza (usando o fator de força e direção do grafo) os choques nas empresas satélites.
   - Os ruídos são filtrados via Winsorização Transversal e normalizados como um `Z-Score`.

## Resultados da Validação

A execução processou quase 2.500 dias de pregão sobre as 39 empresas capturadas.
A Regressão Múltipla, a propagação do Grafo e a normalização Z-Score foram executadas perfeitamente em apenas 18 segundos de computação!
O arquivo mestre final, `sinal_sinapse.parquet`, foi gerado e salvo com sucesso na pasta `data/`.

> [!IMPORTANT]
> A matriz final `sinal_sinapse.parquet` contém, para cada dia e para cada ação-alvo, a pontuação estatística limpa que dita qual ação deve ser operada (comprada ou vendida) no dia seguinte. Este é o exato arquivo que o simulador final de carteira (Backtest / Bloco 3) irá ingerir.
