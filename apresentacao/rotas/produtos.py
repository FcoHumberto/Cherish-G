"""Rotas de catálogo, produto, acessados recentes e área do vendedor (CMP01 ↔ CMP03/CMP04)."""
from flask import Blueprint, render_template, request, redirect, url_for, flash, g, abort, jsonify, Response
from negocio import produtos, recomendacoes, pedidos
from negocio.contas import ErroNegocio
from negocio.pedidos import Conflito
from acesso_dados import produtos_repo, pedidos_repo
from ..contexto import login_obrigatorio, vendedor_obrigatorio
from .contas import salvar_upload

bp = Blueprint("produtos", __name__)
CORES = ["#F4C7C3", "#BFE3C0", "#A9CCE8", "#F6DDA0", "#D9CCF0", "#FFD9B8", "#A8DCD9"]


@bp.route("/")
@bp.route("/produtos")
def listar():  # RF15 / RF37
    pagina = request.args.get("pagina", 1, type=int)
    busca, cat = request.args.get("q", "").strip(), request.args.get("categoria", "")
    itens, paginas = produtos.listar(busca, cat, pagina, g.prefs["produtos_por_vez"])
    recs = recomendacoes.recomendados(g.usuario["id"]) if g.usuario else []
    return render_template("produtos.html", itens=itens, pagina=pagina, paginas=paginas, busca=busca, cat=cat,
                           categorias=produtos_repo.categorias(), recs=recs)


@bp.route("/produto/<int:pid>")
def detalhe(pid):  # RF17
    p = produtos_repo.por_id(pid)
    if not p or p["status"] != "ativo":
        abort(404)
    pode_avaliar = False
    if g.usuario:
        recomendacoes.registrar_acesso(g.usuario["id"], pid)  # RF26
        pode_avaliar = pedidos_repo.comprou_produto(g.usuario["id"], pid)
    return render_template("produto.html", p=p, preco=produtos.preco_final(p), fotos=[f for f in p["imagens"].split(",") if f],
                           avaliacoes=produtos_repo.avaliacoes(pid), pode_avaliar=pode_avaliar)


@bp.route("/produto/<int:pid>/carrinho", methods=["POST"])
@login_obrigatorio
def adicionar_carrinho(pid):
    try:
        pedidos.adicionar(g.usuario["id"], pid, request.form.get("quantidade", 1, type=int))
        flash("Produto adicionado ao carrinho.", "ok")
    except ErroNegocio as e:
        flash(str(e), "erro")
    return redirect(url_for("produtos.detalhe", pid=pid))


@bp.route("/produto/<int:pid>/avaliar", methods=["POST"])
@login_obrigatorio
def avaliar(pid):
    try:
        produtos.avaliar(g.usuario, pid, request.form.get("nota", type=int), request.form.get("comentario"))
        flash("Avaliação registrada. Obrigado!", "ok")
    except ErroNegocio as e:
        flash(str(e), "erro")
    return redirect(url_for("produtos.detalhe", pid=pid))


@bp.route("/acessados")
@login_obrigatorio
def acessados():  # RF26
    return render_template("acessados.html", itens=recomendacoes.acessados(g.usuario["id"]))


@bp.route("/imagem/<int:pid>")
def imagem(pid):
    """Imagem de reposição (SVG) para produtos sem foto enviada."""
    p = produtos_repo.por_id(pid)
    letra = (p["nome"][:1] if p else "?").upper()
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 300"><rect width="400" height="300" fill="{CORES[pid % len(CORES)]}"/>'
           f'<text x="200" y="195" font-size="130" text-anchor="middle" fill="#2b2230" font-family="Georgia,serif">{letra}</text></svg>')
    return Response(svg, mimetype="image/svg+xml")


# --- área do vendedor ---
@bp.route("/meus-produtos")
@vendedor_obrigatorio
def meus_produtos():  # RF10
    return render_template("meus_produtos.html", itens=produtos_repo.do_vendedor(g.usuario["id"]))


@bp.route("/meus-produtos/novo", methods=["GET", "POST"])
@vendedor_obrigatorio
def novo_produto():  # RF11
    if request.method == "POST":
        f = request.form
        try:
            fotos = [n for n in (salvar_upload(a) for a in request.files.getlist("fotos")) if n]
            pid = produtos.cadastrar(g.usuario, f.get("nome"), f.get("descricao"), f.get("categoria"), f.get("preco"), f.get("promocao"),
                                     f.get("estoque"), fotos, f.get("tipo_comprovante"), f.get("ref_comprovante"))
            flash("Produto publicado.", "ok")
            return redirect(url_for("produtos.editar_produto", pid=pid))
        except ErroNegocio as e:
            flash(str(e), "erro")
            return render_template("produto_form.html", p=f, novo=True, tipos=produtos.TIPOS_COMPROVANTE), 422
    return render_template("produto_form.html", p={}, novo=True, tipos=produtos.TIPOS_COMPROVANTE)


@bp.route("/meus-produtos/<int:pid>", methods=["GET", "POST"])
@vendedor_obrigatorio
def editar_produto(pid):  # RF14
    p = produtos_repo.por_id(pid)
    if not p or p["vendedor_id"] != g.usuario["id"] or p["status"] != "ativo":
        abort(403 if p else 404)
    if request.method == "POST":
        f = request.form
        try:
            produtos.editar(g.usuario, pid, f.get("nome"), f.get("descricao"), f.get("categoria"), f.get("preco"), f.get("promocao"), f.get("estoque"))
            flash("Produto atualizado.", "ok")
        except ErroNegocio as e:
            flash(str(e), "erro")
        return redirect(url_for("produtos.editar_produto", pid=pid))
    return render_template("produto_form.html", p=dict(p), novo=False, pendentes=pedidos_repo.pedidos_pendentes_do_produto(pid),
                           avaliacoes=produtos_repo.avaliacoes(pid), tipos=produtos.TIPOS_COMPROVANTE)


@bp.route("/meus-produtos/<int:pid>/remover", methods=["POST"])
@vendedor_obrigatorio
def remover_produto(pid):
    produtos.remover(g.usuario, pid)
    flash("Produto retirado da venda.", "ok")
    return redirect(url_for("produtos.meus_produtos"))


# --- API ilustrativa (7.2 / 7.3) ---
@bp.route("/api/v1/produtos")
def api_listar():
    itens, _ = produtos_repo.listar(request.args.get("q", ""), request.args.get("categoria", ""), 50, 0)
    return jsonify([_json(p) for p in itens])


@bp.route("/api/v1/produtos/<pid>")
def api_detalhe(pid):
    if not pid.isdigit():
        return jsonify(erro="identificador inválido"), 400
    p = produtos_repo.por_id(int(pid))
    return (jsonify(_json(p)), 200) if p and p["status"] == "ativo" else (jsonify(erro="não encontrado"), 404)


def _json(p):
    return {"id": p["id"], "nome": p["nome"], "loja": p["loja"], "preco": produtos.preco_final(p), "promocao": p["promocao_pct"] > 0, "estoque": p["estoque"]}
