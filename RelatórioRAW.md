# SINAPSE — Relatório Completo da Estratégia

> **Documento-mestre.** Versão longa e completa, escrita para ser comprimida no PPT de 5 páginas.
> Reflete o estado **final** do código (commit `76b9037`) e da estratégia.
> Todos os números vieram de uma única execução do pipeline. Nada é estimativa.

---

# 0. Identidade do robô

| | |
|---|---|
| **Nome** | **SINAPSE** |
| **Classe de ativos** | Ações (renda variável brasileira, B3) |
| **Universo** | 543 ações com histórico, ~140 na carteira por dia |
| **Frequência** | Rebalanceamento **diário suavizado**; grafo reconstruído **mensalmente** |
| **Benchmark** | **CDI** (performance absoluta). Ibovespa só como referência de descorrelação |
| **Tipo** | Long-short **market-neutral**, autofinanciada |
| **AUM de referência** | R$ 100 milhões |

## Por que "Sinapse"

Uma sinapse é a junção onde um neurônio transmite sinal a outro. O impulso não nasce no destino
— ele **chega** de outro lugar, com atraso e com intensidade variável.

É exatamente o que a estratégia faz: ela **não** analisa a empresa em que investe. Ela observa o
choque numa empresa **vizinha** — mais líquida, mais coberta por analistas — e aposta que o
impulso vai percorrer a rede até chegar na empresa lenta.

O nome também descreve a arquitetura: um **grafo** de conexões, onde cada elo transmite um sinal
com direção e intensidade. Não é metáfora decorativa; é a estrutura de dados literal do código.

## Identidade visual

```
         ●━━━━━━━━▶ ○
      líquido      ilíquido
     (dispara)     (recebe)

   SINAPSE
   o sinal chega antes do preço
```

Paleta: azul (sinal), violeta (propagação), cinza (ruído removido).

---

# 1. Conceito da estratégia

## 1.1 A ineficiência explorada

> **Atenção é um recurso escasso.** A Vale tem 20 analistas cobrindo e bilhões negociados por
> dia. A Usiminas tem uma fração disso. Quando sai uma notícia que afeta o ramo inteiro — preço
> do minério, câmbio, juro — o nome líquido reprecifica em minutos. O ilíquido leva semanas.

O choque de hoje na ação líquida é uma **prévia** do que a ação lenta fará depois.

## 1.2 A hipótese, em uma linha

**A informação difunde do nome líquido para o nome ilíquido, dentro do mesmo ramo econômico.**

Isso tem literatura estabelecida:

| trabalho | achado |
|---|---|
| Lo & MacKinlay (1990) | ações grandes lideram pequenas |
| **Hou (2007)** | **o lead-lag é DENTRO da indústria, não entre indústrias** |
| Cohen & Frazzini (2008) | links econômicos preveem retorno |
| Blitz, Huij & Martens (2011) | momento residual (controle desta estratégia) |

**Não estamos alegando descoberta.** Estamos testando com rigor se um efeito documentado
sobrevive na B3, com custo real. Um fundo não ganha dinheiro com efeito inédito — ganha
implementando bem efeitos conhecidos. E uma hipótese com literatura é muito mais difícil de
atacar como *data mining*: não escolhemos a hipótese olhando os dados.

## 1.3 A hipótese ORIGINAL foi refutada — e isso é o resultado mais importante

Este projeto começou com outra tese, **pré-registrada** em `CRITERIOS_GRAFO_MANUAL.md`:

> *"`concorrente` = −1: a desgraça de um é a sorte do outro. O capital e os clientes migram de A
> para B."*

**Os dados derrubaram isso.** Concorrentes **co-movem**: Vale e CSN dependem do mesmo minério de
ferro, e essa exposição compartilhada domina qualquer efeito de soma-zero. A correlação T+1 é
**positiva**, não negativa.

**Como a inversão foi decidida** — e é isto que a torna defensável:

```
  2016 ─────────── 2020  │  2021 ─────────── 2025
    decide a direção     │    mede UMA vez
    congela em CSV       │
```

