"""
Script principal de análise diária.
Executado pelo GitHub Actions todo dia às 8h.
"""

import json
import logging
import os
from datetime import date, datetime
from pathlib import Path

from collectors.data_collector import (
    buscar_jogos_do_dia,
    buscar_odds,
    buscar_estatisticas,
)
from engine.scoring import MotorScoring, DadosJogo
from db.init_db import get_connection, init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

OUTPUT_DIR = Path(__file__).parent.parent.parent / "data"


def run():
    logger.info("🚀 Iniciando análise diária...")
    init_db()

    jogos = buscar_jogos_do_dia()
    motor = MotorScoring()
    conn = get_connection()
    recomendacoes_saida = []

    for jogo in jogos:
        try:
            # Buscar odds
            odds = buscar_odds(
                jogo["time_casa"],
                jogo["time_visitante"],
                jogo.get("liga_id", 39)
            )

            # Buscar estatísticas
            stats = buscar_estatisticas(
                jogo.get("fixture_id", 0),
                jogo.get("liga_id", 39)
            )

            # Montar objeto de dados
            dados = DadosJogo(
                fixture_id=jogo.get("fixture_id", 0),
                campeonato=jogo["campeonato"],
                time_casa=jogo["time_casa"],
                time_visitante=jogo["time_visitante"],
                horario=jogo["horario"],
                media_gols_marcados_casa=stats.get("media_gols_marcados_casa", 1.2),
                media_gols_sofridos_casa=stats.get("media_gols_sofridos_casa", 1.0),
                media_gols_marcados_visitante=stats.get("media_gols_marcados_visitante", 0.9),
                media_gols_sofridos_visitante=stats.get("media_gols_sofridos_visitante", 1.3),
                xg_casa=stats.get("xg_casa", 1.2),
                xg_visitante=stats.get("xg_visitante", 0.9),
                historico_goleadas_casa=stats.get("historico_goleadas_casa", 1),
                historico_goleadas_visitante=stats.get("historico_goleadas_visitante", 1),
                elo_casa=stats.get("elo_casa", 1600.0),
                elo_visitante=stats.get("elo_visitante", 1550.0),
                odd_lay_goleada_casa=odds.get("odd_lay_goleada_casa", 2.0),
                odd_lay_goleada_visitante=odds.get("odd_lay_goleada_visitante", 3.0),
                odd_lay_0x0=odds.get("odd_lay_0x0", 1.5),
            )

            # Analisar
            rec = motor.analisar(dados)

            # Salvar no banco
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO jogos (data, campeonato, time_casa, time_visitante, horario)
                VALUES (?, ?, ?, ?, ?)
            """, (
                date.today().isoformat(),
                jogo["campeonato"],
                jogo["time_casa"],
                jogo["time_visitante"],
                jogo["horario"],
            ))
            jogo_id = cur.lastrowid

            cur.execute("""
                INSERT INTO recomendacoes
                (jogo_id, mercado, lado, probabilidade, indice_qualidade,
                 confianca, risco, justificativas, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                jogo_id,
                rec.mercado,
                rec.lado,
                rec.probabilidade,
                rec.indice_qualidade,
                rec.confianca,
                rec.risco,
                json.dumps(rec.justificativas, ensure_ascii=False),
                rec.status,
            ))
            conn.commit()

            # Montar JSON de saída
            recomendacoes_saida.append({
                "jogo": f"{jogo['time_casa']} x {jogo['time_visitante']}",
                "campeonato": jogo["campeonato"],
                "horario": jogo["horario"],
                "mercado": rec.mercado,
                "lado": rec.lado,
                "probabilidade": rec.probabilidade,
                "indice_qualidade": rec.indice_qualidade,
                "confianca": rec.confianca,
                "risco": rec.risco,
                "justificativas": rec.justificativas,
                "status": rec.status,
            })

            status_emoji = "✅" if rec.status == "ENTRAR" else "⏭️"
            logger.info(
                f"{status_emoji} {jogo['time_casa']} x {jogo['time_visitante']} "
                f"→ {rec.mercado} {rec.lado or ''} | IQ: {rec.indice_qualidade}"
            )

        except Exception as e:
            logger.error(f"Erro ao analisar {jogo.get('time_casa')} x {jogo.get('time_visitante')}: {e}")

    conn.close()

    # Salvar JSON para o frontend
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    hoje = date.today().strftime("%Y-%m-%d")
    output_path = OUTPUT_DIR / f"recomendacoes_{hoje}.json"

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({
            "data": hoje,
            "gerado_em": datetime.now().isoformat(),
            "total": len(recomendacoes_saida),
            "entrar": sum(1 for r in recomendacoes_saida if r["status"] == "ENTRAR"),
            "recomendacoes": recomendacoes_saida,
        }, f, ensure_ascii=False, indent=2)

    logger.info(f"✅ Análise concluída. {len(recomendacoes_saida)} jogos processados.")
    logger.info(f"📄 Resultado salvo em: {output_path}")


if __name__ == "__main__":
    run()
