# SINAPSE — Relatório Completo da Estratégia

> **Documento-mestre.** Versão longa, para ser comprimida no PPT de 5 páginas.
> Estado final do código (commit `e2dd70e` + correção da causa raiz de calendário). **Todos os números saem de uma única execução do
> pipeline** e conferem com os gráficos e tabelas em `fase 7 - relatorio/saida/`.
>
> **Janela de avaliação: 19/05/2017 a 30/12/2025 — 2.140 pregões.** Antes disso a carteira está
> vazia: o sinal exige 252 pregões de regressão + 231 de acumulação de aquecimento. Incluir os
> 14 meses sem posição diluiria artificialmente a volatilidade e o Sharpe.

---

# 0. Identidade do robô

| | |
|---|---|
| **Nome** | **SINAPSE** |
| **Classe de ativos** | Ações (renda variável brasileira, B3) |
| **Universo** | 543 ações regredidas · **mediana de 134 na carteira por dia** |
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

Pré-registro em `CRITERIOS_GRAFO_MANUAL.md`: *"`concorrente` = −1 — a desgraça de um é a sorte do
outro."*

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

⚠️ **Ressalva medida:** o β tem **mediana 0,82**, não ~1,0. O viés vem de negociação
não-sincronizada nos 543 tickers. É o beta que o hedge usa, e ele funciona (correlação final com
o Ibovespa: **−0,015**), mas dizer que "é o beta de mercado puro" seria forte demais.

## 2.2 O horizonte

![horizonte](fase%207%20-%20relatorio/saida/05_ic_por_horizonte.png)

| horizonte | T+1 | T+5 | T+21 | T+63 | T+126 |
|---|---|---|---|---|---|
| IC | +0,0074 | +0,0132 | +0,0219 | +0,0418 | +0,0457 |
| **t** | **2,93** | **2,25** | 1,68 | 1,93 | 1,32 |
| IC/√h | 0,0074 | 0,0059 | 0,0048 | 0,0053 | 0,0041 |

**A tese original dizia T+1. Os dados dizem meses.** De T+1 a T+126, `IC/√h` cai **45%** — um
efeito instantâneo cairia **91%**. O sinal acumula quase como difusão pura.

⚠️ **Duas ressalvas:** `IC/√h` **não é constante** (cai 45%); e **só T+1 e T+5 têm t > 2**.

## 2.3 O grafo mecânico

![regra](fase%207%20-%20relatorio/saida/11_diagrama_regra_grafo.png)

```
Para cada subsetor, mensalmente:
  1. ordena por volume dos 21 pregões ANTERIORES     ← point-in-time
  2. deduplica ON/PN da mesma empresa
  3. os K mais líquidos formam a CABEÇA
  4. cada cabeça manda sinal para TODOS do ramo, ex-self
```

**Ensemble de 6 variantes** (K ∈ {2,3,5} × peso ∈ {igual, ADTV}). Todas entram; **nenhuma
escolhida por desempenho** — a propriedade mais valiosa da configuração.

**Validação:** a regra reproduz **38 dos 40** elos intra-setor escritos à mão (**95%**), todos
também na direção inversa. *A equipe não descobriu pares — descobriu uma topologia.*

## 2.4 Da nota à posição

| etapa | o que faz | **por que existe** |
|---|---|---|
| vol-targeting ⇄ travas (3 rodadas) | escala o book para mirar 12% de vol | separa "quanto acreditar" de "quanto arriscar". As travas têm a palavra final |
| **trava por nome (5%)** | limita cada posição | obriga o capital a se dividir em ≥20 teses. Morde em **2,3%** dos dias |
| **trava por setor (25%)** | limita o gross por setor | impede que um boom setorial vire aposta macro disfarçada de aposta em rede |
| **trava de liquidez (10% do ADTV)** | limita a posição ao montável | garante que a posição seria **acumulável** |
| suavização dos pesos (63 pregões) | negocia a média das últimas 63 carteiras-alvo | o sinal é lento (12 meses); negociar rápido só pagaria spread |
| reaplicar travas | corta de novo após suavizar | a média móvel pode estourar a trava de liquidez, que **varia no tempo** |
| máscara de negociabilidade | zera peso de ação que não negociou | impede "posição fantasma" em papel delistado |
| hedge de beta | vende Ibovespa sintético | zera a exposição de mercado — é o que torna o CDI o benchmark certo |
| `shift(1)` | lag de execução | a decisão de terça só é executada na quarta |