Um analista parado em 31/12/2020, sem ver nada de 2021, escolheria `+1` do mesmo jeito
(t = 4,50 in-sample). O controle — mantendo `−1` — dá **alfa negativo** fora da amostra.

> **A tese substituta não é "propagação de soma-zero entre rivais". É difusão de informação
> intra-indústria.** E o teste bidirecional confirma a assimetria que a difusão prevê: o sentido
> reverso (pequeno → grande) é mais fraco nas **6 categorias, sem exceção**.

## 1.4 A evidência de que o mecanismo é real

**O placebo do gatilho.** Mantivemos o subsetor, o número de líderes e os satélites — e
**sorteamos qual nome é a cabeça**, 300 vezes:

| métrica | real | placebo (média) | **p** |
|---|---|---|---|
| IC in-sample | +0,0464 | +0,0321 | **0,010** |
| IC out-of-sample | +0,0221 | +0,0075 | **0,003** |
| IC total | +0,0312 | +0,0168 | **<0,001** |
| Sharpe out-of-sample | −0,150 | −0,540 | **<0,001** |

**Escolher a cabeça pelo volume negociado bate 300 cabeças sorteadas em todas as janelas.**
A liquidez carrega informação — o mecanismo não é aleatório.

---

# 2. Modelagem

![fluxograma](fase%207%20-%20relatorio/saida/10_fluxograma_pipeline.png)

## 2.1 O que acontece em um dia

**Passo 1 — Isolar o choque.** A VALE3 subiu 3% hoje. Quanto disso é *da Vale* e quanto é "a
bolsa subiu"? Uma regressão móvel de 252 pregões separa:

```
retorno_VALE = α + β · Ibovespa + ε
                                 ↑
                          o choque limpo
```

> **Por que NÃO removemos o setor.** A versão anterior subtraía também um índice setorial. Mas a
> tese é difusão **intra-indústria** — o termo setorial removia exatamente a informação que se
> quer propagar. Removê-lo elevou o IC de +0,0506 para **+0,0621**.
>
> Bônus: com a regressão simples, o β **é** o beta de mercado (mediana ~1,0), que é o que o hedge
> precisa. Na versão bivariada era um coeficiente *parcial* (mediana 0,335) e o book ficava
> sub-hedgeado.

**Passo 2 — Acumular no horizonte certo.** Somamos o choque nos 231 pregões que terminam 22 dias
atrás (janela "12-1", padrão da literatura).

![horizonte](fase%207%20-%20relatorio/saida/05_ic_por_horizonte.png)

| horizonte | T+1 | T+5 | T+21 | T+63 | T+126 |
|---|---|---|---|---|---|
| IC | +0,0074 | +0,0132 | +0,0219 | +0,0418 | +0,0457 |
| IC/√h | 0,0074 | 0,0059 | 0,0048 | 0,0053 | 0,0041 |

> **A tese original dizia T+1. Os dados dizem meses.** Se o efeito fosse instantâneo, `IC/√h`
> cairia 91% de T+1 a T+126. Ele cai **45%**. O sinal acumula quase como difusão pura.
>
> **Isso não é um parâmetro calibrado — é um fenômeno medido.** E tem consequência prática: o
> giro caiu de 9,7% para 4,8% ao dia.

**Passo 3 — Propagar pelo grafo.**

![regra](fase%207%20-%20relatorio/saida/11_diagrama_regra_grafo.png)

O grafo é **mecânico**, reconstruído todo mês:

```
Para cada subsetor, mensalmente:
  1. ordena por volume negociado dos 21 pregões ANTERIORES   ← point-in-time
  2. deduplica ON/PN da mesma empresa
  3. os K mais líquidos formam a CABEÇA
  4. cada cabeça manda sinal para TODOS do ramo, ex-self
```

**A peça central é o passo 4:** a cabeça também **recebe**. Isso cria elos **mútuos** entre os
líquidos de cada ramo — `VALE3↔CSNA3`, `PETR3↔PETR4`, `SUZB3↔KLBN11`.

