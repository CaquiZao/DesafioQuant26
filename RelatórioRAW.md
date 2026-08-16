# SINAPSE — Relatório Completo da Estratégia

> **Documento-mestre.** Versão longa, escrita para ser comprimida no PPT de 5 páginas.
> Estado final do código (commit `76b9037` + Bloco 7). Todos os números saem de **uma única
> execução** do pipeline e foram **verificados de forma independente** por auditoria dedicada.
>
> **Período de avaliação: 17/05/2017 a 30/12/2025.** Antes disso não há posição — o sinal exige
> 252 pregões de regressão + 231 de acumulação de aquecimento. Incluir os 14 meses vazios
> diluiria artificialmente a volatilidade e o Sharpe.

---

# 0. Identidade do robô

| | |
|---|---|
| **Nome** | **SINAPSE** |
| **Classe de ativos** | Ações (renda variável brasileira, B3) |
| **Universo** | 543 ações regredidas · **mediana de 128 na carteira por dia** |
| **Frequência** | Rebalanceamento **diário suavizado**; grafo reconstruído **mensalmente** |
| **Benchmark** | **CDI**. Ibovespa apenas como referência de descorrelação |
| **Tipo** | Long-short **market-neutral**, autofinanciada |
| **AUM de referência** | R$ 100 milhões |

## Por que "Sinapse"

Uma sinapse é a junção onde um neurônio transmite sinal a outro. O impulso não nasce no destino
— ele **chega** de outro lugar, com atraso.

É o que a estratégia faz: ela **não** analisa a empresa em que investe. Observa o choque numa
empresa **vizinha** — mais líquida, mais coberta — e aposta que o impulso percorre a rede até
chegar na empresa lenta.

O nome também descreve a arquitetura literal: um **grafo** onde cada elo transmite sinal com
direção e intensidade. Não é metáfora — é a estrutura de dados do código.

```
         ●━━━━━━━━▶ ○
      líquido      ilíquido
     (dispara)     (recebe)

   SINAPSE · o sinal chega antes do preço
```

---

# 1. Conceito da estratégia

## 1.1 A ineficiência

> **Atenção é um recurso escasso.** Quando sai notícia que afeta um ramo inteiro — minério,
> câmbio, juro — o nome líquido reprecifica em minutos. O ilíquido leva semanas.

## 1.2 A hipótese

**A informação difunde do nome líquido para o ilíquido, dentro do mesmo ramo econômico.**

| trabalho | achado |
|---|---|
| Lo & MacKinlay (1990) | ações grandes lideram pequenas |
| **Hou (2007)** | **o lead-lag é DENTRO da indústria** |
| Cohen & Frazzini (2008) | links econômicos preveem retorno |
| Blitz, Huij & Martens (2011) | momento residual — o **controle** desta estratégia |

**Não alegamos descoberta.** Testamos se um efeito documentado sobrevive na B3 com custo real.
Uma hipótese com literatura é muito mais difícil de atacar como *data mining*: não a escolhemos
olhando os dados.

## 1.3 A hipótese ORIGINAL foi refutada

Pré-registro em `CRITERIOS_GRAFO_MANUAL.md`: *"`concorrente` = −1 — a desgraça de um é a sorte
do outro."*

**Os dados derrubaram.** Concorrentes **co-movem** — Vale e CSN dependem do mesmo minério, e a
exposição compartilhada domina o efeito de soma-zero.

A inversão foi decidida **só com 2016–2020**, congelada, e medida uma vez. O controle mantendo
`−1` dá **alfa negativo** fora da amostra. O teste bidirecional confirma a assimetria que a
difusão prevê: o sentido reverso é mais fraco nas **6 categorias, sem exceção**.

---

# 2. Modelagem

![fluxograma](fase%207%20-%20relatorio/saida/10_fluxograma_pipeline.png)

## 2.1 Isolar o choque

```
retorno_VALE = α + β · Ibovespa + ε      ← regressão móvel de 252 pregões
                                 ↑
                          o choque limpo
```

> **Por que NÃO removemos o setor.** A tese é difusão **intra-indústria** — o termo setorial
> removia exatamente a informação que se quer propagar. Removê-lo elevou o IC de +0,0506 para
> **+0,0621**.

