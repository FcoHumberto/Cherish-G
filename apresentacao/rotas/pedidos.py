"""Rotas de carrinho, checkout, pagamento e acompanhamento de pedidos (CMP01 ↔ CMP05)."""
from flask import Blueprint, render_template, request, redirect, url_for, flash, g, session, jsonify, abort
from negocio import pedidos, validacoes
from negocio.contas import ErroNegocio
from negocio.pedidos import Proibido, Conflito
from acesso_dados import pedidos_repo, produtos_repo
from integracoes import stripe_simulado as stripe
from ..contexto import login_obrigatorio, vendedor_obrigatorio

bp = Blueprint("pedidos", __name__)


@bp.route("/carrinho")
@login_obrigatorio
def carrinho():  # RF18.1
    itens, total = pedidos.itens_carrinho(g.usuario["id"])
    return render_template("carrinho.html", itens=itens, total=total)


@bp.route("/carrinho/remover/<int:pid>", methods=["POST"])
@login_obrigatorio
def remover(pid):
    pedidos.remover(g.usuario["id"], pid)
    return redirect(url_for("pedidos.carrinho"))


@bp.route("/entrega", methods=["GET", "POST"])
@login_obrigatorio
def entrega():  # RF19
    itens, _ = pedidos.itens_carrinho(g.usuario["id"])
    if not itens:
        return redirect(url_for("pedidos.carrinho"))
    if request.method == "POST":
        end = (request.form.get("endereco") or "").strip()
        if not end:
            flash("Informe ou selecione o local de entrega.", "erro")
        else:
            session["entrega"] = end
            return redirect(url_for("pedidos.recibo"))
    return render_template("entrega.html", salvo=g.usuario["endereco_padrao"])


@bp.route("/api/enderecos")
@login_obrigatorio
def api_enderecos():
    return jsonify(pedidos.sugestoes_endereco(request.args.get("q", "")))


@bp.route("/recibo")
@login_obrigatorio
def recibo():  # RF20
    itens, total = pedidos.itens_carrinho(g.usuario["id"])
    if not itens or not session.get("entrega"):
        return redirect(url_for("pedidos.carrinho"))
    return render_template("recibo.html", itens=itens, total=total, endereco=session["entrega"])


@bp.route("/pagamento", methods=["GET", "POST"])
@login_obrigatorio
def pagamento():  # RF21
    itens, total = pedidos.itens_carrinho(g.usuario["id"])
    if not itens or not session.get("entrega"):
        return redirect(url_for("pedidos.carrinho"))
    if request.method == "POST":
        f = request.form
        try:
            pgid = pedidos.iniciar_pagamento(g.usuario["id"], session["entrega"], f.get("forma"), f.get("cpf"),
                                             {"numero": f.get("cartao_numero", "")})
            return redirect(url_for("pedidos.pix" if f.get("forma") == "pix" else "pedidos.sucesso", pgid=pgid))
        except ErroNegocio as e:  # recusado / estoque: itens permanecem no carrinho (7.7)
            flash(str(e), "erro")
            return render_template("pagamento.html", total=total, f=f), 422
    return render_template("pagamento.html", total=total, f={})


@bp.route("/pagamento/<int:pgid>/pix")
@login_obrigatorio
def pix(pgid):
    pg = pedidos.estado_pagamento(g.usuario["id"], pgid)
    if pg["status"] == "expirado":  # RF21.3
        flash("O tempo do PIX acabou. Seus itens continuam no carrinho.", "aviso")
        return redirect(url_for("pedidos.carrinho"))
    if pg["status"] == "aprovado":
        return redirect(url_for("pedidos.sucesso", pgid=pgid))
    from datetime import datetime
    restante = max(0, int((datetime.fromisoformat(pg["expira_em"]) - datetime.now()).total_seconds()))
    return render_template("pix.html", pg=pg, qr=pedidos.qr_do_pagamento(pg), restante=restante)


@bp.route("/pagamento/<int:pgid>/status")
@login_obrigatorio
def status_pagamento(pgid):
    return jsonify(status=pedidos.estado_pagamento(g.usuario["id"], pgid)["status"])


