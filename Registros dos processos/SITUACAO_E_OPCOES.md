# Situação, opções e caminhos — consolidado

> Documento único. Consolida as quatro rodadas de revisão (quant × 2, risco, custo/execução)
> e as verificações independentes. **Nada aqui foi executado.**
> Substitui a informação espalhada nos registros anteriores desta sessão.

---

# PARTE 1 — ONDE ESTAMOS

## 1.1 Os números oficiais de hoje

| | 10 anos | OOS 21–25 |
|---|---|---|
| Alfa líquido (a 5 bps) | +2,83%/ano | +3,91%/ano |
| Sharpe | 0,36 | 0,50 |
| Volatilidade | 7,84% (meta 12%) | 7,86% |
| Drawdown máximo | −19,6% | |
| Giro | 10,8%/dia | 9,2%/dia |
| Retorno do fundo (CDI + alfa) | +210,1% | |
| CDI | +141,9% | |

Como perfil de fundo, **CDI + 2,83% com 7,8% de vol está dentro da faixa de um long-short neutro
brasileiro**. O problema não é o nível — é que ele não sobrevive a duas coisas.

## 1.2 Problema 1 — não é estatisticamente significante

```
Sharpe 0,361 × √9,8 anos  =  t = 1,13
IC 95% do Sharpe: [−0,27 ; +0,99]   →  inclui zero com folga
Deflated Sharpe (N=50 tentativas):   0,05
```

O IC tem t = 2,73 no período completo, mas **IC não é o que o cotista compra** — e o próprio
código já reconhece internamente que t alto em correlação transversal diária "não é prova de
edge econômico" (`s6_validacao_oos.py:185-188`).

**100% do P&L está em 3 anos:**

| período | acumulado | Sharpe |
|---|---|---|
| 2016–2022 (7 anos) | **−4,23%** | −0,04 |
| 2023–2025 (3 anos) | +33,84% | +1,38 |

A curva fica abaixo de 1,0 depois de sete anos. E 2022 sozinho foi −13,3%.

**Um momentum trivial de 21 dias bate a estratégia:** IC OOS +0,0232 (t=2,81) contra +0,0091
(t=1,72). Três linhas de código, sem grafo nenhum.

E após controlar por momentum/reversão/low-vol, **não sobra alfa significante** (t = 0,89).

## 1.3 Problema 2 — o custo real mata

O modelo atual usa 5 bps flat. Medido para este book: **20,3 bps**.

| cenário | alfa/ano | Sharpe |
|---|---|---|
| 5 bps (premissa atual) | +2,83% | 0,36 |
| spread + emolumentos por faixa | +1,24% | 0,16 |
| + impacto de mercado | −1,33% | −0,17 |
| **+ aluguel BTC** | **−2,28%** | **−0,29** |

Causa: **73% do giro está abaixo de R$150MM de ADTV** — 5 bps é número de large cap aplicado a
um book mid cap.

**E o fato estrutural que fecha a porta:** o alfa por unidade de giro é **~15 bps e constante**.
Testado em suavização de 1 a 34 dias e em banda de não-negociação de 0,25% a 2,0% — o breakeven
fica travado entre 11,4 e 16,3 bps. **Não existe ponto de operação em que a estratégia sobreviva
a 20 bps.** Suavizar mais corta custo e alfa na mesma proporção.

## 1.4 Os bugs encontrados

| # | bug | onde | impacto medido |
|---|---|---|---|
| 1 | Resíduo vira **retorno bruto** sem 252 obs | `s4:233` | **13,4% das células**, 100% de 2016. **IC IS: t 2,14 → 1,39** |
| 2 | Beta do hedge é **parcial**, não de mercado | `s4:226-236` | mediana 0,28, **24% negativos**. Hedge com ~1/3 do beta correto |
| 3 | Beta NaN vira zero no hedge | `s5:209` | **12,8% das posições** sem hedge |
| 4 | `clip` com limite NaN não corta | `s5:176-178` | 353 posições escapam da trava |
| 5 | `s11` duplica os 28 elos históricos | `s11:189-192` | os "86 elos" são 58 com 28 dobrados |

