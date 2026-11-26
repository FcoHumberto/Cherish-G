"""Validações e formatações puras (sem acesso a banco)."""
import re


def so_digitos(txt: str) -> str:
    return re.sub(r"\D", "", txt or "")


def formatar_telefone(txt: str) -> str:
    """RF01.1: +XX (XX) XXXXX-XXXX"""
    d = so_digitos(txt)[:13]
    if len(d) < 12:
        return txt
    return f"+{d[:2]} ({d[2:4]}) {d[4:9]}-{d[9:13]}"


def telefone_valido(txt: str) -> bool:
    return re.fullmatch(r"\+\d{2} \(\d{2}\) \d{5}-\d{4}", txt or "") is not None


def formatar_cpf(txt: str) -> str:
    d = so_digitos(txt)[:11]
    return f"{d[:3]}.{d[3:6]}.{d[6:9]}-{d[9:]}" if len(d) == 11 else d


def cpf_valido(txt: str) -> bool:
    d = so_digitos(txt)
    if len(d) != 11 or d == d[0] * 11:
        return False
    for n in (9, 10):
        soma = sum(int(d[i]) * (n + 1 - i) for i in range(n))
        if int(d[n]) != (soma * 10 % 11) % 10:
            return False
    return True


def luhn_valido(numero: str) -> bool:
    d = [int(c) for c in numero if c.isdigit()]
    if len(d) < 13:
        return False
    soma = 0
    for i, n in enumerate(reversed(d)):
        if i % 2:
            n = n * 2 - 9 if n * 2 > 9 else n * 2
        soma += n
    return soma % 10 == 0


def email_valido(txt: str) -> bool:
    return re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", txt or "") is not None


def cor_hex_valida(txt: str) -> bool:
    return re.fullmatch(r"#[0-9a-fA-F]{6}", txt or "") is not None


def _lum(hexcor: str) -> float:
    c = [int(hexcor[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def contraste(a: str, b: str) -> float:
    la, lb = sorted((_lum(a), _lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def cor_texto_para(fundo: str) -> str:
    """Escolhe texto escuro ou claro com maior contraste (WCAG, mínimo 4.5:1 — RNF06)."""
    return "#1d1d2b" if contraste(fundo, "#1d1d2b") >= contraste(fundo, "#ffffff") else "#ffffff"
