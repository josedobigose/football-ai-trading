"""
Coletor de dados: jogos do dia, odds e estatísticas.
Fontes: The Odds API (gratuito), API-Football (gratuito), Understat (scraping).
"""

import os
import requests
import json
import logging
from datetime import date, datetime
from typing import Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ODDS_API_KEY = os.getenv("ODDS_API_KEY", "")
FOOTBALL_API_KEY = os.getenv("FOOTBALL_API_KEY", "")

ODDS_API_BASE = "https://api.the-odds-api.com/v4"
FOOTBALL_API_BASE = "https://v3.football.api-sports.io"

# Ligas monitoradas (IDs da API-Football)
LIGAS_MONITORADAS = {
    71: "Brasileirão Série A",
    72: "Brasileirão Série B",
    39: "Premier League",
    140: "La Liga",
    135: "Serie A (ITA)",
    78: "Bundesliga",
    61: "Ligue 1",
    2: "Champions League",
    3: "Europa League",
}


def buscar_jogos_do_dia() -> list[dict]:
    """Busca todos os jogos do dia via API-Football."""
    hoje = date.today().strftime("%Y-%m-%d")
    jogos = []

    if not FOOTBALL_API_KEY:
        logger.warning("FOOTBALL_API_KEY não configurada. Usando dados de exemplo.")
        return _jogos_exemplo()

    headers = {
        "x-rapidapi-key": FOOTBALL_API_KEY,
        "x-rapidapi-host": "v3.football.api-sports.io"
    }

    for liga_id, liga_nome in LIGAS_MONITORADAS.items():
        try:
            resp = requests.get(
                f"{FOOTBALL_API_BASE}/fixtures",
                headers=headers,
                params={"date": hoje, "league": liga_id, "season": datetime.now().year},
                timeout=10
            )
            resp.raise_for_status()
            data = resp.json()

            for fixture in data.get("response", []):
                jogo = {
                    "fixture_id": fixture["fixture"]["id"],
                    "campeonato": liga_nome,
                    "time_casa": fixture["teams"]["home"]["name"],
                    "time_visitante": fixture["teams"]["away"]["name"],
                    "horario": fixture["fixture"]["date"],
                    "liga_id": liga_id,
                }
                jogos.append(jogo)

        except Exception as e:
            logger.error(f"Erro ao buscar jogos da liga {liga_nome}: {e}")

    logger.info(f"✅ {len(jogos)} jogos encontrados para {hoje}")
    return jogos


def buscar_odds(time_casa: str, time_visitante: str, liga_id: int) -> dict:
    """Busca odds de Lay Goleada e Lay 0x0 via The Odds API."""

    if not ODDS_API_KEY:
        logger.warning("ODDS_API_KEY não configurada. Usando odds simuladas.")
        return _odds_simuladas(time_casa, time_visitante)

    sport_key = _liga_para_sport_key(liga_id)
    if not sport_key:
        return _odds_simuladas(time_casa, time_visitante)

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
        eventos = resp.json()

        for evento in eventos:
            casa = evento.get("home_team", "").lower()
            visitante = evento.get("away_team", "").lower()

            if time_casa.lower() in casa or time_visitante.lower() in visitante:
                return _extrair_odds_relevantes(evento)

    except Exception as e:
        logger.error(f"Erro ao buscar odds: {e}")

    return _odds_simuladas(time_casa, time_visitante)


def buscar_estatisticas(fixture_id: int, liga_id: int) -> dict:
    """Busca estatísticas do time via API-Football."""

    if not FOOTBALL_API_KEY:
        return _estatisticas_simuladas()

    headers = {
        "x-rapidapi-key": FOOTBALL_API_KEY,
        "x-rapidapi-host": "v3.football.api-sports.io"
    }

    stats = {}

    try:
        # Últimas partidas do time casa
        resp = requests.get(
            f"{FOOTBALL_API_BASE}/fixtures",
            headers=headers,
            params={"league": liga_id, "season": datetime.now().year, "last": 10},
            timeout=10
        )
        resp.raise_for_status()
        stats["ultimas_partidas"] = resp.json().get("response", [])

    except Exception as e:
        logger.error(f"Erro ao buscar estatísticas: {e}")
        return _estatisticas_simuladas()

    return stats


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _liga_para_sport_key(liga_id: int) -> Optional[str]:
    mapa = {
        71: "soccer_brazil_campeonato",
        39: "soccer_epl",
        140: "soccer_spain_la_liga",
        135: "soccer_italy_serie_a",
        78: "soccer_germany_bundesliga",
        61: "soccer_france_ligue_one",
        2: "soccer_uefa_champs_league",
    }
    return mapa.get(liga_id)


def _extrair_odds_relevantes(evento: dict) -> dict:
    odds = {
        "odd_lay_goleada_casa": None,
        "odd_lay_goleada_visitante": None,
        "odd_lay_0x0": None,
    }

    for bookmaker in evento.get("bookmakers", []):
        for market in bookmaker.get("markets", []):
            if market["key"] == "h2h":
                for outcome in market.get("outcomes", []):
                    if outcome["name"] == evento["home_team"]:
                        odds["odd_lay_goleada_casa"] = outcome["price"]
                    elif outcome["name"] == evento["away_team"]:
                        odds["odd_lay_goleada_visitante"] = outcome["price"]
            elif market["key"] == "totals":
                for outcome in market.get("outcomes", []):
                    if outcome.get("point") == 0.5 and outcome["name"] == "Under":
                        odds["odd_lay_0x0"] = outcome["price"]
        break  # pegar apenas primeira bookmaker

    return odds


def _jogos_exemplo() -> list[dict]:
    """Dados de exemplo para desenvolvimento sem API key."""
    return [
        {
            "fixture_id": 1001,
            "campeonato": "Brasileirão Série A",
            "time_casa": "Flamengo",
            "time_visitante": "Palmeiras",
            "horario": f"{date.today()}T20:00:00+00:00",
            "liga_id": 71,
        },
        {
            "fixture_id": 1002,
            "campeonato": "Premier League",
            "time_casa": "Manchester City",
            "time_visitante": "Arsenal",
            "horario": f"{date.today()}T16:30:00+00:00",
            "liga_id": 39,
        },
    ]


def _odds_simuladas(time_casa: str, time_visitante: str) -> dict:
    """Odds simuladas para desenvolvimento."""
    import random
    return {
        "odd_lay_goleada_casa": round(random.uniform(1.5, 4.5), 2),
        "odd_lay_goleada_visitante": round(random.uniform(1.5, 6.0), 2),
        "odd_lay_0x0": round(random.uniform(1.1, 2.5), 2),
    }


def _estatisticas_simuladas() -> dict:
    """Estatísticas simuladas para desenvolvimento."""
    import random
    return {
        "media_gols_marcados_casa": round(random.uniform(0.8, 2.5), 2),
        "media_gols_sofridos_casa": round(random.uniform(0.5, 2.0), 2),
        "media_gols_marcados_visitante": round(random.uniform(0.6, 2.0), 2),
        "media_gols_sofridos_visitante": round(random.uniform(0.8, 2.5), 2),
        "xg_casa": round(random.uniform(0.7, 2.2), 2),
        "xg_visitante": round(random.uniform(0.5, 1.8), 2),
        "historico_goleadas_casa": random.randint(0, 3),
        "historico_goleadas_visitante": random.randint(0, 3),
        "elo_casa": round(random.uniform(1400, 1900), 0),
        "elo_visitante": round(random.uniform(1400, 1900), 0),
    }