> **O #1 é o mais grave conceitualmente:** o `t = 2,14` in-sample que sustenta o protocolo P1
> inteiro (e a conclusão do `s13`) **é artefato do bug**. Corrigido, o IS não é significante.

## 1.5 Controles de risco faltantes

| | medido |
|---|---|
| Exposição líquida (long − short) | desvio 14,7%, faixa **[−38,5% ; +34,9%]** — **sem trava** |
| Exposição setorial **líquida** | até **24,9%**; 86,2% dos dias com algum setor acima de ±10% — a trava atual mede `Σ\|w\|`, grandeza errada |
| Vol de 12% | **estourada**: 18,12% em maio/2020 (2,62% dos dias acima de 12%) |
| Concentração | **79% do P&L bruto em 5 nomes**; AZUL4 sozinha = 19% |
| Capacidade | R$100M → Sharpe 0,41; R$300M → 0,21; R$1bi → 0,12 |

## 1.6 O que é genuinamente bom (verificado)

1. **Pré-registro provável no git** — `PARAMETROS.md` em 21/07, primeiro backtest em 29/07.
2. **O grafo bate placebo** — reembaralhando os gatilhos 300 vezes, inclusive restrito ao mesmo
   setor: **p ≤ 0,015**, rodado com o código de produção.
3. **`forca` pode ser deletada** — todas em 1,0 e direções em +1 dá IC **melhor** (+0,0125,
   t=3,23). Elimina 116 parâmetros subjetivos.
4. **Trava de liquidez com 0 violações** em 93.022 posições.
5. **Breadth reconciliando Grinold sem parâmetro livre** — previsto 0,49 / realizado 0,50.
6. **Stress: a estratégia protegeu de verdade** — COVID −5,6% (IBOV −29,6%), Joesley +1,4%
   (IBOV −8,8%). Hoje **invisível** no relatório.
7. **Hipóteses refutadas preservadas no código**, não apagadas.

---

# PARTE 2 — O QUE JÁ FOI TESTADO E FALHOU

Registro para não retestar.

| ideia | resultado | como foi testado |
|---|---|---|
| **Controle por subsetor** ("Caminho 2") | **rejeitado** — baseline vence os 7 limiares no IS | protocolo IS/OOS completo (`s13`) |
| **Grafo mecânico substituindo o manual** (horizonte 1d) | melhor em todos os eixos, **mas ainda Sharpe 0,41 (t=1,28)** | K escolhido só no IS, congelado |
| **Regra + grafo manual combinados** | **pior** que a regra sozinha (Sharpe OOS −0,03) | idem |
| **Suavização maior** (até 34d) | breakeven não se move | varredura completa |
| **Banda de não-negociação** (0,25% a 2,0%) | breakeven não se move | varredura completa |
| **Filtro de liquidez nos satélites** | o alfa sai junto com o custo | ADTV>20MM e >50MM |
| **Corte de liquidez** (a "pista sobrevivente") | **não replica** — era quebra de regime, 1 de 5 testes | varredura de pisos |
| **Elos bidirecionais** (P7) | rejeitado — ganho de Sharpe dentro do ruído | sessão 04/08 |
| **Reordenar o loop de vol** (P4/`s9`) | as 3 variantes pioraram | sessão 04/08 |

**Conclusão da Parte 2:** o sinal da Sinapse **no horizonte de 1 dia** não tem edge, e nenhum
ajuste de execução, filtro ou construção o recupera.

---

# PARTE 3 — O QUE FOI ENCONTRADO QUE FUNCIONA

Três achados **mecânicos** (sem nenhuma escolha subjetiva, logo sem risco de viés) e um achado
**ambíguo** que exige decisão do time.

---

## 3.1 Expandir o universo de choques

### Como está hoje

O Bloco 4 calcula o "choque limpo" de cada ação assim:

```
retorno_da_acao = α + β₁·Ibovespa + β₂·índice_do_setor + RESÍDUO
                                                          ↑
                                            isto é o "choque limpo"
```

Mas **ele só faz essa conta para 73 ações** — as que aparecem no grafo. A restrição está numa
linha, `tickers_alvo` em `s4_sinapse_sinal.py:125`:

