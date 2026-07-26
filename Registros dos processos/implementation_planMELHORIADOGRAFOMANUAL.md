# Plano de Expansão e Verificação do Grafo Manual

## 1. Crítica Racional: Os Tipos de Elo atuais são limitados?
**Sim, eles são limitados.** 
Os 4 critérios iniciais (`fornecedor`, `cliente`, `imobiliario_logistica` e `concorrente`) cobrem as forças básicas de Porter e a cadeia de suprimentos física, o que é excelente para empresas industriais e de varejo. No entanto, a bolsa brasileira (B3) possui características fortíssimas que escapam dessas categorias:

1.  **Teia Societária (Cross-ownership):** A bolsa brasileira é dominada por holdings e subsidiárias. Um choque idiossincrático na subsidiária destrói o valor da holding instantaneamente, não por fornecimento, mas por equivalência patrimonial (Ex: Itaúsa e Itaú; Bradespar e Vale; Cosan e Raízen).
2.  **Bens Substitutos vs. Concorrência Direta:** Concorrência pura (soma-zero) ocorre quando duas empresas vendem exatamente a mesma coisa (Localiza vs Movida). Bens substitutos ocorrem em crises específicas: se há um choque negativo severo na JBS por febre aftosa (carne bovina), a BRF (frango/suíno) captura a demanda por substituição de proteína, não apenas por concorrência de gôndola.
3.  **Dependência de Crédito (Credor/Devedor):** Choques de crédito (como o caso Americanas) afetam diretamente os balanços dos bancos expostos.

**Proposta de Melhoria:** Devemos adicionar os elos `holding_subsidiaria`, `substituto` e `credor_devedor` aos nossos critérios no `CRITERIOS_GRAFO_MANUAL.md`.

---

## 2. Proposta de Revisão e Justificativa dos 30 Elos (Base Verificável)

Para garantir que o `grafo_manual_base.csv` seja blindado contra críticas da banca, cada um dos 30 elos foi revisado, substituindo empresas deslistadas (como ENBR3) por pares reais, e justificado com base em dados públicos do mercado:

### Cadeia Vale (VALE3 - Âncora)
1.  **VALE3 $\rightarrow$ USIM5** (`cliente`, Força: 0.7, Direção: 1): A Usiminas depende do minério de ferro nacional da Vale para alimentar seus altos-fornos.
2.  **VALE3 $\rightarrow$ CSNA3** (`concorrente`, Força: 0.6, Direção: -1): A CSN possui a CSN Mineração (CMIN3). Um choque negativo na Vale (ex: paralisação de mina) aumenta o prêmio de minério, beneficiando a CSN.
3.  **VALE3 $\rightarrow$ BRAP4** (`holding_subsidiaria`, Força: 0.9, Direção: 1): A Bradespar é uma holding cujo principal ativo é a Vale. A correlação beira 1.

### Cadeia Petrobras (PETR4 - Âncora)
4.  **PETR4 $\rightarrow$ VBBR3** (`cliente`, Força: 0.8, Direção: 1): A Vibra (ex-BR) compra derivados diretamente das refinarias da Petrobras para distribuir.
5.  **PETR4 $\rightarrow$ UGPA3** (`cliente`, Força: 0.7, Direção: 1): O braço Ipiranga (Ultrapar) tem a mesma dependência de fornecimento da Petrobras.
6.  **PETR4 $\rightarrow$ PRIO3** (`concorrente`, Força: 0.6, Direção: -1): Independentes de petróleo. Um choque negativo regulatório na Petrobras atrai capital para petroleiras privadas.
7.  **PETR4 $\rightarrow$ BRAV3** (`concorrente`, Força: 0.5, Direção: -1): Brava Energia (fusão 3R + Enauta). Mesma tese da PRIO3.

### Cadeia Indústria e Bens de Capital
8.  **WEGE3 $\rightarrow$ AERI3** (`fornecedor`, Força: 0.9, Direção: 1): A Aeris fabrica pás eólicas e a WEG é historicamente sua cliente dominante de equipamentos de geração.
9.  **WEGE3 $\rightarrow$ ROMI3** (`cliente`, Força: 0.5, Direção: 1): A Indústrias Romi (máquinas industriais) utiliza motores elétricos e automação da WEG em seu maquinário pesado.

