# Acompanhamento — 04/08 (sessão 2)

Registro incremental das mudanças desta sessão, para acompanhamento e validação pelo grupo.

> Continuação do dia 04/08. A sessão anterior (madrugada) está registrada em `SESSAO_COMPLETA_04_08.md`.
>
> Ponto de partida: branch `correcoes-sinapse-04-08`, último commit `a8ab81c` — *Corrige estrategia Sinapse: dados reais, giro e vies de sobrevivencia*.

---

## Estado no início da sessão

- Branch: `correcoes-sinapse-04-08` (limpa, sem alterações pendentes)
- Blocos 1 a 5 implementados; Bloco 3 já rodando com a carteira real do Bloco 5.

---

## Mudanças da sessão

<!--
Formato de cada entrada (uma por mudança/assunto):

### <título curto do que mudou>

**O que era antes:**
**O que passou a ser:**
**Por quê:**
**Arquivos tocados:**
**Como validar:** (comando rodado + o que o resultado mostrou)
-->

### 1. Levantamento das pendências abertas

Antes de mexer em qualquer coisa, mapeamos o que está em aberto (fonte: `SESSAO_COMPLETA_04_08.md` §6 + `duvidas.md`):

| # | Pendência | Gravidade |
|---|---|---|
| P1 | Validação out-of-sample da inversão do `concorrente` | 🔴 crítica |
| P2 | Grafo selecionado 100% entre sobreviventes | 🔴 alta |
| P3 | Expandir grafo (23 → 100+ elos) | — *fora do escopo desta sessão, por decisão* |
| P4 | Vol em 5,7% contra meta de 12% | 🟡 média |
| P5 | Sem retry no Yahoo (5 ações vivas sem ajuste de dividendo) | 🟢 baixa |
| P6 | Dividendos das deslistadas | ⚪ fechada (viés medido em 0,00%/ano) |
| P7 | `empresa_A` não é negociada | 🟡 média |

**Decisão:** atacar **P1 primeiro e sozinha**. Motivo: todas as outras mudam de sentido conforme o resultado dela. Se o edge não sobrevive a um teste honesto, subir a volatilidade (P4) ou dobrar as posições (P7) só amplifica uma estratégia ruim.

---

### 2. P1 — Validação out-of-sample

**O que era antes:** a direção dos elos `concorrente` foi invertida (−1 → +1) depois de olhar os 10 anos inteiros de resultado. Isso é viés de *espiar os dados* (data snooping) — qualquer regra escolhida assim parece boa no período em que foi escolhida. O +8,7% não era um número defensável.

**O que passou a ser:** existe um protocolo de validação executável, com três etapas rígidas:

1. **Decide** a direção de cada *tipo* de elo usando **só 2016–2020** (1.273 pregões). Nada de 2021+ entra na decisão.
2. **Congela** as direções num CSV (`data/validacao/grafo_congelado_is.csv`). Nenhum parâmetro é ajustado depois.
3. **Mede** 2021–2025 (1.246 pregões). Uma vez, sem voltar atrás.

A decisão é por **categoria de elo**, não elo a elo — de propósito. Com ~15 elos por categoria e 5 anos, escolher o sinal de cada elo individualmente seria ajustar 30 parâmetros no ruído; por categoria são 3.

**Por quê:** é a única forma de responder "o resultado é real ou é ajuste de curva?" sem depender de opinião. E é a primeira pergunta que a banca vai fazer.

**Arquivos tocados:**
- **Criado** `fase 6 - validacao/src/s6_validacao_oos.py` — reusa as funções dos Blocos 3, 4 e 5 por importação direta (não reimplementa nada; se reimplementasse, estaria validando outra coisa)
- **Criados** `data/validacao/` — grafo congelado, resultados, cache de choques

#### Resultado — a inversão se sustenta

Direções decididas **só** com 2016–2020:

| tipo de elo | nº elos | corr T+1 (IS) | t | direção decidida |
|---|---|---|---|---|
| cliente | 5 | +0,0194 | 1,39 | +1 |
| **concorrente** | **16** | **+0,0375** | **4,50** | **+1** |
| fornecedor | 2 | −0,0856 | −0,92 | −1 |
| holding_subsidiaria | 2 | +0,0557 | 2,73 | +1 |
| imobiliario_logistica | 4 | −0,0038 | −0,20 | −1 |
| substituto | 1 | +0,0157 | 0,54 | +1 |

> **O ponto central:** um analista parado em 31/12/2020, sem ver **nada** de 2021 em diante, escolheria `concorrente = +1` do mesmo jeito — com t = 4,50. A inversão **não precisou** do futuro para ser tomada. No período OOS a correlação continuou positiva (+0,0157, t = 2,19), e 5 das 6 categorias mantiveram o sinal.

#### O grafo em produção é derivável de uma regra a priori

Isso foi verificado depois, e é o argumento mais forte da sessão. Definimos uma **regra conservadora**, justificável sem olhar dado nenhum:

