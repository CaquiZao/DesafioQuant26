# Plano de implementação v2 — configuração A3

> **PLANO. Nada aqui foi executado.**
> Substitui o `PLANO_IMPLEMENTACAO.md` (escrito antes da descoberta do horizonte).
> Escopo: M1, M2, M3→A3, M6/M7, M9, M10, M0. Estimativa: **4 a 5 dias.**

---

# 1. O que muda, em uma tabela

| | hoje (produção) | depois |
|---|---|---|
| **choque** | `ret − β₁·IBOV − β₂·SETOR` | **`ret − β₁·IBOV`** (só mercado) |
| **universo regredido** | 73 tickers (só os do grafo) | **~249** (todos com preço) |
| **horizonte do sinal** | choque de 1 dia, média móvel 21d | **acumulado 12-1** (231d, defasado 22d) |
| **grafo** | 58 elos escritos à mão, fixos | **ensemble A3**, reconstruído mensalmente |
| **força / direção** | 0,4 a 0,9 / mista | **1,0 / +1** em todos |
| **suavização de pesos** | 10 pregões | **63 pregões** |
| **validação** | IS/OOS único | **walk-forward** |
| giro | 9,7%/dia | **~1,3%/dia** |
| nomes/dia | 27,6 | **~98** |
| breadth efetiva | 9,9 | **24,9** |
| drawdown | −26,0% | **−8,2%** |

---

# 2. A configuração congelada

Escrita aqui para ser **imutável** a partir do momento em que a Fase 4 rodar.

## 2.1 Choque limpo (M0)

```
Para cada ticker do universo, regressão rolling de 252 pregões:
    retorno_t = α + β·IBOV_t + ε_t
O choque é ε_t. O β desta regressão É o beta de mercado — usar no hedge.
```

**Mudança em relação a hoje:** sai o regressor `SETOR`. Motivo medido: a tese de difusão
intra-indústria diz que a informação de setor **é** o que se propaga; removê-la remove o sinal.
IC(T+21) do grafo manual: +0,0506 → **+0,0621**. Da regra: +0,0130 → **+0,0315**.

> **Efeito colateral bom:** o bug do "beta parcial" desaparece por construção. Com a regressão
> univariada, `res.params['IBOV']` passa a ser o beta de mercado de verdade (mediana ~1,01, contra
> 0,335 da bivariada), que é o que o hedge precisa.

## 2.2 Universo (M2)

Todos os tickers com preço e histórico suficiente — **remover a restrição `tickers_alvo`**.
Passa de 73 para ~249 regressões. Custo: irrelevante com a regressão vetorizada.

## 2.3 Grafo — ensemble A3 (substitui M3)

```
Mensalmente, para cada SUBSETOR:
    1. ordena os membros por ADTV dos 21 pregões anteriores (point-in-time)
    2. deduplica por raiz de ticker (PETR3/PETR4 contam como uma empresa)
    3. os K primeiros formam a CABECA
    4. gera elo de cada nome da CABECA para TODOS os membros do ramo, ex-self
       -> inclusive para as outras cabeças (é isto que cria os elos mútuos)
    5. forca = 1, direcao = +1

ENSEMBLE: repete para K ∈ {2, 3, 5} × peso da cabeça ∈ {igual, ponderado por ADTV}
          = 6 variantes. O sinal final é o z-score do sinal médio das 6.
```

**Por que `alvo = todos` é a peça central:** a regra antiga proibia o líder de ser satélite. Com
`alvo = todos` e K=2, formam-se elos **mútuos** entre os dois nomes mais líquidos de cada ramo —
`VALE3↔CSNA3`, `PETR3↔PETR4`, `SUZB3↔KLBN11`. É exatamente a topologia do grafo manual.

**Verificado:** a regra reproduz **100% dos 40 elos same-subsetor** do grafo manual, todos também
na direção inversa.

**Por que ensemble e não a melhor variante:** nenhum parâmetro é escolhido por desempenho. As 6
entram todas. Isso é o que torna a configuração defensável — e há evidência direta de que escolher
importa: nos testes de A1, o critério de escolha no in-sample elegeu **o pior membro OOS, duas
vezes seguidas**.

## 2.4 Sinal (M6/M7)

```
sinal_bruto_B[t] = Σ_elos  choque_A acumulado em [t-252, t-22]  ×  1  ×  (+1)
```

