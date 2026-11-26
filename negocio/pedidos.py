"""Carrinho, checkout, pagamento, status de entrega e reembolso (CMP05)."""
import json
from datetime import datetime, timedelta
from acesso_dados import pedidos_repo as repo, produtos_repo
from integracoes import stripe_simulado as stripe, eventos
from .contas import ErroNegocio
from .produtos import preco_final

MINUTOS_PIX = 10  # RF21.3


class Proibido(ErroNegocio):
    """Recurso de outro usuário (HTTP 403)."""


class Conflito(ErroNegocio):
    """Operação repetida ou estado incompatível (HTTP 409)."""


def _fmt(dt):
    return dt.strftime("%d/%m/%Y %H:%M")


# --- carrinho ---
def itens_carrinho(uid):
    itens = [dict(i, preco_final=preco_final(i), subtotal=round(preco_final(i) * i["quantidade"], 2)) for i in repo.carrinho(uid)]
    return itens, round(sum(i["subtotal"] for i in itens), 2)


def adicionar(uid, pid, qtd=1):
    p = produtos_repo.por_id(pid)
    if not p or p["status"] != "ativo":
        raise ErroNegocio("Produto não encontrado.")
    if p["vendedor_id"] == uid:
        raise ErroNegocio("Você não pode comprar o seu próprio produto.")
    ja = next((i["quantidade"] for i in repo.carrinho(uid) if i["produto_id"] == pid), 0)
    if qtd < 1 or ja + qtd > p["estoque"]:
        raise Conflito("Quantidade indisponível em estoque.")
    repo.adicionar_ao_carrinho(uid, pid, qtd)


def remover(uid, pid):
    repo.remover_do_carrinho(uid, pid)


def sugestoes_endereco(consulta):
    """RF19: sugestões de bairro/rua enquanto o usuário digita (base ilustrativa)."""
    base = ["Av. Beira Mar, Meireles", "Av. Dom Luís, Aldeota", "Rua Barão de Studart, Aldeota", "Av. Santos Dumont, Aldeota",
            "Rua Silva Jatahy, Meireles", "Av. Washington Soares, Edson Queiroz", "Rua Carolina Sucupira, Centro", "Av. Treze de Maio, Benfica",
            "Rua Tibúrcio Cavalcante, Meireles", "Av. Eng. Santana Júnior, Cocó"]
    q = (consulta or "").lower()
    return [b for b in base if q in b.lower()][:6] if q else base[:6]


# --- pagamento ---
def iniciar_pagamento(uid, endereco, forma, cpf, cartao=None):
    itens, total = itens_carrinho(uid)
    if not itens:
        raise ErroNegocio("Seu carrinho está vazio.")
    if not (endereco or "").strip():
        raise ErroNegocio("Informe o local de entrega.")
    if forma not in ("pix", "cartao"):
        raise ErroNegocio("Escolha a forma de pagamento.")
    for i in itens:
        if i["quantidade"] > i["estoque"]:
            raise Conflito(f"Estoque insuficiente para «{i['nome']}».")
    ref = stripe.nova_referencia()
    resp = stripe.criar_cobranca(forma, total, ref, cpf, cartao)  # CPF/cartão morrem aqui (RNF03)
    if resp["estado"] == "recusado":
        raise ErroNegocio(resp["motivo"])
    snap = [{"produto_id": i["produto_id"], "nome": i["nome"], "preco_unitario": i["preco_final"], "quantidade": i["quantidade"]} for i in itens]
    expira = (datetime.now() + timedelta(minutes=MINUTOS_PIX)).isoformat(timespec="seconds") if forma == "pix" else None
    pgid = repo.criar_pagamento(uid, forma, total, ref, expira, endereco.strip(), snap, resp.get("codigo_pix"))
    if forma == "cartao":
        _registrar(pgid)
    return pgid


def _registrar(pgid):
    """Só pagamento confirmado registra o pedido e baixa o estoque (idempotente)."""
    pg = repo.pagamento(pgid)
    if pg["status"] == "aprovado":
        return pg["pedido_id"]
    if pg["status"] == "expirado":
        raise Conflito("O PIX expirou.")
    previsao = _fmt(datetime.now() + timedelta(days=5))
    pedido_id, erro = repo.registrar_pedido_atomico(pg["comprador_id"], pgid, pg["endereco"], json.loads(pg["itens_json"]), previsao)
    if erro:
        repo.atualizar_pagamento(pgid, status="recusado")
        raise Conflito(erro)
    repo.esvaziar_carrinho(pg["comprador_id"])
    eventos.publicar("pedido_registrado", pedido_id=pedido_id)  # RF13
    return pedido_id