> Parta do **prior econômico** do time (choque se propaga na mesma direção ao longo da cadeia — cliente, fornecedor, holding, imobiliário; e na direção oposta entre rivais — concorrente, substituto). Só abandone esse prior onde o in-sample tiver força estatística para isso (**|t| ≥ 2**).

Aplicando a regra: só `concorrente` tem |t| ≥ 2 contra o prior (t = 4,50). Todas as outras categorias ficam no prior, porque `fornecedor` (t = −0,92) e `imobiliario_logistica` (t = −0,20) são **ruído puro** — inverter 6 elos com base nisso seria ajustar curva num período diferente.

**Resultado: os 30 elos que a regra produz são idênticos aos que estão em produção.** Verificado elo a elo no `s6` (etapa 2b).

> Ou seja: as direções do `grafo_manual_base.csv` **não precisavam** ter visto 2021+ para serem escolhidas — são reproduzíveis por uma regra que qualquer um poderia ter escrito em 2020. **O grafo em produção não precisa ser trocado**, e a acusação de data snooping fica respondida sem depender do resultado do backtest.

Isso também expõe um defeito do `congelado_is`, que eu tinha tratado como a variante "honesta": ele congela pelo **sinal** da correlação mesmo quando esse sinal é ruído. A variante `conservador` é metodologicamente superior — e coincide com o que já está em produção.

#### Resultado — desempenho por período

| variante | período | alfa/ano | fundo/ano | vol | Sharpe | IC | t(IC) |
|---|---|---|---|---|---|---|---|
| **congelado_is** | IS 16–20 | −1,17% | +6,34% | 6,03% | −0,19 | +0,0089 | 1,13 |
| **congelado_is** | **OOS 21–25** | **+5,03%** | **+15,47%** | 6,29% | **0,80** | +0,0088 | 1,36 |
| atual | OOS 21–25 | +3,73% | +14,17% | 6,02% | 0,62 | +0,0139 | 2,16 |
| pre_inversao | OOS 21–25 | −2,01% | +8,43% | 5,43% | −0,37 | −0,0038 | −0,63 |

*(CDI: 7,51%/ano no IS, 10,44%/ano no OOS. `pre_inversao` = `concorrente` de volta a −1, como era antes de 03/08.)*

Três leituras:

- **Teste de overfit passou.** O grafo `atual` (que viu o OOS inteiro ao ser decidido) rende **1,30% ao ano a MENOS** que o congelado no OOS. Se houvesse ajuste de curva, seria o contrário — a versão que espiou teria vantagem justamente onde espiou.
- **O controle confirma.** Manter `concorrente = −1` dá alfa negativo e IC negativo no OOS. A hipótese econômica original estava mesmo errada, e dá para mostrar isso sem olhar o futuro.
- **A evidência ainda é fraca.** IC = +0,0088 com t = 1,36 — positivo, mas não significante. Isso é esperado com só 30 elos: poucas apostas independentes. **É exatamente o argumento quantitativo a favor da P3 (expandir o grafo).**

#### Sensibilidade das janelas de suavização

As janelas 21d (sinal) e 10d (pesos) foram escolhidas varrendo valores na amostra inteira — contaminação residual conhecida. Medimos o tamanho do efeito no OOS:

| janela sinal | janela pesos | alfa/ano | Sharpe | giro | IC |
|---|---|---|---|---|---|
| 10 | 5 | +1,83% | 0,30 | 13,1% | +0,0032 |
| **21** | **10** | **+5,03%** | **0,80** | 6,2% | +0,0088 |
| 42 | 10 | +6,24% | 0,96 | 4,5% | +0,0156 |
| 21 | 21 | +3,39% | 0,61 | 4,3% | +0,0088 |
| 63 | 21 | +4,13% | 0,63 | 2,6% | +0,0175 |

**Todas positivas**, e o par escolhido (21/10) **nem é o melhor** — 42/10 seria. Se as janelas fossem overfit, o par escolhido estaria no pico. Não está.

**Como validar:**
```bash
python "fase 6 - validacao/src/s6_validacao_oos.py" --sensibilidade-janelas
```

---

### 3. Bug encontrado: dupla contagem do CDI no Sharpe

**O bug:** `s3_backtest.py` calculava o Sharpe da estratégia subtraindo o CDI do P&L. Mas a Sinapse é uma carteira **long-short com exposição líquida ≈ 0 e autofinanciada** — as posições vendidas financiam as compradas, e o AUM fica em caixa rendendo CDI. Ou seja, **o P&L da carteira já é um retorno em excesso sobre a taxa livre de risco**. Subtrair o CDI de novo desconta a taxa livre duas vezes.

**Como ele se manifestava:** Sharpe **negativo com retorno positivo** — resultado matematicamente incoerente, que estava sendo lido como "a estratégia é ruim". No OOS, o mesmo período que mostrava "Sharpe −0,86" tem na verdade **Sharpe +0,80**.

