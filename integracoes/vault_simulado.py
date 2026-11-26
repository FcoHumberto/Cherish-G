"""HashiCorp Vault (simulado): cifra preferências e guarda segredos. Em produção, use o Vault real."""
import os
from cryptography.fernet import Fernet

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ARQ_CHAVE = os.path.join(_RAIZ, ".vault_key")


def _chave():
    env = os.environ.get("CHERISH_VAULT_KEY")
    if env:
        return env.encode()
    if not os.path.exists(_ARQ_CHAVE):
        with open(_ARQ_CHAVE, "wb") as f:
            f.write(Fernet.generate_key())
    with open(_ARQ_CHAVE, "rb") as f:
        return f.read()


def cifrar(texto: str) -> str:
    return Fernet(_chave()).encrypt(texto.encode()).decode()


def decifrar(token: str) -> str:
    return Fernet(_chave()).decrypt(token.encode()).decode()


def segredo(nome: str, padrao: str = "") -> str:
    """Chaves de API vêm do 'cofre' (aqui: variáveis de ambiente), nunca do código."""
    return os.environ.get(nome, padrao)
