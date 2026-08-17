# Plano de implementação — reta final do Desafio Quant Itaú Asset 2026

> **Status: PLANO. Nada aqui foi executado.**
> Escrito em 11/08 após três revisões independentes (quant, risco, custo/execução).
> Leia a §1 antes de qualquer coisa — ela muda o objetivo do trabalho.

---

## 1. A situação, sem rodeios

Três revisões independentes convergiram no mesmo ponto: **não existe edge estatisticamente
defensável nesta estratégia.**

| evidência | número |
|---|---|
| Sharpe (10 anos), melhor configuração possível | 0,41 — **t = 1,28** |
| Deflated Sharpe (N=20 configurações declaradas) | **0,27** |
| Diferença contra um momentum trivial de 21d | −0,94%/ano (**t = −0,26**) |
| Placebo do mecanismo, no período de calibração | **p = 0,164** |
| Alfa com custo realista (20,3 bps medidos) | **−2,28%/ano** |

E o achado que reordena tudo: o bug em `s4_sinapse_sinal.py:233` faz **13,4% das células de
choque serem retorno bruto** (100% de 2016). Corrigido:

```
IC in-sample:  +0,0118 (t = 2,14)   ->   +0,0077 (t = 1,39)
```

**O `t = 2,14` que sustenta o protocolo P1 inteiro é artefato de bug.** Isso derruba por tabela a
conclusão do `s13` e a regra conservadora de direção.

### O que isso significa para o desafio

O objetivo deixa de ser *"entregar uma estratégia que ganha dinheiro"* e passa a ser
**"entregar a demonstração rigorosa de por que ela não ganha"**.

Isso não é o prêmio de consolação. Numa banca de asset manager, um grupo que audita a si mesmo
até derrubar o próprio resultado demonstra mais competência que um grupo com Sharpe 2,3 não
testado. O ativo do projeto é o **método**, e ele é genuinamente bom:

- pré-registro de parâmetros **provável no git** (`PARAMETROS.md` em 21/07, primeiro backtest em 29/07)
- protocolo IS/OOS com decisões congeladas em CSV
- placebo de grafo passando com **p ≤ 0,015** (verificado contra o código de produção)
- hipóteses refutadas **preservadas no código**, não apagadas
- breadth efetiva reconciliando Grinold sem parâmetro livre (previsto 0,49 / realizado 0,50)
- auto-auditoria que derrubou o próprio t-stat

**A decisão estratégica deste plano: parar de tentar consertar o retorno e passar a blindar o
método.** Todo item abaixo serve a isso.

---

## 2. Princípios que governam o plano

Estes não são conselhos — são restrições. Violar qualquer um destrói mais valor do que o item
em questão adiciona.

**P1 — O OOS é um recurso que se gasta.** Cada re-execução de 2021-2025 cujo resultado
influencie uma decisão queima um pouco do período. O plano prevê **UMA rodada final** depois de
todas as correções, não uma rodada por correção.

**P2 — Não recalibrar nada.** Nenhum parâmetro é reescolhido neste plano. Corrigimos bugs,
adicionamos controles e medimos melhor. Se um número piorar, ele piora.

**P3 — Não quebrar o pré-registro.** `PARAMETROS.md` é o ativo mais valioso do projeto. Não
alterar valores pré-registrados (12% de vol, 5% por nome, 25% por setor, 10% do ADTV, AUM 100M).
Reescrever *justificativas* é permitido e necessário; trocar *valores* não é.

**P4 — Escopo fechado.** Nada de tese nova, nada de sinal novo, nada de reescrever o motor.
Correções + controles + medição + apresentação.

**P5 — Apresentar as duas versões, nunca substituir em silêncio.** Onde uma correção muda os
números oficiais, o relatório mostra "pré-registrado" e "corrigido" lado a lado. É o que um
comitê de risco faz.

---

## 3. Fases

Ordem obrigatória — cada fase depende da anterior. Estimativa total: **3 a 4 dias de trabalho.**

### FASE 0 — Congelar o estado atual · 30 min

Antes de tocar em qualquer linha.

| # | tarefa |
|---|---|
| 0.1 | Commit de tudo que está em working tree (registros, `s12`, `s13`, `s4c`, `.gitignore`) |
| 0.2 | Tag `v1-pre-correcoes` no git |
| 0.3 | Copiar `data/` inteiro para `data_v1_backup/` (fora do git) |