**Ensemble de 6 variantes** (K ∈ {2,3,5} × peso ∈ {igual, ADTV}). Todas entram; nenhuma é
escolhida por desempenho.

## 2.2 A validação do grafo mecânico

Antes da regra, escrevemos **58 elos à mão** com análise fundamentalista. Depois perguntamos se
uma regra mecânica os encontraria:

> **A regra reproduz 38 dos 40 elos intra-setor escritos à mão (95%), todos também na direção
> inversa.**

**A equipe não descobriu pares — descobriu uma topologia.** E topologia é mecanizável. Os dois
não reproduzidos caem no filtro de subsetores com menos de 4 membros.

Isso resolve três problemas de uma vez: o grafo passa a ser **point-in-time**, **se atualiza
sozinho** e **não tem julgamento humano** para defender.

## 2.3 Da nota à posição

O z-score transversal **é** a carteira-alvo. Passa por uma esteira de restrições:

| etapa | o que faz |
|---|---|
| vol-targeting ⇄ travas (3 rodadas) | escala para mirar 12% de vol; as travas têm a palavra final |
| suavização dos pesos (63 pregões) | a carteira executada é a média das últimas 63 carteiras-alvo |
| reaplicar travas | *(bug corrigido: a suavização estourava a trava de liquidez, que varia no tempo)* |
| máscara de negociabilidade | zera peso de ação que não negociou |
| hedge de beta | posição vendida em Ibovespa sintético que zera o beta |
| `shift(1)` | lag de execução T+1 |

## 2.4 Por que "diário" não significa girar a carteira toda

Duas médias móveis empilhadas: **12 meses no sinal**, **63 pregões nos pesos**. A carteira é
*decidida* todo dia, mas se *move* devagar.

> É a diferença entre um volante travado em 12 posições fixas (rebalanceamento mensal) e um
> volante livre que você segura com firmeza. O segundo responde a informação nova na hora, mas
> não dá guinada.

Rebalancear mensal descartaria informação por até 21 dias. Diário-suavizado captura o sinal na
hora e paga o custo só na margem.

## 2.5 Tabela de parâmetros

<!-- inserir: fase 7 - relatorio/saida/16_tabela_parametros.md -->

Ver `saida/16_tabela_parametros.md`. Os 7 primeiros foram **pré-registrados antes de qualquer
backtest** — e o histórico do Git comprova (`PARAMETROS.md` commitado em 21/07; primeiro backtest
em 29/07).

---

# 3. Backtest

## 3.1 Metodologia

O motor **não decide nada**. Ele recebe a matriz de pesos pronta e faz uma multiplicação
matricial: `P&L = Σ(peso × retorno) − custo`. Sem loop, sem renormalização, sem rebalanceamento
inventado.

**Lag de execução T+1**: a decisão tomada com o fechamento de terça só é executada na quarta.

## 3.2 Tratamento de vieses

| viés | como foi tratado | custo honesto |
|---|---|---|
| **Sobrevivência (preços)** | COTAHIST da B3 tem as empresas mortas. Cobertura 66% → **98%** | **+19,9% → +8,7%** |
| **Sobrevivência (grafo)** | grafo mecânico usa o universo point-in-time; empresa morta entra e sai sozinha | −0,58 p.p./ano |
| **Retrovisão** | a regra só usa volume **passado**; um analista em 2016 rodaria a mesma regra | — |
| **Look-ahead de execução** | `shift(1)` obrigatório; um dia a mais custaria 32% do alfa (medido e declarado) | — |
| **Data snooping** | protocolo IS/OOS congelado + walk-forward | — |
| **Comparações múltiplas** | **Deflated Sharpe com N = 294 declarado** | — |

> Duas vezes o número **piorou** por uma correção e foi adotado assim mesmo. Remover o viés de
> sobrevivência custou metade do resultado. **Publicar o número pior é o que torna o resto
> crível.**

