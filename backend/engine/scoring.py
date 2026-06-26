"""
Motor de scoring principal.
Calcula score e índice de qualidade para Lay Goleada e Lay 0x0.
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Pesos padrão (recalibrados pelo backtest)
WEIGHTS_PATH = Path(__file__).parent.parent / "ml" / "weights.json"


def _carregar_pesos() -> dict:
    try:
        with open(WEIGHTS_PATH) as f:
            return json.load(f)
    except FileNotFoundError:
        return _pesos_padrao()


def _pesos_padrao() -> dict:
    return {
        "lay_goleada": {
            "media_gols_marcados": 0.30,
            "xg": 0.25,
            "odd_lay": 0.20,
            "historico_goleadas": 0.15,
            "diferenca_elo": 0.10,
        },
        "lay_0x0": {
            "media_gols_primeiro_tempo": 0.35,
            "xg_total": 0.30,
            "odd_lay_0x0": 0.25,
            "historico_0x0": 0.10,
        }
    }


@dataclass
class DadosJogo:
    # Identificação
    fixture_id: int
    campeonato: str
    time_casa: str
    time_visitante: str
    horario: str

    # Estatísticas
    media_gols_marcados_casa: float = 1.2
    media_gols_sofridos_casa: float = 1.0
    media_gols_marcados_visitante: float = 0.9
    media_gols_sofridos_visitante: float = 1.3
    xg_casa: float = 1.2
    xg_visitante: float = 0.9
    historico_goleadas_casa: int = 1     # últimos 10 jogos
    historico_goleadas_visitante: int = 1
    elo_casa: float = 1600.0
    elo_visitante: float = 1550.0

    # Odds
    odd_lay_goleada_casa: float = 2.0
    odd_lay_goleada_visitante: float = 3.0
    odd_lay_0x0: float = 1.5


@dataclass
class Recomendacao:
    mercado: str                    # LAY_GOLEADA | LAY_0X0 | NAO_OPERAR
    lado: Optional[str]             # CASA | VISITANTE | None
    probabilidade: float
    indice_qualidade: float
    confianca: float
    risco: str                      # BAIXO | MEDIO | ALTO
    justificativas: list[str]
    status: str                     # ENTRAR | NAO_OPERAR
    dados: DadosJogo = field(repr=False)


class MotorScoring:

    def __init__(self):
        self.pesos = _carregar_pesos()

    def analisar(self, dados: DadosJogo) -> Recomendacao:
        """Analisa um jogo e retorna a melhor recomendação."""

        score_lg_casa = self._score_lay_goleada(dados, lado="CASA")
        score_lg_visitante = self._score_lay_goleada(dados, lado="VISITANTE")
        score_0x0 = self._score_lay_0x0(dados)

        melhor = max(
            [
                ("LAY_GOLEADA", "CASA", score_lg_casa),
                ("LAY_GOLEADA", "VISITANTE", score_lg_visitante),
                ("LAY_0X0", None, score_0x0),
            ],
            key=lambda x: x[2]["indice_qualidade"]
        )

        mercado, lado, score = melhor

        if score["indice_qualidade"] < 80:
            return Recomendacao(
                mercado="NAO_OPERAR",
                lado=None,
                probabilidade=score["probabilidade"],
                indice_qualidade=score["indice_qualidade"],
                confianca=score["confianca"],
                risco="ALTO",
                justificativas=[
                    f"Índice de qualidade abaixo do mínimo: {score['indice_qualidade']:.1f}/100",
                    "Nenhum mercado atingiu critérios mínimos de confiança."
                ],
                status="NAO_OPERAR",
                dados=dados
            )

        return Recomendacao(
            mercado=mercado,
            lado=lado,
            probabilidade=score["probabilidade"],
            indice_qualidade=score["indice_qualidade"],
            confianca=score["confianca"],
            risco=score["risco"],
            justificativas=score["justificativas"],
            status="ENTRAR",
            dados=dados
        )

    def _score_lay_goleada(self, d: DadosJogo, lado: str) -> dict:
        pesos = self.pesos["lay_goleada"]

        if lado == "CASA":
            media_gols = d.media_gols_marcados_casa
            xg = d.xg_casa
            odd = d.odd_lay_goleada_casa
            historico_goleadas = d.historico_goleadas_casa
            diferenca_elo = d.elo_casa - d.elo_visitante
        else:
            media_gols = d.media_gols_marcados_visitante
            xg = d.xg_visitante
            odd = d.odd_lay_goleada_visitante
            historico_goleadas = d.historico_goleadas_visitante
            diferenca_elo = d.elo_visitante - d.elo_casa

        # Normalizar componentes (0-1)
        comp_gols = max(0, 1 - (media_gols / 3.5))
        comp_xg = max(0, 1 - (xg / 3.0))
        comp_odd = min(1, (odd - 1.0) / 4.0)  # odds altas = time mais fraco = mais seguro
        comp_historico = max(0, 1 - (historico_goleadas / 5))
        comp_elo = max(0, min(1, (diferenca_elo + 400) / 800))  # diferença ELO normalizada

        score_bruto = (
            comp_gols * pesos["media_gols_marcados"] +
            comp_xg * pesos["xg"] +
            comp_odd * pesos["odd_lay"] +
            comp_historico * pesos["historico_goleadas"] +
            comp_elo * pesos["diferenca_elo"]
        )

        probabilidade = round(score_bruto * 100, 1)
        indice_qualidade = self._calcular_indice_qualidade(
            score_bruto,
            componentes=[comp_gols, comp_xg, comp_odd, comp_historico, comp_elo]
        )
        risco = self._calcular_risco(odd, historico_goleadas)

        justificativas = self._justificativas_lay_goleada(
            d, lado, comp_gols, comp_xg, comp_odd, comp_historico
        )

        return {
            "probabilidade": probabilidade,
            "indice_qualidade": indice_qualidade,
            "confianca": round(score_bruto * 100, 1),
            "risco": risco,
            "justificativas": justificativas,
        }

    def _score_lay_0x0(self, d: DadosJogo) -> dict:
        pesos = self.pesos["lay_0x0"]

        xg_total = d.xg_casa + d.xg_visitante
        media_gols_total = d.media_gols_marcados_casa + d.media_gols_marcados_visitante

        comp_gols_pt = min(1, media_gols_total / 4.0)
        comp_xg = min(1, xg_total / 4.0)
        comp_odd = max(0, 1 - (d.odd_lay_0x0 - 1.0) / 3.0)
        comp_historico = 0.7  # placeholder — calcular com histórico real

        score_bruto = (
            comp_gols_pt * pesos["media_gols_primeiro_tempo"] +
            comp_xg * pesos["xg_total"] +
            comp_odd * pesos["odd_lay_0x0"] +
            comp_historico * pesos["historico_0x0"]
        )

        probabilidade = round(score_bruto * 100, 1)
        indice_qualidade = self._calcular_indice_qualidade(
            score_bruto,
            componentes=[comp_gols_pt, comp_xg, comp_odd, comp_historico]
        )
        risco = self._calcular_risco(d.odd_lay_0x0, 0)

        justificativas = self._justificativas_lay_0x0(
            d, xg_total, comp_gols_pt, comp_xg
        )

        return {
            "probabilidade": probabilidade,
            "indice_qualidade": indice_qualidade,
            "confianca": round(score_bruto * 100, 1),
            "risco": risco,
            "justificativas": justificativas,
        }

    def _calcular_indice_qualidade(self, score: float, componentes: list[float]) -> float:
        """
        Índice de qualidade 0-100.
        Penaliza se componentes divergem muito entre si (baixa consistência).
        """
        base = score * 85  # base até 85 pontos
        variancia = sum((c - score) ** 2 for c in componentes) / len(componentes)
        bonus_consistencia = max(0, 15 * (1 - variancia * 4))
        return round(min(100, base + bonus_consistencia), 1)

    def _calcular_risco(self, odd: float, historico_ruins: int) -> str:
        if odd < 2.0 and historico_ruins <= 1:
            return "BAIXO"
        elif odd < 3.5 and historico_ruins <= 2:
            return "MEDIO"
        return "ALTO"

    def _justificativas_lay_goleada(
        self, d: DadosJogo, lado: str,
        comp_gols, comp_xg, comp_odd, comp_historico
    ) -> list[str]:
        time = d.time_casa if lado == "CASA" else d.time_visitante
        media = d.media_gols_marcados_casa if lado == "CASA" else d.media_gols_marcados_visitante
        xg = d.xg_casa if lado == "CASA" else d.xg_visitante
        hist = d.historico_goleadas_casa if lado == "CASA" else d.historico_goleadas_visitante
        odd = d.odd_lay_goleada_casa if lado == "CASA" else d.odd_lay_goleada_visitante

        motivos = []
        if comp_gols > 0.6:
            motivos.append(f"{time} marca em média {media:.1f} gols/jogo — baixo volume ofensivo.")
        if comp_xg > 0.6:
            motivos.append(f"xG esperado de {xg:.1f} — chance de goleada reduzida.")
        if comp_odd > 0.5:
            motivos.append(f"Odd Lay de {odd:.2f} indica mercado favorável à operação.")
        if comp_historico > 0.7:
            motivos.append(f"Apenas {hist} goleadas nos últimos 10 jogos — bom histórico.")

        return motivos or ["Score calculado com base nos indicadores disponíveis."]

    def _justificativas_lay_0x0(
        self, d: DadosJogo, xg_total: float, comp_gols, comp_xg
    ) -> list[str]:
        motivos = []
        media_total = d.media_gols_marcados_casa + d.media_gols_marcados_visitante

        if comp_gols > 0.5:
            motivos.append(f"Média combinada de {media_total:.1f} gols/jogo — partida tende a ter gols.")
        if comp_xg > 0.5:
            motivos.append(f"xG total esperado de {xg_total:.1f} — alta probabilidade de sair do 0x0.")
        motivos.append("Estratégia: fechar ao primeiro gol ou obrigatoriamente aos 65 minutos.")

        return motivos
