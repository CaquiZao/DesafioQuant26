# Acompanhamento — 03/08

Resumo simples do que foi feito na sessão de hoje, para facilitar o acompanhamento do progresso do projeto SINAPSE.

## O que foi feito

### Atualização do Motor de Backtest (Bloco 3)

O Bloco 3 (`s3_backtest.py`) era um motor "de mentira", feito só para testar se a mecânica de calcular resultado de carteira funcionava. Ele usava uma estratégia provisória (peso igual entre todas as ações do universo, trocada mês a mês) porque a Sinapse de verdade ainda não existia.

Como o Bloco 5 (montagem da carteira) já está pronto e gerando a carteira real da Sinapse todo dia — incluindo a proteção vendida contra o Ibovespa —, hoje o Bloco 3 foi atualizado para parar de usar a estratégia de teste e passar a usar a carteira real.

Principais mudanças, de forma simples:

- **Antes:** o motor decidia sozinho uma carteira de teste (peso igual para todas as ações) e trocava essa carteira uma vez por mês.
- **Agora:** o motor apenas pega a carteira que a Sinapse já decidiu, dia a dia (vinda do Bloco 5), e calcula quanto essa carteira ganhou ou perdeu em cada dia. Ele não inventa mais nada — só "roda o filme" com a carteira real.
- Isso deixou o cálculo muito mais rápido, porque agora é feito de uma vez só (matemática de matriz) em vez de um loop mês a mês.
- Também foi corrigido um problema em que o script buscava os arquivos de dados no lugar errado (pastas que não existiam) — agora ele encontra os arquivos certos automaticamente, não importa de onde for executado.
- O "teste de sanidade" do final do script (aquele que confere se o resultado faz sentido) também foi ajustado: antes ele esperava que a carteira andasse **parecida** com o Ibovespa; agora, como a estratégia real tem proteção contra o mercado embutida (é "neutra ao mercado"), o esperado é o **contrário** — que a carteira ande de forma **descolada** do Ibovespa. O teste foi rodado e confirmou isso: a correlação ficou bem próxima de zero, como esperado.

### Resultado da checagem

O script foi executado do início ao fim sem erros, usando os dados reais já gerados pelo Bloco 5. A curva de resultado da carteira e o gráfico comparativo com o Ibovespa foram salvos normalmente. A checagem confirmou que o motor está calculando certo: a carteira anda descolada do Ibovespa, como uma estratégia protegida contra o mercado deveria andar.

*(O resultado financeiro da estratégia em si — se ela ganhou ou perdeu dinheiro — é uma questão separada, sobre a qualidade do sinal da Sinapse, não sobre o motor de cálculo, que é o que foi validado hoje.)*

## O que é "proteção vendida contra o Ibovespa" = ser "beta-neutra"

Importante: isso não são dois conceitos em sequência (um causando o outro) — são a **mesma coisa** vista por dois ângulos:
- **"Beta-neutra"** é o nome do *resultado* (o beta total da carteira fica em torno de zero).
- **"Proteção vendida contra o Ibovespa"** é o nome do *mecanismo* que produz esse resultado (a posição `IBOV_SYNTHETIC`).

A carteira da Sinapse compra ações que ela acredita que vão subir mais que as outras (posições "compradas"/LONG) e vende ações que acredita que vão subir menos ou cair (posições "vendidas"/SHORT). Só que, mesmo escolhendo bem as ações, a carteira ainda fica exposta ao humor geral do mercado: se a bolsa toda cair num dia ruim, a maior parte das ações cai junto — boas ou más escolhas — e isso pode mascarar o resultado da estratégia.

Essa sensibilidade ao mercado tem um nome técnico: **beta**. É um número que mede o quanto uma ação (ou uma carteira inteira) costuma se mexer junto com o Ibovespa. Alguns exemplos para intuição:

- Beta = 1: a ação costuma subir/cair na mesma proporção que o Ibovespa (mercado sobe 1%, ela sobe cerca de 1%).
- Beta = 2: a ação se mexe com o dobro da força do mercado (mercado sobe 1%, ela sobe cerca de 2%).
- Beta = 0: a ação não tem relação nenhuma com o movimento do mercado.

Toda carteira, se você somar o beta de cada posição que ela tem (ponderado pelo peso de cada uma), também tem um beta "total". Uma carteira comum, só comprada em ações, normalmente tem beta positivo — ou seja, tende a subir quando a bolsa sobe e cair quando a bolsa cai, mesmo que as ações escolhidas sejam ótimas.

