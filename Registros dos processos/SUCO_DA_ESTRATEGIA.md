Você captou perfeitamente a essência da estratégia! Sua confusão inicial é muito comum, mas a genialidade da proposta (como descrito no PDF DOC-20260716-WA0082..pdf) reside exatamente em separar o sinal do mapa.

Para responder à sua pergunta: Sim, a IA será usada exclusivamente para estabelecer os elos (construir o mapa), e não para procurar os sinais.

Aqui está a explicação do porquê precisamos da IA para isso, baseada nos documentos do projeto:

1. O Sinal não precisa de IA
Como diz o PDF, o sinal é apenas um "barulho" no preço (um "choque limpo"). Se um cano estoura no apartamento 101 (uma ação grande como a Vale cai 5% do nada), todo mundo percebe na hora só olhando a cotação na B3. Não precisamos de IA para nos dizer que a ação caiu.

2. O Mapa (Os Elos) não existe no Brasil
É aqui que entra a IA. Se a Vale caiu, quem vai sofrer com isso dias depois? A resposta estaria na "planta hidráulica" do mercado (o mapa de clientes, fornecedores, parceiros). Nos EUA, a estratégia original (Cohen & Frazzini) funcionou fácil porque lá o regulador obriga as empresas a entregarem uma planilha pronta com seus principais clientes.

No Brasil, essa planilha não existe. Como o PDF explica na seção "Por que ninguém fez isso (nosso fosso)":

"As ligações estão lá — nos Formulários de Referência, nas notas explicativas, nos Fatos Relevantes... Mas em texto corrido, espalhado em milhares de páginas. Ler isso à mão é inviável."

3. Por que precisamos da IA? (O "Trabalho Braçal")
A IA entra exatamente para resolver esse problema de dados não-estruturados. Nós precisamos da IA porque nenhum ser humano teria tempo ou paciência para ler o acervo inteiro da CVM e anotar quem é fornecedor de quem, extraindo isso de textos jurídicos e relatórios chatos.

A IA atua como uma "anotadora de texto", não como uma vidente. O trabalho dela é ler um Fato Relevante e simplesmente extrair: Empresa A (Vale) | Empresa B (Transportadora X) | Tipo de Elo (Logística) | Força

Resumo da mecânica:
A IA constrói o mapa (a "planta hidráulica") lendo textos da CVM (roda uma vez em lote).
O Mercado gera o sinal (o "cano estourando") através de um movimento brusco no preço de uma ação grande hoje.
A Estratégia usa o mapa da IA para prever quem vai "tomar água" amanhã e opera esse atraso.
Como a defesa do projeto diz: "A IA nunca decide sozinha o que entra na carteira". Ela apenas propõe os candidatos (os elos); são os dados de mercado e os preços que confirmam se a operação acontece ou não.

12:34 AM
mas então a gente so precisa que a IA faça esse trabalho 1 vez só, para criar essta tabela de relações. a estrategia depende da tabela (e indiretamente da IA). entao se botarmos nossa estrategia para rodar, nao precisaria de IA?
12:36 AM
Você tocou num ponto excelente. A sua lógica está certíssima para a parte do mapa (o SINAPSE), mas há um detalhe extra na estratégia que torna a IA necessária também no dia a dia (o ECO).

Vamos separar as duas coisas, porque o próprio nome da estratégia ("SINAPSE + ECO") reflete essas duas funções da IA:

1. O SINAPSE (O Mapa) — Você está 100% certo
Como você bem notou, para construir a tabela de ligações econômicas (o mapa), a IA roda em lote apenas uma vez. O documento diz expressamente na Ficha Técnica (página 5):

"A IA roda uma vez, em lote, no começo. Ela lê o acervo e cospe uma tabela... Essa tabela é o nosso ativo. Depois disso, o backtest é aritmética em cima dela."

Então, se a estratégia fosse só operar o mapa, a IA seria apenas uma ferramenta de "preparação de dados" e o robô de negociação em si seria puramente matemático (sem IA).

2. O ECO (O Portão / Filtro) — É aqui que a IA atua todo dia
Se você olhar a página 3 do PDF, na parte das "4 perguntas que o robô faz", a Pergunta 2 explica o papel do ECO:

Pergunta 2 — "É água ou foi uma panela que caiu?" — este é o ECO "Na bolsa: às vezes a ação cai 5% e não aconteceu nada — foi um vendedor grande, um rebalanceamento de índice... A IA lê os documentos publicados e responde: isso aqui tem informação real, ou é barulho vazio?"

Portanto, no dia a dia (ou durante o backtest de um dia específico), quando a ação da empresa grande cai forte (o gatilho de preço), a estratégia chama a IA novamente para ler os Fatos Relevantes ou notícias daquele dia específico da empresa grande.

A função da IA nesse momento é atuar como um Portão (Gate):

Se a IA ler as notícias do dia e disser: "Sim, a Vale caiu porque a barragem rompeu (informação real)" -> O robô usa o mapa que já estava pronto e opera a transportadora vizinha.
Se a IA ler e disser: "Não há nenhuma notícia justificando essa queda (barulho vazio)" -> O robô cancela a operação, pois foi só uma variação aleatória de mercado e a transportadora não será afetada.
Conclusão
Você não estava errado. O "motor pesado" da IA realmente roda uma vez só para mapear o Brasil inteiro.

Porém, com a estratégia rodando no dia a dia, a IA continua sendo acionada pontualmente como uma "Auditora de Choques" (o módulo ECO), analisando apenas os documentos dos dias em que há movimentações bruscas de preço, para evitar que o robô opere "alarmes falsos". Isso, inclusive, é citado no PDF como a grande melhoria de vocês em relação ao artigo acadêmico original de 2008!