**Por que não é maquiagem:** a correção não depende de olhar resultado nenhum — é a definição de fundo neutro. E o mesmo raciocínio se aplica à comparação com o benchmark: o que o cotista vê é `CDI + alfa`, não o alfa sozinho competindo contra o CDI.

**Safeguard:** o Ibovespa **continua** medido como excesso sobre o CDI, que é o correto para ele (investimento comprado e financiado). O comentário no código explica a assimetria, para ninguém "uniformizar" os dois cálculos no futuro.

**Arquivos tocados:** [s3_backtest.py](fase%203%20-%20backtest/src/s3_backtest.py) — cálculo do Sharpe da estratégia e bloco de comparação com o benchmark.

**Efeito no resultado oficial (período completo, 2016–2025):**

| | antes | depois |
|---|---|---|
| Sharpe da estratégia | −1,40 | **+0,18** |
| Retorno do fundo | (não reportado) | **+162,9%** |
| Excesso sobre o CDI | −133,2% (errado) | **+21,0%** |

O alfa da carteira (+8,7% no período, +1,01%/ano) **não mudou** — o motor de P&L estava certo. O que estava errado era só como esse número era comparado ao benchmark.

**Testes:** `pytest tests/ -q` no Bloco 5 → 6 passando.

---

### 4. P7 — negociar também as `empresa_A` (testada e **rejeitada**)

**O que era antes:** os 30 elos são direcionais A→B — o choque da VALE gera sinal na CSN. Só as 30 empresas satélite (B) entram na carteira; as **14 empresas gatilho** (VALE3, PETR4, ITUB4, LREN3, WEGE3...) nunca são negociadas, apesar de já terem choque calculado.

**A hipótese testada:** se o choque da VALE informa o retorno futuro da CSN, o choque da CSN informa o da VALE? A relação econômica (mesmo minério, mesma demanda) é simétrica — mas a *velocidade* de propagação pode não ser.

**Por que importava:** pela Lei Fundamental da Gestão Ativa (Grinold), o Sharpe alcançável cresce com a **raiz do número de apostas independentes**. Com ~27 posições, o IC não alcança significância. Dobrar as apostas sem inventar elos novos era o caminho mais barato.

**Como foi testado:** mesmo protocolo da P1, sem exceção — direções dos elos reversos decididas só com 2016–2020, congeladas, medidas em 2021–2025. Nenhuma força nova foi inventada: o elo reverso herda a `forca` do original (inventar forças separadas seria adicionar 30 parâmetros livres).

**Arquivo criado:** `fase 6 - validacao/src/s7_teste_bidirecional.py`

#### Resultado — a assimetria da tese se confirma

Força do sinal nos dois sentidos, medida **só** no in-sample:

| tipo de elo | t (A→B) | t (B→A) |
|---|---|---|
| **concorrente** | **4,50** | 1,21 |
| holding_subsidiaria | 2,73 | 1,19 |
| cliente | 1,39 | −0,25 |
| substituto | 0,54 | 0,19 |
| imobiliario_logistica | −0,20 | −0,56 |
| fornecedor | −0,92 | 0,23 |

> O sentido reverso é **sistematicamente mais fraco em todas as categorias**. Isso é uma confirmação empírica da tese original da Sinapse: a informação flui do grande e líquido para o pequeno e lento, não o contrário. Faz sentido econômico — a gigante é mais coberta por analistas e precifica mais rápido.

#### Resultado — desempenho OOS (2021–2025)

| variante | alfa/ano | vol | Sharpe | giro | posições | t(IC) |
|---|---|---|---|---|---|---|
| `so_B` (atual) | +5,03% | 6,29% | **0,80** | 6,2% | 27 | 1,36 |
| `bidirecional` | +6,58% | 7,63% | **0,86** | 10,2% | 41 | 1,78 |
| `so_A_reverso` | +2,16% | 5,45% | 0,40 | 5,1% | 14 | 2,24 |

**Veredito: rejeitada.** O ganho de Sharpe é **+0,06** — dentro do ruído. O alfa sobe, mas às custas de giro (6,2% → 10,2%) e de mais risco; ajustado por risco, não melhora nada.

**A armadilha que evitamos:** o lado reverso sozinho tem IC out-of-sample de **+0,0201 (t = 2,24)** — mais alto que o do lado original! Olhando só isso, pareceria um achado. Mas no in-sample ele era fraco (t = 0,45). **Sinal que só aparece fora da amostra é mais provável ser sorte do que edge** — exatamente o tipo de conclusão que o protocolo IS/OOS existe para bloquear. Sem ele, teríamos "descoberto" um alfa que não existe.

**Efeito colateral relevante para P4:** a vol sobe de 6,3% para 7,6%, mais perto da meta de 12%. Mas isso não justifica P7 — se o objetivo é vol, **aumentar a alavancagem da carteira atual é mais limpo** do que adicionar elos de sinal comprovadamente mais fraco.

---