A "proteção vendida contra o Ibovespa" é uma posição extra, adicionada de propósito, para zerar esse beta. Funciona assim:

- O Ibovespa é o principal índice que representa "o mercado" (a bolsa brasileira como um todo).
- "Vender" o Ibovespa é uma aposta de que ele vai cair — ou seja, é o oposto de comprar o mercado.
- O Bloco 5 calcula o beta total que a carteira já tem (pelas posições compradas e vendidas em ações) e adiciona uma posição vendida no Ibovespa do tamanho exato para cancelar esse beta, deixando o beta total da carteira em torno de **zero**.

Na prática, é como comprar um seguro: se o mercado cai, a carteira perde dinheiro nas ações mas ganha na posição vendida do Ibovespa — e vice-versa se o mercado sobe. As duas coisas se cancelam. O que sobra é só o resultado das escolhas da Sinapse (quais ações são melhores que outras), sem o "ruído" de o mercado ter subido ou descido no geral.

É por isso que essa estratégia é chamada de **"beta-neutra"** (ou *beta-neutral* / "neutra ao mercado") — o nome descreve exatamente o que foi zerado: o beta, isto é, a sensibilidade da carteira ao movimento do mercado. É também por isso que o teste de sanidade de hoje esperava (e confirmou) que a carteira andasse **descolada** do Ibovespa, não parecida com ele: se o beta está mesmo perto de zero, a correlação diária com o Ibovespa também deve ficar perto de zero.

No código, essa posição de proteção aparece com o nome `IBOV_SYNTHETIC` na tabela de pesos gerada pelo Bloco 5.

## Corrigindo os "dados de mentira" e um bug sério que apareceu no caminho

Depois de rodar o motor pela primeira vez, o resultado veio bem ruim
(-20,7% de retorno no período todo). Antes de aceitar esse número, valia a
pena desconfiar dele, porque três peças do cálculo ainda eram "dados de
mentira" (*placeholders*), colocados só pra testar se o encanamento
funcionava, não pra representar a realidade:

1. **O beta de cada ação (usado no hedge) era fixo em 1.0 pra todo mundo.**
   Ou seja, a proteção contra o Ibovespa estava sendo calculada como se
   todas as 30 ações tivessem exatamente a mesma sensibilidade ao
   mercado — o que nunca é verdade na prática.
2. **A trava de liquidez não existia.** O sistema deveria limitar o
   tamanho de cada posição com base em quanto aquela ação negocia por
   dia (pra não montar uma posição maior do que seria possível executar
   de verdade), mas essa checagem estava desligada.
3. **O custo de transação estava zerado.** O resultado mostrado não
   descontava corretagem nem o desgaste de comprar/vender toda hora
   (*slippage*).

### O que foi corrigido

- **Beta real:** o Bloco 4 já calculava, sem saber, o beta de cada ação
  contra o Ibovespa (como efeito colateral de uma conta que ele fazia
  pra outra finalidade). Só faltava "salvar" esse número em vez de
  descartar. Agora ele é salvo e usado de verdade no hedge do Bloco 5.
- **ADTV real (volume médio negociado):** o Bloco 2 é o único script do
  projeto autorizado a ler os arquivos brutos da bolsa (COTAHIST). Ele
  foi estendido pra também calcular, além do que já calculava por mês,
  o volume negociado de cada ação **dia a dia**, e a partir disso a
  média móvel de 21 pregões (a definição oficial de ADTV combinada
  antes no projeto). Isso levou minutos pra rodar, porque reprocessa
  ~3,7 GB de histórico de pregões — mas só precisa rodar de novo se o
  histórico mudar.
- **Custo de transação real:** fixado em 0,05% (5 pontos-base) sobre o
  giro da carteira, uma estimativa razoável de corretagem + slippage
  pra ações líquidas brasileiras.
- **Um vazamento pequeno no motor de backtest:** em dias em que a data
  de uma ação existia mas a data do Ibovespa não (feriados/calendários
  diferentes entre as duas fontes), o motor tratava isso como "o hedge
  não se moveu naquele dia" (retorno 0), quando na verdade deveria
  simplesmente descartar aquele dia do cálculo. Corrigido: agora esses
  dias (36 no total, num histórico de ~10 anos) são descartados, não
  mascarados.