```python
tickers_do_grafo = set(df_grafo['empresa_A']) | set(df_grafo['empresa_B'])
df_choques, df_betas = calcular_choque_limpo(..., tickers_alvo=tickers_do_grafo)
```

**Por que essa restrição existe:** foi uma otimização de performance, documentada em
`Correcoes1.md` §2.5. Rodar 543 regressões rolling de 252 dias quando você só precisa de 44 era
desperdício — levava minutos.

### Qual é a proposta

**Tirar a restrição.** Calcular o choque limpo de todas as ~249 ações que têm preço.

### Por que isso importa

Porque **um gatilho só pode ser gatilho se tiver choque calculado.** Hoje, mesmo que você
quisesse usar a Cyrela como gatilho de construção civil ou a Fleury como gatilho de saúde, não
dá — elas não têm choque. O grafo está preso a um pool de 73 nomes.

É como ter um mapa de 249 cidades mas só ter medido a temperatura em 73 delas: você não consegue
prever nada sobre as outras 176, por melhor que seja o seu modelo.

### O que muda na prática

| | hoje | depois |
|---|---|---|
| tickers com choque calculado | 73 | **249** |
| nomes na carteira por dia | 46 | **127** |
| **apostas independentes (breadth)** | 22,5 | **33,7** |

Aqueles **33,7** passam do limiar de **~31** que o `s12` calculou como necessário para a trava de
5% por nome deixar de bloquear a meta de vol de 12%. Ou seja: **isto sozinho resolve o gap de
volatilidade** que P4 tentou resolver por três caminhos diferentes e falhou.

### E o argumento de performance?

**Sumiu.** O protótipo reescreveu a regressão rolling de forma vetorizada e ela reproduz a
produção **exatamente** (correlação 1,000000, erro 2,6e-13) rodando em **1,5 segundo** em vez de
minutos. A restrição virou desnecessária.

### Risco de viés: zero

Não há escolha nenhuma envolvida. Ou você calcula o choque de todo mundo, ou de um subconjunto.
Calcular de todo mundo é estritamente mais informação, sem decisão humana.

---

## 3.2 A regra de gatilhos e satélites — e como ela se conecta ao 3.1

> **Sua leitura está certa, e é importante deixar explícito: 3.1 e a regra são coisas
> DIFERENTES que só funcionam bem JUNTAS.**

| | o que é |
|---|---|
| **3.1 (universo)** | *calcular* o choque de 249 ações em vez de 73 |
| **a regra** | *decidir quem informa quem*, mecanicamente, por liquidez dentro do ramo |

Uma é o **insumo**, a outra é a **decisão**. Separadamente:

- **Universo expandido sozinho:** você calcula 249 choques, mas o grafo manual continua usando só
  28 gatilhos. Os outros 221 choques ficam sem uso.
- **Regra sozinha (com 73 choques):** a regra só pode escolher gatilhos entre os 73 que têm
  choque. Fica limitada aos ramos que já estão no grafo.
- **As duas juntas:** a regra escolhe gatilhos em **todos** os 22 ramos, inclusive saúde,
  saneamento, tecnologia, logística e seguros — que hoje não têm gatilho nenhum.

### Como a regra funciona, passo a passo

```
Uma vez por mês, para cada ramo (subsetor):
   1. lista as ações daquele ramo que estavam negociando naquele mês
   2. ordena pelo dinheiro negociado nos 21 pregões ANTERIORES (ADTV)
   3. as K mais líquidas viram GATILHOS
   4. as demais viram SATÉLITES
   5. cria um elo de cada gatilho para cada satélite, forca = 1, direcao = +1
```

**Exemplo — ramo "Siderurgia", numa data qualquer de 2018:**

```
ordena por volume negociado nos 21 dias anteriores:
   GGBR4   R$ 180 M  ─┐
   CSNA3   R$ 120 M  ─┴─ K=2, viram GATILHOS
   USIM5   R$  95 M  ─┐
   GOAU4   R$  40 M   ├─ viram SATÉLITES
   GGBR3   R$   8 M  ─┘

elos gerados (2 × 3 = 6):
   GGBR4 → USIM5      CSNA3 → USIM5
   GGBR4 → GOAU4      CSNA3 → GOAU4
   GGBR4 → GGBR3      CSNA3 → GGBR3
```

