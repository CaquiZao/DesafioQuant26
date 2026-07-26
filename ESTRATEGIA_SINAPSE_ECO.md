# Estratégia SINAPSE + ECO
**Desafio Quant AI 2026**

Este documento centraliza a tese e a mecânica da estratégia SINAPSE + ECO, servindo de contexto unificado para a implementação do código.

## 1. A Tese Principal (Atenção Escassa e Fronteira)
Empresas não são ilhas. Elas estão conectadas através de laços econômicos e societários (clientes, fornecedores, controladores, subsidiárias). Quando acontece um evento de grande impacto (choque) em uma empresa, as ações das empresas ligadas a ela demoram a reprecificar. 

**Por quê?** Porque o mercado possui "atenção escassa". Analistas que cobrem Vale (mineração) não acompanham os detalhes micro de suas pequenas transportadoras com o mesmo rigor, no mesmo instante. O mercado leva tempo (dias) para transferir a informação através da cadeia econômica.
**O Fosso:** No Brasil, não existe um dataset limpo com essas conexões (ao contrário dos EUA, onde o regulador exige declaração estruturada dos clientes relevantes). Essas ligações estão enterradas na prosa de milhares de Fatos Relevantes, Comunicados (IPE) e Formulários de Referência (FRE) da CVM. A estratégia usa IA (LLMs) para ler esse acervo, extrair as ligações e montar o mapa. Com o mapa em mãos, operamos o atraso da reprecificação.

## 2. Componentes da Estratégia

### 2.1. O Grafo de Elos (A "Planta Hidráulica")
Um mapa estruturado das conexões entre empresas brasileiras.
- **Formato:** `Empresa A | Empresa B | Tipo_do_Elo | Força | Direção | Data_em_que_virou_público`
- **Validação Inicial (Bloco 4.1):** Começa com um "Grafo Manual" de ~30 elos (Petrobras <-> Fornecedores, Vale <-> Logística, Varejo <-> Shoppings) para provar o mecanismo estatisticamente antes de acionar a extração em massa pela IA.

### 2.2. Choque Limpo (O Gatilho)
O choque na "Empresa A" (a grande) precisa ser **idiossincrático** — não pode ser o mercado caindo inteiro ou o setor caindo inteiro. 
- Retira-se a parcela explicada pelo beta do mercado e beta do setor.
- **Cálculo:** Regressão simples onde o resíduo (epsilon) é o choque limpo.
- `Choque_limpo_A = Retorno_A - (alpha + beta1 * Retorno_Ibovespa + beta2 * Retorno_Setor)`

### 2.3. O Sinal SINAPSE (A Propagação)
O sinal gerado para a "Empresa B" (a vizinha atrasada, onde vamos operar).
- **Sinal_B** = `Choque_limpo_A` * `Força do Elo` * `Direção (assimetria)`.
- A relação precisa respeitar a mecânica do negócio (ex: quebra de um fornecedor exclusivo pode ser ruim para o cliente, mas o fechamento de um concorrente pode ser ótimo).

### 2.4. Portão ECO e Distração (Opcionais e Filtros de Atenção)
- **Portão ECO (Silêncio de Volume):** A janela de oportunidade só existe se ninguém estiver olhando para a Empresa B. Se a Empresa B já teve pico de volume de negociação após o choque em A, a janela fechou. Só operamos se houver silêncio.
- **Bônus de Distração:** Se o choque acontece num dia em que muitas outras empresas publicam Fatos Relevantes (dias de temporada de balanços, etc), o investidor está mais distraído e o atraso é maior. O prêmio é escalado por esse fator.

## 3. Gestão de Risco e Construção da Carteira
As restrições de operação garantem que o backtest seja institucional e replicável.

1. **Assimetria Direcional:** Só operamos no sentido `Empresa Grande (com atenção)` -> `Empresa Pequena (desatendida)`. 
2. **Vol-Targeting:** O dimensionamento das posições usa o inverso da volatilidade recente, para não dar peso irresponsável a nomes pequenos e altamente erráticos. (Módulo defensivo contra Risk-Off).
3. **Travas:**
   - Máximo de **5%** por nome.
   - Máximo de **25%** por setor.
   - Posição máxima de **10%** do Volume Médio Diário Negociado (ADTV).
4. **Tratamento de Outliers:** Sinal final sofre winsorização (corte dos extremos de 2%) e ranqueamento (z-score), impedindo que um outlier desconfigure a carteira.
5. **Neutralidade:** A carteira agregada deve ser `Beta-neutra` contra o Ibovespa.
6. **Execução Institucional:** A posição entra sempre no pregão de **t+1**, nunca no fechamento do dia do choque, pagando os devidos spreads e custos.

## 4. O Argumento Final para a Banca (Ablação)
Para justificar a complexidade, provaremos o valor de cada camada estatisticamente através de uma **Tabela de Ablação**:
- Modelo Base: Grafo Cru (Cohen-Frazzini).
- Adicionando Assimetria Direcional.
- Adicionando Portão ECO (volume).
- Adicionando Fator de Distração.
- **Teste de Placebo (Sanidade):** Embaralhar aleatoriamente os nomes do grafo e testar. O alfa deve colapsar para próximo de zero, provando que é o *mapeamento da dependência econômica* que gera dinheiro, e não sorte sistêmica.

---
*Nota ao programador: Todos os limiares devem ser fixados no arquivo `PARAMETROS.md` antes da execução dos testes de backtest. Evitar ao máximo a calibração de parâmetros (overfitting).*
