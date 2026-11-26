"""Contas: cadastro, login, perfil, preferências e recuperação de senha (CMP02)."""
import secrets
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from acesso_dados import usuarios_repo as repo
from integracoes import auth0_simulado as auth0, postmark_simulado as postmark
from . import validacoes as v


class ErroNegocio(Exception):
    pass


PRESETS_CORES = {  # RN07: todas pastéis; RF31.2
    "padrao": ("Padrão", "#BFE3C0", "#F4C7C3"),
    "deuteranopia": ("Deuteranopia / Protanopia", "#A9CCE8", "#F6DDA0"),
    "tritanopia": ("Tritanopia", "#F2B8C6", "#A8DCD9"),
    "alto_contraste": ("Pastel suave", "#D9CCF0", "#FFD9B8"),
}
TAMANHOS_FONTE = {"pequeno": 14, "medio": 16, "grande": 19, "extra": 22}


def cadastrar(nome, email, telefone, tipo, senha, endereco=""):
    nome, email, telefone = (nome or "").strip(), (email or "").strip().lower(), v.formatar_telefone((telefone or "").strip())
    if not nome or not email or not telefone or not senha or tipo not in ("comum", "vendedor"):
        raise ErroNegocio("Preencha todos os campos obrigatórios.")
    if not v.email_valido(email):
        raise ErroNegocio("E-mail inválido.")
    if not v.telefone_valido(telefone):
        raise ErroNegocio("Telefone inválido. Use +XX (XX) XXXXX-XXXX.")
    if len(senha) < 6:
        raise ErroNegocio("A senha precisa ter ao menos 6 caracteres.")
    if repo.por_email(email):  # RN01
        raise ErroNegocio("Já existe uma conta com este e-mail.")
    return repo.criar(nome, email, telefone, tipo, endereco.strip(), generate_password_hash(senha))


def autenticar(email, senha):
    """RF02: apenas e-mail e senha. Retorna o usuário ou levanta ErroNegocio."""
    u = repo.por_email((email or "").strip())
    if not u or not check_password_hash(u["senha_hash"], senha or ""):
        raise ErroNegocio("E-mail ou senha incorretos.")
    return u


def emitir_codigo_2fa(usuario):
    codigo = f"{secrets.randbelow(1000000):06d}"
    postmark.enviar(usuario["email"], "Seu código de verificação Cherish", f"Seu código de verificação é {codigo}. Ele vale por poucos minutos.")
    return codigo


def emitir_sessao(usuario_id):
    return auth0.emitir_token(usuario_id)


def usuario_da_sessao(token):
    uid = auth0.validar_token(token)
    return repo.por_id(uid) if uid else None


def editar(uid, nome, email, telefone, endereco, nova_senha=""):
    atual = repo.por_id(uid)
    email, telefone = (email or "").strip().lower(), v.formatar_telefone((telefone or "").strip())
    if not (nome or "").strip() or not v.email_valido(email) or not v.telefone_valido(telefone):
        raise ErroNegocio("Dados inválidos. Revise nome, e-mail e telefone.")
    outro = repo.por_email(email)
    if outro and outro["id"] != atual["id"]:
        raise ErroNegocio("Já existe uma conta com este e-mail.")
    campos = dict(nome=nome.strip(), email=email, telefone=telefone, endereco_padrao=(endereco or "").strip() or None)
    if nova_senha:
        if len(nova_senha) < 6:
            raise ErroNegocio("A nova senha precisa ter ao menos 6 caracteres.")
        campos["senha_hash"] = generate_password_hash(nova_senha)
    repo.atualizar(uid, **campos)


def excluir(uid):
    repo.excluir(uid)


def solicitar_redefinicao(email, url_base):
    """RF03.1: sempre responde igual (não revela se o e-mail existe)."""
    u = repo.por_email((email or "").strip())
    if u:
        token = secrets.token_urlsafe(24)
        repo.salvar_token_senha(token, u["id"], (datetime.now() + timedelta(hours=1)).isoformat(timespec="seconds"))
        postmark.enviar(u["email"], "Redefinição de senha Cherish", f"Para trocar sua senha, acesse: {url_base}{token}")


def redefinir_senha(token, nova_senha):
    if len(nova_senha or "") < 6:
        raise ErroNegocio("A senha precisa ter ao menos 6 caracteres.")
    linha = repo.consumir_token_senha(token)
    if not linha or datetime.fromisoformat(linha["expira_em"]) < datetime.now():
        raise ErroNegocio("Link inválido ou expirado.")
    repo.atualizar(linha["usuario_id"], senha_hash=generate_password_hash(nova_senha))


# --- preferências (RF29–RF32) ---
def preferencias(uid):
    return repo.obter_preferencias(uid)


def salvar_privacidade(uid, exibir_nome, dois_fatores, recomendacoes):
    p = repo.obter_preferencias(uid)
    p.update(exibir_nome_comentarios=exibir_nome, dois_fatores=dois_fatores, recomendacoes_historico=recomendacoes)
    repo.salvar_preferencias(uid, p)


def salvar_acessibilidade(uid, tamanho, por_vez, preset, avancar_hex, voltar_hex):
    p = repo.obter_preferencias(uid)
    if tamanho in TAMANHOS_FONTE:
        p["tamanho_fonte"] = tamanho
    p["produtos_por_vez"] = por_vez if por_vez in (4, 8, 12, 16, 24) else 8
    if avancar_hex or voltar_hex:  # "Cores Avançadas" (RF31.3)
        for k, hx in (("avancar", avancar_hex), ("voltar", voltar_hex)):
            if hx:
                if not v.cor_hex_valida(hx):
                    raise ErroNegocio(f"Código HEX inválido: {hx}")
                p["cores_botoes"][k] = hx.upper()
    elif preset in PRESETS_CORES:
        _, a, b = PRESETS_CORES[preset]
        p["cores_botoes"] = {"avancar": a, "voltar": b}
    repo.salvar_preferencias(uid, p)