Seis elos de siderurgia, sem ninguém opinar. Hoje o grafo inteiro tem **zero** elos entre
siderúrgicas (só `VALE3→CSNA3`, e a Vale é mineração).

### A lógica econômica

> Sai uma notícia que afeta o **ramo inteiro** (preço do minério, juro, safra). A ação líquida
> tem 20 analistas e bilhões negociando — precifica em minutos. A ilíquida tem quase ninguém
> olhando — leva dias. O choque de hoje na grande é uma **prévia** do que a pequena fará depois.

Não é "concorrência" no sentido de soma-zero. É **exposição compartilhada com velocidades
diferentes de precificação**. Tem literatura: Lo & MacKinlay (1990), Hou (2007).

E vocês já provaram a assimetria: o teste bidirecional (P7) mostrou que o sentido reverso é mais
fraco **nas 6 categorias, sem exceção**.

### Por que "mais líquido" não é opinião

| pergunta | tipo |
|---|---|
| *"A VALE é concorrente da CSN?"* | **opinião** — dá para discordar |
| *"A VALE negocia mais dinheiro por dia que a CSN?"* | **fato** — abre a tabela e lê |

A regra troca uma opinião por dois fatos: o ramo (que está no cadastro) e o volume (que está no
pregão). E o projeto **já calcula** esse volume — é o `adtv_diario.parquet` do Bloco 2.

### Como isso mata os vieses

| viés | como morre |
|---|---|
| **sobrevivência** | usa o universo do COTAHIST, que tem as empresas mortas. Em 2016 a Kroton estava lá e vira gatilho de educação automaticamente |
| **retrovisão** | só usa volume **passado**. Um analista em 2016 rodaria a mesma regra e teria o mesmo grafo |
| **escolher elo a dedo** | não há escolha — a regra gera **todos**, não os melhores |
| **comparações múltiplas** | um parâmetro só (o K), escolhido no IS e congelado |
| **grafo envelhecer** | ele se refaz sozinho todo mês. IPO novo entra; empresa que morre sai |

### O tipo de elo some

Todo elo que a regra gera é "mesmo ramo, o líquido informa o ilíquido" — `concorrente` por
construção, direção `+1`. **Um único tipo, zero classificação.**

Os tipos `cliente`, `fornecedor` e `holding_subsidiaria` exigem saber coisa que não está no
cadastro (que a Itaúsa controla o Itaú; que a Vibra compra da Petrobras). Esses **continuam
vindo do grafo manual**, como camada de aprofundamento:

| camada | origem | tamanho | papel |
|---|---|---|---|
| **base** | regra automática | ~220 elos | escala, cobre todos os ramos, sem viés |
| **overlay** | grafo manual | 21 elos | relações especiais que só humano sabe |

> ⚠️ **Ressalva medida:** no horizonte de 1 dia, a combinação regra + grafo manual foi **pior**
> que a regra sozinha (Sharpe OOS −0,03 vs +0,33). O grafo manual adicionou ruído e giro. Isso
> não invalida a camada overlay como ideia, mas significa que ela precisa provar seu valor, não
> ser assumida.

---

## 3.3 Neutralizar o sinal contra beta e setor

### O sintoma

Um book long-short de 127 nomes, com exposição bruta de 1,0, **deveria** ter ~3,5% de volatilidade
se as posições fossem razoavelmente independentes. O medido é **8,7%**.

Essa diferença não é concentração — é **exposição a fator**. A carteira está acidentalmente
comprada ou vendida em setores inteiros e em beta.

### Como está hoje

O Bloco 5 pega o z-score e usa direto como peso (`s5_portfolio_builder.py:39`):

```python
df_weights = df_zscore.copy()      # o sinal JÁ É o peso
```

> **Correção a um item anterior:** eu havia listado "peso ∝ z em vez de z/vol" como melhoria.
> Reli o código — **a produção já faz o certo**. Aquele achado era sobre alternativas testadas no
> protótipo, não uma mudança para produção. O item real é só a neutralização abaixo.

