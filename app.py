"""Ponto de entrada da Cherish.  Uso:  python app.py   (http://127.0.0.1:5000)"""
import os
import threading
import time

os.environ.setdefault("CHERISH_DEMO", "1")  # caixa de saída pública e dados de demonstração

from apresentacao import create_app
from functions_python import handlers
from semear import semear, SENHA


def agendar_expiracao_pix(intervalo=30):
    """Equivalente local do timer da Azure Function que expira PIX (RF21.3)."""
    def laco():
        while True:
            time.sleep(intervalo)
            try:
                handlers.expirar_pix()
            except Exception:
                pass
    threading.Thread(target=laco, daemon=True).start()


app = create_app()
with app.app_context():
    semear()

if __name__ == "__main__":
    agendar_expiracao_pix()
    print(f"\n  Contas de demonstração (senha: {SENHA})\n   vendedor@cherish.demo\n   comprador@cherish.demo\n")
    app.run(debug=False, threaded=True)
