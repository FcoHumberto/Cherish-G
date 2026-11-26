"""Repositório de usuários, preferências (cifradas) e tokens de senha."""
import json
from .conexao import get_db
from integracoes import vault_simulado as vault

PREFERENCIAS_PADRAO = {
    "exibir_nome_comentarios": True, "dois_fatores": False, "recomendacoes_historico": True,
    "tamanho_fonte": "medio", "produtos_por_vez": 8,
    "cores_botoes": {"avancar": "#BFE3C0", "voltar": "#F4C7C3"},
}


def criar(nome, email, telefone, tipo, endereco, senha_hash):
    db = get_db()
    cur = db.execute("INSERT INTO usuarios (nome,email,telefone,tipo,endereco_padrao,senha_hash) VALUES (?,?,?,?,?,?)",
                     (nome, email.lower(), telefone, tipo, endereco or None, senha_hash))
    db.commit()
    salvar_preferencias(cur.lastrowid, PREFERENCIAS_PADRAO)
    return cur.lastrowid


def por_id(uid):
    return get_db().execute("SELECT * FROM usuarios WHERE id=?", (uid,)).fetchone()


def por_email(email):
    return get_db().execute("SELECT * FROM usuarios WHERE email=?", (email.lower(),)).fetchone()


def atualizar(uid, **campos):
    db = get_db()
    cols = ", ".join(f"{c}=?" for c in campos)
    db.execute(f"UPDATE usuarios SET {cols} WHERE id=?", (*campos.values(), uid))
    db.commit()


def excluir(uid):
    db = get_db()
    db.execute("DELETE FROM usuarios WHERE id=?", (uid,))
    db.commit()


def obter_preferencias(uid):
    linha = get_db().execute("SELECT dados_cifrados FROM preferencias WHERE usuario_id=?", (uid,)).fetchone()
    prefs = json.loads(json.dumps(PREFERENCIAS_PADRAO))
    if linha:
        prefs.update(json.loads(vault.decifrar(linha["dados_cifrados"])))
    return prefs


def salvar_preferencias(uid, prefs):
    db = get_db()
    db.execute("INSERT INTO preferencias (usuario_id,dados_cifrados) VALUES (?,?) "
               "ON CONFLICT(usuario_id) DO UPDATE SET dados_cifrados=excluded.dados_cifrados",
               (uid, vault.cifrar(json.dumps(prefs))))
    db.commit()


def salvar_token_senha(token, uid, expira_em):
    db = get_db()
    db.execute("INSERT INTO tokens_senha VALUES (?,?,?)", (token, uid, expira_em))
    db.commit()


def consumir_token_senha(token):
    db = get_db()
    linha = db.execute("SELECT * FROM tokens_senha WHERE token=?", (token,)).fetchone()
    if linha:
        db.execute("DELETE FROM tokens_senha WHERE token=?", (token,))
        db.commit()
    return linha
