# Funcionamento da Estratégia e Tecnicidades: SINAPSE + ECO

Este documento é um guia passo a passo, escrito de forma extremamente didática, para você entender **toda a lógica financeira, matemática e sequencial** por trás da nossa estratégia. Vamos desmistificar o "economês" e o "quantspeak" (jargões de fundos quantitativos).

---

## 1. Universo e Preços (O Início de Tudo)
Imagine que a Bolsa de Valores (B3) é um supermercado gigante com milhares de produtos (ações, fundos, ETFs). 
Nós não podemos olhar para todos os produtos. Alguns são vendidos apenas uma vez por mês e seus preços são irreais. 
- **O Universo:** Nós pegamos o histórico da bolsa (COTAHIST) e filtramos apenas as **100 ações mais negociadas (mais líquidas)**. Retiramos fundos imobiliários e recibos gringos (BDRs). Esse é o nosso "Universo Point-in-Time" (um retrato fiel do que era negociável em cada mês do passado, sem olhar para o futuro).
- **Preços Ajustados:** Uma ação custa R$10. No dia seguinte a empresa distribui R$1 de dividendo. O preço da ação na tela cai para R$9, mas o investidor não perdeu dinheiro (ele tem R$9 em ação + R$1 na conta). Para os nossos cálculos matemáticos não acharem que a ação "caiu" 10%, nós usamos "Preços Ajustados", que somam esses eventos na série histórica.

---

## 2. O Grafo e o Choque Limpo (O Gatilho)
A nossa tese é que empresas estão conectadas na economia real (ex: a VALE vende minério, a GERDAU compra minério). Se acontece algo com a VALE, em breve vai sobrar para a GERDAU. O mercado financeiro é lento para processar isso, e nós vamos lucrar com esse "atraso".

Mas aqui entra o pulo do gato: **O Choque Limpo**.
Se o mercado inteiro cair porque estourou uma guerra, a VALE vai cair. A GERDAU também vai cair. Isso não é informação útil, é apenas o mercado caindo. 
Nós queremos descobrir se a VALE caiu por um motivo **único e exclusivo dela** (ex: uma mina desabou).
Para isso, fazemos uma regressão estatística (matemática que tira o peso do Ibovespa e do Setor no retorno da ação). O que sobra é o "Choque Limpo" (o que a ação se moveu puramente por conta própria).

---

## 3. O Z-Score (A Padronização)
Temos 100 ações. Algumas oscilam 1% ao dia, outras oscilam 5% ao dia. Como comparar bananas com maçãs para saber qual ação tomou um choque realmente gigante e fora do comum?
**O que é o Z-Score?**
Na estatística, o Z-Score é uma forma de medir "quantos passos de distância" um evento está do normal. 
- Se uma ação conservadora que quase não se mexe cai 2%, isso é raríssimo (Z-Score alto, tipo -3).
- Se uma ação super volátil cai 2%, isso é terça-feira normal (Z-Score baixo, tipo -0.5).
Nós calculamos o Z-Score para criar um **Ranking Padronizado** diário. Nós pegamos os maiores Z-Scores para definir em quem vamos apostar.

---

## 4. Rankeamento, Lado (Long e Short) e Direção
Aqui é onde ganhamos o dinheiro.
Se a Empresa A (Vale) sofreu um choque limpo negativo (caiu) com Z-Score alto, e sabemos que ela impacta a Empresa B (Gerdau), nós apostamos que **a Empresa B VAI CAIR nos próximos dias**.

**O que é Comprar (Long) e Vender a Descoberto (Short)?**
- **Long (Comprado):** Você aposta que a ação vai **SUBIR**. Você compra por R$10 para vender por R$12. Lucro: R$2.
- **Short (Vendido a Descoberto):** Você aposta que a ação vai **CAIR**. Mas como vender algo que você não tem? Você "aluga" a ação de outra pessoa e vende na mesma hora por R$10 (você fica com R$10 na mão e uma dívida de 1 ação). Dias depois, a ação cai para R$8. Você compra a ação no mercado por R$8, devolve para o dono, e fica com R$2 no bolso. O lucro é o mesmo!