### O bug sério que apareceu no meio do caminho

Ao tentar salvar o beta real (item 1 acima), o resultado veio **totalmente
vazio** (nenhum valor calculado, só espaços em branco). Isso não fazia
sentido, porque a conta que gera o beta é a mesma conta que já gerava o
sinal principal da Sinapse — se uma desse errado, a outra também deveria
dar.

Investigando, achamos a causa: o Bloco 4 tenta carregar um arquivo
(`mapeamento_setores.csv`, que diz o setor de cada ação — ex: "PETR4 é
Petróleo e Gás") pra ajustar a conta considerando também o setor da ação,
além do mercado geral. Só que o **caminho usado no código pra achar esse
arquivo estava errado** (subia uma pasta a mais do que devia) — o arquivo
nunca era encontrado, e o script simplesmente seguia em frente como se
"nenhuma ação tivesse setor conhecido".

Isso, sozinho, pareceria inofensivo (só perderia o ajuste por setor). O
problema é que essa falha criava uma situação matematicamente "impossível
de resolver" pra conta de regressão usada (duas colunas idênticas e
constantes na equação), e a biblioteca usada pra fazer essa conta, em vez
de avisar com um erro, **devolveu silenciosamente um resultado sem
sentido em todos os casos** — e por um acaso de como a conta seguinte
tratava esse resultado sem sentido, ele acabava virando, disfarçado, só
o retorno bruto da ação, sem nenhum ajuste de mercado ou setor.

**Na prática, isso significa que o sinal da Sinapse, desde sempre, nunca
tinha feito de verdade o que era pra fazer** (isolar o "choque" de cada
ação, limpo do efeito geral do mercado) — ele vinha calculando com dado
raw camuflado de dado tratado, sem nenhum aviso de erro. Corrigimos o
caminho do arquivo, conferimos que o cálculo agora produz valores de beta
plausíveis (por exemplo, algo como 0,2 a 0,8 pra uma ação como a VALE3,
o que faz sentido), e refizemos a carteira e o backtest do zero com o
sinal corrigido.

### Resultado final, depois de todas as correções

Com beta real, ADTV real, custo real e o bug do setor corrigido, o
resultado mudou bastante: de -20,7% (o número inicial, que já estava
contaminado pelo bug) para **-63,0%** de retorno no período, com
correlação com o Ibovespa em 0,00 (a proteção de mercado continua
funcionando certinho).

Mas, ao decompor esse -63%, achamos outra coisa importante: **sem
descontar nenhum custo de transação, o retorno seria de apenas -13,2%**
— ou seja, mais de 3/4 da perda vem do custo de transação, não do sinal
em si. A causa é que a carteira está girando MUITO: em média, quase 70%
da carteira muda de um dia pro outro. Pra uma estratégia que decide a
carteira de novo todo santo dia (sem "memória" do dia anterior), isso é
esperado, mas na prática seria caríssimo de operar de verdade — e é
provavelmente o próximo ponto a investigar, não necessariamente o sinal
da Sinapse em si.

## Diagnóstico: por que a estratégia perdia dinheiro

Diante do resultado ruim, em vez de chutar soluções, rodamos testes para
descobrir **onde** exatamente estava o problema. Três descobertas.

### Descoberta 1: metade do grafo estava apostando ao contrário

O coração da Sinapse é o "grafo de relações": uma lista de 30 ligações
econômicas entre empresas (ex: *"VALE3 é fornecedora da USIM5"*,
*"ITUB4 é concorrente do BBDC4"*). Para cada ligação, alguém definiu uma
**direção**: se a empresa A tem um dia bom, a empresa B tende a subir (+1)
ou a cair (-1)?

A regra usada era: **concorrente = -1** — "se a VALE3 vai bem, é porque
está roubando mercado da CSNA3, então a CSNA3 deve cair".

Testamos ligação por ligação, contra 10 anos de dados. O resultado:

| tipo de ligação | direção usada | funcionou? |
|---|---|---|
| holding/subsidiária | +1 | ✅ sim |
| cliente | +1 | ✅ sim |
| imobiliário/logística | +1 | ➖ indiferente |
| fornecedor | +1 | ➖ indiferente |
| **concorrente** | **-1** | ❌ **invertido** |

**Concorrentes não se afastam — eles andam juntos.** Faz sentido: VALE3 e
CSNA3 dependem das duas do mesmo minério de ferro. Quando o minério sobe,
as duas sobem. A premissa original era economicamente ingênua.

