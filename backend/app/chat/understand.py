"""Step 1-2 of the chat: turn a sentence into an intent plus resolved entities (accent-insensitive keywords and fuzzy names).

This is the offline path and the fallback of the LLM understanding: it must work with no key at all.
"""
from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field
from functools import lru_cache

from ..analytics.maps import canonical_map_name
from ..data.catalog import get_catalog
from ..deps import get_store
from ..routers.meta import _norm, _tables, meta
from ..schemas.chat import ChatContext, Intent

FUZZY_CUTOFF = 0.84
MIN_NAME_LEN = 3

PLAN_WORDS = ("plano", "planejar", "enfrentar", "jogar contra", "lutar contra", "preparar", "estrategia contra", " vs ", " x ", "contra o", "contra a", "contra ")
BOARD_WORDS = ("ranking", "melhores", "melhor jogador", "top ", "lider", "destaques", "quem e o melhor")
TOURNAMENT_WORDS = ("campeonato", "torneio", "copa", "fase", "campeonatos", "torneios")
MATCH_WORDS = ("ultima partida", "ultimo jogo", "ultima map", "partida recente", "partida do", "jogo do")
HELP_WORDS = ("ajuda", "o que voce faz", "o que voce pode", "o que posso", "como funciona", "o que da para", "oi", "ola", "bom dia", "boa tarde", "boa noite")
PLAYER_CUES = ("jogador", "player", "informacoes do", "info do", "perfil do", "sobre o jogador")
TEAM_CUES = ("time", "equipe", "esquadrao")
MAP_CUES = ("mapa", "map ")


@dataclass
class Names:
    teams: list[str]
    players: list[tuple[str, str, str]]  # (puuid, riot_id, team)
    maps: list[str]  # public names
    tournaments: list[dict]  # {id, name, phases}


@lru_cache(maxsize=1)
def names() -> Names:
    pt, tt = _tables(None)
    cat = get_catalog()
    maps = sorted({cat.map_ref(n).name for n in get_store().matches.map_name.unique() if cat.map_ref(n).name})
    return Names(
        teams=list(tt.index),
        players=[(str(i), str(r.riot_id), str(r.team)) for i, r in pt.iterrows() if isinstance(r.riot_id, str)],
        maps=maps,
        tournaments=[{"id": t["id"], "name": t["name"], "phases": t["phases"]} for t in meta()["tournaments"]],
    )


@dataclass
class Understood:
    intent: Intent = "unknown"
    teams: list[str] = field(default_factory=list)
    players: list[tuple[str, str, str]] = field(default_factory=list)  # candidates: ambiguity when more than one
    map: str | None = None
    tournament: str | None = None
    source: str = "rules"
    partial: tuple[str, list[str]] | None = None  # a word that belongs to several team names: (word, candidates)
    miss: str | None = None  # something the person named that does not exist ("jogador xyz")


def _has(text: str, words: tuple[str, ...]) -> bool:
    return any(w in text for w in words)


def _find_whole(text: str, name: str) -> bool:
    n = _norm(name)
    return len(n) >= MIN_NAME_LEN and re.search(rf"(?<![a-z0-9]){re.escape(n)}(?![a-z0-9])", text) is not None


def _ngrams(text: str, max_n: int = 4) -> list[str]:
    toks = re.findall(r"[a-z0-9#]+", text)
    return [" ".join(toks[i:i + n]) for n in range(1, max_n + 1) for i in range(len(toks) - n + 1)]


def _fuzzy(text: str, pool: dict[str, object], skip: set[str]) -> list[object]:
    """Best fuzzy hits of the sentence's n-grams against normalised names (typos like 'loutus')."""
    keys = list(pool)
    hits: dict[str, float] = {}
    for g in _ngrams(text):
        if len(g) < 4 or g in skip:
            continue
        for k in difflib.get_close_matches(g, keys, n=2, cutoff=FUZZY_CUTOFF):
            hits[k] = max(hits.get(k, 0), difflib.SequenceMatcher(None, g, k).ratio())
    return [pool[k] for k in sorted(hits, key=hits.get, reverse=True)]


def _teams_in(text: str, nm: Names) -> list[str]:
    found = sorted((t for t in nm.teams if _find_whole(text, t)), key=lambda t: -len(t))
    # a team name contained in a longer matched name is the same mention
    kept = [t for i, t in enumerate(found) if not any(_norm(t) in _norm(o) for o in found[:i])]
    return sorted(kept, key=lambda t: re.search(rf"(?<![a-z0-9]){re.escape(_norm(t))}", text).start())  # order of mention