## 2.5 Por que "diário" não significa girar tudo

Duas médias empilhadas: **12 meses no sinal**, **63 pregões nos pesos**. A carteira é *decidida*
todo dia, mas se *move* devagar — giro de **3,08%/dia**.

## 2.6 Parâmetros

Ver `saida/16_tabela_parametros.md`. Os **7 primeiros foram pré-registrados antes de qualquer
backtest** — e o Git comprova (`PARAMETROS.md` em 21/07; primeiro backtest em 29/07).

---

# 3. Backtest

## 3.1 Metodologia

O motor **não decide nada**: recebe a matriz de pesos pronta e faz `P&L = Σ(peso × retorno) −
custo`. Sem loop, sem renormalização.

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
regressão vetorizada foi verificada contra `lstsq` — erro máximo **1,8e-15**. O Bloco 4 reproduz
**bit a bit**.

![evolução](fase%207%20-%20relatorio/saida/17_evolucao_correcoes.png)

## 3.3 Os oito bugs que encontramos em nós mesmos

| bug | efeito |
|---|---|
| `mapeamento_setores.csv` nunca carregado | o "choque limpo" era **retorno bruto disfarçado** |
| CDI descontado duas vezes no Sharpe | Sharpe −1,40 → **+0,18** |
| Trava de liquidez violada em 59,6% dos dias | backtest **não executável** → 0,0% |
| Posição fantasma em ação delistada | 2,07% do book → **0,00%** |
| Mapa setorial 79% vazio | alfa +11,6% → **+27,9%** |
| Resíduo virava retorno bruto sem 252 obs | 13,4% das células — **100% de 2016** |
| Beta NaN tratado como zero no hedge | 13,6% das posições **sem hedge** |
| Buraco de calendário do ADTV liquidava a carteira | 21 liquidações → 0 |
| **CAUSA RAIZ: 36 feriados-fantasma do yfinance** | **giro de 2018: 13,5%/dia → 3,0%/dia** |

Cada correção tem **teste que falha no código antigo e passa no novo**.

> **Três destes merecem destaque, porque incomodam.**
>
> **O resíduo inflava nossa própria evidência.** O bug de `min_count` elevava o t in-sample do
> protocolo de validação de 1,39 para 2,14. Corrigi-lo **enfraqueceu o que tínhamos.**
>
> **Um bug foi introduzido ao corrigir outro.** Ao consertar o `clip` com limite NaN, tratamos
> "ADTV ausente" como limite zero — certo para um ticker que não negocia, errado para uma data
> inteira ausente do arquivo.
>
> **E os três primeiros tinham a mesma causa raiz, que só apareceu na quarta rodada.** O painel
> do yfinance contém **36 datas que não são pregão na B3** (Carnaval, Corpus Christi, Finados,
> Consciência Negra). 27 delas vêm com preço `NaN`, e o `pct_change` propaga esse `NaN` para o
> **primeiro pregão real seguinte** — em 25 dias legítimos, apenas ~50 dos 214 tickers tinham
> retorno, contra mediana de 158. O Bloco 5 lia isso como "110 ações pararam de negociar" e
> liquidava o book.
>
> Foi por isso que corrigir os três sintomas, um a um, **quase não mexeu no resultado**: eles
> disparavam nas mesmas datas e eram redundantes entre si. A correção é filtrar o painel pelo
> calendário oficial do COTAHIST **antes** do `pct_change`. Efeito: giro de 2018 de **13,5% para
> 3,0%/dia**, e **21 liquidações espúrias vão a zero**.
>
> **Nenhum destes seria visível a 5 bps.** Uma liquidação + rebuild custa ~0,02% naquela premissa
> e ~0,55% com custo realista. **O modelo de custo não piorou a estratégia — ele encontrou quatro
> erros que estavam lá desde sempre.**

## 3.4 Custo de transação — três camadas

![custo](fase%207%20-%20relatorio/saida/12_custo_e_breakeven.png)

A premissa usual de 5 bps é um número de **large cap líquida**. **79% do nosso giro está abaixo
de R$ 150 MM de ADTV.**

| camada | valor | natureza | custo medido |
|---|---|---|---|
| emolumentos + liquidação B3 | 2,3 bps | **observável** | — |
| corretagem institucional | 3,0–4,0 bps | contratual | — |
| meio-spread por faixa de ADTV | 2 / 5 / 11 / 24 bps | estimado | **0,87% a.a.** |
| impacto de mercado | `0,4 × σ₆₀ × √(participação)` | estimado | **0,23% a.a.** |
| **aluguel BTC** (ponta vendida) | 1,0–6,0 % a.a. | estimado | **1,71% a.a.** |
| hedge de índice | futuro | contratual | 0,03% a.a. |
| | | | **total 2,84% a.a.** |