⚠️ **Ressalva medida:** o β desta regressão tem **mediana 0,82** (p1 −0,02; p99 2,20), não ~1,0.
O viés vem de negociação não-sincronizada nos 543 tickers. É o beta que o hedge usa, e ele
funciona (correlação final com o Ibovespa: **−0,01**), mas a afirmação "é o beta de mercado puro"
seria forte demais.

## 2.2 O horizonte

![horizonte](fase%207%20-%20relatorio/saida/05_ic_por_horizonte.png)

| horizonte | T+1 | T+5 | T+21 | T+63 | T+126 |
|---|---|---|---|---|---|
| IC | +0,0074 | +0,0132 | +0,0219 | +0,0418 | +0,0457 |
| **t** | **2,93** | **2,25** | 1,68 | 1,93 | 1,32 |
| IC/√h | 0,0074 | 0,0059 | 0,0048 | 0,0053 | 0,0041 |

**A tese original dizia T+1. Os dados dizem meses.** De T+1 a T+126, `IC/√h` cai **45%** — um
efeito instantâneo cairia **91%**. O sinal acumula quase como difusão pura.

⚠️ **Duas ressalvas honestas:** `IC/√h` **não é constante** (cai 45%); e **só T+1 e T+5 têm
t > 2**. O horizonte efetivamente usado (12-1) tem t entre 1,3 e 1,9.

## 2.3 O grafo mecânico

![regra](fase%207%20-%20relatorio/saida/11_diagrama_regra_grafo.png)

```
Para cada subsetor, mensalmente:
  1. ordena por volume dos 21 pregões ANTERIORES     ← point-in-time
  2. deduplica ON/PN da mesma empresa
  3. os K mais líquidos formam a CABEÇA
  4. cada cabeça manda sinal para TODOS do ramo, ex-self
```

**Ensemble de 6 variantes** (K ∈ {2,3,5} × peso ∈ {igual, ADTV}). Todas entram; **nenhuma é
escolhida por desempenho** — essa é a propriedade mais valiosa da configuração.

**Validação:** a regra reproduz **38 dos 40** elos intra-setor escritos à mão (**95%**), todos
também na direção inversa. *A equipe não descobriu pares — descobriu uma topologia.* Os dois
faltantes caem no filtro de subsetores com menos de 4 membros.

## 2.4 Da nota à posição

| etapa | o que faz | **por que existe** |
|---|---|---|
| vol-targeting ⇄ travas (3 rodadas) | escala o book para mirar 12% de vol | separa "quanto acreditar" de "quanto arriscar". As travas têm a palavra final: são restrição real, não sugestão |
| **trava por nome (5%)** | limita cada posição | obriga o capital a se dividir em ≥20 teses. Hoje morde em **1,9%** dos dias |
| **trava por setor (25%)** | limita o gross por setor | impede que um boom setorial vire aposta macro disfarçada de aposta em rede |
| **trava de liquidez (10% do ADTV)** | limita a posição ao montável | garante que a posição seria **acumulável**; o impacto de execução é tratado no custo |
| suavização dos pesos (63 pregões) | negocia a média das últimas 63 carteiras-alvo | o sinal é lento (12 meses); negociar rápido só pagaria spread |
| reaplicar travas | corta de novo após suavizar | a média móvel pode estourar a trava de liquidez, que **varia no tempo** *(bug corrigido)* |
| máscara de negociabilidade | zera peso de ação que não negociou | impede "posição fantasma" em papel delistado |
| hedge de beta | vende Ibovespa sintético | zera a exposição de mercado — é o que torna o CDI o benchmark certo |
| `shift(1)` | lag de execução | a decisão de terça só é executada na quarta |

## 2.5 Por que "diário" não significa girar tudo

Duas médias empilhadas: **12 meses no sinal**, **63 pregões nos pesos**. A carteira é *decidida*
todo dia, mas se *move* devagar. Rebalancear mensal descartaria informação por até 21 dias.

## 2.6 Parâmetros

Ver `saida/16_tabela_parametros.md`. Os **7 primeiros foram pré-registrados antes de qualquer
backtest** — e o Git comprova (`PARAMETROS.md` em 21/07; primeiro backtest em 29/07).

---

# 3. Backtest

## 3.1 Metodologia