**Critério de aceite:** `git status` limpo e a tag existindo. Sem isso não há como mostrar
"antes vs depois" na apresentação, que é a §P5.

---

### FASE 1 — Bugs que contaminam os números · 4 h

Os cinco são de correção mecânica. Nenhum envolve escolha.

| # | bug | arquivo:linha | correção | impacto medido |
|---|---|---|---|---|
| 1.1 | Resíduo vira retorno bruto sem 252 obs | `s4_sinapse_sinal.py:233` | `sum(axis=1, min_count=1)` | **IC IS 2,14 → 1,39** |
| 1.2 | Beta do hedge é **parcial**, não de mercado | `s4_sinapse_sinal.py:226-236` | `β_total = β_IBOV + β_SETOR·β(setor,IBOV)`, ou regressão univariada separada só para o hedge | mediana dos betas 0,28 e **24% negativos** — o book é hedgeado com ~1/3 do beta correto |
| 1.3 | Beta NaN vira zero no hedge | `s5_portfolio_builder.py:209` | exigir beta válido como elegibilidade + assert de cobertura | **12,8% das posições** sem hedge |
| 1.4 | `clip` com limite NaN não corta | `s5_portfolio_builder.py:176-178` | `.where()` explícito + `limit_w.fillna(0)` | 353 posições escapam da trava |
| 1.5 | `s11` duplica os 28 elos históricos | `s11_grafo_point_in_time.py:189-192` | remover a concatenação redundante | os "86 elos" são 58 com 28 dobrados |

**Bônus sem impacto numérico, mas que destrava a Fase 5:**

| 1.6 | Winsorização vetorizada | `s4_sinapse_sinal.py:288-293` | `x.clip(lower=q01, upper=q99, axis=0)` | **idêntica** (verificado: `equals()==True`), **14x mais rápida** |

> **1.2 é o mais grave e o mais recente.** A regressão `y ~ const + IBOV + SETOR` divide a
> exposição de mercado entre os dois regressores, e `res.params['IBOV']` vira o resíduo dessa
> divisão — não o beta de mercado. Beta univariado de ação brasileira líquida não é 0,28 nem
> negativo em 24% dos casos. Isso não aparecia no beta cheio da carteira porque o book é quase
> dollar-neutral na média, mas nos dias de net ±35% o sub-hedge é real.

**Critério de aceite:** os 5 testes existentes continuam passando; um teste novo para 1.1
(resíduo é NaN, não retorno bruto, antes de 252 observações) e um para 1.3 (assert de cobertura
de beta) — ambos falhando no código antigo e passando no novo, que é o padrão que o projeto já
usa.

---

### FASE 2 — Custo realista · 4 h

O modelo atual (5 bps flat) está **4x otimista**. Custo realizado medido: **20,3 bps** por
unidade de giro. Causa: **73% do giro está abaixo de R$150MM de ADTV** — 5 bps é número de large
cap aplicado a um book mid cap.

| # | tarefa | onde |
|---|---|---|
| 2.1 | Custo por faixa de ADTV: emolumentos+liquidação (2,3) + corretagem (3,0–4,0) + meio-spread (2,0/5,0/11,0/24,0) | `s3_backtest.py:79, 210-215` |
| 2.2 | Impacto de mercado: `0,4 × σ₆₀ × √(participação)`, com clip de participação | idem |
| 2.3 | Aluguel BTC sobre `W.clip(upper=0).abs()`, tier por ADTV (1,0/2,0/3,5/6,0% a.a.), base 252 | idem |
| 2.4 | Tabela de sensibilidade: custo × η × aluguel, com o resultado honesto em cada célula | painel do `s3` |
| 2.5 | **Tabela de breakeven por unidade de giro** | painel do `s3` |

Insumo: `data/universo/adtv_diario.parquet`, que já existe. São ~40 linhas, sem tocar no motor.

> **2.5 é o item de maior valor da fase**, e talvez do plano inteiro. O alfa por unidade de giro
> é **~15 bps e constante** — testado em suavização de 1 a 34 dias e em banda de não-negociação
> de 0,25% a 2,0%, o breakeven fica travado entre 11,4 e 16,3 bps. **Não existe ponto de
> operação em que a estratégia sobreviva a 20 bps.** Isso blinda contra "vocês foram pessimistas
> no custo": o resultado não depende da calibração, depende de um fato do sinal.

