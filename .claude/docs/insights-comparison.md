# Regras × LLM: comparação de insights (2026-10-21)

Modelos (ordem de tentativa): gemini-3-flash-preview, gemini-flash-latest, gemini-3.5-flash, gemma-4-31b-it, gemma-4-26b-a4b-it. Amostra: 5 jogadores, 4 times, 2 mapas, 3 partidas. Gerado por `backend/scripts/compare_insights.py`. Os números vêm sempre do código; o LLM só escolhe os fatos e redige.

## Métricas

| métrica | valor |
|---|---|
| insights por regras | 61 |
| insights propostos pelo LLM | 93 |
| rejeitados pela validação dura (id inexistente, número fora dos fatos citados, formato) | 0 (0% dos propostos) |
| aceitos pela validação dura, antes da guarda de coerência | 93 |
| desses, reprovados pela guarda de coerência (ponto forte/fraco fora da faixa, direção errada, amostra baixa) | 0 (0%) |
| **insights do LLM servidos (com guarda)** | **93** |
| tópicos das regras também cobertos pelo LLM (com guarda) | 33 de 43 (77%) |
| insights do LLM sobre um tópico que nenhuma regra cobre | 46 de 93 |
| insights do LLM que cruzam 2+ tópicos | 14 de 93 |
| insights do LLM com amostra baixa declarada | 20 de 93 |
| tipos (strength/weakness/tip/strategy): regras | 18/13/26/4 |
| tipos (strength/weakness/tip/strategy): LLM com guarda | 22/15/31/25 |
| tamanho médio do texto (palavras): regras / LLM | 13.3 / 17.7 |
| latência média por chamada (sem cache) | 0.0 s |

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


## Jogador: ONEZERA 愛#JPN

Fatos enviados: 29 · propostos 6 · rejeitados (duro) 0 · reprovados na guarda 0 · 0.1 s (cache)

Tópicos das regras: map, weapon. Tópicos citados pelo LLM (com guarda): first_death, hs, map, role, weapon.

**Regras**

- **strength** — Rende muito mais em Sunset: K/D de 1,24 contra 0,98 no geral.
- **tip** — Com a Sheriff o time venceu só 36% dos rounds (média do jogador 56%): reveja quando comprá-la.
- **tip** — Em Fracture o K/D cai para 0,40 (geral 0,98): revise as posições e os ângulos desse mapa.

**LLM** (🚫 = reprovado pela guarda de coerência)

- **weakness** — O desempenho com a Sheriff é crítico, com a taxa de vitória do time sendo de 35.96%, valor significativamente abaixo da referência de 56.17%. _[Vitórias do time em rounds com Sheriff: 35.96% · ref 56.17 · n=89]_
- **weakness** — A taxa de vitória do time em rounds com a Classic (44.44%) também está abaixo da referência de 56.17%. _[Vitórias do time em rounds com Classic: 44.44% · ref 56.17 · n=36]_
- **tip** — Há espaço para melhorar a precisão, com um acerto de cabeça de 22.59%, ficando abaixo da referência de 25.87%. _[Acerto de cabeça (HS%): 22.59% · ref 25.87 · n=1567]_
- **tip** — Tente reduzir a frequência de mortes iniciais, que ocorrem em 10.21% dos rounds, superando a referência de 9.4%. _[Rounds em que morre primeiro (menor é melhor): 10.21% · ref 9.4 · n=705]_
- **strategy** — O jogador apresenta um perfil versátil, com pontuações altas em flex (0.9) e lurker (0.85), permitindo adaptações táticas durante a partida. _[Pontuação do perfil de flex (0 a 1): 0.9 · n=705]_
- **strategy** — O jogador mantém consistência positiva em mapas como Ascent (1.05 K/D), Haven (1.03 K/D) e Lotus (1.01 K/D), todos acima da referência de 0.98. _[K/D em Ascent: 1.05 · ref 0.98 · n=12]_

## Jogador: Kaytoh#prime

Fatos enviados: 28 · propostos 8 · rejeitados (duro) 0 · reprovados na guarda 0 · 0.1 s (cache)

Tópicos das regras: adr, hs, kd, map, weapon. Tópicos citados pelo LLM (com guarda): adr, agent, first_death, first_kill, hs, kd, map, opening, weapon.

**Regras**