O motor **não decide nada**: recebe a matriz de pesos pronta e faz `P&L = Σ(peso × retorno) −
custo`. Sem loop, sem renormalização, sem rebalanceamento inventado.

## 3.2 Tratamento de vieses

| viés | tratamento | custo honesto |
|---|---|---|
| **Sobrevivência (preços)** | COTAHIST tem as empresas mortas. Cobertura 66% → **98%** | **+19,9% → +8,7%** |
| **Sobrevivência (grafo)** | grafo mecânico sobre universo point-in-time | −0,58 p.p./ano |
| **Retrovisão** | a regra usa só volume **passado** | — |
| **Look-ahead de execução** | `shift(1)`; um dia a mais custaria 32% do alfa | — |
| **Data snooping** | protocolo IS/OOS congelado | — |
| **Comparações múltiplas** | Deflated Sharpe com **N = 294 declarado** | — |

**Auditoria independente testou e não encontrou look-ahead em nenhum ponto**: o grafo de junho
usa ADTV até 31/maio; o choque de t usa só dados ≤ t; a covariância exclui o próprio dia. A
regressão vetorizada foi verificada contra `lstsq` bruto — erro máximo **1,8e-15**. O Bloco 4
reproduz **bit a bit**.

![evolução](fase%207%20-%20relatorio/saida/17_evolucao_correcoes.png)

## 3.3 Os bugs que encontramos em nós mesmos

| bug | efeito |
|---|---|
| `mapeamento_setores.csv` nunca carregado | o "choque limpo" era **retorno bruto disfarçado** |
| CDI descontado duas vezes no Sharpe | Sharpe −1,40 → **+0,18** |
| Trava de liquidez violada em 59,6% dos dias | backtest **não executável** → 0,0% |
| Posição fantasma em ação delistada | 2,07% do book → **0,00%** |
| Mapa setorial 79% vazio | alfa +11,6% → **+27,9%** |
| Resíduo virava retorno bruto sem 252 obs | 13,4% das células — **100% de 2016** |
| Beta NaN tratado como zero no hedge | 13,6% das posições **sem hedge** |

Cada correção tem **teste que falha no código antigo e passa no novo**.

> O bug do resíduo **inflava o t in-sample do nosso próprio protocolo**, de 1,39 para 2,14.
> Corrigi-lo **enfraqueceu nossa própria evidência**.

## 3.4 Custo de transação — três camadas

![custo](fase%207%20-%20relatorio/saida/12_custo_e_breakeven.png)

A premissa usual de 5 bps é um número de **large cap líquida**. **79% do nosso giro está abaixo
de R$ 150 MM de ADTV.**

| camada | valor | natureza |
|---|---|---|
| emolumentos + liquidação B3 | 2,3 bps | **observável** |
| corretagem institucional | 3,0–4,0 bps | contratual |
| meio-spread por faixa de ADTV | 2 / 5 / 11 / 24 bps | estimado |
| impacto de mercado | `0,4 × σ₆₀ × √(participação)` | estimado |
| **aluguel BTC** (ponta vendida) | 1,0–6,0 % a.a. | estimado |

**Custo medido: 3,86% ao ano = 32,2 bps por unidade de giro. Alfa por unidade de giro:
33,7 bps.**

> **Este par é o resultado mais defensável do trabalho.** Ele não depende da nossa calibragem:
> se acharem nosso custo pessimista, o alfa por giro continua o mesmo; se otimista, também.

---

# 4. Análise de resultados

## 4.1 As duas leituras — e as duas precisam estar na mesa

![curva](fase%207%20-%20relatorio/saida/01_retorno_acumulado.png)

| métrica | Sinapse<br>*(5 bps)* | **Sinapse<br>*(realista)*** | Fundo<br>*(5 bps)* | **Fundo<br>*(realista)*** | Ibovespa | CDI |
|---|---|---|---|---|---|---|
| Retorno acumulado | +38,1% | **+6,2%** | +180,3% | **+115,4%** | +97,8% | +102,9% |
| Retorno anualizado | +3,91% | **+0,71%** | +13,01% | **+9,54%** | +8,44% | +8,76% |
| Volatilidade | 8,26% | 8,28% | 8,25% | 8,27% | 23,07% | 0,24% |
| **Sharpe** | 0,506 | **0,127** | 1,524 | **1,143** | 0,468 | — |
| Sortino | 0,78 | 0,20 | 2,38 | 1,78 | 0,58 | — |
| **Drawdown máximo** | −15,8% | **−18,5%** | −8,6% | **−8,9%** | **−46,8%** | 0,0% |
| Calmar | 0,25 | 0,04 | 1,52 | 1,07 | 0,18 | — |
| **Excesso sobre o CDI** | — | — | **+77,4%** | **+12,6%** | −5,0% | — |