![evolução](fase%207%20-%20relatorio/saida/17_evolucao_correcoes.png)

## 3.3 Os bugs que encontramos em nós mesmos

| bug | efeito |
|---|---|
| `mapeamento_setores.csv` nunca carregado | o "choque limpo" era **retorno bruto disfarçado**, desde sempre |
| CDI descontado duas vezes no Sharpe | Sharpe −1,40 → **+0,18** |
| Trava de liquidez violada em 59,6% dos dias | backtest com posições **não executáveis** → 0,0% |
| Posição fantasma em ação delistada | 2,07% do book → **0,00%** |
| Mapa setorial 79% vazio | alfa +11,6% → **+27,9%** |
| Resíduo virava retorno bruto sem 252 obs | 13,4% das células — **100% de 2016** |
| Beta NaN tratado como zero no hedge | 13,6% das posições **sem hedge** |

Cada correção tem **teste de regressão que falha no código antigo e passa no novo**.

> O bug do resíduo tem uma consequência que preferimos reportar: ele **inflava** o t in-sample do
> nosso próprio protocolo de validação, de 1,39 para 2,14. Corrigi-lo enfraqueceu nossa própria
> evidência.

## 3.4 Custo de transação — três camadas

A maioria dos backtests usa um custo único de 5 bps. **Isso é um número de large cap líquida**, e
73% do nosso giro está abaixo de R$ 150 MM de ADTV.

![custo](fase%207%20-%20relatorio/saida/12_custo_e_breakeven.png)

| camada | valor | natureza |
|---|---|---|
| emolumentos + liquidação B3 | 2,3 bps | **observável** |
| corretagem institucional | 3,0–4,0 bps | contratual |
| meio-spread por faixa de ADTV | 2 / 5 / 11 / 24 bps | estimado |
| impacto de mercado | `0,4 × σ₆₀ × √(participação)` | estimado |
| **aluguel BTC** (ponta vendida) | 1,0–6,0 % a.a. | estimado |

**Custo total: 4,02% ao ano = 33,6 bps por unidade de giro.**

> **O número que não depende da nossa calibragem:**
> **alfa por unidade de giro = 33,7 bps · custo = 33,6 bps.**
>
> Se acharem nosso custo pessimista, o alfa por giro continua o mesmo. Se acharem otimista,
> também. O resultado depende de uma **propriedade medida do sinal**, não de uma premissa nossa.

**Achado:** no período recente, **60%+ do custo é aluguel da ponta vendida** — carrego
proporcional ao book, imune a qualquer redução de giro.

## 3.5 Validação

**Protocolo IS/OOS.** O in-sample (2016–2020) é a zona onde se pode testar à vontade. O
out-of-sample (2021–2025) só vale porque se olha **uma vez**.

**Walk-forward.** Para o ano Y, os parâmetros são re-decididos só com 2016..Y−1:

```
decide com 2016-2018 → testa 2019      decide com 2016-2021 → testa 2022
decide com 2016-2019 → testa 2020      decide com 2016-2022 → testa 2023
decide com 2016-2020 → testa 2021      decide com 2016-2023 → testa 2024
                                        decide com 2016-2024 → testa 2025
```

7 anos, **100% out-of-sample**, e não "gasta" período nenhum.

---

# 4. Análise de resultados

## 4.1 Retorno acumulado

![curva](fase%207%20-%20relatorio/saida/01_retorno_acumulado.png)

| métrica | Sinapse (alfa) | **Fundo (CDI+alfa)** | Ibovespa | CDI |
|---|---|---|---|---|
| Retorno acumulado | +36,4% | **+229,9%** | +279,8% | +141,9% |
| Retorno anualizado | +3,20% | **+12,89%** | +14,52% | +9,39% |
| Volatilidade | 7,64% | **7,64%** | 23,33% | 0,24% |
| **Sharpe** | 0,45 | **1,63** | 0,70 | — |
| Sortino | 0,64 | **2,34** | 0,89 | — |
| **Drawdown máximo** | −15,8% | **−8,6%** | **−46,8%** | 0,0% |
| Calmar | 0,20 | **1,50** | 0,31 | — |