- **strength** — Acerta a cabeça em 35% dos tiros (mediana 26%): mira precisa.
- **strength** — Causa 172 de dano por round (mediana 138): pressão constante sobre o inimigo.
- **strength** — K/D de 1,26, entre os melhores do campeonato (mediana 0,99).
- **tip** — Com a Sheriff o time venceu só 34% dos rounds (média do jogador 58%): reveja quando comprá-la.
- **tip** — Rende mais com a Operator: o time venceu 74% dos rounds em que comprou (média do jogador 58%).
- **tip** — Em Sunset o K/D cai para 0,89 (geral 1,26): revise as posições e os ângulos desse mapa.

**LLM** (🚫 = reprovado pela guarda de coerência)

- **strength** — Apresenta excelente impacto individual, estando entre os melhores do campeonato em K/D (1.26) e ADR (171.95). _[K/D: 1.26 · ref 0.99 · n=705]_
- **strength** — Precisão letal com 34.69% de acerto de cabeça, marca que o coloca entre os melhores do campeonato. _[Acerto de cabeça (HS%): 34.69% · ref 25.87 · n=1649]_
- **strength** — Domina as aberturas, com 14.47% de rounds abrindo com abate e 57.95% de duelos de abertura vencidos, ambos entre os melhores. _[Duelos de abertura vencidos: 57.95% · ref 48.73 · n=176]_
- **weakness** — Baixa eficiência com a Sheriff, com taxa de vitória de 34.18% contra a referência de 57.59%. _[Vitórias do time em rounds com Sheriff: 34.18% · ref 57.59 · n=79]_
- **tip** — Apesar de abrir muitos rounds (14.47%), a taxa de primeira morte (10.5%) está em faixa intermediária; buscar maior sobrevivência após a abertura. _[Rounds em que morre primeiro (menor é melhor): 10.5% · ref 9.4 · n=705]_
- **tip** — O K/D com Neon (1.12) e Jett (1.1) está abaixo da sua média geral de 1.26; ajustar a agressividade com esses agentes. _[K/D com Neon: 1.12 · ref 1.26 · n=12]_
- **strategy** — Hipótese de alta eficiência com a Operator (74.07% de vitórias), porém a amostra é pequena. _[Vitórias do time em rounds com Operator: 74.07% · ref 57.59 · n=27 · amostra baixa]_
- **strategy** — Amostra pequena indica potencial elevado em Split (2.04 de K/D) e Fracture (1.88 de K/D). _[K/D em Split: 2.04 · ref 1.26 · n=2 · amostra baixa]_

## Jogador: ddz#evom

Fatos enviados: 29 · propostos 5 · rejeitados (duro) 0 · reprovados na guarda 0 · 0.0 s (cache)

Tópicos das regras: map, weapon. Tópicos citados pelo LLM (com guarda): adr, hs, map, trade, weapon.

**Regras**

- **strength** — Rende muito mais em Haven: K/D de 1,64 contra 1,07 no geral.
- **tip** — Com a Classic o time venceu só 40% dos rounds (média do jogador 56%): reveja quando comprá-la.
- **tip** — Rende mais com a Bulldog: o time venceu 70% dos rounds em que comprou (média do jogador 56%).
- **tip** — Em Fracture o K/D cai para 0,67 (geral 1,07): revise as posições e os ângulos desse mapa.

**LLM** (🚫 = reprovado pela guarda de coerência)

- **strength** — Você está entre os melhores do campeonato em trocas de abate, registrando 24.94% de mortes trocadas por colegas em 437 situações, superando a referência de 21.45%. _[Mortes trocadas por um colega: 24.94% · ref 21.45 · n=437]_
- **tip** — Busque melhorar seu volume de dano e precisão: seu dano por round é 127.1 em 705 rounds (referência 138.5) e seu acerto de cabeça está em 24.43% em 1355 disparos (referência 25.87%). _[Dano por round (ADR): 127.1 · ref 138.5 · n=705]_
- **tip** — Ajuste a postura em rounds econômicos e de pistola, pois a taxa de vitórias do time fica em 40% em 80 rounds com Classic e 41.98% em 81 rounds com Sheriff, ambas abaixo da referência de 56.07%. _[Vitórias do time em rounds com Classic: 40% · ref 56.07 · n=80]_
- **strategy** — Sempre que possível, favoreça escolhas de Phantom e Bulldog no seu arsenal: o time venceu 66.67% dos 66 rounds com Phantom e 70.45% dos 44 rounds com Bulldog (referência 56.07%). _[Vitórias do time em rounds com Phantom: 66.67% · ref 56.07 · n=66]_
- **strategy** — Trate os dados de vetos com cautela como uma hipótese baseada em amostra pequena: seu K/D foi 0.67 em 2 rounds na Fracture e 0.42 em 1 round na Abyss, comparado à referência de 1.07. _[K/D em Fracture: 0.67 · ref 1.07 · n=2 · amostra baixa]_