> **A leitura honesta.** Sob custo realista, o alfa isolado rende **+0,71% ao ano** — praticamente
> nada. O produto entregue ao cotista (CDI + alfa) rende **+115,4%**, batendo o CDI em **+12,6%
> em 8,6 anos (≈ +0,7%/ano)** com **um quinto do drawdown do Ibovespa**.
>
> **O ganho é marginal, e depende inteiramente de o custo real ficar no cenário central.**

## 4.2 Drawdown e neutralidade

![drawdown](fase%207%20-%20relatorio/saida/02_drawdown.png)
![distribuição](fase%207%20-%20relatorio/saida/09_distribuicao_neutralidade.png)

**Correlação com o Ibovespa: −0,01.** A nuvem não tem inclinação — a neutralidade é medida, não
alegada.

| janela de stress | Sinapse | Ibovespa |
|---|---|---|
| **COVID (fev–abr/2020)** | **+2,47%** | **−29,62%** |
| Joesley (mai/2017) | −0,06% | −8,80% |
| Americanas (jan/2023) | +0,69% | +2,36% |

> O dano não vem de evento de mercado — vem de **regime**. 2022–2023 corridos, sem evento
> identificável, foram os dois piores anos.

## 4.3 Por ano

![anual](fase%207%20-%20relatorio/saida/03_performance_anual.png)

Ver `saida/14_tabela_desempenho_anual.md`.

> **O custo realista inverte o sinal em 5 dos 9 anos.** 2019–2021 sozinhos carregam o resultado;
> fora dessa janela a estratégia é negativa. **2018 é o pior caso** — giro de 16,6%/dia torna o
> ano inviável com custo real (−5,84%).

## 4.4 Carteira e execução

![giro](fase%207%20-%20relatorio/saida/04_giro_e_posicoes.png)
![exposições](fase%207%20-%20relatorio/saida/06_exposicoes.png)

| | |
|---|---|
| ações na carteira | **mediana 128/dia** |
| **apostas independentes (breadth)** | **~14–20** |
| giro | 4,8%/dia |
| exposição bruta | 134,7% |
| exposição líquida | ≈ 0 |
| dias com posição no teto de 5% | **1,9%** |
| concentração (top-5 do P&L) | **13,2%** (era 79%) |

> ⚠️ **128 posições não são 128 apostas.** Satélites do mesmo subsetor recebem sinal quase
> idêntico — correlação **+0,887**, e **35% dos pares acima de 0,99**. A breadth efetiva é ~14–20.
> **Mais posições não é mais diversificação.**

Ver `saida/15_tabela_sinais_exemplo.md` — a carteira **não entra e sai** de posições; ajusta o
*tamanho* continuamente.

## 4.5 Estabilidade

![rolling](fase%207%20-%20relatorio/saida/08_rolling_sharpe_vol.png)
![heatmap](fase%207%20-%20relatorio/saida/07_heatmap_mensal.png)

Volatilidade móvel de 63d: mediana ~8%, **máximo 13,71% (abr/2020)**, e **6,1% dos dias acima do
teto de 12%**. O estouro é limitação do estimador de covariância (janela de 60 pregões com peso
igual demora a reagir a mudança de regime), não do parâmetro.

## 4.6 O que NÃO funciona

Seção deliberada. Um relatório que só mostra o que deu certo não é análise.

**(a) A propagação não bate a persistência.** Contra o momento residual do **próprio nome**, o
alfa incremental é **+0,03%/ano (t = 0,01)**. A tese "difusão entre nomes" não se separa de "o
nome tem momento residual próprio".

**(b) Carga em momento de indústria: t = 6,2.** Depois de controlar por ele e pelos fatores
clássicos, o alfa out-of-sample é **−0,02% (t = −0,01)**.