### 5. P4 — volatilidade em 6% contra meta de 12% (diagnosticada, **não resolvida**)

**O que era antes:** o relatório de 03/08 atribuía o gap à trava de liquidez ("as travas de liquidez limitam"). Isso nunca tinha sido medido.

**O que passou a ser:** existe um diagnóstico estágio a estágio, e a explicação anterior estava **errada**.

**Arquivos criados:**
- `fase 6 - validacao/src/s8_diagnostico_vol.py` — mede onde a vol se perde, qual trava morde, e a curva de capacidade
- `fase 6 - validacao/src/s9_teste_vol_corrigida.py` — testa três correções (registro de resultado negativo)

#### Onde a volatilidade se perde

| etapa | vol estimada | gross |
|---|---|---|
| sinal cru (z-score) | 49,86% | 4,77 |
| após vol-targeting #1 | **12,02%** | 1,38 |
| após travas #1 | 5,73% | 0,47 |
| após vol-targeting #2 | 11,79% | 1,03 |
| após travas #2 | 6,73% | 0,56 |
| após vol-targeting #3 | 11,97% | 1,06 |
| após travas #3 | **7,12%** | 0,60 |
| após suavização dos pesos | **5,95%** | 0,50 |

Duas causas mecânicas:
1. **O loop não converge.** Cada rodada o targeting acerta 12% e as travas derrubam. Em 3 rodadas chegou a 7,12% — ainda subindo quando o loop termina.
2. **A suavização custa mais 16,4%** (7,12% → 5,95%) e roda *depois* de todo o loop, sem recalibração.

#### O que NÃO é a causa (contrariando o relatório anterior)

- **Não é alavancagem:** o escalar mediano pedido é 0,27 (a estratégia *desalavanca*) e bate no teto de 3,0 em **0% dos dias**.
- **Não é liquidez:** a curva de capacidade — prevista no `PARAMETROS.md` §7 e nunca executada até hoje — mostra que o AUM quase não muda a vol.

| AUM | período | alfa/ano | vol | Sharpe |
|---|---|---|---|---|
| 20M | OOS 21–25 | +4,67% | 6,51% | 0,72 |
| 100M | OOS 21–25 | +5,03% | 6,29% | 0,80 |
| 300M | OOS 21–25 | +2,98% | 5,48% | 0,54 |

Reduzir o fundo 5x leva a vol de 6,29% para apenas 6,51%. **As travas são substitutas:** relaxa a liquidez, a setorial morde. Isoladamente, a trava setorial corta **−55,9%** do gross, a de liquidez −53%, a de nome −32%.

#### As três correções testadas — todas falharam

| variante | vol OOS | alfa OOS | Sharpe OOS |
|---|---|---|---|
| atual | 6,29% | +5,05% | **0,80** |
| mais_iteracoes (10 rodadas) | 6,36% | +4,82% | 0,76 |
| suav_no_loop | 6,50% | +2,49% | **0,38** |
| ambas | 6,34% | +1,05% | 0,17 |

A vol mal se move e o Sharpe despenca. Causa: suavizar dentro do loop aplica a média móvel 3x, o que equivale a uma janela muito maior e destrói o sinal (o giro caindo de 6,2% para 5,3% confirma). O `s9` foi **mantido como registro de resultado negativo** — sem ele, a próxima pessoa tentaria as mesmas três coisas.

**Veredito de P4: o gap não é erro de código, é estrutural.** Com ~24 posições concentradas em poucos setores, a trava setorial de 25% limita o tamanho do book. Não há reordenação de etapas que contorne isso — só mais elos (**P3**) aumentam o teto de vol alcançável.

---

### 6. 🔴 Bug grave encontrado no caminho: trava de liquidez violada

Esse não estava em nenhuma lista de pendências. Apareceu porque o `s9` verifica numericamente as travas em vez de confiar no argumento teórico.

**O bug:** `build_portfolio` suavizava os pesos **depois** das travas e não as reaplicava. A justificativa no código era o argumento de convexidade: *"a média móvel é uma combinação convexa de carteiras que já respeitam os limites, e como |média(w)| ≤ média(|w|), os limites continuam válidos"*.

**Por que o argumento estava errado:** ele vale para limites **constantes** (5% por nome, 25% por setor). A trava de liquidez **varia no tempo** — `limite[t] = ADTV[t] × 10% / AUM`. Se o volume negociado despenca, a média dos pesos dos 10 pregões anteriores, calculada quando a ação ainda era líquida, estoura o limite de hoje.

**Tamanho do problema (medido nos dados reais):**

| medida | valor |
|---|---|
| Dias com ao menos uma violação | **59,6%** |
| Posições-dia violando | 9,7% |
| Fração média do book em posição ilegal | 5,2% |
| Pior dia | **74% do book** |
| Pior caso | posição em ação com ADTV = 0 — **não negociou naquele pregão** |

Os tickers são exatamente as small caps: LOGG3, FIQE3, PRIO3, ROMI3, IGTI11, GUAR3, PGMN3, AERI3.

