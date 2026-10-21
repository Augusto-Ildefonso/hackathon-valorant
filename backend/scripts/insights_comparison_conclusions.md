## Conclusões (leitura manual dos textos; texto fixo, não gerado)

**Como as três rodadas evoluíram.** A primeira usou um prompt simples: 118 insights propostos, 14% rejeitados pela checagem de números (o modelo escrevia "20%" ao citar a faixa) e vários exageros que a checagem não pega (ponto forte sobre valor na mediana, "domínio" com 1 a 2 jogos). Depois do prompt mais rígido, da guarda de coerência e de duas correções nos pacotes de fatos, a última rodada serviu 93 insights sem nenhuma reprovação. Esse zero depende da rodada e do prompt: a guarda continua ligada em produção.

**O que o LLM faz melhor que as regras**
- **Cruza fatos e explica o porquê**: "abre muitos rounds com abate, mas a taxa de primeira morte está acima da referência: mais cautela"; as regras só olham uma métrica por vez.
- **Estratégia e tendência explorável**: 25 insights `strategy` contra 4 das regras (por exemplo "o adversário pode reforçar o site C, onde o time planta 52%").
- **Cobre mais temas**: 46 dos 93 insights falam de assuntos que nenhuma regra cobre (funções, agentes, jogadores do elenco, sites do time).
- **Trata amostra pequena melhor**: escreve "hipótese, amostra pequena" em vez de afirmar. As regras ainda emitem "Mapa fraco: Sunset, 0%" com 2 partidas (só com o selo de amostra baixa).

**O que as regras fazem melhor**
- **Precisão e estabilidade**: mesma entrada, mesma saída; cada número foi calculado pelo código e o limiar vem do percentil do campeonato.
- **Velocidade e custo**: instantâneas e offline. O LLM levou de 20 s a mais de 200 s por página nesta rodada (cota gratuita esgotada, caindo para os modelos Gemma) e consome cota.
- **Sem texto de enchimento**: o LLM às vezes produz "dicas" fracas, como "priorize a Vandal (35%), a arma mais comprada do mapa", ou repete a mesma ideia como ponto fraco e como dica.

**Erros que a validação de números não pega (e o que foi feito)**
- Mapa: o modelo leu a contagem "61 abates" como "61%". Corrigido expressando as zonas como percentuais com referência. Lição: a qualidade depende de como cada fato é definido; um fato ambíguo gera texto errado mesmo com número "certo".
- Inferências sem base: "rounds econômicos" para Sheriff/Classic, "economia reduzida" para pistol, "quase impenetrável". Não há guarda para isso; o prompt pede para não fazer, mas continua acontecendo ocasionalmente.
- Evidência: só o primeiro fato citado vira a evidência exibida; um texto que cita dois fatos mostra a evidência de um.

**Recomendação.** Híbrido: as regras seguem como padrão e sempre ativas (pontos fortes e fracos pelos percentis, com amostra); o modo LLM entra como uma análise opcional por página, claramente rotulada, com cache em disco e queda automática para as regras. Se for para escolher uma divisão, o LLM rende mais em `tip` e `strategy` (cruzar fatos, explicar, hipóteses) e as regras em `strength`/`weakness` (limiares objetivos). Falta um toggle "Regras | IA" no frontend, que precisa de uma mudança no Figma antes.