Depois disso, a carteira tenta **corrigir** a exposição de fator com duas ferramentas, ambas
depois do fato:

- hedge de beta (posição vendida em `IBOV_SYNTHETIC`) — **corrige só o beta de mercado**
- trava setorial de 25% — **corta** o excesso, mas não neutraliza

Resultado medido: exposição líquida chegando a **±38,5%** e setorial líquida a **24,9%**.

### Qual é a proposta

**Remover a exposição de fator do sinal, na origem, antes de virar peso.** Todo dia, na seção
transversal:

```
z_neutro = resíduo de   z ~ β + [dummies de setor]
```

Ou seja: regride o sinal contra o beta de cada ação e contra o setor a que ela pertence, e usa
**o que sobra**. O que sobra é, por construção, ortogonal a beta e a setor.

### Por que isso melhora o Sharpe

Não porque aumenta o retorno — **porque reduz o risco mantendo o retorno.**

| | antes | depois |
|---|---|---|
| volatilidade | 10,0% | **8,3%** |
| retorno | ~igual | ~igual |
| Sharpe | | **sobe** |

A exposição a setor e a beta é risco **que não é remunerado pela tese**. A Sinapse não tem
opinião sobre "petróleo vai subir" — ela tem opinião sobre "esta ação vai subir mais que aquela".
Carregar exposição setorial é carregar uma aposta que ninguém quis fazer.

### Dois efeitos colaterais bons

1. **A trava de 5% por nome deixa de morder.** Testado: 3% / 5% / 10% dão Sharpe 0,67 / 0,68 /
   0,69 — praticamente igual. Hoje ela morde em **76% dos dias**.
2. **O laço `vol-target ↔ travas` do `s5` fica desnecessário.** Aquele loop de 3 iterações que
   nunca converge (diagnóstico de P4) existe porque as travas derrubam a vol calibrada. Sem as
   travas mordendo, o problema some.

### Risco de viés: baixo

É uma operação mecânica (regressão transversal contra variáveis observáveis) sem parâmetro
escolhido. O único julgamento é *quais* fatores neutralizar, e beta + setor são a escolha padrão
e conservadora.

---

## 3.4 Walk-forward — e a sua pergunta sobre viés

### Como está hoje: IS/OOS único

```
2016 ──────── 2020  │  2021 ──────── 2025
  decide tudo aqui  │   mede UMA vez
```

**Problema:** você só tem uma medição honesta. E o projeto **já gastou** esse período várias
vezes ao longo das sessões.

### Como funciona o walk-forward

Em vez de um corte, uma **janela que rola**:

```
decide com 2016-2018  →  testa em 2019
decide com 2016-2019  →  testa em 2020
decide com 2016-2020  →  testa em 2021
decide com 2016-2021  →  testa em 2022
decide com 2016-2022  →  testa em 2023
decide com 2016-2023  →  testa em 2024
decide com 2016-2024  →  testa em 2025
                          ─────────────
                          7 anos de resultado, e CADA UM
                          foi medido com parâmetros que
                          não tinham visto aquele ano
```

Resultado medido: **Sharpe 0,589 (t=1,55), IC +0,0168 (t=4,25)**, 1.743 pregões.

**Vantagens sobre o IS/OOS único:**

1. **Não "gasta" período.** Você pode rodar de novo depois de corrigir um bug sem queimar nada.
2. **Usa 7 anos de teste em vez de 5.**
3. **É mais próximo da realidade.** É literalmente o que um gestor faz: recalibra com o que sabe,
   opera o mês seguinte, repete.
4. **Testa estabilidade.** Se a estratégia só funciona em 2 dos 7 anos, aparece.

### Sua pergunta: 100% out-of-sample significa sem viés?

**Não. Significa sem UM tipo de viés — o mais importante, mas não o único.**

