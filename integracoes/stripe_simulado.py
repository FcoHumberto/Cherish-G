"""Stripe (simulado). CPF, número do cartão e chave PIX são usados só para validar e NUNCA persistidos (RNF03/RN06).
Cartões de teste: terminados em 0002 são recusados; Luhn inválido também."""
import hashlib
import hmac
import secrets
from . import vault_simulado as vault
from negocio.validacoes import luhn_valido, cpf_valido


def _segredo_webhook():
    return vault.segredo("STRIPE_WEBHOOK_SECRET", "whsec_cherish_dev").encode()


def assinar_evento(referencia: str, estado: str) -> str:
    return hmac.new(_segredo_webhook(), f"{referencia}:{estado}".encode(), hashlib.sha256).hexdigest()


def verificar_assinatura(referencia, estado, assinatura) -> bool:
    return hmac.compare_digest(assinar_evento(referencia, estado), assinatura or "")


def nova_referencia() -> str:
    return "pi_" + secrets.token_hex(10)


def _qr_svg(texto: str) -> str:
    try:
        import segno, io
        buf = io.BytesIO()
        segno.make(texto, error="m").save(buf, kind="svg", scale=5, border=2, xmldecl=False, svgns=True, nl=False)
        return buf.getvalue().decode()
    except ImportError:  # sem segno: padrão ilustrativo (NÃO é um QR válido)
        h = hashlib.sha256(texto.encode()).digest()
        cel = "".join(f'<rect x="{(i%21)*8}" y="{(i//21)*8}" width="8" height="8"/>' for i in range(441) if (h[i % 32] >> (i % 8)) & 1)
        return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 168 168"><rect width="168" height="168" fill="#fff"/><g fill="#000">{cel}</g></svg>'


def criar_cobranca(forma, valor, referencia, cpf, cartao=None):
    """Retorna dict com 'estado' (aprovado|recusado|pendente) e, no PIX, 'codigo_pix' e 'qr_svg'."""
    if not cpf_valido(cpf):
        return {"estado": "recusado", "motivo": "CPF inválido."}
    if forma == "cartao":
        numero = "".join(c for c in (cartao or {}).get("numero", "") if c.isdigit())
        if not luhn_valido(numero) or numero.endswith("0002"):
            return {"estado": "recusado", "motivo": "Cartão recusado pela operadora."}
        return {"estado": "aprovado", "referencia": referencia}
    codigo = f"00020126PIX-CHERISH-{referencia}-{valor:.2f}".replace(".", "")
    return {"estado": "pendente", "referencia": referencia, "codigo_pix": codigo, "qr_svg": _qr_svg(codigo)}


def qr_svg_do_codigo(codigo):
    return _qr_svg(codigo)
