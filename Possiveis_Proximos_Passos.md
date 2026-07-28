# Possíveis Próximos Passos: Expansão da Tese (Parte 2)

Este documento contém os resultados de um *brainstorming* sobre como podemos evoluir a estratégia no futuro. O foco aqui é tirar proveito não apenas dos movimentos idiossincráticos das empresas ("Choque Limpo"), mas também da forma lenta como os movimentos sistêmicos e macroeconômicos do mercado se propagam pela rede da economia real.

Nenhuma dessas ideias foi implementada no momento, elas servem como um banco de propostas para a Parte 2 da nossa tese do Desafio Quant.

---

## Ideia 1: Beta Timing via "Termômetro da Rede" (Market Timing)

**A Ideia Básica:**
Atualmente, definimos que a carteira seria 100% "Beta-Neutra", fazendo hedge no Ibovespa para isolar completamente a estratégia das altas e baixas da Bolsa.

**A Expansão:**
E se a nossa rede for um **termômetro antecedente** da economia real? 
Se as empresas fornecedoras gigantes começam a repassar movimentos macroeconômicos positivos para o restante da cadeia, a rede inteira da Sinapse vai começar a registrar choques. Em vez de sermos 100% Beta-Neutro cegamente, podemos criar um "Beta Dinâmico":
- Se a rede indica que a economia real está recebendo fortes impulsos (sinais positivos se propagando), o algoritmo **tira o pé do Hedge** e deixa a carteira com um Beta positivo (ex: 0.5) para surfar a alta da bolsa antes dos índices tradicionais perceberem.
- Se a rede aponta que os repasses são negativos e há uma retração na economia real, o algoritmo zera ou até torna o Beta negativo para proteger o fundo.

---

## Ideia 2: Propagação de Choques Sistêmicos (Atraso Macro)

**A Ideia Básica:**
O mercado precifica grandes eventos macroeconômicos (inflação, juros, PIB) nas gigantes da Bolsa (Petrobras, Itaú, Vale) no milissegundo em que a notícia sai. Mas, quanto tempo leva para uma alta brutal na taxa de juros ser precificada no balanço de uma empresa menor de varejo no fim da cadeia de crédito? A hipótese é que existe um claro atraso na digestão sistêmica.

**A Expansão:**
Além do "Choque Limpo", o algoritmo passaria a medir o **Choque de Fatores de Mercado**. Se o setor bancário salta 5% em um dia por causa da curva de juros, nós não operamos os bancos (pois a notícia já está no preço deles). Em vez disso, o algoritmo busca as empresas do nosso grafo que são altamente dependentes dos bancos e opera o impacto que esse movimento de mercado causará nelas nos dias e semanas seguintes. O lucro vem do atraso informacional da digestão do cenário macro.

---

## Ideia 3: O "Smart BAB" (BAB turbinado pela Sinapse)

**A Ideia Básica:**
Na tese original do Cérbero Adaptado (BAB - Betting Against Beta), a regra é matemática e cega: comprar ações de baixo risco (Baixo Beta) e vender ações de alto risco (Alto Beta) para extrair o prêmio de risco estrutural da restrição de alavancagem.

**A Expansão:**
Nós podemos usar os sinais capturados pela rede da Sinapse para atuar como um **filtro inteligente** para o BAB.
- Em vez de comprar *qualquer* ação de Baixo Beta, nós compramos **apenas** as ações de Baixo Beta que também estejam no lado recebedor de fluxos positivos na rede da Sinapse.
- Em vez de vender a descoberto *qualquer* ação de Alto Beta, nós vendemos **apenas** aquelas que a Sinapse acusa estarem recebendo um fluxo informacional negativo no Grafo.

Isso une a ineficiência do prêmio de risco estrutural com a ineficiência de propagação de informação de rede, criando uma sobreposição de teses extremamente sólida para justificar a adição de complexidade para a banca avaliadora.