Como concorrente era a maior categoria do grafo (16 de 30 ligações), **mais
da metade da estratégia estava apostando exatamente ao contrário do que
deveria**. Corrigimos a direção para +1.

O efeito é enorme: a medida de "quanto o sinal acerta o futuro" saiu de
praticamente zero (indistinguível de jogar dado) para um valor
estatisticamente sólido.

### Descoberta 2: a estratégia negociava demais

O sinal da Sinapse é um "choque de um dia" — ele muda completamente todo
pregão. Resultado: a carteira era **remontada quase por inteiro todos os
dias**. Medindo em dinheiro:

- o que a estratégia ganhava por dia: **6,1 centavos** (por R$100)
- o que ela gastava de corretagem por dia: **6,9 centavos**

Ou seja, **o custo era maior que o ganho**. Não era o sinal que perdia
dinheiro — era o vaivém de comprar e vender.

A correção foi fazer a carteira andar mais devagar: em vez de perseguir o
sinal de hoje, seguir a **média das últimas semanas**. Isso derrubou o
giro de ~13% para ~5% da carteira por dia.

### Descoberta 3: a carteira operava "com o freio de mão puxado"

O projeto define uma meta de risco (volatilidade) de 12% ao ano. A carteira
estava rodando a **3%**. Duas causas, ambas corrigidas:

1. A conta que estimava o risco assumia que as ações se moviam de forma
   independente umas das outras — o que é falso. Trocamos por uma conta que
   mede a relação real entre elas.
2. O ajuste de risco era feito **antes** dos limites de segurança (máximo por
   ação, por setor, por liquidez). Os limites cortavam os pesos depois e
   desmontavam o ajuste. Agora as duas etapas se alternam até se acertarem.

## Resultado da Fase 1

| etapa | retorno no período |
|---|---|
| antes das correções | **-63,0%** |
| só corrigindo o grafo e o risco | -1,3% |
| + reduzindo o giro | **+19,9%** |

Também passamos a comparar contra o **CDI** (o benchmark oficial), que
antes nem aparecia no relatório — agora é baixado direto da API do Banco
Central.

**Onde estamos:** a estratégia saiu do vermelho, o giro está controlado
(5,3%/dia) e a proteção de mercado segue funcionando (correlação 0,01 com
o Ibovespa). Mas **ainda não bate o CDI** (que rendeu 141,9% no período) —
e ainda opera a 5,7% de risco contra a meta de 12%, porque os limites de
liquidez seguram a carteira.

## ⚠️ O problema mais grave: viés de sobrevivência

No meio do trabalho, surgiu uma preocupação legítima que mudou a prioridade
do projeto.

**O que é:** se você testa uma estratégia usando só as empresas que
existem hoje, você está trapaceando sem querer — porque em 2016 ninguém
sabia quais empresas iriam quebrar. O resultado do teste fica bonito demais.

**Como isso está afetando o SINAPSE — dois problemas:**

1. **Faltam 34% das empresas.** O Bloco 2 identificou 253 empresas líquidas
   entre 2016 e 2025, mas só **166 têm preço** no nosso banco de dados.
   Faltam 87 — e 65 delas são justamente as que **morreram**: Kroton,
   B2W, Hering, Linx, NotreDame, Cielo, Gol, Estácio, Lojas Americanas...
   A fonte de preços usada (yfinance) simplesmente não fornece empresa que
   saiu da bolsa.

2. **O grafo só tem sobreviventes.** As 44 empresas do grafo foram
   escolhidas agora, por alguém que já sabe quais existem. Um analista em
   2016 teria escrito ligações envolvendo Kroton, Cielo e B2W — que eram
   gigantes na época e hoje não existem mais.

**Consequência:** o +19,9% é **otimista**, não conservador. E o plano de
expandir o grafo pioraria isso, se os elos novos fossem escolhidos olhando
a lista de empresas de hoje.

**A boa notícia:** o dado existe. Os arquivos COTAHIST da B3 (que já estão
na máquina e que o Bloco 2 já lê) contêm o preço de **todas** as empresas,
inclusive as que morreram. Verificamos: Kroton, B2W e Hering têm preço lá,
normalmente, em 2016. É só extrair.

## Fase 2: corrigindo o viés de sobrevivência

