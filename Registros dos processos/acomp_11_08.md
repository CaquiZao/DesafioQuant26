# Acompanhamento — 11/08

Registro incremental das mudanças desta sessão, para acompanhamento e validação pelo grupo.

> Ponto de partida: branch `correcoes-sinapse-04-08`, sincronizada com `main` (`275321a`).
> Sessões anteriores em `acomp_03_08.md` e `acomp_04_08_sessao2.md`.

---

## Estado no início da sessão

- 4 pendências fechadas (P1, P2, P5, P7); **P3 (expandir o grafo) era o gargalo único**, com três argumentos apontando para ela.
- Resultado oficial: alfa +2,81%/ano, Sharpe 0,36, vol 7,84%, excesso sobre CDI +67,5%.
- Validação OOS do grafo de produção: alfa +3,91%/ano, Sharpe 0,50, IC +0,0091 (t = 1,72).

**A pergunta desta sessão:** P3 estava dimensionada por estimativa — a tabela de Grinold em
`Correcoes1.md` conta *elos* e fecha a lacuna entre teórico e realizado com um fator de 50%
declaradamente ad hoc. Dava para trocar isso por medição?

---

## 1. Auditoria da inferência estatística

**O que era antes:** todos os t-stats do projeto saíam de fórmulas que supõem observações
independentes. Duas suspeitas foram levantadas e testadas.

**Arquivo criado:** [s12_inferencia_e_breadth.py](../fase%206%20-%20validacao/src/s12_inferencia_e_breadth.py)

### 1a. Os t-stats da decisão de direção estavam inflados — confirmado

`medir_direcao_por_categoria` no `s6` empilha todos os elos de uma categoria num vetor único
(~15 elos × 1.273 pregões) e roda um t de Pearson sobre `n` observações. Isso trata ~19.000
observações como independentes, mas **o mesmo pregão aparece uma vez por elo** — e num dia de
alta geral todos os satélites sobem juntos.

Refeito com erro-padrão **clusterizado por data** (cada pregão = um cluster):

| categoria | elos | t ingênuo | t clusterizado | inflação | \|t\| ≥ 2 |
|---|---|---|---|---|---|
| concorrente | 37 | 4,91 | **3,13** | 1,57x | sim |
| cliente | 7 | 3,61 | **2,20** | 1,64x | sim |
| holding_subsidiaria | 5 | 2,96 | **1,79** | 1,66x | **perde** |
| imobiliario_logistica | 6 | −0,89 | −0,36 | 2,49x | não |
| fornecedor | 2 | −1,38 | −1,41 | 0,98x | não |
| substituto | 1 | 0,61 | 0,59 | 1,05x | não |

**O que muda:** `concorrente` sobrevive com folga — **a conclusão central de P1 se sustenta**.
Mas `holding_subsidiaria` cruzava o limiar |t| ≥ 2 da regra conservadora com o erro-padrão
errado e não cruza com o certo. Pela regra como escrita, essa categoria volta ao prior
econômico — que por acaso é o mesmo `+1`, então **o grafo de produção não muda**. O que muda é
a justificativa: de "o in-sample tem força para isso" para "fica no prior por falta de
evidência".

> ⚠️ A tabela de P1 em `acomp_04_08_sessao2.md` está defasada: foi medida com 30 elos
> (`concorrente` = 16). Produção tem 58 (`concorrente` = 37). Se ela for reapresentada, precisa
> ser refeita.

### 1b. A suspeita sobre o t do IC foi **refutada** pelos dados

A hipótese era que a média móvel de 21 pregões no sinal deixasse os ICs diários
autocorrelacionados, inflando o t. Medido com Newey-West:

| período | IC | t ingênuo | t HAC | ρ(1) |
|---|---|---|---|---|
| IS 16–20 | +0,0118 | 2,14 | 2,09 | 0,026 |
| OOS 21–25 | +0,0091 | 1,72 | **1,84** | 0,002 |
| completo | +0,0105 | 2,73 | **2,79** | 0,014 |

ρ(1) ≈ 0. **Os t do IC reportados nas sessões anteriores estão corretos.**

Motivo: o IC de cada dia correlaciona o sinal suave com o retorno do dia **seguinte**, e esse
retorno é ruído fresco a cada pregão. A persistência do sinal não se transmite ao produto.

**Achado colateral relevante:** no período completo (10 anos) o t do IC é **2,79** — o IC *é*
significante. É o recorte OOS de 5 anos que é curto.