**Critério de aceite:** o painel do Bloco 3 imprime a decomposição de custo por faixa, o
breakeven, e a tabela de sensibilidade. O número headline passa a ser o realista.

---

### FASE 3 — Controles de risco faltantes · 4 h

Os três primeiros são **críticos** e uma banca de asset vai perguntar por eles.

| # | controle | racional | onde |
|---|---|---|---|
| 3.1 | **Exposição líquida \|net\| ≤ 10%** | hoje: desvio 14,7%, faixa **[−38,5%, +34,9%]**. Um fundo que se diz neutro e roda 38% comprado perde a conversa ali | novo método em `s5`, após linha 74 |
| 3.2 | **Exposição setorial LÍQUIDA ±10%** (mantendo a gross de 25%) | a trava atual mede `Σ\|w\|` — bloqueia long PETR4/short PRIO3 (inofensivo) e é cega para 24,9% net em Financeiro. **86,2% dos dias têm algum setor acima de ±10% net** | `s5:183-201` |
| 3.3 | **Participação por ORDEM** (fluxo), não só por posição (estoque) | a trava de ADTV limita a posição; foi encontrado participation rate de **8.719%** em dias de ADTV colapsado | `s5:174` |
| 3.4 | `validar_carteira()` — verificação da matriz FINAL entregue, com CSV de violações | hoje os testes só cobrem dados sintéticos; nada confere o artefato que alimenta o backtest | `s5`, após linha 98 |

> Escalar para baixo nunca viola as travas de nome/setor/liquidez, então 3.1 e 3.2 podem entrar
> depois delas sem reaplicá-las. **3.4 é o maior retorno por hora do plano inteiro**: transforma
> "temos travas" em evidência auditável dia a dia, que é exatamente o que uma banca quer ver.

**Critério de aceite:** `validar_carteira()` roda sobre `df_weights_sinapse.parquet` e reporta
**zero violações** em todas as travas, ou lista exatamente quais e por quê.

---

### FASE 4 — A rodada única · 1 h de execução

**Aqui se gasta o OOS.** Depois desta rodada, nenhum número muda mais.

```
1. fase 4 - sinal da sinapse/src/s4_sinapse_sinal.py      (sinal + betas corrigidos)
2. fase 5 - construcao da carteira/src/exec_s5.py         (pesos com controles novos)
3. fase 3 - backtest/src/s3_backtest.py                   (P&L com custo realista)
4. fase 6 - validacao/src/s6_validacao_oos.py             (protocolo IS/OOS)
5. fase 6 - validacao/src/s12_inferencia_e_breadth.py     (breadth e inferência)
6. fase 6 - validacao/src/s13_protocolo_subsetor.py       (registro do subsetor)
```

**Regra dura:** rodar tudo numa passada, na ordem, e **regerar todos os CSVs de
`data/validacao/`**. Hoje eles são de safras diferentes (30 elos vs 58) e estão sendo citados
lado a lado — a tabela de sensibilidade de janelas, que é o argumento de que 21/10 não foi
otimizado, foi medida com **metade do grafo**.

**Critério de aceite:** todos os artefatos com o mesmo timestamp e o mesmo número de elos.
Qualquer número que apareça no deck sai desta rodada.

> **Ponto de decisão.** Depois desta fase os números oficiais mudam — provavelmente para alfa
> negativo com custo realista. Isso é esperado e está previsto na §1. Não recalibrar nada em
> resposta (§P2).

---

### FASE 5 — A evidência que sustenta a conclusão · 6 h

É o conteúdo do deck. Cada item responde a uma pergunta que a banca vai fazer.

