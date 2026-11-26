"""Recomendações por histórico e acessados recentemente (CMP04, RF16/RF26)."""
from acesso_dados import produtos_repo, pedidos_repo
from . import contas


def registrar_acesso(uid, pid):
    produtos_repo.registrar_acesso(uid, pid)


def acessados(uid):
    return produtos_repo.acessos(uid)


def recomendados(uid, limite=4):
    if not contas.preferencias(uid)["recomendacoes_historico"]:
        return []
    base = {i["produto_id"] for i in pedidos_repo.pedidos_do_usuario(uid)} | {p["id"] for p in produtos_repo.acessos(uid)}
    cats, vendedores = set(), set()
    for pid in base:
        p = produtos_repo.por_id(pid)
        if p:
            cats.add(p["categoria"]); vendedores.add(p["vendedor_id"])
    return produtos_repo.semelhantes(uid, list(cats), list(vendedores), list(base), limite)