**(c) O Deflated Sharpe reprova.** Com **N = 294** configurações declaradas, DSR ≈ 0,005.
**O que sustenta o resultado é o placebo, não o Sharpe.**

**(d) O in-sample não seleciona.** Testamos duas decisões sob protocolo (teto de satélites,
neutralização contra beta). A grade OOS completa **não tem nenhuma célula positiva — exceto
exatamente a que ambos os critérios rejeitaram**. Por isso **não adotamos nenhuma das duas**.

**(e) A vol fica em 8,3%, não nos 12%.** Não é escolha: atingir 12% exigiria peso de 8,3% por
nome, acima da trava. E o Sharpe é **invariante à escala** — o gap não explica o resultado.

---

# 5. Conclusão e próximos passos

## 5.1 Onde a estratégia está

**O mecanismo é real.** O placebo confirma que escolher a cabeça pela liquidez bate sorteios
aleatórios. A neutralidade funciona (COVID +2,5% contra −29,6%).

**O tamanho não é.** 33,7 bps de alfa contra 32,2 de custo. **A tese é verdadeira e pequena
demais para pagar com folga o custo de negociá-la — e sabemos disso porque medimos as duas
coisas.**

## 5.2 Viabilidade

| | |
|---|---|
| Capacidade | ~R$ 100 MM. A R$ 1 bi o alfa some |
| Executabilidade | trava de liquidez com **0 violações** em 93.022 posições |
| Gargalo real | **aluguel da ponta vendida** — imune a redução de giro |

## 5.3 Limitações declaradas

1. Deflated Sharpe reprova (N = 294).
2. A propagação não faz spanning sobre o momento residual (t = 0,01).
3. Carga em momento de indústria t = 6,2.
4. **5 dos 9 anos negativos com custo real**; 2019–2021 carregam tudo.
5. Breadth efetiva ~14–20 contra 128 posições.
6. O ganho sobre o CDI (+12,6% em 8,6 anos) é marginal.

## 5.4 Próximos passos

| # | ação | por quê |
|---|---|---|
| 1 | **Trocar o short de ações por venda de índice/futuro** | ~40% do custo é aluguel |
| 2 | **Aumentar breadth via mais SUBSETORES** | o teto é o nº de ramos, não o nº de nomes |
| 3 | **Fatores explícitos** (minério, câmbio, juro) no choque | choques mais independentes |
| 4 | **Grafo cego construído por terceiro** | única forma de testar se a curadoria generaliza |
| 5 | **Trava de exposição líquida** | hoje inexistente |

---

# 6. Uso de IA Generativa

A IA foi usada em **quatro papéis distintos**, e o valor veio de papéis diferentes em momentos
diferentes.

## 6.1 Como geradora de código e executora

Todo o pipeline foi escrito com IA: os 7 blocos, ~4.000 linhas de Python. Não como
autocompletar, mas como **par de programação que executa**: escreve, roda, lê a saída, corrige.

Exemplos onde isso foi decisivo:
- **Regressão rolling vetorizada** — a versão original levava minutos por rodada e limitava o
  universo a 73 tickers. A versão vetorizada roda 543 em segundos, e foi **verificada contra
  `lstsq` bruto com erro de 1,8e-15**. Isso desbloqueou a expansão do universo.
- **Winsorização vetorizada** — 14× mais rápida e numericamente idêntica. Sem ela, testes de
  reamostragem (placebo, bootstrap) eram inviáveis como rotina.
- **Acervo visual** — 13 gráficos e 5 tabelas gerados por script reexecutável, com paleta
  validada para daltonismo por script.

## 6.2 Como ferramenta de planejamento de ideias, hipóteses e teses

Este foi o uso de maior impacto. A IA **propôs hipóteses testáveis** e desenhou os testes:

| hipótese proposta | como foi testada | resultado |
|---|---|---|
| "o horizonte está errado" | IC em T+1/5/21/63/126 | **confirmada** — reescreveu a tese |
| "o choque não deveria ser limpo de setor" | IC com e sem o termo setorial | **confirmada** — +0,0506 → +0,0621 |
| "a curadoria manual é mecanizável" | regra por liquidez vs grafo manual | **confirmada** — 95% de reprodução |
| "elos cross-setor são mais fortes" | partição do grafo por subsetor | **refutada** — cross é pior |
| "a autocorrelação do IC infla o t" | Newey-West | **refutada** — ρ(1) ≈ 0 |
| "controle por subsetor melhora o resíduo" | protocolo IS/OOS completo | **refutada** — baseline vence |