## Jogador: balalov3#pas

Fatos enviados: 28 · propostos 8 · rejeitados (duro) 0 · reprovados na guarda 0 · 0.0 s (cache)

Tópicos das regras: kd, map, opening, weapon. Tópicos citados pelo LLM (com guarda): agent, first_death, hs, kd, map, opening, role, weapon.

**Regras**

- **strength** — K/D de 1,26, entre os melhores do campeonato (mediana 0,99).
- **strength** — Vence 58% dos duelos de abertura (mediana 49%): boa opção para abrir o round.
- **tip** — Com a Classic o time venceu só 20% dos rounds (média do jogador 57%): reveja quando comprá-la.
- **tip** — Em Sunset o K/D cai para 0,73 (geral 1,26): revise as posições e os ângulos desse mapa.

**LLM** (🚫 = reprovado pela guarda de coerência)

- **strength** — K/D de 1.26 entre os melhores do campeonato. _[K/D: 1.26 · ref 0.99 · n=705]_
- **strength** — Vence 58.02% dos duelos de abertura, entre os melhores do campeonato. _[Duelos de abertura vencidos: 58.02% · ref 48.73 · n=81]_
- **strength** — Apenas 4.82% de rounds morrendo primeiro, entre os melhores do campeonato. _[Rounds em que morre primeiro (menor é melhor): 4.82% · ref 9.4 · n=705]_
- **tip** — Melhorar a precisão de HS, que está em 22.44%. _[Acerto de cabeça (HS%): 22.44% · ref 25.87 · n=1533]_
- **tip** — Explorar o uso de Sova, que apresenta K/D de 1.3. _[K/D com Sova: 1.3 · ref 1.26 · n=24]_
- **tip** — Hipótese: revisar o uso da Classic, que possui 20% de vitórias em amostra pequena. _[Vitórias do time em rounds com Classic: 20% · ref 56.85 · n=25 · amostra baixa]_
- **strategy** — Utilizar o perfil de support (0.87) para abrir espaço, visto que vence 58.02% dos duelos de abertura e morre apenas 4.82% das vezes primeiro. _[Pontuação do perfil de support (0 a 1): 0.87 · n=705]_
- **strategy** — Priorizar Ascent e Haven, mapas onde o K/D é de 1.54. _[K/D em Ascent: 1.54 · ref 1.26 · n=12]_

## Jogador: metamorphosis#IFHY

Fatos enviados: 18 · propostos 8 · rejeitados (duro) 0 · reprovados na guarda 0 · 0.0 s (cache)

Tópicos das regras: hs, kd. Tópicos citados pelo LLM (com guarda): agent, first_death, first_kill, hs, kd, opening, role, trade.

**Regras**

- **strength** — Acerta a cabeça em 37% dos tiros (mediana 26%): mira precisa.
- **strength** — K/D de 1,20, entre os melhores do campeonato (mediana 0,99).

**LLM** (🚫 = reprovado pela guarda de coerência)

- **strength** — K/D de 1.2, posicionando-se entre os melhores do campeonato. _[K/D: 1.2 · ref 0.99 · n=53]_
- **strength** — Precisão de HS de 37.17%, destacando-se entre os melhores do campeonato. _[Acerto de cabeça (HS%): 37.17% · ref 25.87 · n=113]_
- **strength** — Taxa de trocas de 25.71%, situando-se entre os melhores do campeonato. _[Mortes trocadas por um colega: 25.71% · ref 21.45 · n=35]_
- **tip** — Tentar reduzir a frequência de mortes iniciais, que está em 11.32%, acima da referência de 9.4%. _[Rounds em que morre primeiro (menor é melhor): 11.32% · ref 9.4 · n=53]_
- **tip** — Aprimorar a eficiência em aberturas, com 53.85% de duelos vencidos e 13.21% de rounds com primeiro abate, ambos em faixa intermediária. _[Duelos de abertura vencidos: 53.85% · ref 48.73 · n=13]_
- **tip** — Analisar a consistência com Killjoy (K/D 1.12) e Fade (K/D 1.36), embora a amostra seja pequena. _[K/D com Killjoy: 1.12 · ref 1.2 · n=2 · amostra baixa]_
- **strategy** — Explorar a versatilidade entre as funções de lurker (0.83) e anchor (0.78) para adaptar a movimentação conforme a necessidade do time. _[Pontuação do perfil de lurker (0 a 1): 0.83 · n=53]_
- **strategy** — Utilizar a alta precisão de HS (37.17%) para sustentar o K/D de 1.2 em confrontos diretos. _[Acerto de cabeça (HS%): 37.17% · ref 25.87 · n=113]_

