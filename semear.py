"""Dados fictícios para demonstração (RNF03: sem informações reais)."""
from acesso_dados import usuarios_repo, produtos_repo
from negocio import contas

SENHA = "cherish123"
PRODUTOS = [
    ("Caneca de cerâmica", "Caneca artesanal de 300 ml, esmaltada à mão, própria para micro-ondas e lava-louças.", "Casa", 39.90, 0, 25),
    ("Vaso de cactos", "Kit com 3 vasinhos de cactos decorativos em cerâmica.", "Casa", 59.00, 15, 12),
    ("Fone Bluetooth", "Fone sem fio com bateria de 20 horas e estojo de carregamento.", "Eletrônicos", 149.90, 10, 30),
    ("Carregador USB-C 20W", "Carregador rápido compacto com cabo de 1 m.", "Eletrônicos", 69.90, 0, 40),
    ("Camiseta de algodão", "Camiseta unissex 100% algodão, disponível em tamanho M.", "Moda", 49.90, 20, 50),
    ("Mochila urbana", "Mochila impermeável com compartimento para notebook de 15\".", "Moda", 129.00, 0, 18),
    ("Caderno pontilhado A5", "Caderno de 160 páginas, papel 90 g/m².", "Papelaria", 29.90, 0, 60),
    ("Kit de canetas pastel", "12 canetas em tons pastel para estudos e journaling.", "Papelaria", 34.50, 5, 35),
]


def semear():
    if usuarios_repo.por_email("vendedor@cherish.demo"):
        return
    vend = contas.cadastrar("Casa Aconchego", "vendedor@cherish.demo", "+55 (85) 91234-5678", "vendedor", SENHA)
    contas.cadastrar("Maria Compradora", "comprador@cherish.demo", "+55 (85) 98765-4321", "comum", SENHA, "Rua Silva Jatahy, Meireles")
    for nome, desc, cat, preco, promo, est in PRODUTOS:
        produtos_repo.criar(vend, nome, desc, cat, preco, promo, est, "", {"tipo": "Registro de produção", "referencia": "DEMO-001"})