**Por que importa:** significava um backtest com posições **não executáveis na vida real** — exatamente a crítica que a trava de liquidez existe para prevenir. É o tipo de furo que a banca ataca primeiro.

**Correção:** novo passo 3c em [s5_portfolio_builder.py](fase%205%20-%20construcao%20da%20carteira/src/s5_portfolio_builder.py) — reaplicar as travas após a suavização.

**Safeguard:** teste novo `test_suavizacao_respeita_trava_de_liquidez_variavel`, com ADTV que colapsa no meio da série. Verificado que ele **falha** com o código antigo (excesso +0,0241) e **passa** com o novo (0,0000) — um teste que não pega a regressão não serve para nada.

> **Detalhe importante que o teste revelou:** o critério de verificação precisa comparar o peso contra o limite do dia da **decisão**, não da execução. O peso decidido em `t` só é executado em `t+1` (o `shift(1)`), e o ADTV de `t+1` não era conhecido. Violação que só aparece por causa do lag é inerente à execução real, não erro de construção.

**Impacto no resultado — praticamente nulo:**

| | antes | depois |
|---|---|---|
| Alfa OOS | +5,03%/ano | +5,05%/ano |
| Sharpe OOS | 0,80 | 0,80 |
| Dias com violação | 59,6% | **0,0%** |
| Retorno oficial (10 anos) | +8,7% | +8,5% |
| Excesso sobre CDI | +21,0% | +20,5% |

Esse é o melhor desfecho possível: a carteira passa a ser **executável** e o resultado não dependia das posições ilegais. Se o alfa tivesse desabado, saberíamos que a estratégia vivia de liquidez que não existe.

**Testes:** 7 passando (6 antigos + 1 novo).

---

### 7. P5 — retry no Yahoo (fechada como diagnosticada, não como corrigida)

**A premissa original estava errada.** O relatório de 03/08 supunha que os 5 tickers vivos que caem no COTAHIST falhavam por *rate-limiting* do Yahoo — a mesma causa já tratada para outros tickers (`JBSS3` etc.). Testado isoladamente hoje, isso não se confirma.

Os 5: **AXIA6, CPLE5, GUAR3, NEOE3, PETZ3**.

**O que a investigação mostrou:** todos falham com **HTTP 404 "Quote not found"** — imediato e consistente, em duas janelas de data diferentes e dois endpoints do yfinance. Controle: `PETR4.SA` no mesmo instante devolve 499 linhas normalmente. **Não é bloqueio geral, é o Yahoo não reconhecer esses códigos específicos.** Retry com qualquer atraso não mudaria isso — 404 "quote not found" não é o tipo de erro que retry resolve.

**Achado parcial:** `CPLE3.SA` (ordinárias da Copel) existe e tem histórico 2016–2023 — hipótese de que `CPLE5` (preferencial) deixou de existir como instrumento separado na privatização/unificação societária da Copel em 2023. Para os outros 4, nenhuma pista.

**Por que não implementei uma correção:** trocar `CPLE5` por `CPLE3` seria trocar de instrumento financeiro (ações preferenciais por ordinárias, séries de preço distintas antes de qualquer unificação). Fazer isso corretamente exige confirmar data e razão da conversão — investigação própria, fora do escopo de "fechar P5" em 30 minutos. Fazer sem essa verificação arriscaria injetar preço errado, pior do que a situação atual.

**Duas hipóteses minhas foram refutadas pelos próprios dados:**
- *"CPLE5 sumiu na unificação da Copel em 2023"* → o COTAHIST mostra CPLE5 negociando até 2025-12-19. Coexiste com CPLE3.
- *"são ilíquidos demais para o Yahoo cobrir"* → todos têm ADTV relevante (AXIA6 R$124M, CPLE5 R$117M, PETZ3 R$29M, NEOE3 ~R$24M, GUAR3 R$20M em dez/2025).

> ⚠️ **Armadilha de medição em que caí:** calculei mediana do ADTV sobre a série inteira, e os anos anteriores à existência do papel entram como **zero** (não NaN). Isso me fez concluir que AXIA6 e CPLE5 "quase não negociam" — errado. Para ticker novo, medir só na janela em que ele existe.

**O impacto real foi medido, e é desprezível.** Dos 5, **só GUAR3 está no grafo** — os outros 4 nunca entram na carteira:

| dividend yield assumido para GUAR3 | viés no alfa |
|---|---|
| 2%/ano | −0,0015%/ano |
| 4%/ano | −0,0030%/ano |
| 6%/ano | −0,0046%/ano |

Contra alfa de +1,0%/ano, isso é **0,5% do alfa** no pior caso. Motivo: a carteira fica long GUAR3 em 47,2% dos dias e short em 52,8% — num book long-short, um viés constante de retorno se cancela entre as pontas. Consistente com a medição de P6 (0,00%/ano).