**Metade das hipóteses foi refutada.** Isso é o processo funcionando, não falhando.

## 6.3 Como auditora adversarial

```
                    ┌─ quant-analyst  → auditoria estatística, protótipos, placebos
   coordenação ─────┼─ risk-manager   → controles de risco, exposições, capacidade
                    └─ fintech-eng    → custo realista, aluguel, execução
```

Subagentes **independentes**, com contexto próprio, instruídos a serem adversariais: *"o objetivo
é encontrar o que a banca encontraria."*

**Os 7 bugs da §3.3 foram todos encontrados assim.** E a auditoria final encontrou, no próprio
material do relatório, que **a manchete "+88% de excesso sobre o CDI" só valia a 5 bps** — o
número correto sob custo realista é +12,6%.

## 6.4 Limitações encontradas

**A IA errou, e errou de formas instrutivas:**

1. **Escreveu um gráfico cuja legenda os próprios dados contradiziam.** O gráfico de IC por
   horizonte dizia "IC/√h é constante"; a curva mostrava queda de 45%. **Foi pego ao renderizar
   e olhar** — não por revisão de código.
2. **Introduziu um bug num script de verificação.** Ao validar um resultado, escreveu uma
   regressão que mascarava 46% dos dados por tratamento errado de NaN, e chegou à conclusão
   **oposta**. Outro subagente encontrou.
3. **Propôs um caminho que os dados invalidaram.** Sugeriu buscar elos cross-setor na Matriz de
   Insumo-Produto do IBGE. A medição mostrou que cross-setor é imaterial. Uma semana evitada.
4. **Tendeu a otimismo em resultados próprios.** Precisou de instrução explícita para reportar
   resultado nulo sem maquiar, e de auditoria dedicada para descobrir que as tabelas geradas não
   refletiam as ressalvas já escritas na documentação.

> **A lição operacional:** IA como **um** analista é perigosa — ela concorda consigo mesma. Como
> **vários analistas adversariais que se auditam**, encontra o que um humano sozinho não
> encontraria. Toda afirmação relevante deste relatório foi verificada por um segundo agente ou
> por medição direta.

## 6.5 O que a IA NÃO fez

Não escolheu parâmetros olhando o resultado. Não decidiu quais restrições de protocolo aplicar.
As decisões de método — congelar, medir uma vez, não recalibrar, publicar o número pior — foram
impostas como regra e verificadas a cada passo.

---

# 7. Observações finais — coerência da tese e reprodutibilidade

## 7.1 Onde a tese e o código divergem

**A tese declarada é "difusão intra-indústria — o líquido lidera". O código implementa isso
parcialmente, com três contradições que precisam estar escritas:**

**(1) Não é "A informa B". É "o composto líquido do ramo informa todo mundo igual."**
Cada cabeça manda o mesmo sinal para todos os elegíveis com força `1/K` (ou share de ADTV).
Resultado medido: **todo não-líder do subsetor recebe sinal idêntico** — correlação **+0,887**,
**35% dos pares acima de 0,99**. Isso é um **fator de momento de indústria**, não uma rede de
elos. O próprio projeto mede a carga nesse fator com **t = 6,2**.

**(2) A assimetria "líquido → ilíquido" é parcialmente revertida por construção.**
`alvo = todos ex-self` inclui as outras cabeças, então **os nomes mais líquidos também são
operados** — o oposto do mecanismo alegado (atraso de atenção em nomes pequenos). A justificativa
para incluí-los é que isso reproduz a topologia do grafo manual — argumento de **ajuste ao grafo
humano**, não de tese.

**(3) O horizonte de 12 meses torna a tese empiricamente inseparável do momento residual do
próprio nome.** É o controle de persistência, reportado com **t = 0,01**. "Difusão lenta ao longo
de 12 meses" e "momento de indústria" são o **mesmo objeto** neste desenho.

> Nada disso é bug. Mas a frase *"o líquido lidera o ilíquido"* não é exatamente o que o código
> faz — e a banca vai perguntar.

