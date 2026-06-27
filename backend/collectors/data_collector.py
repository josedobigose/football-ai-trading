"""
Coletor de dados: jogos do dia, odds e estatísticas.
"""

import os
import requests
import logging
import random
from datetime import date, datetime
from typing import Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ODDS_API_KEY = os.getenv("ODDS_API_KEY", "")
FOOTBALL_API_KEY = os.getenv("FOOTBALL_API_KEY", "")

FOOTBALL_API_BASE = "https://v3.football.api-sports.io"
ODDS_API_BASE = "https://api.the-odds-api.com/v4"

LIGAS_MONITORADAS = {
    78:  "Bundesliga",
    39:  "Premier League",
    140: "La Liga",
    135: "Serie A",
    79:  "Bundesliga 2",
    61:  "Ligue 1",
    1:   "Copa do Mundo",
}


def buscar_jogos_do_dia() -> list[dict]:
    hoje = date.today().strftime("%Y-%m-%d")

    if not FOOTBALL_API_KEY:
        logger.warning("FOOTBALL_API_KEY não configurada. Usando dados de exemplo.")
        return _jogos_exemplo()

    headers = {
        "x-rapidapi-key": FOOTBALL_API_KEY,
        "x-rapidapi-host": "v3.football.api-sports.io"
    }

    jogos = []
    for liga_id, liga_nome in LIGAS_MONITORADAS.items():
        try:
            resp = requests.get(
                f"{FOOTBALL_API_BASE}/fixtures",
                headers=headers,
                params={"date": hoje, "league": liga_id, "season": datetime.now().year},
                timeout=10
            )
            resp.raise_for_status()
            for fixture in resp.json().get("response", []):
                jogos.append({
                    "fixture_id": fixture["fixture"]["id"],
                    "campeonato": liga_nome,
                    "liga_id": liga_id,
                    "time_casa": fixture["teams"]["home"]["name"],
                    "time_visitante": fixture["teams"]["away"]["name"],
                    "horario": fixture["fixture"]["date"],
                })
        except Exception as e:
            logger.error(f"Erro liga {liga_nome}: {e}")

    logger.info(f"✅ {len(jogos)} jogos encontrados para {hoje}")
    return jogos


def buscar_odds(time_casa: str, time_visitante: str, liga_id: int) -> dict:
    if not ODDS_API_KEY:
        return _odds_simuladas()

    sport_key = _liga_para_sport_key(liga_id)
    if not sport_key:
        return _odds_simuladas()

    try:
        resp = requests.get(
            f"{ODDS_API_BASE}/sports/{sport_key}/odds",
            params={
                "apiKey": ODDS_API_KEY,
                "regions": "eu",
                "markets": "h2h,totals",
                "oddsFormat": "decimal",
            },
            timeout=10
        )
        resp.raise_for_status()
        for evento in resp.json():
            casa = evento.get("home_team", "").lower()
            vis = evento.get("away_team", "").lower()
            if time_casa.lower() in casa or time_visitante.lower() in vis:
                return _extrair_odds(evento)
    except Exception as e:
        logger.error(f"Erro odds: {e}")

    return _odds_simuladas()


def buscar_estatisticas(fixture_id: int, liga_id: int) -> dict:
    if not FOOTBALL_API_KEY:
        return _estatisticas_simuladas()

    headers = {
        "x-rapidapi-key": FOOTBALL_API_KEY,
        "x-rapidapi-host": "v3.football.api-sports.io"
    }

    try:
        resp = requests.get(
            f"{FOOTBALL_API_BASE}/fixtures/statistics",
            headers=headers,
            params={"fixture": fixture_id},
            timeout=10
        )
        resp.raise_for_status()
        data = resp.json().get("response", [])
        if not data:
            return _estatisticas_simuladas()

        stats = {}
        for team_data in data:
            for stat in team_data.get("statistics", []):
                stats[stat["type"]] = stat["value"]
        return stats or _estatisticas_simuladas()

    except Exception as e:
        logger.error(f"Erro stats: {e}")
        return _estatisticas_simuladas()


def _liga_para_sport_key(liga_id: int) -> Optional[str]:
    mapa = {
        78:  "soccer_germany_bundesliga",
        39:  "soccer_epl",
        140: "soccer_spain_la_liga",
        135: "soccer_italy_serie_a",
        79:  "soccer_germany_bundesliga2",
        61:  "soccer_france_ligue_one",
        1:   "soccer_fifa_world_cup",
    }
    return mapa.get(liga_id)