> **O produto entregue ao cotista é o fundo: CDI + alfa.** Ele rende **+229,9%** contra +141,9%
> do CDI — **excesso de +88,0%** — com **um quinto do drawdown do Ibovespa**.

## 4.2 Drawdown e neutralidade

![drawdown](fase%207%20-%20relatorio/saida/02_drawdown.png)
![distribuição](fase%207%20-%20relatorio/saida/09_distribuicao_neutralidade.png)

**Correlação com o Ibovespa: −0,01.** A nuvem de pontos não tem inclinação — a neutralidade não
é alegação, é medida.

**No stress, ela funciona:**

| janela | Sinapse | Ibovespa |
|---|---|---|
| **COVID (fev–abr/2020)** | **+2,47%** | **−29,62%** |
| Joesley (mai/2017) | −0,06% | −8,80% |
| Americanas (jan/2023) | +0,69% | +2,36% |
| 2022 inteiro | −3,18% | +4,97% |

> O dano não vem de evento de mercado — vem de **regime**. 2022–2023 corridos, sem evento
> identificável, foram os dois piores anos.

## 4.3 Por ano

![anual](fase%207%20-%20relatorio/saida/03_performance_anual.png)

<!-- inserir: fase 7 - relatorio/saida/14_tabela_desempenho_anual.md -->

**6 de 9 anos positivos.** O melhor (2020, +13,9%) foi o pior do Ibovespa. O pior (2025, −3,4%)
foi um dos melhores dele. Isso é descorrelação, não sorte.

## 4.4 Carteira e execução

![giro](fase%207%20-%20relatorio/saida/04_giro_e_posicoes.png)
![exposições](fase%207%20-%20relatorio/saida/06_exposicoes.png)

| | |
|---|---|
| ações na carteira | ~140/dia |
| giro | 4,8%/dia |
| exposição líquida | ≈ 0 (dollar-neutral) |
| dias com posição no teto de 5% | **3,3%** (era 77%) |
| concentração (top-5 do P&L) | **13,2%** (era 79%) |

<!-- inserir: fase 7 - relatorio/saida/15_tabela_sinais_exemplo.md -->

> A carteira **não entra e sai** de posições — ela ajusta o *tamanho* continuamente. Uma ação
> típica fica meses no book mudando de peso, e troca de lado quando o choque acumulado do seu
> ramo inverte.

## 4.5 Estabilidade

![rolling](fase%207%20-%20relatorio/saida/08_rolling_sharpe_vol.png)
![heatmap](fase%207%20-%20relatorio/saida/07_heatmap_mensal.png)

## 4.6 O que NÃO funciona — e por quê

Esta seção é deliberada. Um relatório que só mostra o que deu certo não é análise.

**(a) A propagação não bate a persistência.** Comparamos com o controle óbvio — o momento
residual do **próprio nome**:

| | alfa da propagação sobre a persistência | t |
|---|---|---|
| total | **+0,03%/ano** | **+0,01** |

**A tese "difusão entre nomes" não se separa de "o nome tem momento residual próprio".** É a
hipótese nula da nossa própria tese, e ela não é rejeitada.

**(b) A estratégia carrega momento de indústria.** Carga t = 6,2 no fator. Depois de controlar
por ele e pelos clássicos, o alfa out-of-sample é **−0,02% (t = −0,01)**.

**(c) O Deflated Sharpe reprova.** Com N = **294** configurações declaradas ao longo do projeto,
DSR = 0,005 no walk-forward. **O que sustenta o resultado é o placebo, não o Sharpe.**

**(d) O in-sample não seleciona.** Testamos duas decisões (teto de satélites, neutralização
contra beta) sob protocolo. A grade out-of-sample completa **não tem nenhuma célula com Sharpe
líquido positivo — exceto exatamente a que ambos os critérios rejeitaram**. Terceira vez que o
in-sample escolhe errado.

