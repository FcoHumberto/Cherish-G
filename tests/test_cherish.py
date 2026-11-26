"""Testes automatizados (Apêndice B): estoque, PIX 10 min, reembolso único, status, acesso, privacidade."""
import os
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta

os.environ["CHERISH_DEMO"] = "1"
from apresentacao import create_app
from integracoes import eventos, stripe_simulado as stripe
from negocio import validacoes
from acesso_dados import conexao

CPF = "529.982.247-25"
eventos.sincrono = True


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.app = create_app(banco=self.tmp.name, testando=True)
        self.c = self.app.test_client()
        self.v = self.app.test_client()

    def tearDown(self):
        conexao.fechar_db_da_thread()
        os.unlink(self.tmp.name)

    def cadastrar(self, cli, email, tipo):
        r = cli.post("/cadastro", data=dict(nome=email.split("@")[0], email=email, telefone="5585912345678", tipo=tipo, senha="segredo1"))
        self.assertEqual(r.status_code, 302)
        r = cli.post("/login", data=dict(email=email, senha="segredo1"))
        self.assertEqual(r.status_code, 302)

    def produto(self, estoque=5):
        self.cadastrar(self.v, "loja@t.com", "vendedor")
        r = self.v.post("/meus-produtos/novo", data=dict(nome="Caneca", descricao="Boa", categoria="Casa", preco="39,90", promocao="0", estoque=str(estoque),
                                                      tipo_comprovante="Registro de produção", ref_comprovante="X1"))
        self.assertEqual(r.status_code, 302)
        return int(r.headers["Location"].rsplit("/", 1)[1])

    def comprar(self, pid, forma="cartao", cartao="4242424242424242"):
        self.c.post(f"/produto/{pid}/carrinho", data={"quantidade": 1})
        self.c.post("/entrega", data={"endereco": "Rua A"})
        return self.c.post("/pagamento", data=dict(forma=forma, cpf=CPF, cartao_numero=cartao))


class TestContas(Base):
    def test_ct02_email_unico(self):
        self.cadastrar(self.c, "a@t.com", "comum")
        r = self.c.post("/cadastro", data=dict(nome="x", email="a@t.com", telefone="5585912345678", tipo="comum", senha="segredo1"))
        self.assertEqual(r.status_code, 422)

    def test_ct01_login_e_lembrete_2fa(self):
        self.c.post("/cadastro", data=dict(nome="x", email="b@t.com", telefone="5585912345678", tipo="comum", senha="segredo1"))
        r = self.c.post("/login", data=dict(email="b@t.com", senha="segredo1"), follow_redirects=True)
        self.assertIn("dois fatores", r.get_data(as_text=True))

    def test_rf38_login_obrigatorio(self):
        for rota in ("/meus-pedidos", "/acessados", "/perfil"):
            self.assertEqual(self.c.get(rota).headers["Location"], "/login")

    def test_ct04_comum_nao_acessa_meus_produtos(self):
        self.cadastrar(self.c, "c@t.com", "comum")
        self.assertEqual(self.c.get("/meus-produtos").status_code, 403)

    def test_rf07_exige_confirmacao(self):
        self.cadastrar(self.c, "d@t.com", "comum")
        self.assertEqual(self.c.post("/perfil/excluir").status_code, 400)
        self.assertEqual(self.c.post("/perfil/excluir", data={"confirmado": "sim"}).status_code, 302)

    def test_telefone_e_cpf(self):
        self.assertEqual(validacoes.formatar_telefone("5585912345678"), "+55 (85) 91234-5678")
        self.assertEqual(validacoes.formatar_cpf("52998224725"), "529.982.247-25")
        self.assertTrue(validacoes.cpf_valido(CPF)); self.assertFalse(validacoes.cpf_valido("111.111.111-11"))

    def test_rnf06_contraste_dos_presets(self):
        from negocio.contas import PRESETS_CORES
        for _, a, b in PRESETS_CORES.values():
            for cor in (a, b):
                self.assertGreaterEqual(validacoes.contraste(cor, validacoes.cor_texto_para(cor)), 4.5)

    def test_rf33_voltar_sem_loop(self):
        self.cadastrar(self.c, "e@t.com", "comum")
        self.c.get("/perfil"); self.c.get("/configuracoes"); self.c.get("/configuracoes/acessibilidade")
        self.assertEqual(self.c.get("/voltar").headers["Location"], "/configuracoes")
        self.assertEqual(self.c.get("/voltar").headers["Location"], "/perfil")

    def test_rn09_preferencias_por_usuario(self):
        self.cadastrar(self.c, "f@t.com", "comum"); self.cadastrar(self.v, "g@t.com", "comum")
        self.c.post("/configuracoes/acessibilidade", data=dict(tamanho_fonte="extra", por_vez="12", usar_hex="on", hex_avancar="#AABBCC", hex_voltar="#DDEEFF"))
        self.assertIn("#AABBCC", self.c.get("/perfil").get_data(as_text=True))
        self.assertNotIn("#AABBCC", self.v.get("/perfil").get_data(as_text=True))