**Decisão: fechar sem alterar o pipeline.** O retry proposto não funcionaria, e o erro que ele corrigiria está na quinta casa decimal. Só documentação: motivos específicos em [tickers_sem_preco.csv](fase%201%20-%20preço%20ajustado/config/tickers_sem_preco.csv) e o achado completo em [DIAGNOSTICO_P5_RETRY_YAHOO.md](DIAGNOSTICO_P5_RETRY_YAHOO.md).

---

### 8. P2 — viés de seleção do grafo (**corrigida**)

**O que era antes:** as 44 empresas do grafo foram escolhidas em 2025/2026 por alguém que já sabe quem sobreviveu. Ter preço das empresas mortas (resolvido em 03/08) não adianta se o grafo nunca aponta para elas — o viés estava na escolha das *relações*, não dos preços.

#### Etapa 1 — medir antes de corrigir (`s10_vies_selecao_grafo.py`)

| medida | valor |
|---|---|
| Empresas do grafo que **não** eram líquidas em 2016 | **20 de 44 (45%)** |
| Empresas top-60 de 2016 que morreram | 39 |
| Dessas, quantas estavam no grafo | **4** |
| Cobertura do universo 2016–2018 | 21,9% |
| Cobertura do universo 2023–2025 | 29,7% (**1,4× maior**) |

O grafo enxergava o presente com quase o dobro de nitidez que o passado. Viés confirmado com número.

#### Etapa 2 — o grafo histórico (`grafo_historico.csv`)

28 elos novos, 30 empresas que morreram ou foram absorvidas: Kroton/Estácio, B2W/Magazine Luiza, Lojas Americanas/B2W, Hering/Renner, Cielo/Bradesco+BB, Gol/Azul, BR Malls/Multiplan, Fibria/Klabin, Linx/Totvs, NotreDame/Hapvida, Localiza/Locamerica, Eletrobras/CESP+EDP+Tietê.