| viés | walk-forward resolve? |
|---|---|
| **Look-ahead de parâmetro** (escolher janela olhando o resultado) | ✅ **sim, elimina** |
| **Sobrevivência** (só usar empresas que existem hoje) | ❌ não — resolvido separadamente pelo COTAHIST |
| **Look-ahead de execução** (negociar a preço que não conhecia) | ❌ não — é premissa do motor |
| **Seleção da própria estratégia** | ❌ **não** — você escolheu testar *esta* estratégia depois de já ter visto que ela mais ou menos funciona |
| **Comparações múltiplas acumuladas** | ❌ **não** — é o que o Deflated Sharpe mede |

O quarto e o quinto são os que sobram, e **por isso o Deflated Sharpe continua sendo obrigatório**
mesmo com walk-forward.

### Por que viés é inviável perante a banca do Itaú Asset

Duas razões, e a segunda é mais importante que a primeira.

**1. A banca sabe procurar.** Um avaliador de asset manager vê dezenas de backtests por ano.
Ele tem uma lista mental: *sobrevivência? look-ahead? quantas configurações testaram? o Sharpe é
significante? bate um fator simples?* Se encontrar um viés que vocês não declararam, **tudo o
mais que vocês disseram passa a ser suspeito** — inclusive as partes corretas. É assimétrico:
declarar um viés custa pouco; ser pego escondendo custa tudo.

**2. O propósito do exercício é este.** O trabalho de um quant não é achar o número mais alto —
é saber **quanto do número é real**. Um backtest enviesado com Sharpe 2,0 e um honesto com
Sharpe 0,6: o primeiro perde dinheiro de verdade, o segundo talvez não. A banca está avaliando se
vocês sabem a diferença.

> É por isso que eu recusei duas vezes ajustar parâmetro depois de ver o OOS, mesmo sabendo que o
> resultado ficaria pior. O valor do trabalho está inteiro na disciplina — é a única coisa que
> ainda pode ser perdida.

---

## 3.5 O achado ambíguo: momentum vs Sinapse

Este é o ponto que exige decisão do time, então vou destrinchar.

### O que é "momentum de preço" (mom252 / 12-1)

A estratégia mais simples que existe em finanças quantitativas:

> Olhe o retorno de cada ação nos últimos 12 meses (ignorando o mês mais recente).
> **Compre as que mais subiram, venda as que mais caíram.**

Só isso. Sem grafo, sem regressão, sem tese econômica, sem setor. Três linhas de código.

É documentada desde Jegadeesh & Titman (1993), replicada em dezenas de mercados, e **fundos já
exploram isso há 30 anos.**

### O que é a Sinapse

> Calcule o **choque limpo** de uma empresa-gatilho (o que sobra do retorno dela depois de tirar
> o mercado e o setor). Propague esse choque por um grafo de ligações econômicas.
> **Aposte que a empresa-satélite vai seguir.**

### O que o protótipo testou

A configuração que deu Sharpe 0,68 é: **50% momentum de preço + 50% "regramom"** — onde
"regramom" é a maquinaria da Sinapse, mas com o choque acumulado em 12 meses em vez de 1 dia.

### Semelhanças e diferenças

| | momentum de preço | Sinapse (regramom) |
|---|---|---|
| **de onde vem o sinal** | retorno passado **da própria ação** | choque de **outra empresa**, propagado |
| precisa de grafo? | não | sim |
| precisa de regressão? | não | sim (choque limpo) |
| horizonte | 12 meses | 12 meses (na versão nova) |
| tipo de sinal | transversal (rankeia e compra os melhores) | transversal (idem) |
| **é conhecido?** | **sim, há 30 anos** | não, é construção própria |
| **um fundo já explora?** | **sim, muitos** | não |

**Semelhança de fundo:** os dois são apostas de que **o passado recente informa o futuro
próximo**, e os dois operam no mesmo horizonte de ~12 meses. É por isso que eles se combinam bem
— e também por isso que é difícil separar um do outro.

### O problema

| | |
|---|---|
| Sharpe da combinação | **0,68** |
| Sharpe do momentum sozinho | ~0,60 |
| **Alfa incremental da Sinapse sobre o momentum** | **+1,52%/ano, t = 1,01** |

**t = 1,01 significa "não distinguível de zero".** A Sinapse melhora o número, mas não o
suficiente para se provar.

### O que isso significa na prática