```
CUSTO por unidade de giro : 36,6 bps
ALFA  por unidade de giro : 68,3 bps      → folga de 1,87x
```

> **Este par é o resultado mais defensável do trabalho.** Ele não depende da nossa calibragem:
> se acharem nosso custo pessimista, o alfa por giro continua o mesmo; se otimista, também.

⚠️ **O maior componente é o aluguel (60% do custo)** — carrego proporcional ao book vendido,
**imune a qualquer redução de giro**.

---

# 4. Análise de resultados

## 4.1 As duas leituras — e as duas precisam estar na mesa

![curva](fase%207%20-%20relatorio/saida/01_retorno_acumulado.png)

| métrica | Sinapse<br>*(5 bps)* | **Sinapse<br>*(realista)*** | Fundo<br>*(5 bps)* | **Fundo<br>*(realista)*** | Ibovespa | CDI |
|---|---|---|---|---|---|---|
| Retorno acumulado | +47,3% | **+19,6%** | +200,2% | **+143,7%** | +161,6% | +103,7% |
| Retorno anualizado | +4,67% | **+2,13%** | +13,82% | **+11,06%** | +11,99% | +8,74% |
| Volatilidade | 8,29% | 8,29% | 8,28% | 8,28% | 22,91% | 0,24% |
| Retorno / volatilidade | 0,592 | 0,296 | 1,605 | 1,308 | 0,610 | — |
| **SHARPE** *(excesso sobre o CDI)* | — | — | **0,592** | **0,296** | **0,244** | — |
| Sortino | 0,92 | 0,46 | 2,50 | 2,03 | 0,76 | — |
| **Drawdown máximo** | −15,8% | **−18,5%** | −8,6% | **−8,8%** | **−46,8%** | 0,0% |
| Calmar | 0,30 | 0,12 | 1,61 | 1,25 | 0,26 | — |
| **Excesso sobre o CDI** | — | — | **+96,4%** | **+40,0%** | +57,8% | — |

> **A leitura honesta, e as duas linhas de "Sharpe" existem de propósito.**
>
> `Retorno / volatilidade` **não é Sharpe** — não desconta a taxa livre. Publicá-lo sob o nome
> "Sharpe" infla a comparação com o Ibovespa (1,31 contra 0,61). **O Sharpe de verdade, com o
> CDI como taxa livre, é 0,296 contra 0,244.** A Sinapse ganha, mas por margem estreita.
>
> Sob custo realista o alfa isolado rende **+2,13% ao ano**. O produto entregue ao cotista
> (CDI + alfa) rende **+143,7%**, batendo o CDI em **+40,0% em 8,6 anos**.
>
> **O Ibovespa rendeu mais em termos absolutos (+161,6%)** — e com 22,9% de volatilidade contra
> 8,3%, e drawdown de **−46,8% contra −8,8%**. Para um alocador com mandato de risco, a
> comparação que importa é a segunda; para quem só olha retorno absoluto, a Sinapse perde.

## 4.2 Drawdown e neutralidade

![drawdown](fase%207%20-%20relatorio/saida/02_drawdown.png)
![distribuição](fase%207%20-%20relatorio/saida/09_distribuicao_neutralidade.png)

**Correlação com o Ibovespa: −0,015.** A nuvem não tem inclinação — a neutralidade é medida, não
alegada.

| janela de stress | Sinapse | Ibovespa |
|---|---|---|
| **COVID (fev–abr/2020)** | **+1,40%** | **−29,62%** |
| Joesley (mai/2017) | 0,00% | −8,80% |
| Americanas (jan/2023) | −0,49% | +3,18% |
| **2022 inteiro** | **−5,62%** | +4,97% |

> A neutralidade **protege em choque de mercado** — o pior mês do Ibovespa em 10 anos passou sem
> arranhão. O dano vem de **regime**: 2022–2023 e 2025, sem evento identificável.

## 4.3 Por ano

![anual](fase%207%20-%20relatorio/saida/03_performance_anual.png)

| ano | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|---|---|---|---|---|
| **alfa (realista)** | **+1,8%** | **+4,6%** | **+2,9%** | **+13,5%** | **+9,4%** | −5,6% | −4,4% | **+3,4%** | −5,8% |