### Cadeia Varejo de Moda (LREN3 - Âncora)
10. **LREN3 $\rightarrow$ MULT3** (`imobiliario_logistica`, Força: 0.6, Direção: 1): Renner é âncora histórica dos shoppings da Multiplan.
11. **LREN3 $\rightarrow$ IGTI11** (`imobiliario_logistica`, Força: 0.6, Direção: 1): Iguatemi sofre impacto direto em fluxo e vacância se a Renner for mal.
12. **LREN3 $\rightarrow$ ALOS3** (`imobiliario_logistica`, Força: 0.6, Direção: 1): Allos (ex-Aliansce). Mesma lógica imobiliária.
13. **LREN3 $\rightarrow$ CEAB3** (`concorrente`, Força: 0.7, Direção: -1): C&A é a principal concorrente direta em vestuário na mesma faixa de renda.
14. **LREN3 $\rightarrow$ GUAR3** (`concorrente`, Força: 0.7, Direção: -1): Riachuelo (Guararapes). Soma-zero no varejo de moda.

### Cadeia E-commerce (MGLU3 - Âncora)
15. **MGLU3 $\rightarrow$ BHIA3** (`concorrente`, Força: 0.8, Direção: -1): Casas Bahia (ex-Via). O tombo de uma significa ganho imediato de market share da outra.
16. **MGLU3 $\rightarrow$ LOGG3** (`imobiliario_logistica`, Força: 0.6, Direção: 1): A LOG CP loca galpões logísticos pesados para players de e-commerce.

### Cadeia Celulose (SUZB3 - Âncora)
17. **SUZB3 $\rightarrow$ KLBN11** (`concorrente`, Força: 0.7, Direção: -1): Klabin é a principal rival na produção de papel/celulose no Brasil.
18. **SUZB3 $\rightarrow$ AMBP3** (`fornecedor`, Força: 0.5, Direção: 1): Ambipar provê soluções robustas de resposta a emergências e resíduos industriais para as gigantes do papel.

### Cadeia Proteína (JBSS3 - Âncora)
19. **JBSS3 $\rightarrow$ MRFG3** (`concorrente`, Força: 0.7, Direção: -1): Marfrig. Concorrência direta no abate bovino (EUA e BR).
20. **JBSS3 $\rightarrow$ BEEF3** (`concorrente`, Força: 0.6, Direção: -1): Minerva. Concorrência focada em exportação bovina BR.
21. **JBSS3 $\rightarrow$ BRFS3** (`substituto`, Força: 0.7, Direção: -1): BRF domina frango/suíno. Se a JBS (focada em bovinos) sofre um choque sanitário, ocorre migração imediata de consumo para frango.

### Cadeia Financeira (ITUB4 e B3SA3 - Âncoras)
22. **ITUB4 $\rightarrow$ BBDC4** (`concorrente`, Força: 0.8, Direção: -1): Itaú vs Bradesco. A guerra secular por spread bancário e clientes.
23. **ITUB4 $\rightarrow$ ITSA4** (`holding_subsidiaria`, Força: 0.9, Direção: 1): Itaúsa é a holding que controla o Itaú. O valor de face deriva diretamente do banco.
24. **B3SA3 $\rightarrow$ BPAC11** (`cliente`, Força: 0.5, Direção: 1): BTG Pactual é um heavy-user de tesouraria. Falhas estruturais na B3 afetam a receita institucional dos bancos de investimento.

### Cadeias Domésticas (Aluguel, Imóveis e Varejo Farmácia)
25. **RENT3 $\rightarrow$ MOVI3** (`concorrente`, Força: 0.8, Direção: -1): Localiza e Movida. Concentração pura do setor de locação de frota.
26. **RADL3 $\rightarrow$ PGMN3** (`concorrente`, Força: 0.7, Direção: -1): RaiaDrogasil e Pague Menos. Expansão territorial agressiva e roubo de market share.
27. **CYRE3 $\rightarrow$ EZTC3** (`concorrente`, Força: 0.6, Direção: -1): Cyrela e EZTEC. Concorrentes no mercado imobiliário de média/alta renda (foco São Paulo).

### Cadeias de Utilities (Elétricas e Telecom)
28. **ELET3 $\rightarrow$ EGIE3** (`concorrente`, Força: 0.6, Direção: -1): Eletrobras e Engie Brasil. As maiores geradoras privadas do país disputando leilões e mercado livre.
29. **VIVT3 $\rightarrow$ TIMS3** (`concorrente`, Força: 0.8, Direção: -1): Vivo e TIM. O duopólio prático da telefonia móvel.
30. **VIVT3 $\rightarrow$ FIQE3** (`concorrente`, Força: 0.4, Direção: -1): Unifique. Provedora regional que sofre pressão predatória ou se beneficia dos apagões das grandes redes (Vivo).

## User Review Required

> [!IMPORTANT]
> Avalie se as inclusões de `holding_subsidiaria`, `substituto` e a revisão de tickers deslistados (como as trocas para BRAV3, BHIA3) estão aprovadas. 
> Se sim, farei a injeção desse racional formal no documento `.md` e atualizarei o `.csv`.
