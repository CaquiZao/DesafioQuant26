# LOG — Coerência dos artefatos visuais e reconstrução do deck de entrega

**Data:** 2026-08-16 23:43 · **Modo:** Resumo de Sessão
**Branch:** `correcoes-sinapse-04-08` · **Commit inicial:** `1deffe1`
**Plano de origem:** —

---

## 1. Sumário executivo

### O que foi feito

Corrigimos uma inconsistência estrutural no acervo visual: os gráficos plotavam o período
completo (2016–2025) enquanto as tabelas usavam só o período com posição (a partir de
19/05/2017), de modo que o mesmo Ibovespa aparecia **+282% no gráfico e +161,6% na tabela**.
Unificamos a janela em todos os artefatos e, no caminho, encontramos seis afirmações que o
próprio material contradizia. Depois, reconstruímos o deck de entrega (5 páginas, 16:9,
anônimo) do zero em `python-pptx`, porque a estratégia mudou demais para um patch: saiu o
grafo extraído da CVM — que nunca chegou a ser implementado e virou próximo passo — e
entraram o grafo mecânico por ADTV, a acumulação 12-1 e o custo realista de 3 camadas.

### Decisões tomadas

- **Janela única (`idx_ativo`) para todo o material, em vez de corrigir só o gráfico 01** —
  a inconsistência apontada pelo usuário era sintoma, não causa: cinco gráficos tinham o
  mesmo defeito. Descartamos o conserto pontual porque ele deixaria os outros quatro
  divergindo das tabelas.
- **Remoção do alias `d["r_estrategia"]`** — ele apontava silenciosamente para os 5 bps, e
  cinco gráficos o usaram achando que era "o retorno da estratégia" enquanto as tabelas
  mostravam o custo realista. Cada gráfico agora nomeia a premissa: `r_flat` ou `r_real`.
  Descartamos mantê-lo com um comentário de aviso; um alias ambíguo reintroduz o bug.
- **Duas imagens separadas para a curva acumulada (5 bps e realista), com escala Y
  compartilhada** — o usuário pediu a separação para legibilidade; a escala comum é decisão
  nossa, porque eixos independentes esconderiam que a queda de +200,2% para +143,7% é
  inteiramente modelo de custo.
- **Vereditos formatados a partir do valor medido, nunca escritos à mão** — a nota da tabela
  principal afirmava "a estratégia não bate o benchmark" ao lado do `+40,0%` que ela mesma
  imprimia. Sobra de uma rodada em que o excesso era negativo.
- **Reconstruir o deck em vez de editar o XML do original** — a mudança de conteúdo era quase
  total e o layout precisava de reorganização. Descartamos a edição cirúrgica do
  `Ita__Quant_case_presentation-3.pptx` porque exigiria reposicionar ~100 shapes.
- **Gráficos claros sobre cartões `#FCFCFB` no fundo navy** — o usuário pediu para manter a
  aparência normal das figuras. Descartamos regerar as figuras com tema escuro.
- **Variantes de deck das figuras (`saida/deck/`, via `r1_visuais.py --deck`)** — o
  `RelatórioRAW.md` precisa de figuras autoexplicativas; o deck já dá o contexto no slide.
  Descartamos usar um único conjunto: no relatório o subtítulo longo é o comportamento certo.
- **Travessão → dois-pontos caso a caso, não em massa** — em 11 dos 33 casos o `:` ficaria
  agramatical (travessão como aposto no meio do período); ali entrou vírgula ou ponto.

### Bugs encontrados e soluções

- **Gráfico e tabela discordando (achado do usuário)** → causa: `g_curva` plotava
  `d["r_fundo"]` sobre o índice completo enquanto `t_metricas` filtrava por `mask_ativo` →
  correção: `carregar()` passou a expor `idx_ativo`/`pesos_ativo` e o helper `ativo(d, s)`;
  aplicado em `g_curva`, `g_giro`, `g_exposicao`, `g_heatmap`, `g_rolling`, `g_distribuicao`,
  `g_custo` e `t_anual`.