---

## 2. Breadth efetiva: 58 elos entregam 11,3 apostas

**O que era antes:** a projeção de P3 contava elos (23 → 50 → 100 → 200) e aplicava um fator de
50% para reconciliar com o realizado.

**O que passou a ser:** existe a medida direta. O número efetivo de apostas independentes vem
da razão de participação dos autovalores da matriz de correlação dos sinais:
`N_eff = (Σλ)² / Σλ²`.

| | |
|---|---|
| elos | 58 |
| gatilhos distintos (`empresa_A`) | 28 |
| posições com sinal ativo (OOS) | 49 |
| **apostas independentes** | **11,3** |
| razão efetiva / nominal | **23,1%** |

**Teste de Grinold, sem fator livre:**

```
contando elos    (58 apostas):   IR previsto = 1.10
breadth efetiva  (11.3 apostas): IR previsto = 0.49
Sharpe realizado OOS:                          0.50
```

A previsão com breadth efetiva bate o realizado em 0,01. **Isso substitui o fator de 50% ad hoc
por uma quantidade medida** — e diz onde mexer, o que o fator não dizia.

**Consequência para P3:** adicionar satélite a gatilho que já existe quase não aumenta breadth.
Sete elos pendurados na LREN3 são uma aposta replicada sete vezes.

---

## 3. P4 não é um problema separado — P4 *é* P3

**O que era antes:** o diagnóstico de 04/08 concluiu que o gap de volatilidade (7,84% contra
meta de 12%) era "estrutural", com as três travas agindo como substitutas.

**O que passou a ser:** dá para dizer exatamente *qual* é a estrutura, e é aritmética.

O vol-targeting escala o book para mirar 12%. Com poucas apostas, cada posição precisa ser
maior para chegar lá — `vol ≈ peso × σ × √(apostas independentes)`. Medido na carteira real
(OOS):

| | |
|---|---|
| posições ativas/dia (mediana) | 35 |
| peso médio por posição | 2,38% |
| **maior peso do dia (mediana)** | **5,00%** ← exatamente o teto |
| dias com alguma posição ≥ 4,9% | **83,7%** |
| vol anual mediana das ações | 42,9% |

A trava de nome está encostada em 84% dos dias. E a conta fecha:

| apostas independentes | peso necessário p/ 12% | vol máxima com cap de 5% |
|---|---|---|
| **11,3 (hoje)** | 8,3% | **7,2%** |
| 27 | 5,4% | 11,1% |
| **31** | **5,0%** | **12,0%** ← cap para de bloquear |
| 48 | 4,0% | 14,9% |

**Teto previsto 7,2%; vol medida 7,84%.** O modelo prevê o número observado.

> Não é possível atingir 12% de vol com 11,3 apostas independentes e teto de 5% por nome.
> Nenhuma reordenação de etapas contorna isso — o que explica por que as três correções
> testadas no `s9` falharam. **Com ~31 apostas, a vol chega aos 12% sozinha**, sem tocar em
> nenhum parâmetro de risco.

---

## 4. Quanto falta: duas perguntas, duas respostas

A Etapa 3 do `s12` separa duas coisas que o projeto vinha tratando como uma. Um erro na
primeira versão do script expôs a distinção: o cálculo analítico dava 13 e o Monte Carlo dava
45. A discordância era o bug — **são dois N diferentes**, e a checagem virou teste de sanidade
permanente no script.

- **Precisão estatística do IC** → governada pelas *posições efetivas na seção transversal*
  (31,5 hoje, derivadas do desvio medido do IC). Correlação rouba precisão devagar.
- **Teto de retorno ajustado a risco** → governado pela *breadth* (11,3). Correlação destrói
  teto rapidamente.

**A) Quando o IC fica significante?**

```
posicoes    t mediano   poder(t>=2)
      32         1.77          41%     <- ancora: reproduz o t medido de 1.84
      37         1.91          47%
      63         2.47          68%
     126         3.59          95%
```

37 posições dão t *esperado* = 2 — uma moeda. Para **80% de poder**, ~126. "Quase
significante" não é "quase provado".

**B) Quanto pode render?**

| IR alvo | breadth necessária | vs hoje | posições na razão atual |
|---|---|---|---|
| 0,75 | 27 | 2,4x | 116 |
| 1,00 | 48 | 4,2x | 207 |
| 1,50 | 107 | 9,5x | 465 |