> Por isso **não adotamos nenhuma das duas**: adicionar parâmetros escolhidos por um critério que
> comprovadamente não seleciona destruiria a propriedade mais valiosa da configuração —
> **zero parâmetros escolhidos por desempenho**.

**(e) A volatilidade fica em 7,6%, não nos 12% do mandato.** Não é escolha: atingir 12% exigiria
peso de 8,3% por nome, acima da trava de 5%. E o Sharpe é **invariante à escala** — o gap não
explica o resultado. Alavancar 1,57x levaria o custo de impacto a crescer mais rápido que o
retorno.

---

# 5. Conclusão e próximos passos

## 5.1 Onde a estratégia está

**O mecanismo é real.** O placebo confirma com p ≤ 0,010: escolher a cabeça pela liquidez bate
300 sorteios. A neutralidade funciona (COVID +2,5% contra −29,6%).

**O tamanho não é.** A tese é verdadeira e **pequena demais para pagar com folga o custo de
negociá-la**: 33,7 bps de alfa contra 33,6 de custo.

> **Sabemos disso porque medimos as duas coisas.**

## 5.2 Viabilidade prática

| | |
|---|---|
| Capacidade | ~R$ 100 MM. A R$ 1 bi o alfa some |
| Executabilidade | trava de liquidez com **0 violações** em 93.022 posições |
| Gargalo real | **aluguel da ponta vendida** — 60%+ do custo, imune a redução de giro |

## 5.3 Limitações declaradas

1. **Deflated Sharpe reprova** (N = 294).
2. **A propagação não faz spanning** sobre o momento residual próprio (t = 0,01).
3. **Carga em momento de indústria** t = 6,2.
4. **6 de 9 anos positivos** — 2022, 2023 e 2025 negativos.
5. **Breadth efetiva de 14,2** contra ~140 posições: satélites do mesmo ramo recebem sinal quase
   idêntico (correlação +0,884). **Mais posições não é mais aposta.**

## 5.4 Próximos passos, em ordem de retorno esperado

| # | ação | por quê |
|---|---|---|
| 1 | **Trocar o short de ações por venda de índice/futuro** | 60% do custo é aluguel. Sozinho, levaria o Sharpe líquido de −0,03 para +0,145 |
| 2 | **Aumentar a breadth via mais SUBSETORES** | o teto é o nº de ramos (~23), não o nº de nomes |
| 3 | **Melhorar a independência dos choques** | fatores explícitos (minério, câmbio, juro) no lugar do IBOV puro |
| 4 | **Grafo cego, construído por terceiro** | única forma de testar se a curadoria humana generaliza |
| 5 | **Trava de exposição líquida** | hoje inexistente; chega a ±38% em dias extremos |

---

# 6. Uso de IA Generativa

A IA foi usada como **auditor adversarial**, não como gerador de código. O valor não veio de
escrever mais rápido — veio de **encontrar o que estava errado**.

## 6.1 Arquitetura de uso

```
                    ┌─ quant-analyst  → auditoria estatística, protótipos, placebos
   coordenação ─────┼─ risk-manager   → controles de risco, exposições, capacidade
                    └─ fintech-eng    → custo realista, aluguel, execução
```

Subagentes **independentes**, com contexto próprio, rodando em paralelo. Cada um recebeu
instrução explícita de ser adversarial: *"não seja gentil; o objetivo é encontrar o que a banca
encontraria."*

## 6.2 Exemplos concretos de valor agregado

| # | o que a IA encontrou | impacto |
|---|---|---|
| 1 | `mapeamento_setores.csv` nunca era carregado | o sinal **nunca** tinha feito o que dizia fazer |
| 2 | CDI descontado duas vezes no Sharpe | −1,40 → +0,18 |
| 3 | Trava de liquidez violada em 59,6% dos dias | backtest não executável → executável |
| 4 | Resíduo virava retorno bruto sem 252 obs | inflava nosso próprio t de 1,39 para 2,14 |
| 5 | **O horizonte estava errado** | IC/√h revelou difusão de meses, não de 1 dia |
| 6 | **A regra mecânica reproduz 95% do grafo manual** | transformou curadoria em algoritmo |
| 7 | O custo de 5 bps era 4x otimista | modelo de 3 camadas |