- **Nota da tabela contradizendo o próprio número** → causa: texto do veredito hard-coded de
  uma rodada anterior → correção: `t_metricas` monta o veredito a partir do sinal de
  `exc_real`.
- **Gráfico anual afirmando "5 dos 9 anos são negativos"** → causa: string fixa, anterior à
  correção de calendário; o valor medido é 3 → correção: `neg` contado dos dados.
- **Faixa "2019–2021 carregam o resultado"** → causa: anos escolhidos à mão; 2019 rendeu só
  +2,9% → correção: destaque nos dois melhores anos medidos; o rótulo passou a dizer que
  **2020–2021 sozinhos somam +23%, mais que os +20% de todo o período**.
- **Gráfico de exposições alegando "dollar-neutral por construção"** → causa: a legenda
  descrevia a perna de ações, que oscila de −44,6% a +40,7% → correção: plotamos a linha
  **líquida total (ações + hedge)**, que fica em −7,7%/+14,2%, e o texto passou a dizer que a
  neutralidade é comprada com o hedge de índice, não automática.
- **Gráfico de evolução congelado em "+36,4%"** → causa: última barra hard-coded, anterior à
  correção de calendário → correção: `g_evolucao(d)` mede as duas últimas barras a cada
  execução (+47,3% em 5 bps, +19,6% realista).
- **2017 incomparável na tabela anual** → causa: `giro`, `ações` e `vol` usavam o ano inteiro
  enquanto a Sinapse só tem posição a partir de 19/05 → correção: janela ativa em todas as
  colunas; 2017 saiu de 69 ações/2,2% de giro para 111/3,6%.
- **`--deck` quebrando `g_curva`** → causa: variável local `sub` sombreando a função `sub()`
  do modo deck → correção: renomeada para `subt`.
- **Dois-pontos duplicados na mesma frase (5 ocorrências)** → causa: substituição do
  travessão sem checar se a frase já tinha `:` → correção: virou ponto ou vírgula; a base
  teórica do slide 1 foi reordenada.
- **Legenda do gráfico de custo invadindo a faixa 3 do slide 3** → causa: ao perder o
  subtítulo, a figura ficou mais alta e o `figura()` ajustava só pela largura → correção:
  `maxh=3.40` no slide 3.

### Safeguards e lacunas

- ✅ **Protegido/validado:** gráfico e tabela agora batem número a número (+200,2% / +161,6% /
  +103,7% / +47,3% no painel de 5 bps). Deck validado com renderização real via COM do
  PowerPoint, slide a slide, a cada iteração. Anonimato conferido: metadados limpos
  (`last_modified_by` era `'Steve Canny'`, default do python-pptx) e varredura por
  identificadores no XML. Formato conferido: 5 páginas, razão 1,7778.
- ⚠️ **Requer atenção:** o deck tem **~1.517 palavras visíveis** (1.224 nativas + ~291 nas
  figuras) contra as ~750 de referência do edital. Foram quatro rodadas de corte; o que
  restou é numeral, rótulo e as definições dos termos novos. Reduzir mais implica remover
  explicação.
- ⚠️ **Requer atenção:** restam **29 travessões** em `r1_visuais.py`, todos em figuras que só
  o `RelatórioRAW.md` usa (heatmap, rolling, giro, exposições, fluxograma) e nas tabelas
  markdown. O `RelatórioRAW.md` não foi varrido.
- ⚠️ **Requer atenção:** os PNG são cobertos por `*.png` no `.gitignore`, então a regeração
  dos gráficos **não aparece no `git status`**. Quem clonar o repo precisa rodar
  `r1_visuais.py` e `r1_visuais.py --deck` para reproduzir os artefatos.
- ⚠️ **Requer atenção:** `s14_evidencia.py` com 300 sorteios de placebo continua sem execução
  completa. Os números de placebo, walk-forward e DSR citados no deck e no relatório vêm de
  execuções de protótipo.

### Pendências

- [ ] Varrer travessões no `RelatórioRAW.md` e nas figuras exclusivas do relatório, com o
      mesmo cuidado de não gerar dois-pontos duplicado.
- [ ] Rodar `s14_evidencia.py` completo (300 sorteios) e substituir os números de placebo /
      walk-forward / Deflated Sharpe se divergirem.