**As três réguas convergem: precisa de 3 a 4 vezes a breadth atual.**

**Como validar:**
```bash
python "fase 6 - validacao/src/s12_inferencia_e_breadth.py"
```

---

## 5. Caminho testado e **rejeitado**: controle por subsetor

**A hipótese:** os 10 setores da B3 são grosseiros demais — "Materiais Básicos" junta minério,
celulose, siderurgia e química. Controle mais fino removeria mais fator comum, os choques
ficariam mais independentes, e a breadth subiria — elevando de uma vez o teto de IR e o de
volatilidade, **sem escrever um único elo novo**.

**Por que parecia promissor:** o grafo é estruturalmente muito fragmentado (modularidade 0,922,
20 componentes conexos). Isso sugeria que a redundância era estatística, não estrutural.

**Arquivo criado:** [s4c_subsetores.py](../fase%204%20-%20sinal%20da%20sinapse/src/s4c_subsetores.py) —
38 subsetores, 248 dos 255 tickers, classificados por natureza econômica do negócio. Separa
minério / siderurgia / celulose, E&P / distribuição de combustível, transmissão / geração,
shoppings / bancos.

### A hipótese mecânica se confirmou; o efeito útil, não

| | antes (setor) | depois (subsetor, min 5 pares) |
|---|---|---|
| R² da regressão | 0,358 | **0,401** |
| \|corr\| média entre choques | 0,0757 | **0,0689** |
| N_eff dos choques | 19,4 | **20,2** |
| **breadth efetiva** | **11,3** | **11,3** |
| IC OOS | +0,0091 | +0,0070 |
| Sharpe OOS | 0,50 | **0,14** |

O controle mais fino **realmente** removeu mais fator comum. Mas o ganho parou aí: +4% em
independência dos choques, **zero** em breadth, e o sinal piorou.

### Onde o dano se concentrou

| grupo | n | Δ correlação T+1 |
|---|---|---|
| gatilho **ficou** no setor (controle) | 7 | **+0,0000** |
| trocou p/ subsetor de **5–7 ações** | 11 | **−0,0111** |
| trocou p/ subsetor de 8–14 ações | 23 | +0,0012 |
| trocou p/ subsetor de 15+ ações | 11 | −0,0006 |

O controle é limpo: onde nada mudou, o delta foi exatamente zero. Índice de 5 ações é a média
de 4 papéis — carrega a idiossincrasia deles, e a regressão empurra esse ruído para dentro do
resíduo.

### O diagnóstico que estava errado, e por que importa

A inferência *"modularidade alta ⟹ a redundância é estatística"* estava **errada**. Modularidade
mede separação em comunidades, não distribuição de elos entre gatilhos. A decomposição real:

```
25 gatilhos com preço
   ↓  perda estatística (choques co-movem)      −19%
20,2 choques independentes
   ↓  perda ESTRUTURAL (58 elos, 28 gatilhos)   −44%
11,3 apostas independentes
```

**A perda estrutural é mais que o dobro da estatística.** Nenhum tratamento do lado da
regressão desfaz sete elos pendurados na LREN3.

### Decisão: revertido, e o limiar NÃO foi calibrado

A leitura óbvia da tabela acima seria "sobe o limiar para 8". **Não foi feito** — 8 foi lido
olhando o OOS, e escolher parâmetro assim é o data snooping que P1 existe para bloquear.

`USAR_SUBSETOR = False` no Bloco 4, com os números medidos e as duas lições no comentário. O
`s4c` e a coluna `Subsetor` **permanecem no repositório**, mesmo critério do `s9`: registro de
resultado negativo. Sem ele, a próxima pessoa tenta exatamente isso de novo.

**Pipeline revertido e verificado:** alfa OOS +3,91%/ano, Sharpe 0,50, IC +0,0091 (t = 1,72) —
idêntico ao baseline.

---

## 6. A ideia do subsetor sob o protocolo IS/OOS

Restava a objeção legítima: *"o resultado foi negativo porque 5 era um limiar mal escolhido, não
porque a ideia é ruim."* Responder isso exigia escolher o limiar **honestamente**.

**Arquivo criado:** [s13_protocolo_subsetor.py](../fase%206%20-%20validacao/src/s13_protocolo_subsetor.py)

Mesmo protocolo que validou as direções do grafo, com o compromisso fixado no código antes de
rodar:

1. Grade pré-especificada: `[baseline, 3, 5, 8, 10, 12, 15, 20]` — o **baseline é candidato**.
2. Decisão mecânica: maior IC medido **só em 2016–2020**. Sem desempate qualitativo.
3. Congela num CSV.
4. Mede 2021–2025 uma vez.

O critério é o IC (não o Sharpe) porque é o que mede a qualidade do *sinal*, que é o que o
subsetor mexe — Sharpe passa por travas, vol-targeting e custo, camadas alheias à hipótese.

### Resultado — a ideia cai sem precisar do futuro

| limiar | IC (IS) | t(IC) | breadth (IS) |
|---|---|---|---|
| **baseline (só setor)** | **+0,0118** | **2,14** | 12,3 |
| subsetor, min 3 pares | +0,0092 | 1,74 | 12,5 |
| subsetor, min 5 pares | +0,0085 | 1,61 | 12,5 |
| subsetor, min 8 pares | +0,0094 | 1,74 | 12,5 |
| subsetor, min 10 pares | +0,0111 | 2,02 | 12,2 |
| subsetor, min 12 pares | +0,0111 | 2,02 | 12,2 |
| subsetor, min 15 pares | +0,0114 | 2,08 | 12,3 |
| subsetor, min 20 pares | +0,0114 | 2,08 | 12,3 |

**O baseline vence todos os sete limiares no in-sample.** A hipótese está rejeitada pelo próprio
protocolo, **sem que o OOS precise ser consultado** — o desfecho mais limpo possível, e o que
fecha a objeção de forma definitiva.

Note também que a breadth in-sample mal se move em qualquer limiar (12,2 a 12,5 contra 12,3 do
baseline). O subsetor não entrega breadth em nenhuma calibragem.

**Como validar:**
```bash
python "fase 6 - validacao/src/s13_protocolo_subsetor.py"
```

---

## Pendências / decisões em aberto

- **P3 continua o gargalo único, agora dimensionada com número.** Três réguas independentes
  convergem em **3 a 4 vezes a breadth atual** (11,3 → ~31 para a vol; ~48 para IR = 1,0).
- **P4 está explicada e absorvida por P3.** Não é um item separado: com ~31 apostas
  independentes a vol atinge a meta sozinha. O `s8`/`s9` continuam válidos como diagnóstico,
  mas a causa raiz é breadth, não ordenação de etapas.
- **O caminho "limpar mais o resíduo" está fechado.** Testado com implementação completa e sob
  protocolo IS/OOS. Teto de ganho medido: ~4% em independência dos choques, 0% em breadth.
- **Sobra um caminho só: mais gatilhos, menos concentrados.** E dentro dele, uma consequência
  nova: **desconcentrar vale tanto quanto adicionar.** Mover 3 dos 7 elos da LREN3 para
  gatilhos novos aumenta breadth sem escrever mais elos do que já se escreveria.
- **Canal de 2 saltos inexplorado.** 7 empresas são gatilho *e* satélite (BBAS3, BBDC4, BRML3,
  BTOW3, LREN3, MGLU3, VVAR3). Testar propagação A→B→C não exige escrever elo nenhum — só
  mudar `montar_sinal_propagado`.
- **A tabela de P1 em `acomp_04_08_sessao2.md` precisa ser refeita** (mede 30 elos, produção
  tem 58) e os t-stats de lá devem ser trocados pelos clusterizados.
- **`forca` continua sem justificativa documentada** — ~58 julgamentos subjetivos entre 0,4 e
  0,9. Teste barato pendente: fixar tudo em 1,0 e comparar. Se o alfa não mudar, elimina 58
  parâmetros da defesa de graça.
- **O grafo não tem coluna de vigência** (`data_inicio`/`data_fim`) e nada adiciona elos com o
  tempo. A cobertura do universo decai silenciosamente a partir de hoje.

---

## Resumo para o grupo

Em uma linha: **P3 saiu de estimativa para medição — 58 elos entregam 11,3 apostas
independentes, e isso explica ao mesmo tempo o Sharpe (0,49 previsto vs 0,50 realizado) e o gap
de volatilidade (7,2% de teto vs 7,84% medido).**

O caminho barato de melhorar o resíduo foi implementado, medido, submetido ao protocolo IS/OOS
e **rejeitado** — o baseline vence no in-sample. Sobra um caminho: **mais gatilhos, e menos
concentrados**.

Nenhum número oficial mudou nesta sessão. O que mudou foi saber o que eles significam.