## Time: UFMT Turuna

Fatos enviados: 49 · propostos 8 · rejeitados (duro) 0 · reprovados na guarda 0 · 0.0 s (cache)

Tópicos das regras: attack_wr, map, roles, type:pistol, type:semi_eco. Tópicos citados pelo LLM (com guarda): attack_wr, map, round_wr, type:eco, type:pistol, type:semi_eco, win_rate.

**Regras**

- **strength** — Ataque forte: vence 61% dos rounds como atacante (mediana 50%).
- **strength** — Pistols fortes: vence 61% dos pistol rounds (mediana 51%).
- **strength** — Converte bem os rounds semi-eco: vence 42% deles (mediana 28%).
- **weakness** — Mapa fraco: Sunset, com só 0% de vitórias (geral 64%).
- **tip** — Priorize treinar Sunset: é o mapa em que o time mais perde (0% de vitórias).
- **tip** — A última escalação não tem um entry fragger claro: defina quem abre os rounds de ataque.

**LLM** (🚫 = reprovado pela guarda de coerência)

- **strength** — O time apresenta um desempenho sólido, com taxa de partidas vencidas de 63.89% e rounds vencidos de 55.74%, ambos entre os melhores do campeonato. _[Partidas vencidas: 63.89% · ref 47.06 · n=36]_
- **strength** — O ataque é um ponto forte expressivo, com 61.35% de rounds vencidos, situando-se entre os melhores. _[Rounds vencidos no ataque: 61.35% · ref 50 · n=326]_
- **strength** — O time é eficiente em rounds de economia específica, com vitórias em rounds pistol (61.11%) e semi-eco (41.77%) entre os melhores. _[Rounds pistol vencidos: 61.11% · ref 50.76 · n=72]_
- **weakness** — O desempenho em Haven (50%) e Summit (50%) está claramente abaixo da taxa de vitória geral do time, que é de 63.89%. _[Vitórias em Haven: 50% · ref 63.89 · n=6]_
- **tip** — Há espaço para melhorar a conversão de rounds eco (11.63%), que atualmente se encontra em faixa intermediária. _[Rounds eco vencidos: 11.63% · ref 13.64 · n=43]_
- **tip** — Recomenda-se analisar as derrotas em Sunset (0%) e Abyss (0%), embora a amostra seja pequena. _[Vitórias em Sunset: 0% · ref 63.89 · n=2 · amostra baixa]_
- **strategy** — Priorizar a escolha de Ascent em vetoes, dado o alto índice de vitórias de 83.33% no mapa. _[Vitórias em Ascent: 83.33% · ref 63.89 · n=12]_
- **strategy** — Considerar a viabilidade de Split como hipótese de mapa forte, dado o aproveitamento de 100%, apesar da amostra pequena. _[Vitórias em Split: 100% · ref 63.89 · n=2 · amostra baixa]_

## Time: Azure Bears Black

Fatos enviados: 43 · propostos 8 · rejeitados (duro) 0 · reprovados na guarda 0 · 0.0 s (cache)

Tópicos das regras: map, roles. Tópicos citados pelo LLM (com guarda): map, site, type:eco.

**Regras**

- **strength** — Mapa forte: Abyss, com 75% de vitórias (geral 52%).
- **weakness** — Mapa fraco: Haven, com só 30% de vitórias (geral 52%).
- **tip** — A última escalação não tem um entry fragger claro: defina quem abre os rounds de ataque.
- **tip** — Priorize treinar Haven: é o mapa em que o time mais perde (30% de vitórias).