def _players_in(text: str, nm: Names) -> list[tuple[str, str, str]]:
    exact = [p for p in nm.players if _norm(p[1]) in text]  # full "Name#TAG"
    if exact:
        return exact
    hits = [p for p in nm.players if _find_whole(text, p[1].split("#")[0])]
    if hits:
        longest = max(len(p[1].split("#")[0]) for p in hits)
        return [p for p in hits if len(p[1].split("#")[0]) == longest]
    return []


def _map_in(text: str, nm: Names) -> str | None:
    for m in nm.maps:
        if _find_whole(text, m):
            return m
    for tok in re.findall(r"[a-z]+", text):  # codenames ("jam", "triad") resolve through the catalog
        if len(tok) >= 3:
            c = canonical_map_name(tok)
            if c and c in nm.maps:
                return c
    return None


def _tournament_in(text: str, nm: Names) -> str | None:
    for t in nm.tournaments:
        if _find_whole(text, t["id"]) or _find_whole(text, t["name"]):
            return t["id"]
    for t in nm.tournaments:  # "rush series" / "univava" appear in only a part of the name
        words = [w for w in re.findall(r"[a-z0-9]+", _norm(t["name"])) if len(w) > 3 and not w.isdigit()]
        if words and all(w in text for w in words[:2]):
            return t["id"]
    return None


def understand_rules(message: str, ctx: ChatContext | None = None) -> Understood:
    nm = names()
    text = " " + re.sub(r"\s+", " ", _norm(message)).strip() + " "
    u = Understood()

    u.teams = _teams_in(text, nm)
    u.players = _players_in(text, nm)
    u.map = _map_in(text, nm)
    u.tournament = _tournament_in(text, nm)

    taken = {w for n in [*u.teams, *(p[1].split("#")[0] for p in u.players), *( [u.map] if u.map else [])] for w in _norm(n).split()}
    if not u.teams and not u.players:  # typos: fuzzy against names, teams first when the sentence says "time"
        want_team = _has(text, TEAM_CUES) or _has(text, PLAN_WORDS)
        want_player = _has(text, PLAYER_CUES)
        team_pool = {_norm(t): t for t in nm.teams}
        player_pool = {_norm(p[1].split("#")[0]): p for p in nm.players}
        if want_team or not want_player:
            u.teams = _fuzzy(text, team_pool, taken)[:2]  # type: ignore[assignment]
        if not u.teams and (want_player or not want_team):
            u.players = _fuzzy(text, player_pool, taken)[:1]  # type: ignore[assignment]
    if u.map is None:
        hit = _fuzzy(text, {_norm(m): m for m in nm.maps}, taken)
        u.map = hit[0] if hit else None  # type: ignore[assignment]

    if len(u.teams) < 2:  # "time CEUB": a word of several team names is not a team yet, so ask which one
        words = [w for w in re.findall(r"(?:time|equipe|contra)\s+(?:o\s+|a\s+)?(?:time\s+|equipe\s+)?([a-z0-9]{3,})", text) if w not in ("time", "equipe")]
        word = words[0] if words else None
        if word and not any(word in _norm(t).split() for t in u.teams):
            cands = [t for t in nm.teams if word in _norm(t).split()]
            if len(cands) == 1:
                u.teams = sorted([*u.teams, cands[0]], key=lambda t: text.find(_norm(t)) if _norm(t) in text else text.find(word))
            elif cands:
                u.partial = (word, cands)

    named = re.search(r"(?:jogador|player|time|equipe|mapa)\s+([a-z0-9#]+(?:\s+[a-z0-9#]+)?)", text)
    if not (u.teams or u.players or u.map or u.tournament) and named and not _has(text, HELP_WORDS):
        u.miss = named.group(1).strip()

    two_teams = len(u.teams) >= 2
    followup = bool(ctx) and re.match(r"\s*(e |agora|tambem|mas )", text) is not None
    if _has(text, HELP_WORDS) and not (u.teams or u.players or u.map or u.tournament):
        u.intent = "help"
    elif followup and ctx.team and ctx.team_b and u.map and not (u.teams or u.players):  # "e no Lotus?" after a plan
        u.intent = "plan"
    elif two_teams or (u.teams and _has(text, PLAN_WORDS) and not _has(text, MATCH_WORDS)) or (_has(text, PLAN_WORDS) and "plano" in text):
        u.intent = "plan"
    elif u.teams and _has(text, MATCH_WORDS):
        u.intent = "match"
    elif u.tournament or _has(text, TOURNAMENT_WORDS):
        u.intent = "tournament"
    elif _has(text, BOARD_WORDS) and not (u.teams or u.players):
        u.intent = "leaderboard"
    elif u.players:
        u.intent = "player"
    elif u.teams:
        u.intent = "team"
    elif u.map:
        u.intent = "map"
    return u