class TestCompra(Base):
    def estoque(self, pid):
        return sqlite3.connect(self.tmp.name).execute("SELECT estoque FROM produtos WHERE id=?", (pid,)).fetchone()[0]

    def test_ct05_ct07_cartao_atualiza_estoque_recibo_e_carrinho(self):
        pid = self.produto(5)
        self.cadastrar(self.c, "h@t.com", "comum")
        r = self.comprar(pid)
        self.assertEqual(r.status_code, 302)
        pgid = int(r.headers["Location"].split("/")[2])
        self.assertEqual(self.estoque(pid), 4)
        self.assertIn("Pagamento bem-sucedido", self.c.get(r.headers["Location"]).get_data(as_text=True))
        self.c.post(f"/pagamento/{pgid}/concluir")
        self.assertIn("Recibo do pedido", self.c.get("/caixa-de-saida").get_data(as_text=True))
        self.assertNotIn("Carrinho de Compras (", self.c.get("/produtos").get_data(as_text=True))
        self.assertIn("Novo pedido", self.v.get("/notificacoes").get_data(as_text=True))  # CT08

    def test_cartao_recusado_mantem_itens(self):
        pid = self.produto(5); self.cadastrar(self.c, "i@t.com", "comum")
        r = self.comprar(pid, cartao="4000000000000002")
        self.assertEqual(r.status_code, 422); self.assertEqual(self.estoque(pid), 5)
        self.assertIn("Carrinho de Compras (1)", self.c.get("/produtos").get_data(as_text=True))

    def test_ct06_pix_expira_e_itens_ficam_no_carrinho(self):
        pid = self.produto(5); self.cadastrar(self.c, "j@t.com", "comum")
        r = self.comprar(pid, "pix"); pgid = int(r.headers["Location"].split("/")[2])
        con = sqlite3.connect(self.tmp.name)
        con.execute("UPDATE pagamentos SET expira_em=?", ((datetime.now() - timedelta(minutes=1)).isoformat(timespec="seconds"),)); con.commit()
        r = self.c.get(f"/pagamento/{pgid}/pix"); self.assertEqual(r.headers["Location"], "/carrinho")
        self.assertEqual(self.estoque(pid), 5)

    def test_pix_pago_e_webhook_idempotente(self):
        pid = self.produto(5); self.cadastrar(self.c, "k@t.com", "comum")
        r = self.comprar(pid, "pix"); pgid = int(r.headers["Location"].split("/")[2])
        ref = sqlite3.connect(self.tmp.name).execute("SELECT referencia_stripe FROM pagamentos").fetchone()[0]
        self.assertEqual(self.c.post("/api/v1/pagamentos/webhook", json=dict(referencia=ref, estado="aprovado"), headers={"X-Assinatura": "falsa"}).status_code, 401)
        for _ in range(2):  # evento duplicado
            ok = self.c.post("/api/v1/pagamentos/webhook", json=dict(referencia=ref, estado="aprovado"), headers={"X-Assinatura": stripe.assinar_evento(ref, "aprovado")})
            self.assertEqual(ok.status_code, 200)
        self.assertEqual(self.estoque(pid), 4)

    def test_estoque_insuficiente(self):
        pid = self.produto(1); self.cadastrar(self.c, "l@t.com", "comum")
        self.c.post(f"/produto/{pid}/carrinho", data={"quantidade": 1})
        self.cadastrar(self.app.test_client(), "m@t.com", "comum")
        self.assertEqual(self.comprar(pid).status_code, 302)
        self.assertEqual(self.estoque(pid), 0)

    def test_ct09_reembolso_unico_e_rn05(self):
        pid = self.produto(5); self.cadastrar(self.c, "n@t.com", "comum"); self.comprar(pid)
        item = sqlite3.connect(self.tmp.name).execute("SELECT id FROM itens_pedido").fetchone()[0]
        self.assertEqual(self.c.post(f"/api/v1/pedidos/{item}/reembolso").status_code, 409)  # só 'Perdido'
        self.v.post(f"/pedido/{item}/vendedor", data={"acao": "perdido"})
        self.assertEqual(self.c.post(f"/api/v1/pedidos/{item}/reembolso").status_code, 200)
        self.assertEqual(self.c.post(f"/api/v1/pedidos/{item}/reembolso").status_code, 409)
        self.assertIn("Reembolso solicitado", self.c.get(f"/pedido/{item}").get_data(as_text=True))
        outro = self.app.test_client(); self.cadastrar(outro, "o@t.com", "comum")
        self.assertEqual(outro.get(f"/pedido/{item}").status_code, 403)  # RN09

    def test_rn05_entregue_exige_duas_confirmacoes(self):
        pid = self.produto(5); self.cadastrar(self.c, "p@t.com", "comum"); self.comprar(pid)
        item = sqlite3.connect(self.tmp.name).execute("SELECT id FROM itens_pedido").fetchone()[0]
        self.c.post(f"/pedido/{item}/recebido")
        self.assertIn("Pendente", self.c.get(f"/pedido/{item}").get_data(as_text=True))
        self.v.post(f"/pedido/{item}/vendedor", data={"acao": "entregador"})
        self.assertIn("Entregue", self.c.get(f"/pedido/{item}").get_data(as_text=True))

    def test_ct12_sem_dados_sensiveis_no_banco(self):
        pid = self.produto(5); self.cadastrar(self.c, "q@t.com", "comum"); self.comprar(pid)
        bruto = open(self.tmp.name, "rb").read()
        for segredo in (b"4242424242424242", b"529.982.247-25", b"52998224725"):
            self.assertNotIn(segredo, bruto)

    def test_ct10_recomendacoes_e_toggle(self):
        pid = self.produto(5); self.cadastrar(self.c, "r@t.com", "comum")
        self.v.post("/meus-produtos/novo", data=dict(nome="Prato", descricao="Bom", categoria="Casa", preco="10", promocao="0", estoque="3",
                                                    tipo_comprovante="Registro de produção", ref_comprovante="X2"))
        outro = self.app.test_client(); self.cadastrar(outro, "loja2@t.com", "vendedor")
        outro.post("/meus-produtos/novo", data=dict(nome="Tigela", descricao="Boa", categoria="Casa", preco="12", promocao="0", estoque="3",
                                                   tipo_comprovante="Registro de produção", ref_comprovante="X3"))
        self.c.get(f"/produto/{pid}")
        self.assertIn("Baseado nas suas compras", self.c.get("/produtos").get_data(as_text=True))
        self.c.post("/configuracoes", data={"confirmado": "sim", "exibir_nome": "on", "dois_fatores": "on"})
        self.c.post("/login"); 
        self.assertNotIn("Baseado nas suas compras", self.c.get("/produtos").get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()