**LLM** (🚫 = reprovado pela guarda de coerência)

- **strength** — O time apresenta forte desempenho no mapa Split, com 70% de vitórias contra a referência de 51.52%. _[Vitórias em Split: 70% · ref 51.52 · n=10]_
- **strength** — A equipe possui alta taxa de vitória em Abyss, atingindo 75% frente à referência de 51.52%. _[Vitórias em Abyss: 75% · ref 51.52 · n=4]_
- **weakness** — O desempenho em Haven é crítico, com apenas 30% de vitórias comparado à referência de 51.52%. _[Vitórias em Haven: 30% · ref 51.52 · n=10]_
- **weakness** — O time apresenta dificuldade no mapa Lotus, vencendo apenas 33.33% das partidas contra a referência de 51.52%. _[Vitórias em Lotus: 33.33% · ref 51.52 · n=3]_
- **tip** — É recomendável melhorar a eficiência em rounds eco, que possuem taxa de vitória de 8.89%, valor abaixo da referência de 13.64%. _[Rounds eco vencidos: 8.89% · ref 13.64 · n=45]_
- **tip** — A comissão técnica deve atentar para a defesa do site A, local onde ocorrem 45.31% dos plantes do time. _[Plantes no site A: 45.31% · n=245]_
- **strategy** — Priorizar Split no veto, explorando a força do ataque que vence 65.74% dos rounds, sustentando os 70% de vitórias no mapa. _[Vitórias em Split: 70% · ref 51.52 · n=10]_
- **strategy** — Tratar a fragilidade em Breeze como hipótese, dado que o time tem 0% de vitórias, embora a amostra seja pequena. _[Vitórias em Breeze: 0% · ref 51.52 · n=1 · amostra baixa]_

## Time: Azure Bears Golden

Fatos enviados: 46 · propostos 6 · rejeitados (duro) 0 · reprovados na guarda 0 · 0.0 s (cache)

Tópicos das regras: defense_wr, map, retake, type:full_buy. Tópicos citados pelo LLM (com guarda): map, post_plant, retake, round_wr, type:full_buy, type:pistol, type:semi_eco, win_rate.

**Regras**

- **strength** — Defesa sólida: vence 67% dos rounds como defensor (mediana 47%).
- **strength** — Bom retake: desarma a spike em 43% das plantas sofridas (mediana 28%).
- **strength** — Converte bem os rounds full buy: vence 71% deles (mediana 55%).
- **weakness** — Mapa fraco: Abyss, com só 50% de vitórias (geral 75%).
- **tip** — Priorize treinar Abyss: é o mapa em que o time mais perde (50% de vitórias).

**LLM** (🚫 = reprovado pela guarda de coerência)

- **strength** — O time demonstra domínio geral com 75% de partidas vencidas e 64% de rounds vencidos, situando-se entre os melhores do campeonato. _[Partidas vencidas: 75% · ref 47.06 · n=32]_
- **strength** — Alta eficácia em rounds de economia, com 61% de vitórias em pistols e 53% em semi-ecos, ambos entre os melhores do campeonato. _[Rounds pistol vencidos: 60.94% · ref 50.76 · n=64]_
- **strength** — Forte capacidade de fechamento e retomada, com 77% de vitórias em post-plant e 43% em retakes, situando-se entre os melhores do campeonato. _[Rounds vencidos com a spike plantada: 77.39% · ref 69.57 · n=230]_
- **tip** — Manter a consistência em rounds de compra completa, onde o time vence 71% das vezes, situando-se entre os melhores do campeonato. _[Rounds full buy vencidos: 71.04% · ref 54.65 · n=404]_
- **strategy** — Priorizar a escolha da Ascent, mapa onde o time atinge 91% de vitórias. _[Vitórias em Ascent: 90.91% · ref 75 · n=11]_
- **strategy** — Existe a hipótese, devido à amostra pequena, de que o time seja mais eficiente no ataque (68%) do que na defesa (42%) no mapa Abyss. _[Ataque vencido em Abyss: 68.42% · n=19 · amostra baixa]_

## Time: UFU Saints Trigons

Fatos enviados: 29 · propostos 6 · rejeitados (duro) 0 · reprovados na guarda 0 · 0.0 s (cache)

Tópicos das regras: defense_wr, retake, type:pistol. Tópicos citados pelo LLM (com guarda): defense_wr, retake, roles, site, type:eco, type:pistol, win_rate.

