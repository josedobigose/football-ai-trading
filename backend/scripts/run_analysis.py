import json
import logging
import os
from datetime import date, datetime
from pathlib import Path

from collectors.data_collector import buscar_jogos_do_dia, buscar_odds, buscar_estatisticas
from engine.scoring import MotorScoring, DadosJogo, CAMPEONATOS
from db.init_db import get_connection, init_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

OUTPUT_DIR = Path(__file__).parent.parent.parent / "data"
MAX_POR_CAMPEONATO = 2


def run():
    logger.info("🚀 Iniciando análise diária...")
    init_db()

    todos_jogos = buscar_jogos_do_dia()
    logger.info(f"📋 Total de jogos recebidos: {len(todos_jogos)}")

    motor = MotorScoring()
    conn = get_connection()

    # Agrupa por campeonato
    por_campeonato = {}
    for jogo in todos_jogos:
        liga_id = jogo.get("liga_id")
        if liga_id not in CAMPEONATOS:
            continue
        camp = jogo["campeonato"]
        if camp not in por_campeonato:
            por_campeonato[camp] = []
        por_campeonato[camp].append(jogo)

    logger.info(f"📊 Campeonatos com jogos hoje: {list(por_campeonato.keys())}")

    recomendacoes_saida = []
    cur = conn.cursor()

    for campeonato, jogos in por_campeonato.items():
        candidatos = []

        for jogo in jogos:
            try:
                odds = buscar_odds(jogo["time_casa"], jogo["time_visitante"], jogo.get("liga_id", 39))
                stats = buscar_estatisticas(jogo.get("fixture_id", 0), jogo.get("liga_id", 39))

                dados = DadosJogo(
                    fixture_id=jogo.get("fixture_id", 0),
                    campeonato=jogo["campeonato"],
                    liga_id=jogo.get("liga_id", 39),
                    time_casa=jogo["time_casa"],
                    time_visitante=jogo["time_visitante"],
                    horario=jogo["horario"],
                    media_gols_marcados_casa=stats.get("media_gols_marcados_casa", 1.8),
                    media_gols_sofridos_casa=stats.get("media_gols_sofridos_casa", 1.2),
                    media_gols_marcados_visitante=stats.get("media_gols_marcados_visitante", 1.5),
                    media_gols_sofridos_visitante=stats.get("media_gols_sofridos_visitante", 1.4),
                    xg_casa=stats.get("xg_casa", 1.6),
                    xg_visitante=stats.get("xg_visitante", 1.3),
                    historico_goleadas_casa=stats.get("historico_goleadas_casa", 1),
                    historico_goleadas_visitante=stats.get("historico_goleadas_visitante", 1),
                    historico_0x0_casa=stats.get("historico_0x0_casa", 1),
                    historico_0x0_visitante=stats.get("historico_0x0_visitante", 1),
                    elo_casa=stats.get("elo_casa", 1650.0),
                    elo_visitante=stats.get("elo_visitante", 1600.0),
                    odd_lay_goleada_casa=odds.get("odd_lay_goleada_casa", 3.5),
                    odd_lay_goleada_visitante=odds.get("odd_lay_goleada_visitante", 5.0),
                    odd_lay_0x0=odds.get("odd_lay_0x0", 2.5),
                )

                rec = motor.analisar(dados)
                candidatos.append((dados, rec))
                logger.info(f"  {jogo['time_casa']} x {jogo['time_visitante']} → {rec.mercado} IQ:{rec.indice_qualidade} status:{rec.status}")

            except Exception as e:
                logger.error(f"Erro: {e}")

        # Pega os 2 melhores do campeonato — prioriza ENTRAR, depois maior IQ
        candidatos.sort(key=lambda x: (0 if x[1].status == "ENTRAR" else 1, -x[1].indice_qualidade))
        melhores = [r for _, r in candidatos[:MAX_POR_CAMPEONATO] if r.status == "ENTRAR"]

        for rec in melhores:
            d = rec.dados
            cur.execute("""
                INSERT INTO jogos (data, campeonato, time_casa, time_visitante, horario)
                VALUES (?, ?, ?, ?, ?)
            """, (date.today().isoformat(), d.campeonato, d.time_casa, d.time_visitante, d.horario))
            jogo_id = cur.lastrowid

            cur.execute("""
                INSERT INTO recomendacoes
                (jogo_id, mercado, lado, probabilidade, indice_qualidade, confianca, risco, justificativas, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                jogo_id, rec.mercado, rec.lado, rec.probabilidade,
                rec.indice_qualidade, rec.confianca, rec.risco,
                json.dumps(rec.justificativas, ensure_ascii=False), rec.status
            ))

            recomendacoes_saida.append({
                "jogo": f"{d.time_casa} x {d.time_visitante}",
                "campeonato": d.campeonato,
                "horario": d.horario,
                "mercado": rec.mercado,
                "lado": rec.lado,
                "probabilidade": rec.probabilidade,
                "indice_qualidade": rec.indice_qualidade,
                "confianca": rec.confianca,
                "risco": rec.risco,
                "justificativas": rec.justificativas,
                "status": rec.status,
            })

    conn.commit()
    conn.close()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    hoje = date.today().strftime("%Y-%m-%d")
    output_path = OUTPUT_DIR / f"recomendacoes_{hoje}.json"

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({
            "data": hoje,
            "gerado_em": datetime.now().isoformat(),
            "total": len(recomendacoes_saida),
            "entrar": len(recomendacoes_saida),
            "campeonatos_monitorados": list(CAMPEONATOS.values()),
            "recomendacoes": recomendacoes_saida,
        }, f, ensure_ascii=False, indent=2)

    logger.info(f"✅ {len(recomendacoes_saida)} recomendações salvas!")


if __name__ == "__main__":
    run()
