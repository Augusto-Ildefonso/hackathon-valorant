# VaváGym: pitch kit (Stream F)

Deadline: **23/10/2026 23h59 (Brasília)**. Deliverables per `RULES.md`: pitch video up to 5 min (YouTube, unlisted), link to the
slides, optional prototype link, and the form with the team name and **all** member names. Late submissions may be discarded.

Everything below was checked against the running app on 2026-10-21 (numbers come from the data, none are invented).
Regenerate the showcase list with `backend/.venv/bin/python backend/scripts/showcase.py`.

## 1. One-line pitch
VaváGym turns 336 real university-tournament maps into **impartial, evidence-backed analysis** for any player, team, map or match,
and into a **round-by-round Action Plan** for the next match: round type, buy, strategy, enemy weak points and probable enemy move,
each with the sample size behind it.

## 2. Showcase entities (all verified to render with no console errors)
| Scene | Entity | Why |
|---|---|---|
| Home search | player `chadu#2007` (CEUB Octopus, K/D 1,98 in 9 matches, first of the K/D leaderboard) | real top player, search works by handle |
| Team | **UFMT Turuna** (36 maps, most played) | no panel falls into low sample |
| Map | **Ascent** (86 matches, has minimap): attack wins 47%, defense 53%; "Zona descoberta no meio do mapa: 61 de 123 abates dos adversários saíram dali sem ninguém olhando" | clear blind spot to toggle on the heatmap |
| Match report | `/partida/560367e5-24b2-4a9e-9be0-c711ca258398`: PUCGO Sistematica Academy 17 x 19 Fatec PG, Sunset (overtime, 36 rounds, 248 kills with positions, one ace) | long close match, rich kill replay |
| Action Plan | **Azure Bears Golden x UFMT Turuna on Ascent** (11 and 12 maps of history) | both teams know the map, plan is not "low sample" |

Fallbacks if one fails on the day: Haven with Azure Bears Black x Totale UMC (10 and 11 maps), match `fdcc8977-35d4-4234-b985-eb1e5d2f3791`.

## 3. Storyline (5:00) mapped to the judging criteria
| Time | Scene | What to say (pt-BR, short) | Criterion |
|---|---|---|---|
| 0:00-0:30 | Title + Home KPIs | "Treinadores têm milhares de números e pouca resposta. O VaváGym usa 336 mapas, 6.618 rounds e 46.753 abates reais para dizer o que melhorar e por quê." | Impacto |
| 0:30-1:00 | Início (chat): type "informações do jogador chadu#2007" → readable answer → "Ver no dashboard" → Player (the chat is optional; the sidebar and the global search still work) | "Qualquer jogador, time, mapa ou partida. É imparcial: não existe 'nosso time'. Cada ponto forte ou fraco mostra o número, a mediana do campeonato e a amostra; amostra pequena aparece com aviso." | Qualidade da análise |
| 1:00-1:40 | Team (UFMT Turuna) | "Para o time: pontos fortes, fraquezas, papéis comportamentais e recomendações, todas com evidência." | Análise / Usabilidade |
| 1:40-2:30 | Map Ascent: toggle zonas perigosas / descobertas | "Aqui o mapa mostra onde os abates acontecem e onde ninguém está olhando: 61 de 123 abates saíram do meio sem cobertura." | Inovação |
| 2:30-3:10 | Match report: scoreboard, timeline, click round → replay | "No pós-jogo, a linha do tempo leva ao replay de abates no minimapa, com direção de visão." | Protótipo |
| 3:10-4:20 | **Action Plan** (Golden x Turuna on Ascent): timeline of 24 rounds, click R5, flip perspective | "O diferencial: um plano round a round. Para cada round: tipo previsto, compra, estratégia, pontos fracos e movimento provável do adversário, com contingência se vencer ou perder o anterior." Show a round whose type changes in the contingency. | Inovação + Impacto |
| 4:20-4:45 | "Análise por IA" toggle (only if the key works at recording time) | "Opcional: uma IA reescreve e propõe insights, mas o código valida cada número; se falhar, voltamos às regras." | Viabilidade |
| 4:45-5:00 | Close | "Só dados fornecidos, só pós-jogo, funciona offline. Próximo passo: lineups e utilitários quando a base tiver esses dados." | Viabilidade |

Rules to mention once (builds trust with the Riot judges): data only from the provided JSON; analysis and post-match use only;
no Riot logos or fonts; catalog images are the supplied ones (usage confirmed by the organizers).

## 4. Honest limits (say them, do not hide them)
- No utility, lineup or callout data in the files: plans cover positioning, timing, roles and economy only.
- Roles are behavioral estimates (top 2 + confidence); IGL is deliberately not guessed.
- Abyss and Summit have no minimap in the catalog; the UI explains it.
- Win probability model: validated on 93 held-out matches (log-loss 0,623 vs 0,640 for the empirical baseline), a modest, honest gain.
- AI mode is optional, slow (20 s to 2 min) and always falls back to the rules.

## 5. Slides outline (link goes in the form)
1. Problema (coach has numbers, not answers) · 2. Para quem (jogador, treinador/analista, time) · 3. Dados usados (336/6.618/46.753) ·
4. Como pensamos (regras com percentis + evidência + amostra; IA opcional validada) · 5. Telas (6 prints from `demo-shots`) ·
6. Plano de Ação (diferencial) · 7. Limites e próximos passos · 8. Equipe.
Screenshots: `cd frontend && npm run demo-flow ../demo-shots` (dev servers running) writes the six scene images.

## 6. Pre-recording QA checklist (run at CP, repeat before recording)
- [ ] `make test` green (backend + `tsc`).
- [ ] `make dev`, then `cd frontend && npm run smoke` → "all routes ok" (10 routes x 1440/1024 px: no console errors, no failed API calls, one `h1`, alt texts, no horizontal overflow).
- [ ] `npm run demo-flow` → all 6 steps ok, look at the images.
- [ ] Action Plan for the showcase matchup loads in in about 6 s the first time (instant when cached).
- [ ] If showing AI mode: key in `.env` (`GEMINI_API_KEY`), test the toggle once before recording (quota may be exhausted; the app falls back and says so).
- [ ] Browser zoom 100%, window 1440 wide, dark theme, no personal bookmarks or notifications on screen.
- [ ] Do the recording from the same build you submit; keep a backup recording from the previous build.

## 7. Submission checklist (human tasks, cannot be automated)
- [ ] Slides finished and shared as "anyone with the link can view".
- [ ] Pitch recorded (up to 5:00), uploaded to YouTube as **Não listado**, link opens in a private window.
- [ ] Prototype link or repository link (optional complementary material); if only local, say in the slides how to run (`make setup && make dev`).
- [ ] Form filled with the team name and **all** member names. Target: submitted by **22:00** on 23/10 (buffer before 23h59).
- [ ] Screenshot of the form confirmation.