Ou seja: soma do choque nos 231 pregões que terminam 22 dias antes de hoje (janela 12-1 clássica).

**Por que 12-1 e não 1 dia:** o IC cresce com √h — `IC/√h` = 0,0073 / 0,0065 / 0,0069 / 0,0064 em
T+1/5/21/63. Isso é assinatura de difusão lenta. **Não é parâmetro ajustado, é fenômeno medido.**

Depois: winsorização 2% + z-score transversal (como hoje).

## 2.5 Carteira

Igual ao Bloco 5 de hoje, com três mudanças:
- **suavização de pesos: 63 pregões** (era 10) — o sinal é lento, os pesos devem ser
- bugs corrigidos (§3)
- neutralização contra beta: **ver §7, item em aberto**

## 2.6 Validação (M10)

Walk-forward de janela expansiva: decide com 2016..Y−1, testa em Y, rola. Substitui o IS/OOS
único como número oficial.

---

# 3. FASE 0 — Congelar · 30 min

| # | tarefa |
|---|---|
| 0.1 | Commit de tudo que está em working tree |
| 0.2 | Tag `v1-pre-A3` |
| 0.3 | `data/` → `data_v1_backup/` (fora do git) |

**Aceite:** `git status` limpo, tag existindo. Sem isso não há "antes vs depois" para a §5 do deck.

---

# 4. FASE 1 — Bugs · 3 h

| # | bug | arquivo:linha | correção |
|---|---|---|---|
| 1.1 | resíduo vira retorno bruto sem 252 obs | `s4_sinapse_sinal.py:233` | `sum(axis=1, min_count=1)` |
| 1.2 | beta NaN vira zero no hedge | `s5_portfolio_builder.py:209` | exigir beta válido como elegibilidade + assert de cobertura |
| 1.3 | `clip` com limite NaN não corta | `s5_portfolio_builder.py:176-178` | `.where()` explícito + `limit_w.fillna(0)` |
| 1.4 | `s11` duplica os 28 elos históricos | `s11_grafo_point_in_time.py:189-192` | remover a concatenação redundante |
| 1.5 | winsorização com `iterrows()` | `s4_sinapse_sinal.py:288-293` | `x.clip(lower=q01, upper=q99, axis=0)` — **idêntica, 14x mais rápida** |

> O bug do **beta parcial** (`s4:226-236`) não entra na lista: ele **desaparece** com M0, porque a
> regressão passa a ser univariada.

**Aceite:** dois testes novos — resíduo é NaN (não retorno bruto) antes de 252 observações; assert
de cobertura de beta. Ambos falhando no código antigo e passando no novo, que é o padrão do
projeto.

---

# 5. FASE 2 — O motor novo · 1,5 dia

## 5.1 `s4_sinapse_sinal.py` — choque e horizonte

| # | mudança |
|---|---|
| 2.1 | `calcular_choque_limpo`: remover o regressor `SETOR`; regressão passa a `ret ~ const + IBOV` |
| 2.2 | Remover `tickers_alvo` — regredir o universo inteiro |
| 2.3 | Substituir `suavizar_sinal` (média móvel 21d) por **`acumular_12_1`**: `choque.rolling(231, min_periods=120).sum().shift(22)` |
| 2.4 | Reescrever a regressão de forma vetorizada (a por-ticker fica lenta demais com 249) |

> ⚠️ **Cuidado com NaN na regressão vetorizada.** É onde um script de verificação desta sessão
> quebrou: `rolling(W).sum()` com `min_periods` default devolve NaN se houver *qualquer* NaN na
> janela, e o IBOV tem **37 dias NaN** no arquivo de índices. Se cada um desses dias mascarar todos
> os nomes, perde-se 252 dias de todo mundo — a cobertura vai a zero antes de 2020. **Use
> `min_periods` explícito e não mascare o ticker por causa de um NaN do índice.**

## 5.2 `s4d_grafo_regra.py` — NOVO, o ensemble A3

Gera o grafo mensalmente a partir de `adtv_diario.parquet` + coluna `Subsetor`. Saída: um CSV por
variante (ou um único com coluna `variante` e `mes_vigencia`).

Requisitos:
- point-in-time estrito: o grafo do mês M usa ADTV até o fim de M−1
- deduplicar por raiz de ticker antes de escolher a cabeça
- `alvo = todos ex-self`
- as 6 variantes, sem escolha