| # | entrega | responde |
|---|---|---|
| 5.1 | **`s14_painel_risco.py`** — VaR/ES, Sortino, Calmar, vol rolling (p50/p95/**máx 18,12%**), underwater (**1.158 pregões**), gross/net/long/short, beta rolling, concentração, capacidade | *"cadê as métricas de risco?"* |
| 5.2 | **Bloco de stress** — COVID **−5,6%** vs IBOV −29,6%; Joesley **+1,4%** vs −8,8%; eleição 2018; Americanas; **2022 = −13,3%** | *"como se comporta em crise?"* — e aqui a estratégia **protegeu de verdade**, hoje invisível no relatório |
| 5.3 | **`s15_placebo_grafo.py`** — reembaralhamento do gatilho, 300 sorteios, com o código de produção | *"o grafo carrega informação ou é aleatório?"* → **p ≤ 0,015** |
| 5.4 | **`s16_deflated_sharpe.py`** — t(Sharpe), PSR, DSR com **N declarado**, e regressão contra mom21/rev5/lowvol | *"seu Sharpe é significante?"* → **t = 1,28, DSR = 0,27** |
| 5.5 | **Placebo do mecanismo** — sortear o gatilho mantendo subsetor e K | *"a ordenação por liquidez faz trabalho?"* → **p_IS = 0,164, não faz** |
| 5.6 | **`forca = 1.0`** nos 58 elos, com o IC medido | *"vocês ajustaram 58 forças à mão?"* → *"não — a matriz é binária e mostramos que não muda nada"* |

> **5.3 e 5.5 juntos são a espinha intelectual da apresentação.** O grafo manual bate placebo
> (p ≤ 0,015) — logo carrega informação. Mas a ordenação por liquidez **não** bate placebo no
> in-sample (p = 0,164) — logo o mecanismo alegado não é o que gera o sinal. Descobrir isso
> sobre a própria estratégia é o argumento mais forte do trabalho.

---

### FASE 6 — A regra mecânica como segunda implementação · 4 h · **opcional**

Se sobrar tempo. **Não substitui o grafo manual — roda ao lado dele.**

O protótipo já mostrou que a regra é melhor em todos os eixos:

| | grafo manual | regra mecânica |
|---|---|---|
| Sharpe completo | 0,07 | **0,41** |
| Giro diário | 10,8% | **4,8%** |
| Breadth OOS | 11,3 | **14,6** |
| P&L concentrado em 2023-25 | **100%** | **8%** |
| Parâmetros subjetivos | 58 | **0** |

E a combinação regra + grafo é **pior** que a regra sozinha (Sharpe OOS −0,03) — o julgamento
humano adiciona ruído, não alfa. Esse é um resultado, não um fracasso: responde objetivamente à
pergunta "curadoria humana vale a pena?".

**Valor para o deck:** duas implementações independentes que chegam à mesma conclusão é
**replicação**, o padrão-ouro de evidência. Vale mais que qualquer número isolado.

---

### FASE 7 — Documentação · 4 h

| # | entrega |
|---|---|
| 7.1 | Atualizar `PARAMETROS.md` §6: **12% é teto de orçamento de risco, não alvo**; utilização 65%; e reescrever a justificativa de `janela_suavizacao_pesos` |
| 7.2 | Refazer a tabela de P1 no `acomp_04_08_sessao2.md` (mede 30 elos, produção tem 58) e trocar os t-stats pelos clusterizados |
| 7.3 | Registro desta sessão no formato do projeto |
| 7.4 | Deck |

> **7.1 é delicado e precisa ser feito com cuidado.** O comentário em `s5:17-21` diz que a janela
> de 10 dias foi escolhida porque *"dobrou o Sharpe (0,22 → 0,51)"*. É **a única linha do
> repositório onde vocês documentam ter escolhido um parâmetro olhando o resultado** — num
> projeto cuja defesa inteira é o protocolo anti-snooping. Um avaliador atento acha isso.
> A correção é reescrever a justificativa como controle de giro/capacidade e mostrar a
> sensibilidade 5/10/21. **Não recalibrar** (§P2).

---

## 4. O que NÃO fazer

| não faça | por quê |
|---|---|
| Relaxar o teto de 5% por nome para alcançar os 12% de vol | é o único controle que efetivamente morde (76% dos dias) e a razão de a concentração não ser pior |
| Reduzir a meta de vol para 7,5% | quebra o pré-registro por ganho cosmético. E **o Sharpe é invariante à escala** — o gap de vol não explica o resultado nulo. Dizer isso elimina a linha de questionamento inteira |
| Recalibrar `janela_suavizacao_pesos` | reescreva a justificativa, não o valor |
| Escrever mais elos manuais | o `s12` provou que elo em gatilho existente não move breadth |
| Filtro de liquidez nos satélites | testado: o alfa sai junto com o custo (−1,78%/ano com ADTV>20MM) |
| Suavização maior ou banda de não-negociação | testadas até 34d e 2,0%: o breakeven não se move |
| Alavancar para chegar aos 12% | 1,53x faria 2022 virar −21% e o DD máximo −30% |
| Olhar 2021-2025 e ajustar qualquer coisa | §P1. O OOS já foi usado várias vezes; cada uso adicional exige um N maior no Deflated Sharpe |

---

## 5. A apresentação

Não venda Sharpe 0,41. Venda o protocolo. Espinha sugerida:

1. **A hipótese, falseável** — difusão lenta de informação intra-indústria (Hou 2007;
   Lo-MacKinlay 1990). Reconhecer que a tese original (soma-zero entre rivais,
   `CRITERIOS_GRAFO_MANUAL.md:23`) foi **refutada pelos dados**, e que a assimetria big→small do
   teste bidirecional é a confirmação da tese substituta.
2. **Duas implementações independentes** que concordam — 58 elos fundamentalistas e ~220
   mecânicos point-in-time.
3. **O placebo do mecanismo** — `p_IS = 0,164`. *"O IC in-sample mede co-movimento residual de
   subsetor, não difusão de liquidez."*
4. **Os bugs, com impacto medido** — especialmente `s4:233`: o `t = 2,14` que sustentava a tese
   caía para 1,39. **Auto-auditoria que derruba o próprio resultado.**
5. **A aritmética do porquê** — breadth 11,3; com teto de 5%/nome dá no máximo 7,2% de vol;
   ampliar de 58 para 220 elos moveu a breadth 29%, não 4x.
6. **Deflated Sharpe com N declarado** — *"rodamos 20 configurações; o melhor de 20 tentativas
   nulas dá 0,60; o nosso deu 0,41; DSR = 0,27."*
7. **Custo e capacidade como restrição** — breakeven 15,4 bps contra 20,3 medidos; a R$300M o
   alfa é +0,73%/ano.

**Frase de fechamento:**

> *"Testamos uma hipótese econômica específica com duas implementações independentes, um placebo
> do mecanismo e um protocolo IS/OOS congelado. Encontramos IC positivo e ortogonal ao momentum,
> mas não separável de zero após correção por múltiplas tentativas — e o placebo mostra que o
> mecanismo alegado não é o que gera o sinal in-sample. Reportamos isso em vez de calibrar até o
> número ficar bonito."*

**Três coisas para reportar você mesmo, antes que perguntem:** o `t(Sharpe) = 1,13`, o estouro de
vol de **18,12% em maio/2020**, e o resultado com custo realista. Se a banca achar primeiro, a
credibilidade construída com os bugs evapora junto.

---

## 6. Cronograma

| dia | fases | entrega |
|---|---|---|
| 1 | 0, 1 | bugs corrigidos, testes passando |
| 2 | 2, 3 | custo realista + controles de risco |
| 3 | 4, 5 | rodada única + painel, stress, placebos, DSR |
| 4 | 6, 7 | regra mecânica (opcional) + documentação e deck |

**Caminho mínimo, se o tempo apertar:** Fases 0, 1, 4, 5.3, 5.4 e 7. São os bugs, uma rodada
limpa, os dois placebos, o Deflated Sharpe e a documentação — o suficiente para a defesa se
sustentar.

---

## 7. O que este plano deliberadamente NÃO tenta

Está aqui para não haver surpresa:

- **Não tenta salvar o alfa.** Três revisões independentes concluíram que ele não existe.
  Qualquer coisa que "melhore o resultado" a esta altura seria calibragem no OOS.
- **Não muda a tese.** A tese continua sendo difusão de informação intra-indústria. O que muda é
  reconhecer que a versão original (soma-zero entre rivais) foi refutada.
- **Não reconstrói o motor.** Os Blocos 3, 4 e 5 ficam como estão, com correções pontuais.
- **Não gasta o OOS mais de uma vez** (Fase 4).

Se em algum momento a tentação for "e se a gente testasse mais uma coisinha" — a resposta está na
§P1. O valor restante do projeto está inteiro na disciplina, e ela é a única coisa que ainda pode
ser perdida.