def _extrair_odds(evento: dict) -> dict:
    odds = {"odd_lay_goleada_casa": None, "odd_lay_goleada_visitante": None, "odd_lay_0x0": None}
    for bookmaker in evento.get("bookmakers", []):
        for market in bookmaker.get("markets", []):
            if market["key"] == "h2h":
                for o in market.get("outcomes", []):
                    if o["name"] == evento["home_team"]:
                        odds["odd_lay_goleada_casa"] = o["price"]
                    elif o["name"] == evento["away_team"]:
                        odds["odd_lay_goleada_visitante"] = o["price"]
            elif market["key"] == "totals":
                for o in market.get("outcomes", []):
                    if o.get("point") == 0.5 and o["name"] == "Under":
                        odds["odd_lay_0x0"] = o["price"]
        break
    return odds


def _jogos_exemplo() -> list[dict]:
    hoje = date.today().isoformat()
    return [
        {"fixture_id": 1001, "campeonato": "Premier League",  "liga_id": 39,  "time_casa": "Manchester City",  "time_visitante": "Arsenal",          "horario": f"{hoje}T15:00:00+00:00"},
        {"fixture_id": 1002, "campeonato": "Premier League",  "liga_id": 39,  "time_casa": "Liverpool",         "time_visitante": "Chelsea",           "horario": f"{hoje}T17:30:00+00:00"},
        {"fixture_id": 1003, "campeonato": "La Liga",         "liga_id": 140, "time_casa": "Real Madrid",       "time_visitante": "Barcelona",         "horario": f"{hoje}T20:00:00+00:00"},
        {"fixture_id": 1004, "campeonato": "La Liga",         "liga_id": 140, "time_casa": "Atletico Madrid",   "time_visitante": "Sevilla",           "horario": f"{hoje}T18:00:00+00:00"},
        {"fixture_id": 1005, "campeonato": "Bundesliga",      "liga_id": 78,  "time_casa": "Bayern Munich",     "time_visitante": "Borussia Dortmund", "horario": f"{hoje}T16:30:00+00:00"},
        {"fixture_id": 1006, "campeonato": "Bundesliga",      "liga_id": 78,  "time_casa": "Bayer Leverkusen",  "time_visitante": "RB Leipzig",        "horario": f"{hoje}T14:30:00+00:00"},
        {"fixture_id": 1007, "campeonato": "Serie A",         "liga_id": 135, "time_casa": "Inter Milan",       "time_visitante": "AC Milan",          "horario": f"{hoje}T19:45:00+00:00"},
        {"fixture_id": 1008, "campeonato": "Serie A",         "liga_id": 135, "time_casa": "Juventus",          "time_visitante": "Napoli",            "horario": f"{hoje}T17:00:00+00:00"},
        {"fixture_id": 1009, "campeonato": "Ligue 1",         "liga_id": 61,  "time_casa": "PSG",               "time_visitante": "Marseille",         "horario": f"{hoje}T20:00:00+00:00"},
        {"fixture_id": 1010, "campeonato": "Ligue 1",         "liga_id": 61,  "time_casa": "Monaco",            "time_visitante": "Lyon",              "horario": f"{hoje}T18:00:00+00:00"},
        {"fixture_id": 1011, "campeonato": "Bundesliga 2",    "liga_id": 79,  "time_casa": "Hamburg",           "time_visitante": "Schalke",           "horario": f"{hoje}T13:30:00+00:00"},
        {"fixture_id": 1012, "campeonato": "Bundesliga 2",    "liga_id": 79,  "time_casa": "Hannover",          "time_visitante": "Kaiserslautern",    "horario": f"{hoje}T13:30:00+00:00"},
    ]


def _odds_simuladas() -> dict:
    return {
        "odd_lay_goleada_casa": round(random.uniform(2.0, 5.0), 2),
        "odd_lay_goleada_visitante": round(random.uniform(2.5, 7.0), 2),
        "odd_lay_0x0": round(random.uniform(1.3, 3.0), 2),
    }


def _estatisticas_simuladas() -> dict:
    return {
        "media_gols_marcados_casa": round(random.uniform(1.2, 2.8), 2),
        "media_gols_sofridos_casa": round(random.uniform(0.8, 1.8), 2),
        "media_gols_marcados_visitante": round(random.uniform(1.0, 2.5), 2),
        "media_gols_sofridos_visitante": round(random.uniform(0.9, 2.0), 2),
        "xg_casa": round(random.uniform(1.2, 2.5), 2),
        "xg_visitante": round(random.uniform(1.0, 2.2), 2),
        "historico_goleadas_casa": random.randint(0, 2),
        "historico_goleadas_visitante": random.randint(0, 2),
        "historico_0x0_casa": random.randint(0, 2),
        "historico_0x0_visitante": random.randint(0, 2),
        "elo_casa": round(random.uniform(1500, 1900), 0),
        "elo_visitante": round(random.uniform(1450, 1850), 0),
    }