**Regras**

- **weakness** — Defesa frágil: vence só 24% dos rounds como defensor (mediana 47%).
- **weakness** — Retake fraco: desarma a spike em só 12% das plantas sofridas (mediana 28%).
- **weakness** — Pistols fracos: vence só 33% dos pistol rounds (mediana 51%).
- **tip** — A defesa vence 24% dos rounds (mediana 47%): combine trocas entre os defensores e posições de retake.
- **tip** — Retake com 12% de sucesso (mediana 28%): evite retakes em fila e entre no site com utilitários juntos.
- **tip** — Só 33% de vitórias nos pistol rounds (mediana 51%): ensaie uma jogada fixa de pistol por lado.

**LLM** (🚫 = reprovado pela guarda de coerência)

- **weakness** — O time apresenta uma taxa de vitórias de 33% em partidas, situando-se entre os piores do campeonato. _[Partidas vencidas: 33.33% · ref 47.06 · n=3]_
- **weakness** — A capacidade de retake é crítica, com apenas 12% de plantas desarmadas, índice que está entre os piores do campeonato. _[Plantas sofridas desarmadas (retake): 12% · ref 27.79 · n=25]_
- **tip** — A taxa de rounds vencidos na defesa é de 24%, ficando entre os piores do campeonato, embora a amostra seja pequena. _[Rounds vencidos na defesa: 24.14% · ref 46.72 · n=29 · amostra baixa]_
- **tip** — O desempenho em rounds pistol (33%) e eco (0%) está entre os piores do campeonato, mas a amostra é pequena. _[Rounds pistol vencidos: 33.33% · ref 50.76 · n=6 · amostra baixa]_
- **strategy** — O time demonstra preferência pelo site C, concentrando 52% de seus plantes neste local. _[Plantes no site C: 52.17% · n=23]_
- **strategy** — A escalação possui 3 jogadores com perfil de entry, indicando uma tendência de jogo voltada para a agressividade nas entradas. _[Jogadores com perfil de entry na última escalação: 3 · n=5]_

## Mapa: Ascent

Fatos enviados: 18 · propostos 4 · rejeitados (duro) 0 · reprovados na guarda 0 · 0.0 s (cache)

Tópicos das regras: attack_wr, defense_wr, site, zone. Tópicos citados pelo LLM (com guarda): site, weapon, zone.

**Regras**

- **tip** — Zona descoberta no meio do mapa: 61 de 123 abates dos adversários saíram dali sem ninguém olhando. Posicione alguém para cobri-la.
- **strategy** — Ascent favorece a defesa: ela vence 53% dos rounds (5 p.p. a mais que o outro lado).
- **strategy** — O site B recebe 52% dos plantes de Ascent e os defensores desarmam a spike em 27% deles.

**LLM** (🚫 = reprovado pela guarda de coerência)

- **weakness** — Existe uma falha grave na cobertura do meio do mapa, com 49.59% de abates inimigos ocorrendo em zonas descobertas, valor significativamente acima da referência de 24%. _[Zona descoberta: parcela dos abates inimigos na área que saíram sem nenhum adversário cobrindo (a referência é a média do dataset): 49.59% · ref 24 · n=123]_
- **tip** — Reforce a vigilância no site B, que é o alvo preferencial de ataques com 52.24% dos plantes. _[Plantes no site B (parcela dos plantes): 52.24% · n=1049]_
- **tip** — Priorize a aquisição de Vandal, a arma com maior frequência de compra nos rounds (35.43%). _[Rounds com Vandal comprada: 35.43% · n=5922]_
- **strategy** — É fundamental ajustar o posicionamento no meio do mapa para reduzir a taxa de 49.59% de abates em zonas sem cobertura. _[Zona descoberta: parcela dos abates inimigos na área que saíram sem nenhum adversário cobrindo (a referência é a média do dataset): 49.59% · ref 24 · n=123]_

## Mapa: Lotus

Fatos enviados: 19 · propostos 5 · rejeitados (duro) 0 · reprovados na guarda 0 · 0.0 s (cache)

Tópicos das regras: attack_wr, defense_wr, site, zone. Tópicos citados pelo LLM (com guarda): agent, attack_wr, site, zone.

**Regras**

