# Síntese Definitiva: Estratégia SINAPSE + ECO
**Desafio Quant AI 2026**

Este documento é a "fonte da verdade" técnica e didática para todo o time. Ele alinha o que estamos construindo, por que estamos construindo e como o código deve ser estruturado. 

O documento está dividido em duas partes: a **Parte 1** reflete nosso planejamento atual (o *core* da estratégia), e a **Parte 2** detalha a expansão institucional que implementaremos em seguida para blindar a carteira.

---

# PARTE 1: A Estratégia Core (Planejamento Atual)

## 1. A Estratégia SINAPSE (A Tese)

### 1.1 Explicação Didática (A Analogia do Prédio)
Imagine um prédio de apartamentos. Cada apartamento é uma empresa da bolsa.
- Um cano estoura no apto 101. Todo mundo do 101 sabe na hora, e o preço da ação cai imediatamente.
- O apto 201, logo abaixo, vai tomar água. É um fato físico e garantido. Só que o mercado (o pessoal do 201) ainda não percebeu.
- Se você tem a **planta hidráulica** do prédio, você sabe que o 201 terá problemas antes dele próprio saber. 

Ninguém na bolsa brasileira tem essa planta hidráulica, pois ela está escondida em milhares de parágrafos na CVM. Nossa IA vai construir essa planta e nós operaremos o atraso da reprecificação. A lógica central é que **a atenção do mercado é escassa e tem fronteira**: quem acompanha a Vale (gigante) não acompanha sua transportadora (pequena) na mesma velocidade.

### 1.2 Explicação Técnica e Econômica
- **O Grafo Econômico:** Extraído dos comunicados do IPE (Fatos Relevantes). Formato: `Empresa A | Empresa B | Tipo_do_Elo | Força | Direção | Data_em_que_virou_público`.
- **A Janela:** A reprecificação opera em base **mensal** (baseado em Cohen & Frazzini 2008). No início de cada mês, ranqueamos as ações (vizinhas) pelo retorno das empresas-mãe (grandes clientes/fornecedores) no mês anterior.
- **Assimetria Direcional:** O choque só se transmite da empresa GRANDE para a PEQUENA. O inverso não tem atraso informacional porque a grande empresa possui alta cobertura de analistas. Isso nos defende da crítica "é só o setor andando junto".
- **O Sinal Sinapse:** O gatilho não é o retorno bruto da grande, mas o **choque limpo** (retorno idiossincrático, isolando o beta do mercado e o beta do setor via regressão). O sinal final é `Choque Limpo * Força do Elo * Direção`.
- **Portão ECO (Silêncio de Volume):** A janela de oportunidade (atraso) só fica aberta se o volume de negociação do "201" estiver normal. Se o volume aumentou anormalmente, o mercado já viu o vazamento e nós não entramos.
- **Distração (Multiplicador):** Em dias em que a CVM lança milhares de documentos, a desatenção geral é maior (Hirshleifer et al, 2009). O prêmio é escalado (multiplicado) por essa métrica.

## 2. O Pipeline de IA (A Cascata Eficiente)
Não rodaremos IA cega em 10 anos de PDF. A técnica exige restrição de custos (limite de R$ 40) e viabilidade:
1. **Pré-filtro Determinístico:** Regex buscando verbos de dependência. Corta ~90% do volume inútil.
2. **Dedup por Hash de Parágrafo:** Resolve 80% do copy-paste anual de notas repetidas e **entrega a data oficial** em que o elo se tornou público pela primeira vez (resolvendo o *look-ahead bias* por construção).
3. **Cascata de Modelos:** Modelo pequeno (Flash-Lite) diz "sim/não" para dependência no parágrafo. Só os ~5% positivos vão para o modelo forte extrair as variáveis do grafo.
4. **Execução:** Batch API ou Modelos Locais (Ollama) para garantir hash fixo e reprodutibilidade.

## 3. O Fluxo Completo de Código (Arquitetura em Blocos)

### Bloco 0: Conseguir os Dados
- **Fontes exclusivas:** COTAHIST (preços/volumes), Carteiras Quadrimestrais do Ibovespa e Portal de Dados Abertos CVM (IPE).
- **CRÍTICO:** Não usaremos Yahoo Finance, pois gera viés de sobrevivência (*survivorship bias*). Apenas COTAHIST com universo *point-in-time* da B3.

### A FÁBRICA (Blocos 1 a 3): A Mecânica Base
- **Bloco 1 (Preços):** Leitor de COTAHIST (arquivo posicional), ajuste de proventos.
- **Bloco 2 (Universo Point-in-Time):** Montar a composição de quem estava na bolsa mês a mês, garantindo a presença das deslistadas na época certa.
- **Bloco 3 (Motor de Backtest):** Recebe os pesos do Mês X e devolve o P&L do Mês X+1, executando custos de transação. 
- **⚠️ Teste de Sanidade:** Rodar uma "Estratégia Idiota" (comprar todo o universo de forma igual). O retorno DEVE bater com o Ibovespa.