## 6.3 Limitações encontradas — e elas importam

**A IA errou, e errou de formas instrutivas:**

1. **Propôs uma hipótese e refutou a si mesma.** Sugeriu que a autocorrelação do IC inflava o
   t-stat. Mediu: ρ(1) ≈ 0. **A hipótese estava errada e o registro ficou no código.**
2. **Introduziu um bug num script de verificação.** Ao validar um resultado, escreveu uma
   regressão que mascarava 46% dos dados por tratamento errado de NaN — e chegou à conclusão
   oposta. **Foi outro subagente que encontrou.**
3. **Propôs um caminho que os dados invalidaram.** Sugeriu buscar elos cross-setor via Matriz de
   Insumo-Produto do IBGE. A medição mostrou que elos cross-setor são **imateriais** no horizonte
   relevante. Uma semana de trabalho evitada.
4. **Tendeu a otimismo em resultados próprios.** Precisou de instrução explícita para reportar
   resultado nulo sem maquiar.

> **A lição operacional:** IA usada como **um** analista é perigosa. Usada como **vários
> analistas adversariais que se auditam**, ela encontra o que um humano sozinho não encontraria.
> Toda afirmação relevante deste relatório foi verificada de forma independente por um segundo
> agente ou por medição direta.

## 6.4 O que a IA NÃO fez

Não escolheu parâmetros olhando o resultado. Não decidiu a tese. Não escreveu o relatório sem
verificação. Todas as decisões de protocolo — congelar, medir uma vez, não recalibrar — foram
impostas como restrição e verificadas.

---

# 7. Ficha técnica

| bloco | arquivo | função |
|---|---|---|
| 1 | `s1c_retornos_completo.py` | preços sem viés de sobrevivência (yfinance + COTAHIST) |
| 2 | `s2_universo.py` | universo point-in-time e ADTV |
| 4 | `s4_sinapse_sinal.py` | choque limpo, acumulação 12-1, propagação |
| 4d | `s4d_grafo_regra.py` | **grafo mecânico mensal** |
| 5 | `s5_portfolio_builder.py` | vol-targeting, travas, hedge, lag T+1 |
| 3 | `s3_backtest.py` + `s3b_custos.py` | P&L e custo em 3 camadas |
| 6 | `s6`–`s13` | validação OOS, breadth, inferência, placebos |
| 7 | `r1_visuais.py` | acervo visual |

**Reprodução:** blocos 2 → 1c → 4d → 4 → 5 → 3. Um pipeline completo roda em ~3 minutos.

---

# Apêndice — Glossário

| termo | o que é |
|---|---|
| **IC** | correlação entre a nota que damos hoje e o retorno de amanhã. 0,01 é minúsculo — mas o cassino ganha com 2,7% de vantagem repetida milhares de vezes |
| **Breadth** | número de apostas **independentes**. 140 posições que se movem juntas são **uma** aposta, não 140 |
| **Lei Fundamental** | `IR ≈ IC × √breadth`. Vantagem pequena × muitas apostas = negócio |
| **IS / OOS** | período onde se pode testar à vontade / período que só vale se olhado **uma vez** |
| **Walk-forward** | recalibra a cada ano com o que se sabia, opera o ano seguinte. 100% out-of-sample |
| **Deflated Sharpe** | Sharpe corrigido pelo nº de configurações testadas. Pune garimpo |
| **Placebo do gatilho** | sortear qual nome é a cabeça e ver se o real ganha. Testa se o **mecanismo** é real |
| **Giro** | soma das mudanças absolutas de peso, duas pontas |
| **Market-neutral** | beta zero contra o Ibovespa. O benchmark passa a ser o CDI |