- [ ] Decidir se o deck fica em ~1.517 palavras ou se corta explicação para se aproximar das
      750 do edital.
- [ ] Commitar: há 5 arquivos modificados e 2 novos (`SINAPSE_relatorio_final.pptx`,
      `AAGZ.pdf`) fora de controle de versão.

---

## 2. Detalhamento passo a passo

### Etapa 1 — Janela única em gráficos e tabelas — [SUCESSO]

**Arquivos alterados**

| Arquivo | Ação | Mudança |
|---|---|---|
| `fase 7 - relatorio/src/r1_visuais.py` | alterado | `carregar()` passou a expor `idx_ativo` e `pesos_ativo`; novo helper `ativo(d, s)`; alias `r_estrategia` removido |
| `fase 7 - relatorio/src/r1_visuais.py` | alterado | `g_curva` virou duas figuras (`01a`/`01b`) com escala Y comum; `g_giro`, `g_exposicao`, `g_heatmap`, `g_rolling`, `g_distribuicao`, `g_custo`, `g_anual`, `t_anual` recortados para a janela ativa |

**Dependências**
- nenhuma

**Comandos executados**

```sh
$ python r1_visuais.py
dados:  2016-01-05 a 2025-12-30
janela do material (carteira com posicao): 2017-05-19 a 2025-12-30  (2140 pregoes)
todo grafico e toda tabela usam a segunda linha.
  [png] 01a_retorno_acumulado_5bps
  [png] 01b_retorno_acumulado_realista
  […]
```

**Resultado:** o painel de 5 bps passou a exibir +200% / +162% / +104% / +47%, idêntico à
`13_tabela_metricas_periodo.md`. A divergência apontada pelo usuário desapareceu.

---

### Etapa 2 — Afirmações que o material contradizia — [SUCESSO]

**Arquivos alterados**

| Arquivo | Ação | Mudança |
|---|---|---|
| `fase 7 - relatorio/src/r1_visuais.py` | alterado | `t_metricas`: veredito formatado do sinal de `exc_real`; `g_anual`: `neg` e anos de destaque medidos; `g_exposicao`: nova linha "líquida TOTAL"; `g_custo`: margem alfa/custo calculada; `g_rolling`: utilização do teto medida; `g_evolucao(d)`: duas últimas barras medidas |
| `fase 7 - relatorio/src/r1_visuais.py` | alterado | `t_parametros`: winsorização 3,8%→2,57%, trava 3,3%→2,3%, utilização ~65%→63%, custo 33,6→36,6 bps |
| `RelatórioRAW.md` | alterado | conclusão "+15,7%"→"+40,0%", "5 dos 9"→"3 dos 9", COVID "+0,9%"→"+1,40%"; tabela 7.3 atualizada; seções 4.1/4.3/4.4 reescritas |
| `fase 7 - relatorio/saida/13_…md`, `14_…md`, `16_…md` | alterado | regerados |

**Comandos executados**

```sh
$ python -c "... vol 63d ..."
vol 63d  max 13.63%   mediana 7.54%   %dias>12%: 7.2%
utilizacao do teto: 63%

$ python -c "... exposicao ..."
liquida (acoes) media -2.3% | p5 -44.6% p95 +40.7%
liquida + hedge       media +2.7% | p5 -7.7% p95 +14.2%
```

**Resultado:** seis afirmações contraditórias corrigidas com valor medido em vez de texto fixo.

---

### Etapa 3 — Diagnóstico e reconstrução do deck — [SUCESSO]

**Arquivos criados**

| Arquivo | Ação | Mudança |
|---|---|---|
| `SINAPSE_relatorio_final.pptx` | criado | deck de 5 páginas, 16:9 (20×11,25 pol), anônimo |
| `AAGZ.pdf` | criado | PDF exportado; **renomeado pelo usuário para a chave de envio** |
| `fase 7 - relatorio/saida/deck/*.png` | criado | 6 variantes de figura com subtítulo curto |

