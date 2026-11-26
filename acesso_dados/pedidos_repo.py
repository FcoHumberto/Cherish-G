"""Repositório de carrinho, pedidos, pagamentos, reembolsos, notificações e e-mails."""
import json
from .conexao import get_db


# --- carrinho ---
def carrinho(uid):
    return get_db().execute("SELECT c.id, c.quantidade, p.id AS produto_id, p.nome, p.preco, p.promocao_pct, p.estoque, p.imagens, p.vendedor_id "
                            "FROM itens_carrinho c JOIN produtos p ON p.id=c.produto_id WHERE c.usuario_id=? ORDER BY c.id", (uid,)).fetchall()


def adicionar_ao_carrinho(uid, pid, qtd):
    db = get_db()
    db.execute("INSERT INTO itens_carrinho (usuario_id,produto_id,quantidade) VALUES (?,?,?) "
               "ON CONFLICT(usuario_id,produto_id) DO UPDATE SET quantidade=quantidade+excluded.quantidade", (uid, pid, qtd))
    db.commit()


def remover_do_carrinho(uid, pid):
    db = get_db()
    db.execute("DELETE FROM itens_carrinho WHERE usuario_id=? AND produto_id=?", (uid, pid))
    db.commit()


def esvaziar_carrinho(uid):
    db = get_db()
    db.execute("DELETE FROM itens_carrinho WHERE usuario_id=?", (uid,))
    db.commit()


def quantidade_carrinho(uid):
    return get_db().execute("SELECT COALESCE(SUM(quantidade),0) FROM itens_carrinho WHERE usuario_id=?", (uid,)).fetchone()[0]


# --- pagamentos ---
def criar_pagamento(uid, forma, valor, referencia, expira_em, endereco, itens, codigo_pix=None):
    db = get_db()
    cur = db.execute("INSERT INTO pagamentos (comprador_id,forma,valor,referencia_stripe,expira_em,endereco,itens_json,codigo_pix) VALUES (?,?,?,?,?,?,?,?)",
                     (uid, forma, valor, referencia, expira_em, endereco, json.dumps(itens), codigo_pix))
    db.commit()
    return cur.lastrowid


def pagamento(pgid):
    return get_db().execute("SELECT * FROM pagamentos WHERE id=?", (pgid,)).fetchone()


def pagamento_por_referencia(ref):
    return get_db().execute("SELECT * FROM pagamentos WHERE referencia_stripe=?", (ref,)).fetchone()


def atualizar_pagamento(pgid, **campos):
    db = get_db()
    cols = ", ".join(f"{c}=?" for c in campos)
    db.execute(f"UPDATE pagamentos SET {cols} WHERE id=?", (*campos.values(), pgid))
    db.commit()


def pix_expirados(agora_iso):
    return get_db().execute("SELECT * FROM pagamentos WHERE forma='pix' AND status='pendente' AND expira_em<?", (agora_iso,)).fetchall()


# --- pedidos ---
def pedidos_do_usuario(uid):
    return get_db().execute("SELECT i.*, p.id AS pedido_id, p.data_hora, p.endereco_entrega, p.comprador_id FROM itens_pedido i "
                            "JOIN pedidos p ON p.id=i.pedido_id WHERE p.comprador_id=? ORDER BY i.id DESC", (uid,)).fetchall()


def item_pedido(item_id):
    return get_db().execute("SELECT i.*, p.data_hora, p.endereco_entrega, p.comprador_id FROM itens_pedido i "
                            "JOIN pedidos p ON p.id=i.pedido_id WHERE i.id=?", (item_id,)).fetchone()


def pedidos_pendentes_do_produto(pid):
    return get_db().execute("SELECT i.*, p.data_hora, u.nome AS comprador FROM itens_pedido i JOIN pedidos p ON p.id=i.pedido_id "
                            "JOIN usuarios u ON u.id=p.comprador_id WHERE i.produto_id=? AND i.status='Pendente' ORDER BY i.id DESC", (pid,)).fetchall()


