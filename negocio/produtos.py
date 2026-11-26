"""Produtos e estoque (CMP03)."""
from acesso_dados import produtos_repo as repo, pedidos_repo
from .contas import ErroNegocio

TIPOS_COMPROVANTE = ["Nota fiscal de aquisição de fabricante", "Nota fiscal de entrada de matéria-prima", "Registro de produção"]


def preco_final(p) -> float:
    return round(p["preco"] * (100 - (p["promocao_pct"] or 0)) / 100, 2)


def _validar(nome, descricao, preco, promocao, estoque):
    try:
        preco, promocao, estoque = float(str(preco).replace(",", ".")), int(promocao or 0), int(estoque)
    except ValueError:
        raise ErroNegocio("Preço, promoção e estoque precisam ser numéricos.")
    if not (nome or "").strip() or not (descricao or "").strip():
        raise ErroNegocio("Informe nome e descrição.")
    if preco <= 0 or estoque < 0 or not 0 <= promocao <= 90:
        raise ErroNegocio("Valores inválidos: preço > 0, estoque ≥ 0 e promoção entre 0 e 90%.")
    return nome.strip(), descricao.strip(), preco, promocao, estoque


def cadastrar(vendedor, nome, descricao, categoria, preco, promocao, estoque, imagens, tipo_comprovante, ref_comprovante):
    if vendedor["tipo"] != "vendedor":
        raise ErroNegocio("Apenas vendedores podem cadastrar produtos.")
    if tipo_comprovante not in TIPOS_COMPROVANTE or not (ref_comprovante or "").strip():  # RF11
        raise ErroNegocio("Comprove a posse do produto (tipo e número/referência do documento).")
    nome, descricao, preco, promocao, estoque = _validar(nome, descricao, preco, promocao, estoque)
    return repo.criar(vendedor["id"], nome, descricao, (categoria or "Geral").strip().title(), preco, promocao, estoque,
                      ",".join(imagens), {"tipo": tipo_comprovante, "referencia": ref_comprovante.strip()})


def editar(vendedor, pid, nome, descricao, categoria, preco, promocao, estoque):
    p = repo.por_id(pid)
    if not p or p["vendedor_id"] != vendedor["id"]:
        raise ErroNegocio("Você só pode editar os seus próprios produtos.")
    nome, descricao, preco, promocao, estoque = _validar(nome, descricao, preco, promocao, estoque)
    repo.atualizar(pid, nome=nome, descricao=descricao, categoria=(categoria or "Geral").strip().title(), preco=preco, promocao_pct=promocao, estoque=estoque)


def remover(vendedor, pid):
    p = repo.por_id(pid)
    if not p or p["vendedor_id"] != vendedor["id"]:
        raise ErroNegocio("Produto não encontrado.")
    repo.atualizar(pid, status="removido")


def listar(busca, categoria, pagina, por_pagina):
    pagina = max(1, pagina)
    linhas, total = repo.listar(busca, categoria, por_pagina, (pagina - 1) * por_pagina)
    return linhas, max(1, -(-total // por_pagina))


def avaliar(usuario, pid, nota, comentario):
    if not pedidos_repo.comprou_produto(usuario["id"], pid):
        raise ErroNegocio("Só quem comprou o produto pode avaliá-lo.")
    if nota not in range(1, 6):
        raise ErroNegocio("A nota deve ser de 1 a 5 estrelas.")
    from . import contas
    exibir = contas.preferencias(usuario["id"])["exibir_nome_comentarios"]
    repo.salvar_avaliacao(pid, usuario["id"], nota, (comentario or "").strip()[:500], exibir)
