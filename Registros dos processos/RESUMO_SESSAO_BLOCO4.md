# Resumo da Sessão: Conclusão e Engenharia do Bloco 4

**Para:** Equipe do Projeto SINAPSE
**Por:** Caqui (e Assistente IA)
**Objetivo deste documento:** Registrar de forma didática tudo o que foi construído nesta sessão de trabalho, as decisões técnicas tomadas, os atalhos estratégicos utilizados e os próximos passos exatos.

---

## 1. Onde estávamos e Onde chegamos

O nosso foco principal nesta sessão era **destravar e finalizar o Bloco 4 (Sinal da Sinapse)**, que é o coração matemático da estratégia. Nós saímos de um planejamento teórico para um motor quantitativo 100% funcional.

Nós conseguimos rodar o algoritmo completo! O código baixou o histórico de preços, rodou as regressões, propagou os choques pelo grafo e gerou com sucesso o arquivo final de saída: **`sinal_sinapse.parquet`**.

---

## 2. O que foi feito e Como foi feito

### A. A Blindagem do Grafo (A Teoria)
Nós nos debruçamos sobre o `grafo_manual_base.csv` para garantir que as relações entre as empresas fossem inquestionáveis por qualquer avaliador.
*   **O que mudou:** Atualizamos o `grafo_manual_base.csv` e o `mapeamento_setores.csv`, definindo 30 elos institucionais claros (Fornecedor, Concorrente, Holding, etc.).
*   **A Grande Descoberta (O papel do ECO):** Durante a criação do grafo, ficou evidente a necessidade absoluta do módulo **ECO (Eventos, Contexto e Opinião)**. Percebemos que as relações entre os pares não são perfeitamente lineares e simétricas. Por exemplo: A JBS e a BRF são concorrentes, mas a JBS é dona da Seara. Um choque no preço do milho atinge as duas negativamente (vetor 1), enquanto uma crise de imagem exclusiva em uma migra o fluxo de capital para a outra (vetor -1). 
*   👉 **Leitura Obrigatória:** Registramos toda a metodologia de auditoria e essas nuances da necessidade do ECO no arquivo `CRITERIOS_GRAFO_MANUAL.md`. É vital que o grupo leia isso.

### B. O Motor Matemático (A Engenharia)
*   **Índices Sintéticos:** Decidimos abandonar os ETFs (BOVA11, etc.) por serem caixas-pretas limitadas e criamos índices sintéticos na mosca (on-the-fly) dentro do código. A justificativa está no `EXPLICACAO_S1B_INDICES.md` e no `DECISAO_REGUAS_SETORIAIS.md`.
    *   **O Papel do `mapeamento_setores.csv`:** Ele foi a peça-chave para resolver esse problema dos Índices Sintéticos. O algoritmo faz o seguinte passo a passo:
        1. **Leitura do Mapa:** O robô abre o `mapeamento_setores.csv` e decora a qual setor cada ação pertence (Ex: `PETR4` = Petróleo; `VALE3` = Mineração).
        2. **Criação do Índice Sintético:** Todos os dias, ele agrupa as ações por setor. Por exemplo, pega todas as ações de "Energia Elétrica", soma a rentabilidade delas no dia e divide pela quantidade. Pronto! Ele acabou de criar o Retorno do Setor.
        3. **Limpeza do Choque (A Regressão):** Quando vai calcular o "Choque Limpo" da Eletrobras, ele avisa para a regressão matemática: *"Desconte do retorno da Eletrobras o retorno do IBOV e o retorno do Índice Sintético de Energia Elétrica"*.
    *   👉 **Resumo:** Sem o `mapeamento_setores.csv`, o nosso algoritmo não saberia agrupar as empresas e seria incapaz de calcular o "Beta Setorial" para limpar os ruídos macroeconômicos. Ele é o dicionário de agrupamento do nosso robô!
*   **O Coração do Algoritmo (`s4_sinapse_sinal.py`):** O script foi todo programado em Python. Ele faz uma **Regressão Rolling OLS de 252 dias** para limpar o "ruído" do mercado (Beta IBOV e Beta Setorial) e extrair o Alfa puro de cada ativo (o verdadeiro *Choque Limpo*).
*   **O Filtro:** Para evitar alarmes falsos institucionais, nós aplicamos um corte nas caudas extremas (`Winsorização`) e geramos um `Z-Score` transversal todos os dias, comparando todo o universo do portfólio. As explicações de corte foram anexadas no `DECISAO_DOS_PARAMETROS.md`.

---

## 3. O Atalho Estratégico (IMPORTANTE: A "Gambiarra" Necessária)

Para que conseguíssemos rodar o nosso motor `s4_sinapse_sinal.py` e extrair o nosso desejado output `sinal_sinapse.parquet` hoje, nós precisávamos dos preços diários (`s1_precos.py`). 

Pelo PDF original do projeto (`passo 2.pdf`), o script `s1_precos.py` deve ler o arquivo final `universo_mensal.parquet` (que contém as 253 ações mais líquidas da bolsa extraídas daquele monstruoso arquivo de 3,6 GB do COTAHIST da B3). 