- **tip** — Zona descoberta no lado de baixo da esquerda: 80 de 157 abates dos adversários saíram dali sem ninguém olhando. Posicione alguém para cobri-la.
- **strategy** — Lotus favorece a ataque: ela vence 53% dos rounds (6 p.p. a mais que o outro lado).
- **strategy** — O site C recebe 44% dos plantes de Lotus e os defensores desarmam a spike em 36% deles.

**LLM** (🚫 = reprovado pela guarda de coerência)

- **weakness** — A defesa apresenta uma vulnerabilidade crítica em zonas descobertas, com 51% dos abates inimigos ocorrendo em áreas sem cobertura, valor significativamente acima da referência de 24%. _[Zona descoberta: parcela dos abates inimigos na área que saíram sem nenhum adversário cobrindo (a referência é a média do dataset): 50.96% · ref 24 · n=157]_
- **tip** — Priorize ataques ao site A, que possui a menor taxa de desarmes (27%) em comparação ao site B (31%) e ao site C (36%). _[Plantas desarmadas no site A: 27.39% · n=482]_
- **tip** — O site C é o ponto de maior pressão para a defesa, concentrando 44% de todos os plantes realizados. _[Plantes no site C (parcela dos plantes): 43.54% · n=1254]_
- **strategy** — O lado do ataque possui vantagem competitiva no mapa, vencendo 53% dos rounds. _[Rounds vencidos pelo ataque: 53.18% · n=1653]_
- **strategy** — A composição predominante no Lotus baseia-se na escolha de Omen (19%), Raze (17%) e Fade (16%). _[Jogadores que escolhem Omen: 19.39% · n=159]_

## Partida: Azure Bears Golden x UFMT Turuna (Fracture)

Fatos enviados: 26 · propostos 6 · rejeitados (duro) 0 · reprovados na guarda 0 · 0.0 s (cache)

Tópicos das regras: losing_streak, pistols. Tópicos citados pelo LLM (com guarda): attack_wr, defense_wr, openings, player, site.

**Regras**

- **strength** — Venceu os dois pistol rounds da partida.
- **weakness** — Sequência de 4 rounds perdidos seguidos.
- **tip** — Em sequências de derrota, peça tempo e simplifique: voltar ao básico ajuda a quebrar a série.
- **weakness** — Perdeu os dois pistol rounds da partida.
- **weakness** — Sequência de 5 rounds perdidos seguidos.
- **tip** — Revise as jogadas de pistol: perder os dois entrega vantagem de economia ao adversário por vários rounds.
- **tip** — Em sequências de derrota, peça tempo e simplifique: voltar ao básico ajuda a quebrar a série.

**LLM** (🚫 = reprovado pela guarda de coerência)

- _time a_
  - **strength** — O time demonstrou grande eficiência no ataque, vencendo 70% dos rounds. _[Rounds vencidos por Azure Bears Golden no ataque: 70% · n=10]_
  - **tip** — É recomendável melhorar a taxa de duelos de abertura, que ficou em 45.45%, abaixo da referência de 50%. _[Duelos de abertura vencidos por Azure Bears Golden: 45.45% · ref 50 · n=22]_
  - **strategy** — Aproveitar o impacto de andre, que apresentou um K/D de 1.92, embora a amostra seja pequena. _[K/D de andre (Azure Bears Golden): 1.92 · n=22 · amostra baixa]_
- _time b_
  - **weakness** — A defesa foi o ponto fraco da equipe, com apenas 30% de rounds vencidos. _[Rounds vencidos por UFMT Turuna na defesa: 30% · n=10]_
  - **tip** — Manter a agressividade nas aberturas, onde a equipe venceu 54.55% dos duelos, superando a referência de 50%. _[Duelos de abertura vencidos por UFMT Turuna: 54.55% · ref 50 · n=22]_
  - **strategy** — A equipe tende a plantar mais no site B (66.67%), mas isso é uma hipótese devido à amostra pequena. _[Plantes de UFMT Turuna no site B: 66.67% · n=9 · amostra baixa]_

## Partida: Poli Plague x UFMG Fenix B (Pearl)

Fatos enviados: 26 · propostos 8 · rejeitados (duro) 0 · reprovados na guarda 0 · 0.0 s (cache)

Tópicos das regras: losing_streak, pistols. Tópicos citados pelo LLM (com guarda): attack_wr, defense_wr, openings, player, site.

**Regras**

