"""Barramento de eventos que simula o disparo das Azure Functions (ADR-004).
Os handlers rodam em thread separada para não bloquear a compra (7.6, passo 6)."""
import threading
from functions_python import handlers
from acesso_dados.conexao import fechar_db_da_thread

_HANDLERS = {
    "pedido_registrado": handlers.notificar_vendedores,
    "compra_concluida": handlers.enviar_recibo,
}
sincrono = False  # os testes ligam para tornar a execução determinística


def publicar(evento: str, **dados):
    fn = _HANDLERS[evento]
    if sincrono:
        fn(**dados)
        return

    def executar():
        try:
            fn(**dados)
        finally:
            fechar_db_da_thread()
    threading.Thread(target=executar, daemon=True).start()