def comprou_produto(uid, pid):
    return get_db().execute("SELECT 1 FROM itens_pedido i JOIN pedidos p ON p.id=i.pedido_id WHERE p.comprador_id=? AND i.produto_id=? LIMIT 1",
                            (uid, pid)).fetchone() is not None


def atualizar_item(item_id, **campos):
    db = get_db()
    cols = ", ".join(f"{c}=?" for c in campos)
    db.execute(f"UPDATE itens_pedido SET {cols} WHERE id=?", (*campos.values(), item_id))
    db.commit()


def registrar_pedido_atomico(uid, pgid, endereco, itens, previsao):
    """Cria pedido + itens e baixa o estoque em UMA transação (7.7: estoque insuficiente em compras simultâneas).
    Retorna (pedido_id, None) ou (None, mensagem_de_erro)."""
    db = get_db()
    try:
        db.execute("BEGIN IMMEDIATE")
        for it in itens:
            cur = db.execute("UPDATE produtos SET estoque=estoque-? WHERE id=? AND estoque>=?", (it["quantidade"], it["produto_id"], it["quantidade"]))
            if cur.rowcount == 0:
                db.rollback()
                return None, f"Estoque insuficiente para «{it['nome']}»."
        total = round(sum(i["preco_unitario"] * i["quantidade"] for i in itens), 2)
        cur = db.execute("INSERT INTO pedidos (comprador_id,endereco_entrega,data_hora,total) VALUES (?,?,datetime('now','localtime'),?)", (uid, endereco, total))
        pedido_id = cur.lastrowid
        for it in itens:
            db.execute("INSERT INTO itens_pedido (pedido_id,produto_id,nome_produto,preco_unitario,quantidade,previsao) VALUES (?,?,?,?,?,?)",
                       (pedido_id, it["produto_id"], it["nome"], it["preco_unitario"], it["quantidade"], previsao))
        db.execute("UPDATE pagamentos SET pedido_id=?, status='aprovado' WHERE id=?", (pedido_id, pgid))
        db.commit()
        return pedido_id, None
    except Exception:
        db.rollback()
        raise


def itens_do_pedido(pedido_id):
    return get_db().execute("SELECT i.*, p.vendedor_id FROM itens_pedido i JOIN produtos p ON p.id=i.produto_id WHERE i.pedido_id=?", (pedido_id,)).fetchall()


def pedido(pedido_id):
    return get_db().execute("SELECT * FROM pedidos WHERE id=?", (pedido_id,)).fetchone()


# --- reembolso ---
def criar_reembolso(item_id):
    db = get_db()
    try:
        db.execute("INSERT INTO reembolsos (item_pedido_id,data) VALUES (?,datetime('now'))", (item_id,))
        db.commit()
        return True
    except Exception:  # UNIQUE -> RN02
        db.rollback()
        return False


# --- notificações e e-mails ---
def criar_notificacao(vendedor_id, pedido_id, mensagem):
    db = get_db()
    db.execute("INSERT INTO notificacoes (vendedor_id,pedido_id,mensagem,data) VALUES (?,?,?,datetime('now','localtime'))", (vendedor_id, pedido_id, mensagem))
    db.commit()


def notificacoes(vendedor_id):
    return get_db().execute("SELECT * FROM notificacoes WHERE vendedor_id=? ORDER BY id DESC LIMIT 30", (vendedor_id,)).fetchall()


def nao_lidas(vendedor_id):
    return get_db().execute("SELECT COUNT(*) FROM notificacoes WHERE vendedor_id=? AND lida=0", (vendedor_id,)).fetchone()[0]


def marcar_lidas(vendedor_id):
    db = get_db()
    db.execute("UPDATE notificacoes SET lida=1 WHERE vendedor_id=?", (vendedor_id,))
    db.commit()


def gravar_email(destinatario, assunto, corpo):
    db = get_db()
    db.execute("INSERT INTO emails_enviados (destinatario,assunto,corpo,data) VALUES (?,?,?,datetime('now','localtime'))", (destinatario, assunto, corpo))
    db.commit()


def emails_para(destinatario):
    return get_db().execute("SELECT * FROM emails_enviados WHERE destinatario=? ORDER BY id DESC LIMIT 20", (destinatario,)).fetchall()