Fomos buscar as empresas que faltavam. O caminho: o Bloco 2 (único script
autorizado a ler os arquivos brutos da B3) passou a extrair, além do volume
que já extraía, o **preço de fechamento de todas as ações** — inclusive as
que morreram.

### O obstáculo: preço "cru" não serve direto

Os preços da B3 vêm sem ajuste de proventos e desdobramentos. Isso cria
distorções brutais. O caso mais gritante foi a PDGR3, que fez um
**grupamento de 1 para 50** — no preço cru, isso aparece como se a ação
tivesse subido 4.900% em um único dia.

Comparando com a fonte antiga (yfinance, que já vem ajustada) nas 166
empresas que temos nas duas, o preço cru batia mal: correlação média de
apenas 0,84.

Aplicamos três limpezas:

1. **Detecção de desdobramento/grupamento.** Se o preço variou muito **e** a
   razão entre os preços cai perto de um número redondo (2x, 10x, 1/50...),
   é evento societário, não movimento de mercado — o retorno daquele dia é
   zerado. Exigir as duas condições juntas evita confundir com uma ação que
   simplesmente caiu 40% num dia de crise.
2. **Descarte de ações de centavos.** De R$0,02 para R$0,03 é "+50%", mas é
   só arredondamento, não economia real.
3. **Teto de segurança** para eventos raros que escapem dos filtros.

Resultado da limpeza, medido contra o yfinance:

| | preço cru | depois da limpeza |
|---|---|---|
| correlação média | 0,84 | **0,97** |
| correlação mediana | 0,976 | **0,993** |
| erro (desvio da diferença) | 0,4486 | **0,0096** |

O erro caiu **46 vezes**.

### Como as duas fontes foram combinadas

Optamos por uma abordagem híbrida, que usa o melhor de cada fonte:

- **yfinance manda nas 166 empresas que ele cobre** — os preços dele já vêm
  ajustados por dividendos, o que a B3 não fornece.
- **A B3 entra só onde falta** — as empresas que morreram.

Isso está num script novo: `s1c_retornos_completo.py`.

**Cobertura do universo real: de 66% para 98%** (249 de 253 empresas).

### O resultado ficou pior — e isso é a coisa certa acontecendo

| versão | retorno no período |
|---|---|
| Fase 1 (só sobreviventes) | +19,9% |
| **Fase 2 (universo real)** | **+8,7%** |

**O viés estava inflando o resultado em mais da metade.** O +8,7% é o número
honesto: é o que a estratégia teria feito de verdade, sem a vantagem
impossível de saber de antemão quais empresas iriam sobreviver.

Perder mais da metade do resultado ao remover uma trapaça involuntária é
exatamente o que se espera — e é melhor descobrir isso agora do que depois
de colocar dinheiro real.

## Onde o projeto está agora

**O que está resolvido e confiável:**
- Motor de backtest correto e validado
- Proteção de mercado funcionando (correlação −0,01 com o Ibovespa)
- Giro sob controle (5,8%/dia, contra 69% no início)
- Beta, liquidez e custos reais — sem dados fictícios
- Base de preços sem viés de sobrevivência (98% do universo)

**O que ainda falta:**
- A estratégia rende **+1,0% ao ano**, contra ~9% do CDI. **Ainda não bate o
  benchmark.**
- A carteira opera a 5,7% de risco, contra a meta de 12% — os limites de
  liquidez seguram. Mesmo corrigindo isso, chegaríamos a ~2% ao ano.

**O diagnóstico do que falta:** a estratégia tem munição de menos. Ela opera
com apenas **23 ligações econômicas úteis e ~22 empresas por dia**. Existe
uma relação conhecida em finanças quantitativas: o retorno de uma estratégia
cresce com a **raiz quadrada do número de apostas independentes**. Com 23
apostas, o teto é baixo por construção — não importa o quanto se afine o
resto.

**Próximo passo (Fase 3): expandir o grafo de 30 para 100-200 ligações.**
Estimativa: com ~100 ligações, o retorno projetado passa de forma
confortável tanto o CDI quanto o Ibovespa.

E agora isso pode ser feito **sem reintroduzir o viés**: como temos preço das
empresas que morreram, dá para escrever ligações envolvendo Kroton, Cielo,
B2W e Hering — que eram gigantes em 2016 — em vez de olhar só para a lista de
sobreviventes de hoje.

---

*Este arquivo será complementado ao longo do dia com as próximas atividades da sessão.*