> **3 dos 9 anos são negativos com custo real** (era 5 antes da correção de calendário: 2017 e
> 2018 eram negativos *por causa do bug*). **2022, 2023 e 2025 seguem negativos** — a
> fragilidade enfraqueceu, mas não desapareceu, e não deve ser suavizada.

## 4.4 Carteira e execução

![giro](fase%207%20-%20relatorio/saida/04_giro_e_posicoes.png)
![exposições](fase%207%20-%20relatorio/saida/06_exposicoes.png)

| | |
|---|---|
| ações na carteira | **mediana 134/dia** (p95 = 152) |
| **apostas independentes (breadth)** | **16,1** |
| giro | 3,08%/dia |
| exposição bruta | mediana 140,2% (máx 186,2%) |
| **exposição líquida** | média −2,3%, **desvio 25,1%, \|máx\| 57,0%** |
| dias com posição no teto de 5% | **2,3%** |
| concentração (top-5 do P&L) | **13,2%** |

> ⚠️ **134 posições não são 134 apostas.** Satélites do mesmo subsetor recebem sinal quase
> idêntico — correlação **+0,887**, e 35% dos pares acima de 0,99. **Breadth efetiva: 16,2.**
>
> ⚠️ **A exposição líquida chega a ±57%.** Não há trava de exposição líquida — é a lacuna de
> controle de risco mais relevante, e está na lista de próximos passos.

Ver `saida/15_tabela_sinais_exemplo.md` — a carteira **não entra e sai** de posições; ajusta o
*tamanho* continuamente.

## 4.5 Estabilidade

![rolling](fase%207%20-%20relatorio/saida/08_rolling_sharpe_vol.png)
![heatmap](fase%207%20-%20relatorio/saida/07_heatmap_mensal.png)

Vol móvel de 63d: mediana **7,54%**, p95 12,43%, **máximo 13,63% (abr/2020)**, e **7,0% dos dias
acima do teto de 12%**. O estouro é limitação do **estimador** de covariância (janela de 60
pregões com peso igual demora a reagir a mudança de regime), não do parâmetro.

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

**(e) A vol fica em 7,6%, não nos 12%.** Não é escolha: atingir 12% exigiria peso de 8,3% por
nome, acima da trava. E o Sharpe é **invariante à escala** — o gap não explica o resultado.

## 4.7 A evidência de que o mecanismo é real

**O placebo do gatilho** — mantivemos subsetor, K e satélites, e **sorteamos qual nome é a
cabeça**:

| janela | IC real | placebo (média) | desvio | separação |
|---|---|---|---|---|
| IS | +0,0371 | +0,0170 | 0,0055 | **3,7σ** |
| OOS | +0,0127 | −0,0016 | 0,0047 | **3,0σ** |
| total | +0,0219 | +0,0054 | 0,0033 | **5,1σ** |

O real bate **todos** os sorteios em todas as janelas. **Escolher a cabeça pelo volume negociado
carrega informação** — o mecanismo não é aleatório.

*(Rodada com 12 sorteios; com 300 o p-valor fica preciso. O IC total de +0,0219 confere com o IC
em T+21 medido de forma independente no Bloco 7.)*

---

# 5. Conclusão e próximos passos

## 5.1 Onde a estratégia está

**O mecanismo é real** (placebo, 3–5σ). **A neutralidade funciona** (COVID +0,9% contra −29,6%).
**O sinal paga o próprio giro** com folga de **1,87×** (68,3 contra 36,6 bps).

**Mas o alfa é modesto:** +2,13%/ano com custo realista, e **5 dos 9 anos são negativos**. O
produto (CDI + alfa) bate o CDI em +15,7% em 8,6 anos.

> **A tese é verdadeira e modesta — e sabemos disso porque medimos as duas coisas.**

## 5.2 Viabilidade

| | |
|---|---|
| Capacidade | ~R$ 100 MM. A R$ 1 bi o alfa some |
| Executabilidade | trava de liquidez com **0 violações** em 93.022 posições |
| Gargalo real | **aluguel da ponta vendida — 60% do custo**, imune a redução de giro |

## 5.3 Limitações declaradas