No entanto, nós ainda não tínhamos esse arquivo rodado aqui no nosso ambiente local.

**O que eu fiz:** Fiz um atalho estratégico na programação. Eu adaptei o `s1_precos.py` (que antes tinha apenas 2 tickers de "teste") para ler e baixar dinamicamente as **44 empresas que nós já mapeamos dentro do nosso `grafo_manual_base.csv`**. 

Fiz isso propositalmente para destravar o Bloco 4 hoje. Se tivéssemos que esperar os dados densos da B3 para gerar a lista mágica de 253 ações, não teríamos conseguido rodar o algoritmo e testar a nossa matemática (regressões + grafos) agora há pouco.

---

## 4. Mapeamento de Arquivos Impactados

Para o controle do grupo, essa é a lista da "trilha de papel" que deixamos nessa sessão, desde códigos a planos de execução:
*   `fase 1 - preço ajustado/src/s1_precos.py` (Com a nossa adaptação do grafo)
*   `fase 1 - preço ajustado/src/s1b_indices.py`
*   `fase 4 - sinal da sinapse/grafo_manual_base.csv`
*   `fase 4 - sinal da sinapse/mapeamento_setores.csv`
*   `fase 4 - sinal da sinapse/src/s4_sinapse_sinal.py` (Onde mora o algoritmo final)
*   `Registros dos processos/CRITERIOS_GRAFO_MANUAL.md`
*   `Registros dos processos/DECISAO_REGUAS_SETORIAIS.md`
*   `Registros dos processos/EXPLICACAO_S1B_INDICES.md`
*   `Registros dos processos/DECISAO_DOS_PARAMETROS.md`
*   `Registros dos processos/implementation_planBLOCO4.md`
*   `Registros dos processos/implementation_planMELHORIADOGRAFOMANUAL.md`
*   `Registros dos processos/walkthroughBLOCO4.md`
*   `Registros dos processos/walkthroughBLOCO4vfinal.md`

---

## 5. Onde Paramos e O que Falta

Testamos a ponta do Bloco 4 e o motor matemático gerou a matriz. Estamos operantes.

**O que falta agora:**
1. **Desfazer o atalho do COTAHIST:** Quando vocês rodarem o pesado `s2_universo.py` na máquina de vocês, nós só precisaremos ir no `s1_precos.py` e mudar **uma linha** de código para ele voltar a ler as 253 ações do universo total, em vez das 44 da nossa amostra. Feito isso, o projeto estará 100% fiel às diretrizes do `passo 2.pdf`.
2. **Backtest (Bloco 3):** Pegar a nossa grande vitória de hoje, que é o arquivo output `sinal_sinapse.parquet`, e injetar ele no simulador de carteira do Bloco 3. Assim veremos como as rentabilidades dessa estratégia se portaram na linha do tempo de 10 anos.

---

## 6. O Fluxo Completo da Estratégia (Como o nosso robô pensa do zero ao fim)

Para que todos no grupo fiquem na mesma página, aqui está a "Jornada do Dado". É assim que o nosso código transforma arquivos brutos em ordens matemáticas de Compra e Venda:

### Passo 1: Quem pode brincar? (`s2_universo.py`)
Tudo começa aqui na Fase 2. O nosso código engole os gigantescos arquivos históricos da B3 (COTAHIST, com mais de 3,6 GB de dados brutos) e varre 10 anos de pregão. O objetivo dele é responder: *"Quais foram as 100 ações mais negociadas em cada mês?"*. 
Ele joga fora tudo que é "lixo" ou ilíquido (ações mortas, BDRs, ETFs, FIIs) e devolve apenas as ações puras de alta liquidez da bolsa brasileira. O resultado disso são **253 ações únicas** que já fizeram parte da elite da B3. Isso corrige o temido viés de sobrevivência (survivorship bias).

### Passo 2: O preço justo (`s1_precos.py` e `s1b_indices.py`)
Com a lista VIP de 253 ações na mão, o robô precisa saber o histórico real delas. 
O script `s1_precos.py` vai na internet (via API do Yahoo Finance) e baixa o preço diário de fechamento de todas essas ações nos últimos 10 anos. Ele já ajusta os preços perfeitamente (ex: se a empresa pagou dividendo, ele ajusta o gráfico pra trás para não acharmos que a ação caiu). 
O `s1b_indices.py` faz a mesma coisa, mas para o Ibovespa, que é a nossa régua de mercado. O resultado dessa fase são as tabelas limpas de retornos diários (a variação percentual de cada dia de cada papel).

### Passo 3: O Motor Matemático e o Grafo (`s4_sinapse_sinal.py`)
Aqui é onde a mágica — ou melhor, a ciência quantitativa — acontece. Esse script é o cérebro da estratégia (o **Bloco 4** que finalizamos hoje). Ele faz três coisas incríveis todos os dias da história:

1. **Calcula o "Choque Limpo" (O Alfa):** O robô olha para uma ação (ex: Eletrobras). Se ela subiu 5% hoje, ele se pergunta: *"Foi mérito exclusivo dela, ou o Ibovespa inteiro subiu? Ou o setor elétrico inteiro subiu?"*. Para responder isso e isolar a verdade, ele faz uma **Regressão Múltipla Móvel (Rolling OLS) dos últimos 252 dias**. Ele compara a Eletrobras com o Ibovespa e com um Índice Sintético do setor elétrico (construído na mosca graças ao nosso arquivo `mapeamento_setores.csv`). A sobra matemática disso (o resíduo da regressão) é o que chamamos de **Choque Limpo** — um movimento estritamente idiossincrático e exclusivo da empresa, sem contaminação do mercado.
2. **Propaga o Sinal pela Teia:** Agora que ele sabe quem sofreu um choque exclusivo, ele abre o nosso `grafo_manual_base.csv`. Se a Vale tomou um choque negativo muito forte (por exemplo, um desastre numa barragem), o robô olha no grafo e vê: *"A Vale é a principal fornecedora da Usiminas. A força desse elo é 1.0 e a direção é positiva (ou seja, se a Vale vai mal, a Usiminas vai mal junto)"*. Imediatamente, o algoritmo pega a magnitude do choque da Vale e injeta esse sinal (como se fosse um veneno) na Usiminas, alertando que ela vai sofrer no dia seguinte.
    *   👉 **O Cálculo da Magnitude do Choque:** A matemática exata que o robô faz para transferir essa dor (ou alegria) de uma empresa para a outra é: `Sinal Recebido = Choque Limpo da Empresa A × Força do Elo × Direção`.
3. **Soma-zero e Redes Indiretas:** Se o elo fosse de concorrência pura (direção -1), o robô inverteria o sinal através dessa mesma fórmula (multiplicando por -1): o desastre de uma viraria o lucro da outra. Depois que a teia inteira repassa esses choques diários, as empresas satélites vão acumular pontuações dizendo se devem ser compradas ou vendidas no próximo pregão.

### Passo 4: O Filtro de Realidade (Winsorização e Z-Score)
Para o nosso robô não enlouquecer e não dar ordens de compra/venda gigantescas só porque uma empresa sofreu um choque absurdo e irreal num único dia (um erro de digitação da API ou um pânico irracional de curtíssimo prazo), o final do `s4_sinapse_sinal.py` tem um "freio ABS":
*   **A Winsorização:** Ele pega todas as pontuações calculadas do dia, e tudo que estiver no 1% mais extremo do topo e no 1% do fundo da distribuição, ele "corta as pontas", achatando esses outliers absurdos para um limite máximo estipulado. Ele não deleta a empresa, apenas limita a exaltação irracional do sinal dela.
*   **O Z-Score Transversal:** Por fim, o algoritmo não cospe o valor bruto do choque, ele o transforma em uma nota estatística universal chamada **Z-Score**. Mas por que isso é absolutamente necessário e como nos ajuda?
    1. **Justiça entre Volatilidades (Comparabilidade):** Um choque de 2% na Taesa (uma empresa super estável) é um terremoto. O mesmo choque de 2% numa empresa de aviação é só mais uma terça-feira comum. O Z-Score divide o choque pelo desvio padrão da distribuição, nivelando o jogo. Ele responde à pergunta: *"Quantos desvios-padrão esse choque está longe do normal?"*.
    2. **A Competição Diária (Transversalidade):** O cálculo compara todas as empresas do universo **naquele dia específico**. Se o mercado inteiro estiver caótico e cheio de choques, o Z-score destaca apenas as empresas que se sobressaíram em relação ao restante do grupo, forçando o robô a focar apenas nas oportunidades relativas mais gritantes do pregão.
    3. **Tamanho da Aposta (Position Sizing):** É o Z-Score que vai ditar para o nosso simulador (Bloco 3) *quanto dinheiro* apostar. Um Z-Score de `+3.0` (3 desvios para cima) grita para o robô: "CONVICÇÃO MÁXIMA, ALOQUE MUITO CAPITAL!". Já um Z-Score de `+0.5` diz: "Sinal fraco, ignore ou entre pequeno".

### O GRANDE FINAL: O Arquivo Mestre
Toda essa jornada de regressões, grafos e filtros cospe um único e valiosíssimo arquivo: o **`sinal_sinapse.parquet`**. 

Este arquivo é literalmente um mapa oracular do tempo. Ele diz para o simulador quantitativo: *"No dia 15 de março de 2018, a Usiminas recebeu um sinal de contágio com Z-Score de -2.5. Venda Usiminas a descoberto e lucre com a queda"* ou *"No dia 12 de maio de 2020, o Pão de Açúcar recebeu um Z-score de +2.2 graças a uma falha do Carrefour. Compre Pão de Açúcar"*. 

É exatamente este arquivo `sinal_sinapse.parquet` que entrará no Backtester (Bloco 3) para executarmos as simulações e descobrirmos matematicamente se essa nossa genialidade toda realmente supera o Ibovespa e bota dinheiro no bolso!
