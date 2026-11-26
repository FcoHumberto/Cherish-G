"""Utilitários da camada de Apresentação: sessão, permissões, navegação (RF33) e contexto dos templates."""
from functools import wraps
from flask import g, session, request, redirect, url_for, flash, abort
from negocio import contas, notificacoes, validacoes
from acesso_dados import pedidos_repo

PRINCIPAIS = {"produtos.listar", "pedidos.meus_pedidos", "produtos.acessados", "contas.perfil", "produtos.meus_produtos"}
SEM_HISTORICO = {"static", "voltar", "produtos.imagem", "pedidos.api_enderecos", "pedidos.status_pagamento",
                 "produtos.api_listar", "produtos.api_detalhe", "pedidos.webhook", "pedidos.api_reembolso"}


def registrar(app):
    @app.before_request
    def carregar_usuario():
        g.usuario = contas.usuario_da_sessao(session.get("token"))
        if session.get("token") and not g.usuario:  # sessão expirada / conta excluída
            session.clear()
        g.prefs = contas.preferencias(g.usuario["id"]) if g.usuario else dict(contas.repo.PREFERENCIAS_PADRAO)

    @app.before_request
    def pilha_de_navegacao():
        """Pilha de páginas: 'Voltar' desempilha a página atual, então nunca cria loop A↔B."""
        if request.method != "GET" or request.endpoint in SEM_HISTORICO or request.endpoint is None:
            return
        url, pilha = request.full_path.rstrip("?"), session.get("pilha", [])
        if request.endpoint in PRINCIPAIS:
            pilha = [url]
        elif not pilha or pilha[-1] != url:
            pilha.append(url)
        session["pilha"] = pilha[-15:]

    @app.route("/voltar")
    def voltar():
        pilha = session.get("pilha", [])
        if pilha:
            pilha.pop()
        session["pilha"] = pilha
        return redirect(pilha[-1] if pilha else url_for("produtos.listar"))

    @app.context_processor
    def injetar():
        prefs, cores = g.prefs, g.prefs["cores_botoes"]
        qtd = pedidos_repo.quantidade_carrinho(g.usuario["id"]) if g.usuario else 0  # RF18/RF34
        return dict(usuario=g.usuario, prefs=prefs, cores=cores, qtd_carrinho=qtd,
                    txt_avancar=validacoes.cor_texto_para(cores["avancar"]), txt_voltar=validacoes.cor_texto_para(cores["voltar"]),
                    fonte_px=contas.TAMANHOS_FONTE.get(prefs["tamanho_fonte"], 16), notif=notificacoes.nao_lidas(g.usuario))


def login_obrigatorio(f):
    @wraps(f)
    def interno(*a, **k):
        if not g.usuario:  # RF38
            flash("Entre na sua conta para continuar.", "aviso")
            return redirect(url_for("contas.login"))
        return f(*a, **k)
    return interno


def vendedor_obrigatorio(f):
    @wraps(f)
    @login_obrigatorio
    def interno(*a, **k):
        if g.usuario["tipo"] != "vendedor":  # RF09 / CT04
            abort(403)
        return f(*a, **k)
    return interno


def exigir_confirmacao():
    """RF07 / RN03: alterações só são aplicadas com a confirmação explícita do usuário."""
    if request.form.get("confirmado") != "sim":
        abort(400, "Confirmação necessária.")
