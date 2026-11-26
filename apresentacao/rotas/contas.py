"""Rotas de contas, perfil, configurações e caixa de saída (CMP01 ↔ CMP02)."""
import os
import uuid
from flask import abort, Blueprint, render_template, request, redirect, url_for, flash, session, g, current_app
from werkzeug.utils import secure_filename
from negocio import contas, notificacoes
from negocio.contas import ErroNegocio
from negocio import validacoes
from acesso_dados import pedidos_repo, usuarios_repo
from ..contexto import login_obrigatorio, exigir_confirmacao

bp = Blueprint("contas", __name__)
EXT = {"png", "jpg", "jpeg", "webp", "gif"}


def salvar_upload(arquivo):
    if not arquivo or not arquivo.filename:
        return None
    ext = arquivo.filename.rsplit(".", 1)[-1].lower()
    if ext not in EXT:
        raise ErroNegocio("Formato de imagem não suportado (use PNG, JPG, WEBP ou GIF).")
    nome = f"{uuid.uuid4().hex[:12]}_{secure_filename(arquivo.filename)}"
    arquivo.save(os.path.join(current_app.config["PASTA_UPLOADS"], nome))
    return nome


def _abrir_sessao(uid):
    session["token"] = contas.emitir_sessao(uid)
    session["pilha"] = []
    if not contas.preferencias(uid)["dois_fatores"]:  # RF04
        flash("Dica de segurança: ative a autenticação de dois fatores em Perfil → Configurações.", "aviso")


@bp.route("/cadastro", methods=["GET", "POST"])
def cadastro():
    if request.method == "POST":
        f = request.form
        try:
            contas.cadastrar(f.get("nome"), f.get("email"), f.get("telefone"), f.get("tipo"), f.get("senha"), f.get("endereco", ""))
        except ErroNegocio as e:
            flash(str(e), "erro")
            return render_template("cadastro.html", f=f), 422
        flash("Conta criada! Entre para continuar.", "ok")
        return redirect(url_for("contas.login"))  # RF01.2
    return render_template("cadastro.html", f={})


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        try:
            u = contas.autenticar(request.form.get("email"), request.form.get("senha"))
        except ErroNegocio as e:
            flash(str(e), "erro")
            return render_template("login.html"), 401
        if contas.preferencias(u["id"])["dois_fatores"]:
            session["pendente_2fa"] = {"uid": u["id"], "codigo": contas.emitir_codigo_2fa(u)}
            flash("Enviamos um código de 6 dígitos ao seu e-mail (veja a Caixa de saída de demonstração).", "ok")
            return redirect(url_for("contas.dois_fatores"))
        _abrir_sessao(u["id"])
        return redirect(url_for("produtos.listar"))
    return render_template("login.html")


@bp.route("/2fa", methods=["GET", "POST"])
def dois_fatores():
    pend = session.get("pendente_2fa")
    if not pend:
        return redirect(url_for("contas.login"))
    if request.method == "POST":
        if request.form.get("codigo", "").strip() == pend["codigo"]:
            session.pop("pendente_2fa")
            _abrir_sessao(pend["uid"])
            return redirect(url_for("produtos.listar"))
        flash("Código incorreto.", "erro")
    return render_template("dois_fatores.html", email=usuarios_repo.por_id(pend["uid"])["email"])


@bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("produtos.listar"))


@bp.route("/esqueci-senha", methods=["GET", "POST"])
def esqueci_senha():
    if request.method == "POST":
        contas.solicitar_redefinicao(request.form.get("email"), request.host_url + "redefinir/")
        flash("Se o e-mail estiver cadastrado, enviamos um link para trocar a senha.", "ok")
        return redirect(url_for("contas.login"))
    return render_template("esqueci_senha.html")


@bp.route("/redefinir/<token>", methods=["GET", "POST"])
def redefinir(token):
    if request.method == "POST":
        try:
            contas.redefinir_senha(token, request.form.get("senha"))
        except ErroNegocio as e:
            flash(str(e), "erro")
            return render_template("redefinir.html"), 422
        flash("Senha alterada. Entre com a nova senha.", "ok")
        return redirect(url_for("contas.login"))
    return render_template("redefinir.html")


@bp.route("/perfil", methods=["GET", "POST"])
@login_obrigatorio
def perfil():
    if request.method == "POST":
        exigir_confirmacao()
        f = request.form
        try:
            foto = salvar_upload(request.files.get("foto"))
            contas.editar(g.usuario["id"], f.get("nome"), f.get("email"), f.get("telefone"), f.get("endereco"), f.get("nova_senha", ""))
            if foto:
                usuarios_repo.atualizar(g.usuario["id"], foto=foto)
            flash("Perfil atualizado.", "ok")
        except ErroNegocio as e:
            flash(str(e), "erro")
        return redirect(url_for("contas.perfil"))
    return render_template("perfil.html")


@bp.route("/perfil/excluir", methods=["POST"])
@login_obrigatorio
def excluir_conta():
    exigir_confirmacao()
    contas.excluir(g.usuario["id"])
    session.clear()
    flash("Sua conta foi excluída.", "ok")
    return redirect(url_for("produtos.listar"))


@bp.route("/configuracoes", methods=["GET", "POST"])
@login_obrigatorio
def configuracoes():
    if request.method == "POST":
        exigir_confirmacao()
        f = request.form
        contas.salvar_privacidade(g.usuario["id"], "exibir_nome" in f, "dois_fatores" in f, "recomendacoes" in f)
        flash("Configurações salvas.", "ok")
        return redirect(url_for("contas.configuracoes"))
    return render_template("configuracoes.html")


@bp.route("/configuracoes/acessibilidade", methods=["GET", "POST"])
@login_obrigatorio
def acessibilidade():
    if request.method == "POST":
        f = request.form
        try:
            avancar, voltar = (f.get("hex_avancar", "").strip(), f.get("hex_voltar", "").strip()) if f.get("usar_hex") else ("", "")
            contas.salvar_acessibilidade(g.usuario["id"], f.get("tamanho_fonte"), int(f.get("por_vez", 8)), f.get("preset"), avancar, voltar)
            flash("Preferências de acessibilidade salvas.", "ok")
        except (ErroNegocio, ValueError) as e:
            flash(str(e), "erro")
        return redirect(url_for("contas.acessibilidade"))
    return render_template("acessibilidade.html", presets=contas.PRESETS_CORES, tamanhos=contas.TAMANHOS_FONTE)


@bp.route("/notificacoes")
@login_obrigatorio
def lista_notificacoes():
    itens = notificacoes.listar(g.usuario["id"]) if g.usuario["tipo"] == "vendedor" else []
    r = render_template("notificacoes.html", itens=itens)
    notificacoes.marcar_lidas(g.usuario["id"])
    return r


@bp.route("/caixa-de-saida")
@login_obrigatorio
def caixa_de_saida():
    """Demonstração: o Postmark é simulado, então os e-mails 'enviados' aparecem aqui."""
    return render_template("caixa_saida.html", emails=pedidos_repo.emails_para(g.usuario["email"]))


@bp.route("/caixa-de-saida/publica")
def caixa_publica_reset():
    """Para recuperação de senha sem login (só em modo demonstração)."""
    if not os.environ.get("CHERISH_DEMO"):
        abort(404)  # nunca expor e-mails de terceiros fora do modo demonstração (RN09)
    email = request.args.get("email", "")
    return render_template("caixa_saida.html", emails=pedidos_repo.emails_para(email.lower()) if email else [], publica=True)
