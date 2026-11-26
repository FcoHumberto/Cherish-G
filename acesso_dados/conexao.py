"""Conexão SQLite e aplicação de migrações versionadas (camada Acesso a Dados)."""
import os
import sqlite3
import threading
from flask import g, has_app_context

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAMINHO_PADRAO = os.path.join(RAIZ, "cherish.db")
_caminho = CAMINHO_PADRAO
_local = threading.local()


def configurar(caminho):
    global _caminho
    _caminho = caminho


def nova_conexao():
    con = sqlite3.connect(_caminho, timeout=15)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def get_db():
    """Conexão por requisição (ou avulsa fora de contexto Flask, ex.: funções por evento)."""
    if has_app_context():
        if "db" not in g:
            g.db = nova_conexao()
        return g.db
    # fora do Flask (threads de eventos / scripts): uma conexão por thread
    if not hasattr(_local, "con"):
        _local.con = nova_conexao()
    return _local.con


def fechar_db_da_thread():
    con = getattr(_local, "con", None)
    if con is not None:
        con.close()
        del _local.con


def fechar_db(_exc=None):
    con = g.pop("db", None)
    if con is not None:
        con.close()


def aplicar_migracoes():
    con = nova_conexao()
    con.execute("CREATE TABLE IF NOT EXISTS _migracoes (arquivo TEXT PRIMARY KEY)")
    pasta = os.path.join(RAIZ, "migrations")
    for arq in sorted(os.listdir(pasta)):
        if arq.endswith(".sql") and not con.execute("SELECT 1 FROM _migracoes WHERE arquivo=?", (arq,)).fetchone():
            with open(os.path.join(pasta, arq), encoding="utf-8") as f:
                con.executescript(f.read())
            con.execute("INSERT INTO _migracoes VALUES (?)", (arq,))
            con.commit()
    con.close()
