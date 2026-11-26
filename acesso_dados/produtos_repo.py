"""Repositório de produtos, comprovantes, avaliações e acessos recentes."""
from .conexao import get_db

_BASE = """SELECT p.*, u.nome AS loja,
  (SELECT ROUND(AVG(nota),1) FROM avaliacoes a WHERE a.produto_id=p.id) AS nota_media,
  (SELECT COUNT(*) FROM avaliacoes a WHERE a.produto_id=p.id) AS total_avaliacoes,
  (SELECT COALESCE(SUM(i.quantidade),0) FROM itens_pedido i WHERE i.produto_id=p.id AND i.status='Pendente') AS pedidos_pendentes
  FROM produtos p JOIN usuarios u ON u.id=p.vendedor_id"""


def criar(vendedor_id, nome, descricao, categoria, preco, promocao_pct, estoque, imagens, comprovante):
    db = get_db()
    cur = db.execute("INSERT INTO produtos (vendedor_id,nome,descricao,categoria,preco,promocao_pct,estoque,imagens) "
                     "VALUES (?,?,?,?,?,?,?,?)", (vendedor_id, nome, descricao, categoria, preco, promocao_pct, estoque, imagens))
    db.execute("INSERT INTO comprovantes (produto_id,tipo,referencia,data) VALUES (?,?,?,datetime('now'))",
               (cur.lastrowid, comprovante["tipo"], comprovante["referencia"]))
    db.commit()
    return cur.lastrowid


def por_id(pid):
    return get_db().execute(_BASE + " WHERE p.id=?", (pid,)).fetchone()


def listar(busca="", categoria="", limite=8, deslocamento=0):
    filtros, args = ["p.status='ativo'"], []
    if busca:
        filtros.append("(p.nome LIKE ? OR p.descricao LIKE ?)"); args += [f"%{busca}%"] * 2
    if categoria:
        filtros.append("p.categoria=?"); args.append(categoria)
    where = " WHERE " + " AND ".join(filtros)
    total = get_db().execute("SELECT COUNT(*) FROM produtos p" + where, args).fetchone()[0]
    linhas = get_db().execute(_BASE + where + " ORDER BY p.id DESC LIMIT ? OFFSET ?", (*args, limite, deslocamento)).fetchall()
    return linhas, total


def categorias():
    return [r[0] for r in get_db().execute("SELECT DISTINCT categoria FROM produtos WHERE status='ativo' ORDER BY 1")]


def do_vendedor(vendedor_id):
    return get_db().execute(_BASE + " WHERE p.vendedor_id=? AND p.status='ativo' ORDER BY p.id DESC", (vendedor_id,)).fetchall()


def atualizar(pid, **campos):
    db = get_db()
    cols = ", ".join(f"{c}=?" for c in campos)
    db.execute(f"UPDATE produtos SET {cols} WHERE id=?", (*campos.values(), pid))
    db.commit()


def semelhantes(usuario_id, categorias_, vendedores, ids_excluir, limite):
    """Produtos da mesma categoria ou loja dos já comprados/acessados (RF16)."""
    if not categorias_ and not vendedores:
        return []
    ph_c, ph_v = ",".join("?" * len(categorias_)) or "NULL", ",".join("?" * len(vendedores)) or "NULL"
    ph_x = ",".join("?" * len(ids_excluir)) or "NULL"
    sql = (_BASE + f" WHERE p.status='ativo' AND p.estoque>0 AND p.vendedor_id<>? AND (p.categoria IN ({ph_c}) OR p.vendedor_id IN ({ph_v}))"
           f" AND p.id NOT IN ({ph_x}) ORDER BY p.id DESC LIMIT ?")
    return get_db().execute(sql, (usuario_id, *categorias_, *vendedores, *ids_excluir, limite)).fetchall()


# --- avaliações ---
def avaliacoes(pid):
    return get_db().execute("SELECT a.*, u.nome FROM avaliacoes a JOIN usuarios u ON u.id=a.usuario_id "
                            "WHERE a.produto_id=? ORDER BY a.id DESC", (pid,)).fetchall()


def salvar_avaliacao(pid, uid, nota, comentario, exibir_nome):
    db = get_db()
    db.execute("INSERT INTO avaliacoes (produto_id,usuario_id,nota,comentario,exibir_nome,data) VALUES (?,?,?,?,?,datetime('now')) "
               "ON CONFLICT(produto_id,usuario_id) DO UPDATE SET nota=excluded.nota, comentario=excluded.comentario, exibir_nome=excluded.exibir_nome",
               (pid, uid, nota, comentario, int(exibir_nome)))
    db.commit()


# --- acessos recentes ---
def registrar_acesso(uid, pid):
    db = get_db()
    db.execute("INSERT INTO acessos_recentes (usuario_id,produto_id,data) VALUES (?,?,datetime('now')) "
               "ON CONFLICT(usuario_id,produto_id) DO UPDATE SET data=datetime('now')", (uid, pid))
    db.commit()


def acessos(uid, limite=30):
    return get_db().execute(_BASE.replace("SELECT p.*,", "SELECT p.*, ar.data AS acessado_em,") +
                            " JOIN acessos_recentes ar ON ar.produto_id=p.id WHERE ar.usuario_id=? ORDER BY ar.data DESC, ar.id DESC LIMIT ?",
                            (uid, limite)).fetchall()