- **weakness** — Perdeu os dois pistol rounds da partida.
- **tip** — Revise as jogadas de pistol: perder os dois entrega vantagem de economia ao adversário por vários rounds.
- **strength** — Venceu os dois pistol rounds da partida.
- **weakness** — Sequência de 4 rounds perdidos seguidos.
- **tip** — Em sequências de derrota, peça tempo e simplifique: voltar ao básico ajuda a quebrar a série.

**LLM** (🚫 = reprovado pela guarda de coerência)

- _time a_
  - **strength** — Sólida atuação na defesa, vencendo 66.67% dos rounds. _[Rounds vencidos por Poli Plague na defesa: 66.67% · n=12]_
  - **weakness** — Baixo aproveitamento em duelos de abertura, com 37.5% de vitórias contra a referência de 50%. _[Duelos de abertura vencidos por Poli Plague: 37.5% · ref 50 · n=24]_
  - **tip** — Apesar da amostra pequena, LoveHatsuneMiku apresentou um K/D de 1.71. _[K/D de LoveHatsuneMiku (Poli Plague): 1.71 · n=24 · amostra baixa]_
  - **strategy** — Hipótese de preferência pelo site A, onde ocorreram 66.67% dos plantes (amostra pequena). _[Plantes de Poli Plague no site A: 66.67% · n=9 · amostra baixa]_
- _time b_
  - **strength** — Eficiência nos duelos de abertura, com 62.5% de vitórias, superando a referência de 50%. _[Duelos de abertura vencidos por UFMG Fenix B: 62.5% · ref 50 · n=24]_
  - **weakness** — Dificuldade no ataque, com apenas 33.33% de rounds vencidos. _[Rounds vencidos por UFMG Fenix B no ataque: 33.33% · n=12]_
  - **tip** — Apesar da amostra pequena, Cientista manteve um K/D de 1.4. _[K/D de Cientista (UFMG Fenix B): 1.4 · n=24 · amostra baixa]_
  - **strategy** — Hipótese de tendência de ataque ao site A, com 60% dos plantes (amostra pequena). _[Plantes de UFMG Fenix B no site A: 60% · n=5 · amostra baixa]_

## Partida: CAAP Hellhounds x USCS Hawks (Breeze)

Fatos enviados: 26 · propostos 7 · rejeitados (duro) 0 · reprovados na guarda 0 · 0.0 s (cache)

Tópicos das regras: losing_streak, site. Tópicos citados pelo LLM (com guarda): attack_wr, defense_wr, losing_streak, openings, player, site.

**Regras**

- **weakness** — Sequência de 5 rounds perdidos seguidos.
- **weakness** — Previsível no ataque: 4 de 5 plantes foram no site A.
- **tip** — Em sequências de derrota, peça tempo e simplifique: voltar ao básico ajuda a quebrar a série.

**LLM** (🚫 = reprovado pela guarda de coerência)

- _time a_
  - **strength** — A defesa foi o ponto mais forte do time, com uma taxa de vitória de 83.33%. _[Rounds vencidos por CAAP Hellhounds na defesa: 83.33% · n=12]_
  - **tip** — A taxa de vitória no ataque foi de 42.86%, mas a amostra é pequena. _[Rounds vencidos por CAAP Hellhounds no ataque: 42.86% · n=7 · amostra baixa]_
  - **tip** — O K/D de 2.3 do jogador CAAP medina sugere um alto impacto individual, embora a amostra seja pequena. _[K/D de CAAP medina (CAAP Hellhounds): 2.3 · n=19 · amostra baixa]_
- _time b_
  - **weakness** — O ataque apresentou um desempenho muito baixo, vencendo apenas 16.67% dos rounds. _[Rounds vencidos por USCS Hawks no ataque: 16.67% · n=12]_
  - **weakness** — O time demonstrou instabilidade ao sofrer uma sequência de 5 rounds perdidos. _[Maior sequência de rounds perdidos por USCS Hawks: 5 · n=19]_
  - **tip** — A taxa de duelos de abertura vencidos (47.37%) ficou abaixo da referência de 50%. _[Duelos de abertura vencidos por USCS Hawks: 47.37% · ref 50 · n=19]_
  - **tip** — Houve uma tendência de plantar no site A em 80% das vezes, mas a amostra é pequena. _[Plantes de USCS Hawks no site A: 80% · n=5 · amostra baixa]_