> **Regra que me impus ao escrever, e que importa para a defesa:** só relações **estruturais verificáveis na época** — mesmo setor com disputa direta, ou controle acionário declarado em balanço. Nenhum elo foi escrito a partir de desfecho que eu conheço. Exemplo do que isso *exclui*: não criei `GNDI3 → RDOR3` (a Rede D'Or comprou a SulAmérica — evento posterior), nem `LINX3 → STNE` (aquisição pela StoneCo). `LINX3 → TOTS3` entra porque Linx e Totvs disputavam software de gestão em 2016, fato independente do que veio depois.

**Vigência temporal não precisou de coluna de data:** um elo morre sozinho quando a empresa deixa de ter choque calculado — `montar_sinal_propagado` já trata choque ausente como zero.

#### Etapa 3 — 🔴 bug que a correção expôs: posição fantasma

Incluir empresas mortas revelou um defeito que **já existia no grafo atual**: uma ação que para de negociar continua com peso na carteira. A posição consome limite de risco e de setor, entra no cálculo de volatilidade, e rende exatamente zero.

**O ponto sutil — é o mesmo padrão do bug da trava de liquidez:** zerar o sinal na entrada **não basta**, porque a suavização dos pesos (média de 10 pregões) *ressuscita* o peso de uma ação já morta. A máscara tem que rodar **depois** de suavizar.

| | antes | depois |
|---|---|---|
| Fantasma por construção (grafo atual) | **2,07%** do book | **0,00%** |
| Fantasma por lag de execução | — | 1,04% (inevitável) |

A separação importa: o resíduo de 1,04% é a ação que negociava ontem e parou hoje — não havia como saber. Toda estratégia real tem isso. Só o "por construção" é bug, e foi zerado.

**Correção:** passo 3d em [s5_portfolio_builder.py](fase%205%20-%20construcao%20da%20carteira/src/s5_portfolio_builder.py). **Safeguard:** `test_acao_delistada_nao_carrega_posicao_fantasma`, verificado que falha no código antigo (5,0% de peso fantasma) e passa no novo (0,0%).

#### Etapa 4 — resultado

| métrica (OOS 21–25) | grafo atual | point-in-time |
|---|---|---|
| alfa/ano | +3,71% | **+3,13%** |
| Sharpe | 0,62 | **0,45** |
| volatilidade | 6,02% | **7,02%** |
| posições | 27 | **36** |
| IC | +0,0139 | +0,0077 |

**A queda de 0,58 p.p./ano no alfa É a resposta de P2** — é a medida direta de quanto o resultado dependia de só olhar para sobreviventes.

#### Etapa 5 — adoção em produção

O grafo histórico foi **adotado no pipeline oficial** ([s4_sinapse_sinal.py](fase%204%20-%20sinal%20da%20sinapse/src/s4_sinapse_sinal.py) carrega os dois arquivos). Os arquivos são mantidos **separados de propósito**: um descreve a bolsa de hoje, o outro as relações que existiram e acabaram — juntar esconderia quais elos vieram da correção.

Isso segue o mesmo princípio que o projeto já aplicou ao viés de preço em 03/08 (+19,9% → +8,7%): **o número pior e honesto vale mais que o número bonito**.

**Viés medido depois da correção:**

| medida | antes | depois |
|---|---|---|
| Empresas no grafo | 44 | **74** |
| Dependência de empresas pós-2016 | 45% | **34%** |
| Mortas de 2016 cobertas | 4 | **23** |
| Cobertura 2016–2018 | 21,9% | **43,8%** |
| Cobertura 2023–2025 | 29,7% | 36,7% |
| Veredito do script | *"olha para o presente"* | **"cobertura parecida nos dois extremos"** |

A cobertura do período inicial **dobrou** e agora supera a do período recente — o viés inverteu de sinal.

**Resultado oficial (10 anos, pipeline completo):**

| | antes de P2 | depois de P2 |
|---|---|---|
| Alfa acumulado | +8,5% | **+11,6%** |
| Alfa/ano | +1,01% | **+1,35%** |
| Volatilidade | 5,70% | **6,85%** |
| Retorno do fundo | +162,4% | **+170,1%** |
| Excesso sobre CDI | +20,5% | **+28,2%** |
| Giro diário | 5,8% | 8,4% |

> ⚠️ **Atenção ao ler isso:** o resultado *melhorou*, o que pode parecer suspeito numa correção de viés. A explicação é que P2 fez duas coisas ao mesmo tempo: (a) **removeu** a vantagem de só operar sobreviventes — isso piora, e está medido acima como −0,58 p.p. no OOS; e (b) **dobrou o número de apostas**, o que aumenta a exposição efetiva (vol de 5,70% para 6,85%) e escala o retorno. O efeito (b) é maior que o (a) no período completo. **São coisas distintas e não devem ser confundidas:** a qualidade por unidade de risco *caiu* (Sharpe OOS 0,62 → 0,45); o retorno absoluto subiu porque a carteira ficou maior.

**Efeito colateral em P4:** a vol subiu de 5,70% para 6,85%, sem mexer em nenhum parâmetro de risco — exatamente o que o diagnóstico de P4 previu (só mais elos elevam o teto).

---

### 9. 🔴 O mapeamento setorial estava 79% vazio — e isso contaminava tudo

**Como apareceu:** ao adicionar 30 empresas ao grafo (P2), a pergunta natural foi se o `mapeamento_setores.csv` precisava ser atualizado. As 30 novas tinham setor. Mas a checagem revelou algo muito pior: **201 dos 253 tickers estavam com o setor literal `"A DEFINIR"`** — incluindo **43 das 74 empresas do grafo**.

**Por que isso não era um detalhe de cadastro:**

1. **Quebrava a regressão do choque limpo.** O choque sai de `retorno = α + β₁·IBOV + β₂·SETOR + resíduo`, onde `SETOR` é a média das *outras* ações do mesmo setor. Com 201 ações no mesmo balaio, o "índice setorial" de cada uma era a média de 200 ações de todos os setores misturados — ou seja, **praticamente o mercado**. `IBOV` e `SETOR` ficavam quase colineares, e o resíduo chamado de "choque idiossincrático" ainda continha o movimento setorial inteiro.

2. **Distorcia a trava setorial.** O limite de 25% tratava as 43 empresas do grafo como **um setor só**.

> Isso é uma variante do Bug 1 da sessão de 03/08 (mapa de setores nunca lido). Lá o arquivo não era encontrado; aqui ele é lido, mas está quase vazio — e **falha silenciosamente do mesmo jeito**, porque "A DEFINIR" é uma string válida que agrupa em vez de dar erro.

**Correção:** [s4b_atualiza_setores.py](fase%204%20-%20sinal%20da%20sinapse/src/s4b_atualiza_setores.py) — classifica 200 tickers na taxonomia B3 e acrescenta os 2 ausentes (FIQE3, LOGG3). Idempotente: só preenche `"A DEFINIR"`, nunca sobrescreve.

Segui a B3 mesmo onde ela é contra-intuitiva: shoppings e exploração de imóveis → **Financeiro**; construção civil → **Consumo Cíclico**; serviços educacionais → **Consumo Cíclico**; holdings seguem o ativo principal (BRAP4 → Materiais Básicos, ITSA4 → Financeiro).

**Um ticker (PARC3) ficou em `"A DEFINIR"` de propósito** — não identifiquei a empresa com confiança. Chute errado é pior que ausência: contamina o índice setorial de dois setores ao mesmo tempo. Ele não está no grafo.

| | antes | depois |
|---|---|---|
| Tickers em "A DEFINIR" | 201 de 253 | **1 de 255** |
| Empresas do grafo sem setor | 45 de 74 | **0 de 74** |

#### Impacto — e uma revisão do meu próprio diagnóstico de P4

**A trava setorial caiu de −55,9% para −32,9%.** Ou seja: **boa parte do que eu diagnostiquei como "limite estrutural da trava setorial" em P4 era artefato do cadastro quebrado.** A ordem das travas mudou:

| trava | antes | depois |
|---|---|---|
| liquidez | −53,0% | **−44,4%** (agora a maior) |
| setor | **−55,9%** | −32,9% |
| nome | −32,1% | −25,1% |
| todas juntas | −65,6% | −53,4% |

Corrigi o alerta do `s3_backtest.py`, que eu havia acabado de reescrever culpando a trava setorial.

**Resultado oficial (10 anos):**

| | antes | depois |
|---|---|---|
| Alfa acumulado | +11,6% | **+27,9%** |
| Alfa/ano | +1,35% | **+2,81%** |
| Sharpe | 0,20 | **0,36** |
| Volatilidade | 6,85% | **7,84%** |
| Excesso sobre CDI | +28,2% | **+67,5%** |
| Giro diário | 8,4% | 10,8% |

**Validação OOS (grafo de produção):** alfa **+3,91%/ano**, Sharpe **0,50**, IC +0,0091 (t = 1,72).

> **O in-sample deixou de ser negativo.** Aquela assimetria que me incomodava na P1 — IS com alfa −1,99% e OOS positivo, o inverso do padrão de overfit e que eu não sabia explicar — era, em boa parte, **artefato do mapeamento quebrado**. Agora o IS dá +1,69% e o OOS +3,91%: os dois positivos, na mesma direção. Isso é bem mais defensável do que o quadro anterior.

**A regra conservadora continua reproduzindo o grafo de produção** (etapa 2b: os 30 elos são idênticos) — a conclusão de P1 não muda.

> ⚠️ **Uma leitura que mudou de sinal e exige cuidado:** o comparativo `atual` − `congelado_is` no OOS passou de −1,34% para **+2,83%**. Isso **não** é evidência de overfit, e a mensagem automática do script (que dizia isso) foi corrigida. As duas variantes não diferem por "uma viu o futuro e a outra não" — usam **regras de decisão diferentes**. O `congelado_is` inverte pelo *sinal* da correlação mesmo quando é ruído (inverteu `imobiliario_logistica` com t = −0,89 no IS; no OOS essa categoria deu t = +2,47, ou seja, ele errou). O `conservador` só inverte com |t| ≥ 2 e por isso acertou. **O congelado perder mostra que congelar no ruído é regra pior — não que o grafo de produção espiou.** O teste de overfit que vale é a etapa 2b.

---

## Pendências / decisões em aberto

- **P1 está respondida, mas com ressalva:** a direção dos elos sobrevive ao teste honesto; o que **não** se comprova é significância estatística do IC (t = 1,36). O caminho para resolver isso é P3, não mais correção.
- **P7 está respondida e rejeitada.** O sentido reverso do grafo é real mas fraco demais; adicioná-lo não melhora o retorno ajustado a risco. **Isso fecha o caminho "aumentar breadth sem expandir o grafo"** — reforça que P3 é o único caminho para significância.
- **P4 diagnosticada, parcialmente aliviada — e meu diagnóstico foi revisado.** Não é alavancagem (escalar bate no teto em 0% dos dias). As três travas agem como substitutas e juntas cortam ~53% do gross. **Atribuí o gargalo à trava setorial; depois descobri que boa parte disso era o cadastro de setores quebrado.** Com P2 + setores corrigidos, a vol subiu de 5,70% para **7,84%** sem tocar em nenhum parâmetro de risco. Ainda abaixo dos 12%, mas bem mais perto.
- **P2 corrigida.** Grafo point-in-time adotado em produção (74 empresas, 58 elos). Viés medido antes (cobertura 1,4× maior no presente) e depois (cobertura equilibrada). Custo honesto: −0,58 p.p./ano de alfa no OOS.
- **P5 fechada como diagnosticada.** Não era rate-limiting — é 404 permanente do Yahoo para esses códigos. Retry não resolveria. Documentado; sem correção de código (risco de dado errado > benefício).
- **Nada foi commitado ainda** — a sessão inteira está em working tree.
- O resultado do período **in-sample é negativo** (−1,17%/ano de alfa) e o OOS positivo. Vale entender por quê antes de tratar o OOS como representativo — pode ser regime de mercado (2016–2020 inclui a pandemia).

---

## Resumo para o grupo

O documento consolidado desta sessão está em
**[SESSAO_COMPLETA_04_08_SESSAO2.md](SESSAO_COMPLETA_04_08_SESSAO2.md)** —
mesmo formato do `SESSAO_COMPLETA_04_08.md` (visão geral, cronologia
técnica, dúvidas respondidas).

Em uma linha: **4 pendências fechadas (P1, P2, P5, P7), 4 bugs corrigidos,
alfa de +8,5% para +27,9%, e P3 virou o gargalo único** — com três
argumentos quantitativos independentes apontando para ela.

Para quem for ler só uma coisa: a **dúvida 2 da Parte 3** explica por que
ficar longe do Ibovespa é o comportamento esperado (e não um problema), e
por que o CDI é a régua certa.
