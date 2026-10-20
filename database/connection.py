# ========================================================
# 🛡️ SENTINEL AI - GERENCIADOR DE CONEXÃO COM POSTGRESQL
# ========================================================

import os
from contextlib import contextmanager
from typing import Generator
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_NAME = os.getenv("POSTGRES_DB", "sentinel_aml")
DB_USER = os.getenv("POSTGRES_USER", "aml_admin")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "aml_secret_password")

def get_connection_url() -> str:
    """Retorna URL padrão SQLAlchemy/PostgreSQL."""
    return f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

@contextmanager
def get_db_connection() -> Generator[psycopg2.extensions.connection, None, None]:
    """Gerenciador de contexto para conexão segura com o PostgreSQL."""
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        cursor_factory=RealDictCursor
    )
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def execute_query(query: str, params: tuple = None) -> list:
    """Executa uma consulta SELECT e retorna lista de dicionários."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            if cur.description:
                return cur.fetchall()
            return []

def execute_statement(statement: str, params: tuple = None) -> None:
    """Executa um comando DDL ou DML (INSERT, UPDATE, DELETE)."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(statement, params)