## 7.2 Reprodutibilidade — ordem correta de execução

```
1.  fase 1/src/s1_precos.py             [rede: yfinance]
2.  fase 1/src/s1b_indices.py           [rede: yfinance]
3.  fase 2/s2_universo.py               [DEPENDÊNCIA EXTERNA: COTAHIST fora do repo]
4.  fase 1/src/s1c_retornos_completo.py  ← DEPENDE DO PASSO 3
5.  fase 4/src/s4b_atualiza_setores.py
6.  fase 4/src/s4c_subsetores.py        [gera a coluna Subsetor, exigida pelo s4d]
7.  fase 4/src/s4d_grafo_regra.py       → data/grafo_regra_mensal.parquet
8.  fase 4/src/s4_sinapse_sinal.py      → sinal_sinapse.parquet + betas_sinapse.parquet
9.  fase 5/src/exec_s5.py               → df_weights_sinapse.parquet
10. fase 3/src/s3_backtest.py           [rede: API do BCB, se o cache do CDI não existir]
11. fase 7/src/r1_visuais.py
```

**Dependências não declaradas, que precisam ser corrigidas:**

- o passo 4 depende do 3 — **a fase 2 roda antes da fase 1c**, o que a numeração das pastas
  contradiz;
- `s2_universo.py:36` aponta para um diretório **fora do repositório**;
- `data/` é gitignorado por inteiro;
- **não há `requirements.txt`** — e o projeto depende de comportamento específico do pandas 3.0.1
  (documentado em `s5:186-188`);
- `README.md` tem uma linha.

> **Veredito honesto:** quem clonar o repositório **não chega nos mesmos números — nem chega a
> rodar**. Dado os insumos, o Bloco 4 reproduz bit a bit; o problema está em **produzir** os
> insumos.

## 7.3 Alegações que foram corrigidas nesta revisão

Auditoria dedicada encontrou dez afirmações indefensáveis no material anterior. Todas corrigidas:

| alegação anterior | número correto |
|---|---|
| "Excesso sobre o CDI de +88,0%" | **+12,6%** com custo realista |
| "IC/√h é constante — assinatura de difusão" | **cai 45%** |
| "O sinal paga o próprio giro" (33,6 vs 33,7) | **32,2 vs 33,7** — e negativo em 5 dos 9 anos |
| "141 nomes/dia" | **mediana 128**; e ~14–20 apostas independentes |
| "O beta é o beta de mercado (~1,0)" | **mediana 0,82** |
| "A regra reproduz 100% dos elos" | **95%** (38/40) |
| "Vol de 63d atingiu 18,12%" | **13,71%**; e 6,1% dos dias acima de 12%, não 2,6% |
| "Volatilidade 7,64% / utilização 65%" | **8,3% / 69%** no período ativo |
| "73% do giro abaixo de R$150MM" | **79%** |
| "Winsorização corta 3,8% das células" | **2,57%** |

> **Isto é o ponto do trabalho inteiro:** encontrar os próprios erros e publicar o número pior.
> Ver uma equipe que testou, falhou e manteve o registro vale mais que meio ponto de Sharpe.

---

# Apêndice — Glossário

| termo | o que é |
|---|---|
| **IC** | correlação entre a nota de hoje e o retorno futuro. 0,01 é minúsculo — mas o cassino ganha com 2,7% de vantagem repetida milhares de vezes |
| **Breadth** | número de apostas **independentes**. 128 posições que se movem juntas são **uma** aposta |
| **Lei Fundamental** | `IR ≈ IC × √breadth` |
| **IS / OOS** | período onde se pode testar à vontade / período que só vale se olhado **uma vez** |
| **Walk-forward** | recalibra a cada ano com o que se sabia e opera o ano seguinte |
| **Deflated Sharpe** | Sharpe corrigido pelo nº de configurações testadas. Pune garimpo |
| **Placebo do gatilho** | sortear qual nome é a cabeça e ver se o real ganha. Testa o **mecanismo** |
| **Giro** | soma das mudanças absolutas de peso, duas pontas |
| **Market-neutral** | beta zero contra o Ibovespa. O benchmark passa a ser o CDI |
| **BTC** | aluguel de ações para a ponta vendida — ~40% do custo total |
