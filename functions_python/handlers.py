"""Funções orientadas a eventos (CMP08) — equivalentes locais das Azure Functions em Python."""
import json
from datetime import datetime
from acesso_dados import pedidos_repo, usuarios_repo
from acesso_dados.conexao import get_db
from integracoes import postmark_simulado as postmark


def notificar_vendedores(pedido_id: int):
    """RF13: avisa cada vendedor envolvido no pedido."""
    por_vendedor = {}
    for it in pedidos_repo.itens_do_pedido(pedido_id):
        por_vendedor.setdefault(it["vendedor_id"], []).append(f'{it["quantidade"]}x {it["nome_produto"]}')
    for vendedor_id, itens in por_vendedor.items():
        pedidos_repo.criar_notificacao(vendedor_id, pedido_id, "Novo pedido: " + ", ".join(itens))


def enviar_recibo(pagamento_id: int):
    """RF22: e-mail com o recibo da compra (uma única vez)."""
    pg = pedidos_repo.pagamento(pagamento_id)
    if not pg or pg["status"] != "aprovado" or pg["recibo_enviado"]:
        return
    usuario = usuarios_repo.por_id(pg["comprador_id"])
    linhas = [f'- {i["quantidade"]}x {i["nome_produto"]}: R$ {i["preco_unitario"] * i["quantidade"]:.2f}'
              for i in pedidos_repo.itens_do_pedido(pg["pedido_id"])]
    corpo = (f'Olá, {usuario["nome"]}! Obrigado por comprar na Cherish.\n\nPedido #{pg["pedido_id"]}\n' + "\n".join(linhas) +
             f'\n\nTotal: R$ {pg["valor"]:.2f}\nEntrega em: {pg["endereco"]}')
    postmark.enviar(usuario["email"], f'Recibo do pedido #{pg["pedido_id"]}', corpo)
    pedidos_repo.atualizar_pagamento(pagamento_id, recibo_enviado=1)


def expirar_pix():
    """RF21.3: PIX não pago em 10 minutos expira; os itens continuam no carrinho. Rodar periodicamente."""
    agora = datetime.now().isoformat(timespec="seconds")
    expirados = pedidos_repo.pix_expirados(agora)
    for pg in expirados:
        pedidos_repo.atualizar_pagamento(pg["id"], status="expirado")
    return len(expirados)
