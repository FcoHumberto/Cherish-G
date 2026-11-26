"""Auth0 (simulado): emite e valida tokens de sessão assinados, com expiração."""
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from . import vault_simulado as vault

VALIDADE_SEGUNDOS = 8 * 3600


def _ser():
    return URLSafeTimedSerializer(vault.segredo("CHERISH_AUTH_SECRET", "cherish-dev-segredo-troque-em-producao"))


def emitir_token(usuario_id: int) -> str:
    return _ser().dumps({"uid": usuario_id})


def validar_token(token):
    """Retorna o id do usuário ou None (token ausente, inválido ou expirado)."""
    if not token:
        return None
    try:
        return _ser().loads(token, max_age=VALIDADE_SEGUNDOS)["uid"]
    except (BadSignature, SignatureExpired):
        return None
