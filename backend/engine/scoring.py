"""
Motor de scoring v2 — foco em Lay 0x0 com Lay Goleada como segunda opção.
Campeonatos: Bundesliga, Premier League, La Liga, Serie A, Bundesliga 2, Ligue 1
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

WEIGHTS_PATH = Path(__file__).parent.parent / "ml" / "weights.json"

# Campeonatos monitorados (ID API-Football -> nome)
CAMPEONATOS = {
    78:  "Bundesliga",
    39:  "Premier League",
    140: "La Liga",
    135: "Serie A",
    79:  "Bundesliga 2",
    61:  "Ligue 1",
}

MAX_POR_CAMPEONATO = 2
INDICE_MINIMO = 50.0


def _carregar_pesos() -> dict:
    try:
        with open(WEIGHTS_PATH) as f:
            return json.load(f)
    except FileNotFoundError:
        return _pesos_padrao()


def _pesos_padrao() -> dict:
    return {
        "lay_0x0": {
            "media_gols_total": 0.35,
            "xg_total": 0.30,
            "odd_lay_0x0": 0.20,
            "historico_0x0": 0.15,
        },
        "lay_goleada": {
            "media_gols_marcados": 0.30,
            "xg": 0.25,
            "odd_lay": 0.20,
            "historico_goleadas": 0.15,
            "diferenca_elo": 0.10,
        }
    }


@dataclass
class DadosJogo:
    fixture_id: int
    campeonato: str
    liga_id: int
    time_casa: str
    time_visitante: str
    horario: str

    media_gols_marcados_casa: float = 1.5
    media_gols_sofridos_casa: float = 1.0
    media_gols_marcados_visitante: float = 1.2
    media_gols_sofridos_visitante: float = 1.3
    xg_casa: float = 1.4
    xg_visitante: float = 1.1
    historico_goleadas_casa: int = 1
    historico_goleadas_visitante: int = 1
    historico_0x0_casa: int = 1      # qtd de jogos 0x0 nos últimos 10
    historico_0x0_visitante: int = 1
    elo_casa: float = 1600.0
    elo_visitante: float = 1550.0

    odd_lay_goleada_casa: float = 2.5
    odd_lay_goleada_visitante: float = 3.5
    odd_lay_0x0: float = 1.8


@dataclass
class Recomendacao:
    mercado: str           # LAY_0X0 | LAY_GOLEADA | NAO_OPERAR
    lado: Optional[str]    # CASA | VISITANTE | None
    probabilidade: float
    indice_qualidade: float
    confianca: float
    risco: str
    justificativas: list[str]
    status: str
    dados: DadosJogo = field(repr=False)


class MotorScoring:

    def __init__(self):
        self.pesos = _carregar_pesos()

    def analisar(self, dados: DadosJogo) -> Recomendacao:
        """Prioriza Lay 0x0, usa Lay Goleada como segunda opção."""

        score_0x0 = self._score_lay_0x0(dados)

        # Tenta Lay 0x0 primeiro
        if score_0x0["indice_qualidade"] >= INDICE_MINIMO:
            return Recomendacao(
                mercado="LAY_0X0",
                lado=None,
                probabilidade=score_0x0["probabilidade"],
                indice_qualidade=score_0x0["indice_qualidade"],
                confianca=score_0x0["confianca"],
                risco=score_0x0["risco"],
                justificativas=score_0x0["justificativas"],
                status="ENTRAR",
                dados=dados
            )

        # Segunda opção: Lay Goleada
        score_lg_casa = self._score_lay_goleada(dados, "CASA")
        score_lg_vis = self._score_lay_goleada(dados, "VISITANTE")
        melhor_lg = max(
            [("CASA", score_lg_casa), ("VISITANTE", score_lg_vis)],
            key=lambda x: x[1]["indice_qualidade"]
        )
        lado_lg, score_lg = melhor_lg

        if score_lg["indice_qualidade"] >= INDICE_MINIMO:
            return Recomendacao(
                mercado="LAY_GOLEADA",
                lado=lado_lg,
                probabilidade=score_lg["probabilidade"],
                indice_qualidade=score_lg["indice_qualidade"],
                confianca=score_lg["confianca"],
                risco=score_lg["risco"],
                justificativas=score_lg["justificativas"],
                status="ENTRAR",
                dados=dados
            )

        # Melhor score entre todos para mostrar no NAO_OPERAR
        melhor_iq = max(
            score_0x0["indice_qualidade"],
            score_lg["indice_qualidade"]
        )

        return Recomendacao(
            mercado="NAO_OPERAR",
            lado=None,
            probabilidade=score_0x0["probabilidade"],
            indice_qualidade=melhor_iq,
            confianca=score_0x0["confianca"],
            risco="ALTO",
            justificativas=[
                f"Índice de qualidade abaixo do mínimo ({INDICE_MINIMO}): {melhor_iq:.1f}/100",
                "Nenhum mercado atingiu critérios mínimos de confiança."
            ],
            status="NAO_OPERAR",
            dados=dados
        )

    def _score_lay_0x0(self, d: DadosJogo) -> dict:
        pesos = self.pesos["lay_0x0"]

        xg_total = d.xg_casa + d.xg_visitante
        media_gols_total = d.media_gols_marcados_casa + d.media_gols_marcados_visitante
        historico_0x0_medio = (d.historico_0x0_casa + d.historico_0x0_visitante) / 2

        # Componentes — quanto maior = mais chance de gol = melhor para Lay 0x0
        comp_gols = min(1.0, media_gols_total / 4.0)
        comp_xg = min(1.0, xg_total / 4.0)
        comp_odd = min(1.0, (d.odd_lay_0x0 - 1.0) / 3.0)  # odd alta = mercado precifica menos chance de 0x0
        comp_hist = max(0.0, 1.0 - (historico_0x0_medio / 4.0))  # menos 0x0 no histórico = melhor

        score = (
            comp_gols * pesos["media_gols_total"] +
            comp_xg * pesos["xg_total"] +
            comp_odd * pesos["odd_lay_0x0"] +
            comp_hist * pesos["historico_0x0"]
        )

        probabilidade = round(score * 100, 1)
        iq = self._calcular_iq(score, [comp_gols, comp_xg, comp_odd, comp_hist])
        risco = "BAIXO" if d.odd_lay_0x0 > 2.0 else ("MEDIO" if d.odd_lay_0x0 > 1.5 else "ALTO")

        justificativas = []
        if comp_gols > 0.6:
            justificativas.append(f"Média combinada de {media_gols_total:.1f} gols/jogo — alta ofensividade.")
        if comp_xg > 0.6:
            justificativas.append(f"xG total esperado de {xg_total:.1f} — alta probabilidade de gol.")
        if comp_hist > 0.7:
            justificativas.append(f"Histórico de apenas {historico_0x0_medio:.0f} jogos 0x0 em 10 — times tendem a marcar.")
        justificativas.append("Fechar obrigatoriamente ao 1º gol ou aos 65 minutos.")

        return {
            "probabilidade": probabilidade,
            "indice_qualidade": iq,
            "confianca": probabilidade,
            "risco": risco,
            "justificativas": justificativas,
        }

    def _score_lay_goleada(self, d: DadosJogo, lado: str) -> dict:
        pesos = self.pesos["lay_goleada"]

        if lado == "CASA":
            media_gols = d.media_gols_marcados_casa
            xg = d.xg_casa
            odd = d.odd_lay_goleada_casa
            hist_gol = d.historico_goleadas_casa
            dif_elo = d.elo_casa - d.elo_visitante
        else:
            media_gols = d.media_gols_marcados_visitante
            xg = d.xg_visitante
            odd = d.odd_lay_goleada_visitante
            hist_gol = d.historico_goleadas_visitante
            dif_elo = d.elo_visitante - d.elo_casa

        comp_gols = max(0.0, 1.0 - (media_gols / 3.5))
        comp_xg = max(0.0, 1.0 - (xg / 3.0))
        comp_odd = min(1.0, (odd - 1.0) / 5.0)
        comp_hist = max(0.0, 1.0 - (hist_gol / 5.0))
        comp_elo = max(0.0, min(1.0, (dif_elo + 400) / 800))

        score = (
            comp_gols * pesos["media_gols_marcados"] +
            comp_xg * pesos["xg"] +
            comp_odd * pesos["odd_lay"] +
            comp_hist * pesos["historico_goleadas"] +
            comp_elo * pesos["diferenca_elo"]
        )

        time = d.time_casa if lado == "CASA" else d.time_visitante
        probabilidade = round(score * 100, 1)
        iq = self._calcular_iq(score, [comp_gols, comp_xg, comp_odd, comp_hist, comp_elo])
        risco = "BAIXO" if hist_gol <= 1 else ("MEDIO" if hist_gol <= 2 else "ALTO")

        justificativas = []
        if comp_gols > 0.6:
            justificativas.append(f"{time} marca em média {media_gols:.1f} gols/jogo — baixo volume ofensivo.")
        if comp_xg > 0.6:
            justificativas.append(f"xG esperado de {xg:.1f} — chance de goleada reduzida.")
        if comp_odd > 0.4:
            justificativas.append(f"Odd Lay de {odd:.2f} — mercado favorável.")
        if comp_hist > 0.7:
            justificativas.append(f"Apenas {hist_gol} goleada(s) nos últimos 10 jogos.")

        return {
            "probabilidade": probabilidade,
            "indice_qualidade": iq,
            "confianca": probabilidade,
            "risco": risco,
            "justificativas": justificativas,
        }

    def _calcular_iq(self, score: float, componentes: list[float]) -> float:
        base = score * 85
        variancia = sum((c - score) ** 2 for c in componentes) / len(componentes)
        bonus = max(0, 15 * (1 - variancia * 4))
        return round(min(100, base + bonus), 1)


def selecionar_melhores_por_campeonato(
    recomendacoes: list[tuple[DadosJogo, Recomendacao]]
) -> list[Recomendacao]:
    """
    Para cada campeonato, seleciona os 2 melhores jogos com status ENTRAR,
    priorizando Lay 0x0 e depois Lay Goleada, ordenados por índice de qualidade.
    """
    from collections import defaultdict

    por_campeonato = defaultdict(list)
    for dados, rec in recomendacoes:
        if rec.status == "ENTRAR":
            por_campeonato[dados.campeonato].append(rec)

    resultado = []
    for campeonato, recs in por_campeonato.items():
        # Ordena: Lay 0x0 primeiro, depois por índice de qualidade
        ordenados = sorted(
            recs,
            key=lambda r: (0 if r.mercado == "LAY_0X0" else 1, -r.indice_qualidade)
        )
        resultado.extend(ordenados[:MAX_POR_CAMPEONATO])

    # Ordena resultado final por índice de qualidade
    return sorted(resultado, key=lambda r: -r.indice_qualidade)
