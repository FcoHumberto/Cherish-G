"""Postmark (simulado): em vez de enviar, grava na caixa de saída consultável em /caixa-de-saida."""
import logging
from acesso_dados import pedidos_repo

log = logging.getLogger("cherish.email")


def enviar(destinatario: str, assunto: str, corpo: str):
    pedidos_repo.gravar_email(destinatario, assunto, corpo)
    log.info("E-mail para %s: %s", destinatario, assunto)  # sem corpo no log (dados pessoais)