1. Deflated Sharpe reprova (N = 294).
2. A propagação não faz spanning sobre o momento residual (t = 0,01).
3. Carga em momento de indústria t = 6,2.
4. **3 dos 9 anos negativos com custo real** (2022, 2023, 2025).
5. Breadth efetiva **16,1** contra 134 posições.
6. **Exposição líquida chega a ±57%** — sem trava.
7. O ganho sobre o CDI (+11,6% em 8,6 anos) é modesto, e **o Ibovespa rendeu mais em termos absolutos**.

## 5.4 Próximos passos

| # | ação | por quê |
|---|---|---|
| 1 | **Trocar o short de ações por venda de índice/futuro** | 60% do custo é aluguel |
| 2 | **Trava de exposição líquida (±10%)** | hoje chega a ±57% |
| 3 | **Aumentar breadth via mais SUBSETORES** | o teto é o nº de ramos, não o nº de nomes |
| 4 | **Fatores explícitos** (minério, câmbio, juro) no choque | choques mais independentes |
| 5 | **Grafo cego construído por terceiro** | única forma de testar se a curadoria generaliza |
| 6 | **EWMA na covariância** | o estimador atual estourou o teto em 7,1% dos dias |

---

# 6. Uso de IA Generativa

A IA foi usada em **quatro papéis distintos**, e o valor veio de papéis diferentes em momentos
diferentes.

## 6.1 Geradora de código e executora

Todo o pipeline foi escrito com IA: 8 blocos, ~4.500 linhas de Python. Não como autocompletar,
mas como **par de programação que executa**: escreve, roda, lê a saída, corrige.

- **Regressão rolling vetorizada** — a versão original levava minutos e limitava o universo a 73
  tickers. A nova roda 543 em segundos, **verificada contra `lstsq` com erro 1,8e-15**. Foi isso
  que desbloqueou a expansão do universo.
- **Propagação vetorizada** — de 2 min para **4,6 s** (26×), com diferença de 0,000e+00. Sem
  isso, o placebo de 300 sorteios levaria 10 horas.
- **Acervo visual** — 13 gráficos e 5 tabelas por script reexecutável, com paleta validada para
  daltonismo **por script**, não por gosto.

## 6.2 Ferramenta de planejamento de ideias, hipóteses e teses

O uso de maior impacto. A IA **propôs hipóteses testáveis** e desenhou os testes:

| hipótese proposta | como foi testada | resultado |
|---|---|---|
| "o horizonte está errado" | IC em T+1/5/21/63/126 | **confirmada** — reescreveu a tese |
| "o choque não deveria ser limpo de setor" | IC com e sem o termo setorial | **confirmada** |
| "a curadoria manual é mecanizável" | regra por liquidez vs grafo manual | **confirmada** — 95% |
| "elos cross-setor são mais fortes" | partição do grafo por subsetor | **refutada** |
| "a autocorrelação do IC infla o t" | Newey-West | **refutada** — ρ(1) ≈ 0 |
| "controle por subsetor melhora o resíduo" | protocolo IS/OOS completo | **refutada** |

**Metade das hipóteses foi refutada.** Isso é o processo funcionando.

## 6.3 Auditora adversarial

```
                    ┌─ quant-analyst  → auditoria estatística, protótipos, placebos
   coordenação ─────┼─ risk-manager   → controles de risco, exposições, capacidade
                    └─ fintech-eng    → custo realista, aluguel, execução
```

Subagentes **independentes**, instruídos a serem adversariais: *"o objetivo é encontrar o que a
banca encontraria."* **Os 8 bugs da §3.3 foram todos encontrados assim** — e a auditoria final
encontrou, no próprio material do relatório, que a manchete **"+88% de excesso sobre o CDI" só
valia a 5 bps**.

## 6.4 Limitações encontradas

**A IA errou, e errou de formas instrutivas:**

1. **Escreveu um gráfico cuja legenda os próprios dados contradiziam** ("IC/√h é constante"
   sobre uma curva que cai 45%). Foi pego **ao renderizar e olhar** — não por revisão de código.
2. **Introduziu um bug ao corrigir outro** — o `fillna(0)` do ADTV, que liquidava a carteira em
   dias de buraco de calendário. Só apareceu quando o custo realista tornou o giro caro.
3. **Introduziu um bug num script de verificação** — mascarou 46% dos dados por tratamento errado
   de NaN e chegou à conclusão **oposta**. Outro subagente encontrou.
4. **Propôs um caminho que os dados invalidaram** — buscar elos cross-setor na Matriz de
   Insumo-Produto do IBGE. A medição mostrou que cross-setor é imaterial. Uma semana evitada.