**A Lógica do Nosso Algoritmo:**
- Se o Z-Score indica que o choque em A foi **positivo** (A subiu muito por mérito próprio), apostamos que B vai subir. Nós entramos **LONG** em B.
- Se o Z-Score indica que o choque em A foi **negativo** (A caiu muito por falha própria), apostamos que B vai cair. Nós entramos **SHORT** em B.

**A Importância da Magnitude (O Tamanho do Z-Score):**
Enquanto o sinal (+ ou -) define se vamos comprar ou vender a descoberto, a **magnitude** do Z-Score define o **tamanho da nossa aposta**.
- Um Z-Score pequeno (ex: +0.5) significa que a IA está moderadamente confiante. O robô aposta uma fatia pequena do fundo.
- Um Z-Score grande (ex: +3.0) é um grito da IA de que uma anomalia enorme aconteceu. O robô aposta o máximo de dinheiro permitido (até bater na nossa trava de segurança de 5%).

**Na Prática (O Ciclo de Vida de uma Aposta):**
- **Início do Mês:** A IA nos dá o Z-Score. No primeiro dia útil, nós compramos (Long) ou alugamos/vendemos (Short) as ações escolhidas. Nós **não fazemos day trade**; não compramos e vendemos no mesmo dia.
- **Durante o Mês:** Ficamos parados na posição, apenas torcendo para as ações Long subirem e as Short caírem.
- **Fim do Mês:** A IA recalcula tudo. Se a ação ainda for boa, mantemos ela. Se não for mais, vendemos (ou compramos de volta no caso do Short) e colocamos o lucro/prejuízo no bolso para recomeçar o ciclo com novas ações.

**Quantas ações entram na carteira todo mês?**
O número não é fixo (ex: "sempre 10 ações"). Ele é **totalmente dinâmico** e depende da realidade:
- **A Oportunidade:** Se a IA leu 10 anos de CVM e encontrou 45 vazamentos/dependências fortes em um mês agitado, nós teremos até 45 ações na carteira. Se o mês foi silencioso e ela encontrou 12, teremos apenas 12.
- **A Faca da Liquidez:** Mesmo que a IA encontre 50 ações com ótimas notas, o nosso gerenciamento de risco tem a palavra final. Se uma ação for tão pequena que negocie muito pouco dinheiro por dia na bolsa, o robô percebe o perigo (risco de distorcer o preço na hora de comprar) e trava a aposta nela em quase 0%. Ou seja, a empresa pode acabar de fora da carteira por ser muito ilíquida.
Nós operamos apenas as oportunidades que de fato aparecerem, desde que sejam seguras de negociar.

---

## 5. Vol-Targeting (A Mira de Volatilidade) e Corte de Pesos
O mercado tem meses calmos e meses malucos (como março de 2020, na pandemia). Investidores odeiam surpresas. Eles preferem um fundo que oscile de forma constante e previsível.

**O que é Volatilidade Alvo de 12% Anualizada?**
Volatilidade é a medida de quão bruscamente o seu dinheiro sobe e desce. 12% significa que, em um ano normal, esperamos que o fundo varie para cima ou para baixo dentro de uma banda de 12%. É um risco moderado (nem poupança, nem cassino).

**O que é "cortar os pesos pela metade para bater nos 12%"?**
Imagina que você está dirigindo um carro. O "Vol-Targeting" é como um piloto automático que quer manter a turbulência do carro sempre igual.
- Se a estrada está lisa (mercado calmo, baixa volatilidade), você pode acelerar (aumentar o tamanho do dinheiro investido).
- Se a estrada começa a tremer (mercado em crise, volatilidade atual bateu 24%), o algoritmo automaticamente percebe o perigo e tira o pé do acelerador. Para voltar a turbulência de 24% para os 12% desejados, o código literalmente divide a quantidade de dinheiro investido por dois (corta 50%). Em vez de apostar R$100.000, passa a apostar R$50.000, até o mercado se acalmar. Isso impede o fundo de quebrar numa crise.

---

## 6. Travas Institucionais (Otimização e Gerenciamento de Risco)
Se deixarmos o computador solto, ele pode fazer burrices perigosas para buscar o máximo de lucro teórico. Nós colocamos rédeas ("Travas") no otimizador da carteira:

### A. Travado em 5% por empresa
Nunca colocamos mais do que 5% do dinheiro do fundo em uma única empresa. 
*Por quê?* Porque se a nossa IA errar miseravelmente ou o CEO da empresa for preso amanhã, o máximo que o fundo perde é 5%. O resto da carteira compensa. É a lei de ouro da diversificação.

### B. Exposição Bruta Setorial de 25%
**O que é Exposição Bruta?** É a soma de todo o dinheiro apostado (Long e Short), não importa a direção. Se você apostou 10% de Long na Petrobras e 10% de Short na Prio, sua exposição bruta no setor de Petróleo é 20%.
*Por quê travar em 25%?* Porque as empresas de um mesmo setor andam muito juntas. Se não travar, num mês em que o preço do Minério enlouquece, a IA pode querer colocar 80% do dinheiro do fundo em Gerdau, CSN, Vale, Usiminas. O fundo viraria um "fundo de mineração" por acidente. O limite obriga o robô a apostar em vários setores diferentes.

### C. Trava de Liquidez (Não ser um elefante em loja de cristais)
*O que é Volume Diário (ADTV - Average Daily Trading Volume)?* É quantos Reais de uma ação mudam de mãos por dia na Bolsa.
Imagine que uma ação pequena negocie apenas R$ 1 Milhão por dia na B3. E imagine que nosso fundo de investimentos tenha R$ 100 Milhões totais na conta (o nosso "AUM - Assets Under Management").
Se o algoritmo resolver colocar os limites máximos e apostar 5% do fundo nessa ação (R$ 5 Milhões), nós tentaríamos comprar um valor 5 vezes maior que todo o volume diário da ação! O preço explodiria para cima e compraríamos caríssimo.
*A Trava:* O algoritmo é programado para que a nossa aposta financeira seja no máximo 10% do que a ação costuma negociar por dia (no caso, a gente só poderia apostar R$ 100 Mil) para não "estragar o preço" (o famoso slippage).

---

## 7. Beta Neutro e Hedge de Ibovespa
**O que é Beta?** 
Imagine que você tem uma frota de navios (nossa carteira de ações) e ótimos capitães que sempre encontram tesouros (nossa IA escolhendo ações). Porém, se vier um Tsunami (a Bolsa Brasileira desabar por uma crise), todos os navios vão afundar um pouco, por melhores que sejam. O "Beta" é o número que mede exatamente o tamanho do tsunami e o quanto ele balança os seus navios (é a sensibilidade da ação em relação ao Ibovespa).

Nós queremos lucrar com a genialidade da IA ("Alfa"), independente do tsunami acontecer ou não.

**Hedge de Ibovespa (Ser Beta Neutro):**
Para "zerar" esse risco de mercado, toda vez que nossos navios saem para o mar, o robô automaticamente vai a uma seguradora e **compra um seguro contra tsunamis** na proporção exata da frota. 
Na prática, o computador gera uma aposta sintética extra (uma nova coluna no sistema, o `IBOV_SYNTHETIC`). Se a bolsa brasileira despencar 10%, nossas ações vão sofrer, mas a gente ganha rios de dinheiro nessa posição de seguro do Ibovespa para compensar 100% da queda. Assim, nunca somos destruídos pelas loucuras da economia.

---

## 8. Duração e Rebalanceamento
Tudo isso acontece de forma cíclica.
A regra de ouro aqui é: **A escolha das empresas é mensal, mas o ajuste de risco é diário.**

- **A Escolha Mensal:** No último dia útil de cada mês, o motor olha para trás e soma os choques que aconteceram **ao longo do mês inteiro**. Com base no acumulado desses 30 dias, ele cria os rankings (Z-scores) e define a lista de compras e vendas. No primeiro dia do mês seguinte, a carteira antiga é desfeita e a nova carteira é montada (isso é o Rebalanceamento). 
- **O Ajuste Diário:** Os *nomes* das ações ficam estáticos na carteira durante o mês todo. Porém, a *quantidade de dinheiro* alocada nelas é ajustada todo santo dia. Isso acontece graças ao Vol-Targeting (nosso piloto automático). Se o mercado começa a ficar muito louco numa terça-feira, o robô automaticamente diminui o tamanho do cheque na quarta-feira para nos proteger.