**Estrutura:** 1 Tese+robô · 2 Modelagem · 3 Backtest · 4 Resultados · 5 IA+Conclusão+Próximos
passos. Paleta e fonte do deck original preservadas (navy `0A1B3D`, corpo `D5E0F4`, acento
`FF7A29`, Arial).

**O que o deck antigo afirmava e foi corrigido:** "100 ações mais líquidas" → 543 regredidas;
"58 elos extraídos da CVM" → ~1.640 pares mecânicos (a extração via CVM **nunca foi
implementada** e virou próximo passo 01); "média dos 21 últimos pregões" → acumulação 12-1 +
suavização de 63 pregões; "custo 5 bps, estimativa conservadora" → 36,6 bps medidos, com os
5 bps rotulados como premissa otimista; "+27,9% / Sharpe 0,36" → +47,3%/+19,6% e Sharpe
0,592/0,296; tabela de projeção (58 elos→+8,7%, 100→+18%, 200→+26%) **removida**, por ser
contradita pela breadth medida de 16,1.

**Comandos executados**

```sh
$ python build.py
salvo: …/sinapse_deck.pptx

$ powershell render.ps1     # exporta via COM do PowerPoint
slides: 5
```

**Resultado:** deck renderizado e inspecionado slide a slide a cada iteração; sobreposições
e estouros corrigidos.

---

### Etapa 4 — Anonimato e formato — [SUCESSO]

**Comandos executados**

```sh
$ python -c "... core_properties ..."
ANTES  author='' last_modified_by='Steve Canny' title=''
DEPOIS author='' last_modified_by='' title=''

$ grep -rlio "moussalli|ricardo|poli|junior|usp|universidade|equipe" chk/
chk/ppt/media/image4.png
```

**Resultado:** metadados limpos. O único casamento (`usp`, 1 ocorrência) está em bytes
comprimidos de PNG, não em texto — verificado por contagem padrão a padrão. Formato: 5
páginas, razão 1,7778.

---

### Etapa 5 — Contagem de palavras e enxugamento — [SUCESSO]

**Achado relevante:** a primeira contagem (1.617) usava `sh.text_frame.text`, que **não pega
texto dentro de imagem**. O total real era ~1.707. A projeção que fizemos de chegar a ~1.130
estava errada: tratamos todo o texto das figuras como cortável, quando a maior parte é
título, legenda e rótulo de eixo, que precisam ficar. O ganho real das variantes de deck foi
de 151 palavras, não ~350.

| Rodada | Nativo | Figuras | Total |
|---|---|---|---|
| inicial | 1.888 | 442 | — |
| após 2 passes de enxugamento | 1.617 | 442 | ~1.707 |
| após variantes de deck | 1.265 | **291** | ~1.556 |
| após travessão + artigos | 1.254 | 291 | ~1.545 |
| **após corte de redundância (slides 2 e 5)** | **1.224** | 291 | **~1.515** |

**Corte de redundância mais relevante:** no slide 2 o elo mútuo entre as cabeças aparecia
**três vezes** (etapa 04, linha solta sob o diagrama, e painel "Por que isso importa"). A
linha solta saiu; a etapa 04 passou a só descrever a regra; o painel guarda o fato **e** o
porquê.

**Preservado de propósito:** "Escalas independentes" no drawdown (única advertência contra
comparar a altura dos painéis), "2017 é parcial" no anual (não está em outro lugar do deck),
"Total 2,84% ao ano" no custo (única aparição), e a fórmula `IR ≈ IC × √breadth` com a
explicação de por que 134 posições valem 16 apostas.

---

### Etapa 6 — Travessão (—) → dois-pontos — [SUCESSO]

**Arquivos alterados**

| Arquivo | Ação | Mudança |
|---|---|---|
| `fase 7 - relatorio/src/r1_visuais.py` | alterado | 11 travessões trocados nos títulos das figuras do deck |

**Resultado:** 33 travessões no deck → 0. Em 11 casos o `:` ficaria agramatical e entrou
vírgula ou ponto. O traço de intervalo (en dash: `2016–2025`, `3–5σ`, `fev–abr`) é outro
caractere e ficou intacto. Cinco dois-pontos duplicados criados pela troca foram detectados
por verificação automática e corrigidos.