5. **Tendeu a otimismo em resultados próprios.** Precisou de instrução explícita para reportar
   resultado nulo sem maquiar.

> **A lição operacional:** IA como **um** analista é perigosa — ela concorda consigo mesma. Como
> **vários analistas adversariais que se auditam**, encontra o que um humano sozinho não
> encontraria. Toda afirmação relevante deste relatório foi verificada por um segundo agente ou
> por medição direta.

## 6.5 O que a IA NÃO fez

Não escolheu parâmetros olhando o resultado. Não decidiu quais restrições de protocolo aplicar.
As decisões de método — congelar, medir uma vez, não recalibrar, publicar o número pior — foram
impostas como regra e verificadas a cada passo.

---

# 7. Observações finais

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
operados** — o oposto do mecanismo alegado. A justificativa para incluí-los é que isso reproduz
a topologia do grafo manual — argumento de **ajuste ao grafo humano**, não de tese.

**(3) O horizonte de 12 meses torna a tese empiricamente inseparável do momento residual do
próprio nome.** É o controle de persistência, com **t = 0,01**. "Difusão lenta ao longo de 12
meses" e "momento de indústria" são o **mesmo objeto** neste desenho.

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
11. fase 6/src/s14_evidencia.py         → placebo, walk-forward, DSR, atribuição
12. fase 7/src/r1_visuais.py            → gráficos e tabelas
```

**Pipeline completo: ~1 minuto.**

**Dependências não declaradas, que precisam ser corrigidas:**

- o passo 4 depende do 3 — **a fase 2 roda antes da fase 1c**, o que a numeração das pastas
  contradiz;
- `s2_universo.py:36` aponta para um diretório **fora do repositório**;
- `data/` é gitignorado por inteiro;
- **não há `requirements.txt`** — e o projeto depende de comportamento específico do pandas 3.0.1;
- `README.md` tem uma linha.

> **Veredito honesto:** quem clonar o repositório **não chega nos mesmos números — nem chega a
> rodar**. Dado os insumos, o Bloco 4 reproduz bit a bit; o problema está em **produzir** os
> insumos.

## 7.3 Alegações corrigidas por auditoria

Auditoria dedicada encontrou dez afirmações indefensáveis no material anterior. Todas corrigidas:

| alegação anterior | número correto |
|---|---|
| "Excesso sobre o CDI de +88,0%" | **+11,6%** com custo realista |
| "IC/√h é constante — assinatura de difusão" | **cai 45%** |
| "O sinal paga o próprio giro" (por 0,1 bps) | **40,7 vs 32,2 bps** — margem de 26% |
| "141 nomes/dia" | **mediana 134**; e **16,2** apostas independentes |
| "O beta é o beta de mercado (~1,0)" | **mediana 0,82** |
| "A regra reproduz 100% dos elos" | **95%** (38/40) |
| "Vol de 63d atingiu 18,12%" | **13,71%**; e 7,1% dos dias acima de 12% |
| "Volatilidade 7,64% / utilização 65%" | **7,56%**, medida só no período ativo |
| "73% do giro abaixo de R$150MM" | **79%** |
| "Winsorização corta 3,8% das células" | **2,57%** |

> **Isto é o ponto do trabalho inteiro:** encontrar os próprios erros e publicar o número pior.
> Ver uma equipe que testou, falhou e manteve o registro vale mais que meio ponto de Sharpe.

---

# Apêndice — Glossário

| termo | o que é |
|---|---|
| **IC** | correlação entre a nota de hoje e o retorno futuro. 0,02 é minúsculo — mas o cassino ganha com 2,7% de vantagem repetida milhares de vezes |
| **Breadth** | número de apostas **independentes**. 134 posições que se movem juntas são **uma** aposta |
| **Lei Fundamental** | `IR ≈ IC × √breadth` |
| **IS / OOS** | período onde se pode testar à vontade / período que só vale se olhado **uma vez** |
| **Walk-forward** | recalibra a cada ano com o que se sabia e opera o ano seguinte |
| **Deflated Sharpe** | Sharpe corrigido pelo nº de configurações testadas. Pune garimpo |
| **Placebo do gatilho** | sortear qual nome é a cabeça e ver se o real ganha. Testa o **mecanismo** |
| **Giro** | soma das mudanças absolutas de peso, duas pontas |
| **Market-neutral** | beta zero contra o Ibovespa. O benchmark passa a ser o CDI |
| **BTC** | aluguel de ações para a ponta vendida — **60% do custo total** |
