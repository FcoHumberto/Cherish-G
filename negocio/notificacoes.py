"""Notificações a vendedores (CMP06). O disparo ocorre via eventos (functions_python.handlers)."""
from acesso_dados import pedidos_repo as repo


def listar(vendedor_id):
    return repo.notificacoes(vendedor_id)


def nao_lidas(usuario):
    return repo.nao_lidas(usuario["id"]) if usuario and usuario["tipo"] == "vendedor" else 0


def marcar_lidas(vendedor_id):
    repo.marcar_lidas(vendedor_id)