def processar_webhook(referencia, estado, assinatura):
    """Stripe → Sistema: autenticado por assinatura e tolerante a eventos duplicados."""
    if not stripe.verificar_assinatura(referencia, estado, assinatura):
        raise Proibido("Assinatura inválida.")
    pg = repo.pagamento_por_referencia(referencia)
    if not pg:
        raise ErroNegocio("Pagamento desconhecido.")
    if estado == "aprovado":
        _registrar(pg["id"])
    return repo.pagamento(pg["id"])


def estado_pagamento(uid, pgid):
    """Verifica propriedade e aplica expiração por prazo (RF21.3). Retorna a linha atualizada."""
    pg = repo.pagamento(pgid)
    if not pg or pg["comprador_id"] != uid:
        raise Proibido("Pagamento não encontrado.")
    if pg["status"] == "pendente" and pg["expira_em"] and datetime.fromisoformat(pg["expira_em"]) < datetime.now():
        repo.atualizar_pagamento(pgid, status="expirado")
        pg = repo.pagamento(pgid)
    return pg


def qr_do_pagamento(pg):
    return stripe.qr_svg_do_codigo(pg["codigo_pix"])


def concluir_pagamento(uid, pgid):
    """Janela de sucesso fechada: envia recibo e garante carrinho vazio (RF22)."""
    pg = estado_pagamento(uid, pgid)
    if pg["status"] == "aprovado":
        repo.esvaziar_carrinho(uid)
        eventos.publicar("compra_concluida", pagamento_id=pgid)


# --- pedidos ---
def meus_itens(uid):
    return repo.pedidos_do_usuario(uid)


def item_do_usuario(uid, item_id):
    it = repo.item_pedido(item_id)
    if not it:
        raise ErroNegocio("Pedido não encontrado.")
    if it["comprador_id"] != uid:  # RN09
        raise Proibido("Este pedido pertence a outro usuário.")
    return it


def _item_do_vendedor(vendedor, item_id):
    it = repo.item_pedido(item_id)
    p = produtos_repo.por_id(it["produto_id"]) if it else None
    if not p or p["vendedor_id"] != vendedor["id"]:
        raise Proibido("Este pedido não é de um produto seu.")
    return it


def atualizar_localizacao(vendedor, item_id, local):
    it = _item_do_vendedor(vendedor, item_id)
    if local.strip() and it["status"] == "Pendente":
        repo.atualizar_item(item_id, local_atual=local.strip())


def marcar_perdido(vendedor, item_id):
    it = _item_do_vendedor(vendedor, item_id)
    if it["status"] == "Pendente":
        repo.atualizar_item(item_id, status="Perdido")  # RN04


def confirmar_entrega(usuario, item_id, quem):
    """RN05: 'Entregue' só com confirmação do entregador (simulada pelo vendedor) E do cliente."""
    it = _item_do_vendedor(usuario, item_id) if quem == "entregador" else item_do_usuario(usuario["id"], item_id)
    if it["status"] != "Pendente":
        return
    campo = "entregador_ok" if quem == "entregador" else "cliente_ok"
    repo.atualizar_item(item_id, **{campo: 1})
    it = repo.item_pedido(item_id)
    if it["entregador_ok"] and it["cliente_ok"]:
        repo.atualizar_item(item_id, status="Entregue", local_atual="Entregue ao destinatário")


def solicitar_reembolso(uid, item_id):
    """RF25 / RN02: só para 'Perdido' e uma única vez por item."""
    it = item_do_usuario(uid, item_id)
    if it["status"] == "Reembolso solicitado":
        raise Conflito("Reembolso já solicitado.")
    if it["status"] != "Perdido":
        raise Conflito("O reembolso só está disponível para produtos perdidos.")
    if not repo.criar_reembolso(item_id):
        raise Conflito("Reembolso já solicitado.")
    repo.atualizar_item(item_id, status="Reembolso solicitado")
    p = produtos_repo.por_id(it["produto_id"])
    repo.criar_notificacao(p["vendedor_id"], it["pedido_id"], f"Reembolso solicitado: {it['nome_produto']}")
