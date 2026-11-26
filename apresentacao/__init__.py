"""Fábrica da aplicação Flask — camada de Apresentação."""
import os
from flask import Flask, render_template
from acesso_dados import conexao
from negocio.contas import ErroNegocio
from . import contexto


def create_app(banco=None, testando=False):
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    app = Flask(__name__)
    app.config.update(SECRET_KEY=os.environ.get("CHERISH_SECRET", "cherish-dev-chave-troque-em-producao"), TESTING=testando,
                      MAX_CONTENT_LENGTH=12 * 1024 * 1024, SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax",
                      PASTA_UPLOADS=os.path.join(app.static_folder, "uploads"))
    conexao.configurar(banco or os.path.join(raiz, "cherish.db"))
    conexao.aplicar_migracoes()
    app.teardown_appcontext(conexao.fechar_db)
    contexto.registrar(app)

    from .rotas import contas, produtos, pedidos
    for bp in (contas.bp, produtos.bp, pedidos.bp):
        app.register_blueprint(bp)

    @app.template_filter("brl")
    def brl(v):
        return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    @app.errorhandler(403)
    def proibido(_e):
        return render_template("erro.html", titulo="Acesso negado", msg="Você não tem permissão para acessar esta página."), 403

    @app.errorhandler(404)
    def nao_achou(_e):
        return render_template("erro.html", titulo="Não encontrado", msg="Essa página não existe."), 404

    @app.errorhandler(400)
    def invalido(e):
        return render_template("erro.html", titulo="Requisição inválida", msg=getattr(e, "description", "")), 400

    @app.errorhandler(ErroNegocio)
    def erro_negocio(e):
        return render_template("erro.html", titulo="Não foi possível concluir", msg=str(e)), 403 if type(e).__name__ == "Proibido" else 422
    return app