## 5.3 `montar_sinal_propagado` — ensemble

Propagar cada variante separadamente e combinar: **z-score do sinal médio** das 6.

## 5.4 `s5_portfolio_builder.py`

`janela_suavizacao_pesos = 63` (era 10).

**Aceite da Fase 2:** o pipeline roda ponta a ponta; o grafo gerado reproduz **100% dos 40 elos
same-subsetor** do grafo manual (teste automatizado — o script de verificação já existe); nomes/dia
≈ 98; breadth ≈ 25.

---

# 6. FASE 3 — A rodada única · 2 h

**Aqui se gasta o OOS.** Depois desta rodada, nenhum número muda.

```
1. s4_sinapse_sinal.py        (choque M0, universo 249, acumulação 12-1)
2. s4d_grafo_regra.py         (ensemble A3)
3. exec_s5.py                 (pesos, suavização 63d)
4. s3_backtest.py             (P&L com custo realista — ver §8)
5. walk-forward               (número oficial)
6. s12_inferencia_e_breadth   (breadth e inferência)
```

**Regra dura:** uma passada, na ordem, regerando **todos** os CSVs de `data/validacao/`. Hoje eles
são de safras diferentes (30 elos vs 58) e estão sendo citados lado a lado.

**Aceite:** todos os artefatos com o mesmo timestamp e o mesmo grafo.

---

# 7. Itens que exigem UMA decisão só no in-sample

Dois detalhes ficaram ambíguos e precisam ser resolvidos **antes** da Fase 3, decidindo só com
2016–2020 e congelando:

| # | ambiguidade | como decidir |
|---|---|---|
| 7.1 | **Neutralizar o sinal contra beta?** A configuração testada usava `z_beta`, mas a medição isolada mostrou que neutralizar **atrapalha** com suavização longa (−0,085 de Sharpe a 63d) | rodar as duas versões só no IS, escolher pelo IC in-sample, congelar |
| 7.2 | **Dupla listagem** — permitir ON/PN da mesma empresa como par? Permitir dá Sharpe 0,548; proibir dá 0,496 | **proibir**. Não é decisão de performance: um par PETR3→PETR4 não é propagação econômica, é arbitragem de classe. Proibir é a escolha defensável mesmo custando Sharpe |

O 7.2 já está decidido acima. Só o 7.1 exige rodada.

---

# 8. FASE 4 — Custo realista · 3 h

O modelo atual (5 bps flat) é **4x otimista** para este book. Com o horizonte novo o giro cai de
9,7% para 1,3%/dia, então o custo deixa de ser fatal — mas precisa estar certo.

| # | tarefa |
|---|---|
| 8.1 | Custo por faixa de ADTV: emolumentos+liquidação (2,3 bps) + corretagem (3,0–4,0) + meio-spread (2,0/5,0/11,0/24,0) |
| 8.2 | Impacto: `0,4 × σ₆₀ × √(participação)`, com clip |
| 8.3 | Aluguel BTC sobre a ponta vendida, tier por ADTV (1,0/2,0/3,5/6,0% a.a.) |
| 8.4 | Tabela de sensibilidade e **breakeven por unidade de giro** |

> Com o horizonte novo: alfa por unidade de giro ≈ **235 bps** contra ~73 bps de custo. Antes era
> 19 contra 20 — a estratégia pagava para operar. **O breakeven é o número mais defensável do
> projeto**: mostra que o resultado não depende da calibração de custo.

---

# 9. FASE 5 — A evidência · 1 dia

Cada item responde a uma pergunta que a banca vai fazer.

| # | entrega | responde |
|---|---|---|
| 9.1 | **Placebo do gatilho** — sortear qual nome é a cabeça, 300 sorteios | *"a ordenação por liquidez faz trabalho?"* → Sharpe cai de 0,496 para **0,020** |
| 9.2 | **Controle de persistência** — momento residual do próprio nome, mesmo universo | *"o grafo adiciona sobre segurar o choque no próprio nome?"* → **é a hipótese nula da tese** |
| 9.3 | **Reprodução do grafo manual** | *"a regra encontra o que vocês escreveram à mão?"* → **100% dos 40 elos, mutuamente** |
| 9.4 | **Atribuição de fator** — mom21, mom 12-1, reversão 5d, low-vol | *"isso é alfa ou é fator?"* → propagação +41,0 bp (t 1,69) **controlando por momentum** |
| 9.5 | **Deflated Sharpe com N declarado** | *"seu Sharpe é significante?"* → **N = 279**, e o DSR não passa |
| 9.6 | **Bloco de stress** — COVID, Joesley, eleição 2018, Americanas, 2022 | *"como se comporta em crise?"* |
| 9.7 | **Painel de risco** — VaR/ES, gross/net, beta rolling, concentração, capacidade | due diligence padrão |

