"""
Inicialização e modelos do banco de dados SQLite.
"""

import sqlite3
import os
from pathlib import Path

DB_PATH = os.getenv("DB_PATH", str(Path(__file__).parent.parent.parent / "data" / "lay_goleada.db"))


def get_connection():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    # Tabela de jogos analisados
    cur.execute("""
        CREATE TABLE IF NOT EXISTS jogos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data TEXT NOT NULL,
            campeonato TEXT NOT NULL,
            time_casa TEXT NOT NULL,
            time_visitante TEXT NOT NULL,
            horario TEXT NOT NULL,
            status TEXT DEFAULT 'pendente',  -- pendente | encerrado
            placar_casa INTEGER,
            placar_visitante INTEGER,
            minuto_primeiro_gol INTEGER,
            criado_em TEXT DEFAULT (datetime('now'))
        )
    """)

    # Tabela de recomendações
    cur.execute("""
        CREATE TABLE IF NOT EXISTS recomendacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            jogo_id INTEGER NOT NULL,
            mercado TEXT NOT NULL,          -- LAY_GOLEADA | LAY_0X0
            lado TEXT,                      -- CASA | VISITANTE | NULL (para 0x0)
            probabilidade REAL NOT NULL,
            indice_qualidade REAL NOT NULL,
            confianca REAL NOT NULL,
            risco TEXT NOT NULL,            -- BAIXO | MEDIO | ALTO
            justificativas TEXT NOT NULL,   -- JSON array
            status TEXT DEFAULT 'ENTRAR',   -- ENTRAR | NAO_OPERAR
            resultado TEXT,                 -- GREEN | RED | NULL (pendente)
            criado_em TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (jogo_id) REFERENCES jogos(id)
        )
    """)

    # Tabela de dados coletados por jogo (para aprendizado)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS dados_jogo (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            jogo_id INTEGER NOT NULL,
            media_gols_casa REAL,
            media_gols_visitante REAL,
            media_sofridos_casa REAL,
            media_sofridos_visitante REAL,
            xg_casa REAL,
            xg_visitante REAL,
            odd_lay_goleada_casa REAL,
            odd_lay_goleada_visitante REAL,
            odd_lay_0x0 REAL,
            elo_casa REAL,
            elo_visitante REAL,
            importancia_jogo INTEGER,       -- 1 a 5
            raw_json TEXT,                  -- dados brutos completos
            FOREIGN KEY (jogo_id) REFERENCES jogos(id)
        )
    """)

    # Tabela de histórico de backtests
    cur.execute("""
        CREATE TABLE IF NOT EXISTS backtests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data TEXT NOT NULL,
            total_operacoes INTEGER,
            taxa_acerto REAL,
            roi REAL,
            pesos_json TEXT,
            criado_em TEXT DEFAULT (datetime('now'))
        )
    """)

    conn.commit()
    conn.close()
    print(f"✅ Banco de dados inicializado em: {DB_PATH}")


if __name__ == "__main__":
    init_db()
