| parâmetro | valor | justificativa | origem |
|---|---|---|---|
| **Janela da regressão** | `252 pregões` | 12 meses de dados diários é o padrão para estimar beta com precisão sem pegar 'outra empresa' do passado. | pré-registrado |
| **Winsorização** | `2% (1% por cauda)` | Impede que um outlier domine o z-score transversal. Medido: corta 2,57% das células — é guarda leve, não proteção contra caudas gordas. | pré-registrado |
| **Trava por nome** | `5% do AUM` | Obriga o capital a se dividir em ≥20 teses. Hoje morde em apenas 2,3% dos dias — a expansão do universo a soltou. | pré-registrado |
| **Trava por setor** | `25% do gross` | Impede que um boom setorial vire aposta macro disfarçada de aposta em rede. | pré-registrado |
| **Trava de liquidez** | `10% do ADTV (21d)` | Limita a POSIÇÃO ao que seria montável. Não governa impacto de execução — quem faz isso é o modelo de custo. | pré-registrado |
| **Volatilidade-alvo** | `12% a.a.` | TETO de orçamento de risco, não alvo atingido. Utilização medida 63% (mediana da vol de 63d: 7,54%). Atingir 12% exigiria 8,3% por nome, acima da trava. | pré-registrado |
| **AUM** | `R$ 100 milhões` | Fundo de tamanho médio viável no Brasil. Curva de capacidade testada em 20 / 100 / 300 / 1000 MM. | pré-registrado |
| **Horizonte do sinal** | `12-1 (231d, defasado 22)` | IC cresce com o horizonte (+0,0076 em T+1 → +0,0389 em T+126). IC/√h cai 45%, contra 91% de um efeito de 1 dia: difusão lenta, medida. | acrescentado 08/2026 |
| **Modelo do choque** | `só-mercado (α + β·IBOV)` | A tese é difusão intra-indústria: o termo setorial removia justamente a informação que se propaga. | acrescentado 08/2026 |
| **Grafo** | `ensemble de 6 variantes` | K ∈ {2,3,5} × peso ∈ {igual, ADTV}. TODAS entram — nenhuma escolhida por desempenho. | acrescentado 08/2026 |
| **Suavização dos pesos** | `63 pregões` | Deve ser da ordem do horizonte do sinal. Consequência estrutural, não calibragem. | acrescentado 08/2026 |
| **Custo de transação** | `3 camadas` | spread por faixa de ADTV + impacto √(participação) + aluguel BTC. Medido: 36,6 bps por unidade de giro, contra 68,3 bps de alfa gerado. | acrescentado 08/2026 |