### O PRODUTO (Blocos 4 e 5): O Coração da Sinapse
- **Bloco 4.1 (Grafo Manual):** Testamos a tese com **~30 elos construídos na mão**. É um *GO/NO-GO* da estratégia.
- **Blocos 4.2 a 4.4:** Calcular o choque limpo ortogonalizado, multiplicar por força e direção, ordenar e aplicar winsorização de 2% (corte de extremos) para virar Z-Score.
- **Bloco 5 (Construção da Carteira):** Aplicar os multiplicadores (distração e silêncio). Impor travas: máx 5% por nome, máx 25% por setor, posição ≤ 10% do volume médio diário e garantir carteira Beta-Neutra.

### FASE 2: A Automação e Validação Científica
Se o mapa manual passar nas portas (existe efeito e assimetria direcional), ativamos o script da IA:
- **Tabela de Ablação:** Testaremos o Alpha (t-stat) removendo uma camada de cada vez. Simplicidade justificada ganha ponto.
- **Placebo Embaralhado:** Embaralhamos as ligações aleatoriamente e rodamos 500 vezes para provar que a informação textual da CVM previu o mercado.

---

# PARTE 2: Expansão Institucional (O que implementar após o Core)

Assim que o *core* (Sinapse) estiver rodando e validado, nós vamos acionar a "Fase de Defesa e Consistência". Isso significa que adicionaremos uma estratégia base, o **Cérbero Adaptado (BAB-BR)**, em conjunto com a Sinapse. 

Como a infraestrutura de dados (COTAHIST, Universo) e o motor de backtest já estarão prontos graças ao trabalho feito na Parte 1, a implementação disso será extremamente rápida (aproveitamento de ~90% do código) e nos dará pontuação máxima em rigor técnico perante a banca.

## 1. O que vamos implementar
- **BAB-BR (Betting Against Beta no Brasil):** Uma estratégia focada na anomalia estrutural de que ações de baixo beta (baixo risco) costumam performar melhor em termos de retorno ajustado ao risco do que ações de alto beta, porque grandes investidores são limitados por restrições de alavancagem.
- **Vol Targeting:** Dimensionamento dinâmico do tamanho das posições. Escala-se a exposição da carteira pelo inverso da volatilidade realizada.
- **Curva DI como Teste de Funding:** Usaremos a variação do spread da curva de juros (ou a taxa de aluguel de ações da B3) não como um "gatilho mágico" para ligar e desligar o robô, mas como um teste para provar a validade da anomalia do BAB.

## 2. Justificativas Plausíveis (Por que a banca vai aprovar essa adição)

Não estaremos quebrando a regra de "complexidade injustificada". Pelo contrário, essa adição traz as seguintes defesas inquestionáveis:

- **Argumento de *Risk Parity* (O Santo Graal Institucional):** A Sinapse explora uma ineficiência informacional (texto), enquanto o BAB explora um prêmio de risco estrutural (dinâmica de oferta/demanda). Eles têm fontes de retorno totalmente **ortogonais** (descorrelacionadas). Unir as duas abordagens mostra à banca que sabemos fazer gestão de portfólio madura.
- **Redução Drástica do Max Drawdown:** Estratégias puras de *momentum* ou anomalias de informação (como a Sinapse) podem sofrer quedas severas (drawdowns) quando ocorrem choques repentinos no mercado. O BAB, focado em baixo beta, ancora a carteira. Juntos, os vales da curva de capital (*drawdowns*) ficam infinitamente menores.
- **Diminuição do Risco e Consistência (Efeito Vol Targeting):** Quando a volatilidade do mercado explode (ex: crises, eventos políticos surpresas no Brasil), o algoritmo de *Vol Targeting* reduz matematicamente e automaticamente a exposição bruta do fundo. Isso protege a rentabilidade acumulada, tornando a estratégia consistente em cenários onde concorrentes quebrarão.
- **Otimização de Risco/Retorno (Sharpe Ratio):** Com a Tabela de Ablação cruzando as duas estratégias, vamos provar matematicamente para os avaliadores que o Índice de Sharpe da carteira combinada é muito mais atraente do que rodá-las isoladas. A complexidade **se paga**, o que cumpre o edital.
- **"Seguro de Vida" Técnico:** Se houver qualquer dúvida sobre o grau de acerto da IA da Sinapse num determinado mês atípico, o módulo de BAB continuará segurando as pontas gerando alpha estrutural puro, garantindo que o backtest não dependa 100% de uma extração perfeita da CVM a cada segundo.