> Se vocês apresentarem essa versão, a banca vai perguntar:
> *"Isso é uma estratégia de momentum com um grafo por cima. O grafo adiciona alguma coisa?"*
>
> E a resposta honesta é: **melhora o Sharpe de 0,60 para 0,68, mas não de forma estatisticamente
> significante.**

### Vantagens de adotar

- Sharpe 0,59 em walk-forward puro — **é um resultado apresentável**, contra 0,07 de hoje
- Resolve o gap de vol (breadth 34,8)
- Giro cai de 10,8% para 3,4%/dia — o custo deixa de matar
- O placebo **passa** no horizonte longo (p < 0,005), contra p = 0,164 em 1 dia

### Desvantagens de adotar

- **O motor é um fator conhecido.** Vocês estariam apresentando momentum com uma camada própria
  que não se prova
- Deflated Sharpe **não passa em nenhum cenário** (0,079 a 0,74; precisaria de 0,95)
- Bootstrap: **P(Sharpe < 0,63) = 41%** — "passar de 0,63" é cara ou coroa
- **2025 foi −6,67%**; o Sharpe rolante de 252 dias está negativo hoje
- Muda a tese do projeto em cima da hora

### Uma ressalva minha, que não vem do protótipo

Verifiquei de forma independente se trocar o horizonte melhora **o sinal da Sinapse no grafo de
produção**. Não melhora:

| sinal (grafo de produção, 73 tickers) | IC compl | t | IC IS | t | IC OOS | t |
|---|---|---|---|---|---|---|
| produção (choque 1d, suav 21d) | +0,0113 | 2,82 | +0,0130 | 2,36 | **+0,0097** | **1,65** |
| choque acumulado 12-1 | +0,0109 | 2,65 | +0,0159 | 2,90 | **+0,0065** | **1,08** |

Piora no OOS e o giro sobe. Os dois resultados não se contradizem — o protótipo usou grafo
mecânico sobre 249 tickers, e o motor dele é momentum. Mas **reforça a leitura de que o ganho
não vem da Sinapse.**

---

## 3.6 Resumo da Parte 3

| # | melhoria | risco de viés | ganho | vale em qual cenário? |
|---|---|---|---|---|
| 3.1 | Universo 73 → 249 | **zero** | breadth 22,5 → 33,7 | **todos** |
| 3.2 | Regra de gatilhos/satélites | **muito baixo** (1 parâmetro) | cobre todos os ramos, elimina 58 julgamentos | **todos** |
| 3.3 | Neutralizar beta + setor | **baixo** | vol 10,0% → 8,3% | **todos** |
| 3.4 | Walk-forward | **reduz viés** | número 100% OOS, não gasta período | **todos** |
| 3.5 | Horizonte longo (momentum) | **médio** — muda a tese | Sharpe 0,07 → 0,59 | só se o time aceitar |

**Os quatro primeiros são consenso: fazem sentido em qualquer decisão que vocês tomem.**
O quinto é a decisão de verdade.

---

# PARTE 4 — AS TRÊS OPÇÕES

## Opção A — Adotar a versão momentum

Implementa 3.1 + 3.2 + 3.3 + horizonte longo. Sharpe **0,59 em walk-forward puro**.

**A favor:** funciona; tem número apresentável; breadth resolve o gap de vol.
**Contra:** a banca vai perguntar *"então vocês construíram um fundo de momentum?"* — e a
resposta honesta é sim. O Deflated Sharpe não passa.

## Opção B — Ficar na tese Sinapse e apresentar o resultado nulo

**A favor:** íntegro; o método é genuinamente bom (§1.6).
**Contra:** dificilmente ganha um desafio quant.

## Opção C — As duas coisas ⭐ recomendada

Apresentar a pesquisa Sinapse honestamente **e** mostrar que a mesma maquinaria, no horizonte
certo e com universo expandido, produz uma estratégia que funciona — **declarando que o motor é
momentum** e que a contribuição do grafo não é significante (t = 1,01).

**Por que é mais forte que A:** é honesto sobre a atribuição, e honestidade sobre atribuição de
fator é exatamente o que uma banca de asset avalia.
**Por que é mais forte que B:** tem um resultado.