---

# 10. FASE 6 — Documentação · 1 dia

| # | entrega |
|---|---|
| 10.1 | `CRITERIOS_GRAFO_MANUAL.md`: **corrigir a inconsistência** — o documento especifica `direcao = −1` para `concorrente`, mas o CSV tem `+1` em todas as linhas. A inversão foi decidida com protocolo e está registrada; o documento é que não foi atualizado |
| 10.2 | `PARAMETROS.md` §6: 12% é **teto de orçamento de risco**, não alvo. Reescrever a justificativa de `janela_suavizacao_pesos` (hoje diz que foi escolhida porque "dobrou o Sharpe" — é a única linha do repo que documenta escolha por resultado) |
| 10.3 | Refazer a tabela de P1 no `acomp_04_08_sessao2.md` (mede 30 elos; produção tem 58) |
| 10.4 | Registro da sessão + deck |

---

# 11. O que NÃO fazer

| | por quê |
|---|---|
| Escolher a melhor variante do ensemble A3 | o ensemble sem escolha é o ativo. Escolher reintroduz o parâmetro que o torna defensável |
| Empilhar momentum de preço | rejeitado por princípio; entra só como controle de atribuição |
| Voltar a podar elos fracos | testado: **piora**. Os elos fracos são o que dá breadth |
| Refinar a taxonomia de subsetor | testada: Subsetor está certo, agregar para Setor dá Sharpe −0,08 |
| Trocar o ordenador ADTV | testado: inverso da vol dá −0,05; nº de pregões dá −0,33 |
| Buscar elos cross-setor (MIP do IBGE etc.) | cross é **imaterial** no horizonte 12-1 (+0,0373 contra +0,0595 dos internos) |
| Adicionar o grafo manual como overlay | testado: **piora** o mecânico (0,487 contra 0,496) |
| Olhar 2021–2025 e ajustar | cada uso adicional aumenta o N do Deflated Sharpe, que já está em 279 |

---

# 12. As fragilidades a declarar no deck

Reportar antes que perguntem. Se a banca achar primeiro, a credibilidade construída com a
auto-auditoria evapora junto.

1. **O Deflated Sharpe não passa.** N = 279 configurações testadas ao longo do projeto. **O que
   sustenta o resultado é o placebo (Sharpe 0,496 → 0,020 com cabeça sorteada), não o Sharpe.**
2. **Propagação vs persistência empata no OOS.** Em corte transversal a propagação ganha
   (+32,0 bp, t 2,25 contra +23,3 bp, t 1,22). Em espaço de curva o alfa é +2,07%/ano com
   **t 1,32 — não passa de 2**. E no OOS a persistência lidera. *O grafo manual também não passa
   (t 1,69)* — os dois estão no mesmo barco.
3. **2025 foi ruim** (Sharpe anual −0,99 no A3; −2,13 no manual).
4. **Parte do ganho do A3 é mudança de universo**, não só de grafo: entram as cabeças líquidas como
   satélites. Os controles cobrem (momento residual no mesmo universo dá SR 0,266; placebo casado
   dá 0,060), mas é honesto declarar.
5. **A vol cai para 5,7%** contra meta de 12%. Alavancar para casar a vol do manual dá +4,60%/ano
   contra +6,01%. Reportar as duas.

---

# 13. Cronograma

| dia | fases | entrega |
|---|---|---|
| 1 | 0, 1 | bugs corrigidos, testes passando |
| 2–3 | 2 | motor novo: choque M0, universo 249, horizonte 12-1, ensemble A3 |
| 3 | 7 | a decisão de 7.1 só no IS, congelada |
| 4 | 3, 4 | rodada única + custo realista |
| 5 | 5, 6 | evidência + documentação |

**Caminho mínimo se apertar:** Fases 0, 1, 2, 3 e os itens 9.1, 9.2, 9.5. São os bugs, o motor
novo, uma rodada limpa, os dois placebos e o Deflated Sharpe.