@bp.route("/pagamento/<int:pgid>/simular", methods=["POST"])
@login_obrigatorio
def simular_pix(pgid):
    """Demonstração: faz o papel do banco/Stripe chamando o webhook assinado."""
    pg = pedidos.estado_pagamento(g.usuario["id"], pgid)
    try:
        pedidos.processar_webhook(pg["referencia_stripe"], "aprovado", stripe.assinar_evento(pg["referencia_stripe"], "aprovado"))
    except ErroNegocio as e:
        flash(str(e), "erro")
    return redirect(url_for("pedidos.pix", pgid=pgid))


@bp.route("/pagamento/<int:pgid>/sucesso")
@login_obrigatorio
def sucesso(pgid):
    pg = pedidos.estado_pagamento(g.usuario["id"], pgid)
    if pg["status"] != "aprovado":
        return redirect(url_for("pedidos.carrinho"))
    return render_template("sucesso.html", pg=pg)


@bp.route("/pagamento/<int:pgid>/concluir", methods=["POST"])
@login_obrigatorio
def concluir(pgid):  # RF22
    pedidos.concluir_pagamento(g.usuario["id"], pgid)
    return redirect(url_for("pedidos.meus_pedidos"))


@bp.route("/api/v1/pagamentos/webhook", methods=["POST"])
def webhook():
    d = request.get_json(silent=True) or {}
    try:
        pg = pedidos.processar_webhook(d.get("referencia"), d.get("estado"), request.headers.get("X-Assinatura"))
        return jsonify(status=pg["status"]), 200
    except Proibido:
        return jsonify(erro="assinatura inválida"), 401
    except ErroNegocio as e:
        return jsonify(erro=str(e)), 400


# --- pedidos ---
@bp.route("/meus-pedidos")
@login_obrigatorio
def meus_pedidos():  # RF23
    return render_template("meus_pedidos.html", itens=pedidos.meus_itens(g.usuario["id"]))


@bp.route("/pedido/<int:item_id>")
@login_obrigatorio
def detalhes(item_id):  # RF24
    return render_template("pedido_detalhes.html", it=pedidos.item_do_usuario(g.usuario["id"], item_id))


@bp.route("/pedido/<int:item_id>/reembolso", methods=["POST"])
@login_obrigatorio
def reembolso(item_id):  # RF25
    try:
        pedidos.solicitar_reembolso(g.usuario["id"], item_id)
        flash("Reembolso solicitado à loja.", "ok")
    except Conflito as e:
        flash(str(e), "aviso")
    return redirect(url_for("pedidos.detalhes", item_id=item_id))


@bp.route("/api/v1/pedidos/<int:item_id>/reembolso", methods=["POST"])
def api_reembolso(item_id):  # 7.4
    if not g.usuario:
        return jsonify(erro="não autenticado"), 401
    try:
        pedidos.solicitar_reembolso(g.usuario["id"], item_id)
        return jsonify(pedidoId=item_id, status="Reembolso solicitado"), 200
    except Proibido:
        return jsonify(erro="pedido de outro usuário"), 403
    except Conflito as e:
        return jsonify(erro=str(e)), 409
    except ErroNegocio:
        return jsonify(erro="pedido inexistente"), 404


@bp.route("/pedido/<int:item_id>/recebido", methods=["POST"])
@login_obrigatorio
def recebido(item_id):
    pedidos.confirmar_entrega(g.usuario, item_id, "cliente")
    flash("Recebimento confirmado.", "ok")
    return redirect(url_for("pedidos.detalhes", item_id=item_id))


@bp.route("/pedido/<int:item_id>/vendedor", methods=["POST"])
@vendedor_obrigatorio
def acao_vendedor(item_id):
    """Simulação da logística: o vendedor atualiza localização, marca como perdido ou registra a confirmação do entregador."""
    acao = request.form.get("acao")
    if acao == "localizacao":
        pedidos.atualizar_localizacao(g.usuario, item_id, request.form.get("local", ""))
    elif acao == "perdido":
        pedidos.marcar_perdido(g.usuario, item_id)
    elif acao == "entregador":
        pedidos.confirmar_entrega(g.usuario, item_id, "entregador")
    it = pedidos_repo.item_pedido(item_id)
    return redirect(url_for("produtos.editar_produto", pid=it["produto_id"]))