> **As três melhorias mecânicas (3.1, 3.2, 3.3) valem em qualquer opção.** São as primeiras
> coisas a fazer, independente da escolha.

---

# PARTE 5 — COMO FAZER

## 5.1 O piso — sem isso a conclusão está errada (~6 h)

| # | item | por quê |
|---|---|---|
| 1 | Bug `s4:233` (`min_count=1`) | 13,4% dos choques são retorno bruto |
| 2 | Bug do beta parcial (`s4:226-236`) | hedge com 1/3 do beta correto |
| 3 | Bug do beta NaN (`s5:209`) | 12,8% das posições sem hedge |
| 4 | Modelo de custo tiered + aluguel (`s3:79`) | flipa o alfa de +2,83% para −2,28% |

## 5.2 As três melhorias mecânicas (~2 dias)

| # | item | ganho |
|---|---|---|
| 5 | Universo 73 → 249 tickers (tirar `tickers_alvo`) | breadth 22,5 → **33,7** |
| 6 | Construção: peso ∝ z, neutralizar beta+setor | **+0,20 de Sharpe**, vol 10,0% → 8,3% |
| 7 | Validação por **walk-forward** | número 100% OOS, não gasta período |

## 5.3 A evidência para a banca (~3 h)

| # | item | responde |
|---|---|---|
| 8 | Placebo do grafo (300 sorteios) | *"o grafo carrega informação?"* → **p ≤ 0,015** |
| 9 | Deflated Sharpe com **N declarado** | *"seu Sharpe é significante?"* |
| 10 | Bloco de stress (COVID, Joesley, 2022) | *"como se comporta em crise?"* → **protegeu** |
| 11 | `forca = 1.0` | *"vocês ajustaram 58 forças?"* → *"não, e mostramos"* |
| 12 | Atribuição de fator (regressão contra mom/rev/lowvol) | *"isso é alfa ou é fator?"* |

## 5.4 O que eu cortaria — realismo que não muda conclusão

Futuro de índice no lugar do à vista (medido: **+0,05%/ano**), Ledoit-Wolf na covariância, EWMA
na vol, escada de desalavancagem por drawdown, trava de participação por ordem (0,4% das
ordens). São críticas técnicas legítimas, mas **nenhuma muda a conclusão** e todas consomem
tempo que deveria ir para a estratégia.

> **O critério:** realismo que muda a **conclusão** é obrigatório; realismo que muda a
> **aparência** é opcional. O modelo de custo é obrigatório porque flipa o sinal do resultado.
> O resto é polimento.

## 5.5 O que NÃO fazer

- Relaxar o teto de 5% por nome para alcançar os 12% de vol
- Reduzir a meta de vol para 7,5% (quebra o pré-registro; e **o Sharpe é invariante à escala** —
  o gap de vol não explica o resultado)
- Recalibrar `janela_suavizacao_pesos` (reescrever a justificativa, não o valor)
- Escrever mais elos manuais
- Retestar qualquer coisa da Parte 2
- Olhar 2021–2025 e ajustar — **cada uso adicional exige um N maior no Deflated Sharpe**

## 5.6 Ordem sugerida

```
dia 1   itens 1-4        piso: bugs + custo real
dia 2   itens 5-6        universo expandido + construção nova
dia 3   item 7           walk-forward, e é aqui que sai o número oficial
dia 4   itens 8-12       evidência + deck
```

**Caminho mínimo se apertar:** 1, 2, 3, 4, 7, 9. Bugs, custo, walk-forward e Deflated Sharpe.

---

# PARTE 6 — A DECISÃO QUE É SUA

Uma pergunta, e ela define o resto:

> **Vale apresentar uma estratégia cujo motor é momentum de preço, com a contribuição própria
> declarada como não significante?**

Se **sim** → Opção C, e eu reescrevo o plano para o caminho completo.
Se **não** → Opção B, e o plano atual (`PLANO_IMPLEMENTACAO.md`) já serve, tirando os itens de
realismo que a §5.4 corta.

Em qualquer caso, os itens 1 a 7 são os mesmos.
