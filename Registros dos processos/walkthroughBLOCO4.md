# Fundação do Bloco 4 Concluída

Como o plano foi aprovado, eu estruturei todo o alicerce do **Bloco 4 (Sinal da Sinapse)** no projeto. O esqueleto lógico do código já está escrito e preparado para processar a regressão matemática e o grafo.

## Arquivos Criados

### 1. O Grafo Manual (A Prova de Conceito)
Criei o arquivo de texto base para a rede econômica:
[grafo_manual_base.csv](file:///c:/Users/kakam/OneDrive/Documentos/PROJETOS/DesafioQuant26/fase%204%20-%20sinal%20da%20sinapse/grafo_manual_base.csv)

Para exemplificar e evitar que ele fique vazio, pré-preenchi com as 9 relações didáticas listadas no plano (ex: Petrobras com OSXB3 e PRIO3, Vale com CSNA3 e LOGN3, etc). Este arquivo agora possui as 5 colunas estruturais vitais para o backtest rodar sem a IA inicialmente: `empresa_A`, `empresa_B`, `tipo_de_elo`, `forca`, e `direcao`.

### 2. O Motor do Sinal (Python)
Criei a raiz lógica da regressão:
[s4_sinapse_sinal.py](file:///c:/Users/kakam/OneDrive/Documentos/PROJETOS/DesafioQuant26/fase%204%20-%20sinal%20da%20sinapse/src/s4_sinapse_sinal.py)

Neste arquivo, preparei as constantes de mercado puxadas do `PARAMETROS.md` (como o limite de 2% de winsorização e 252 dias úteis da janela) e dividi a execução exatamente nos blocos do PDF:
1. `carregar_dados()`: Puxa o CSV do grafo que criamos e lerá no futuro os Parquets dos Blocos 1 e 2.
2. `calcular_choque_limpo()`: Onde a regressão será codada.
3. `montar_sinal_propagado()`: A função que forçará a assimetria (A afeta B).
4. `limpar_e_winsorizar_sinal()`: Garantia contra outliers.

## Próximos Passos
Tudo está perfeitamente alinhado com o documento `Bloco444.txt`. Agora a estrutura já consegue "respirar" dentro do ecossistema do projeto.

O desafio a partir de agora é alimentar as funções no script com os dados reais do mercado vindos da CVM/B3 (Blocos 1, 1.5 e 2) quando o time terminar de gerar os arquivos base, e então escrever a matemática exata usando `statsmodels` ou `scipy` no interior dessas funções vazias.
