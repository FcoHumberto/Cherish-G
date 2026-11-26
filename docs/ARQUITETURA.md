# Mapa especificação → código

| Camada / componente (PDF) | Pasta | Observação |
|---|---|---|
| CMP01 Interface (Apresentação) | `apresentacao/` (`rotas/`, `templates/`, `static/`) | Valida formato e autorização; sem regras centrais |
| CMP02 Contas | `negocio/contas.py` | RF01–RF07, RF27, RF29–RF32 |
| CMP03 Produtos e estoque | `negocio/produtos.py` | RF09–RF12, RF14, RF15, RF17 |
| CMP04 Recomendações | `negocio/recomendacoes.py` | RF16, RF26 |
| CMP05 Pedidos e pagamento | `negocio/pedidos.py` | RF18–RF25, RF34; estoque em transação |
| CMP06 Notificações | `negocio/notificacoes.py` + `integracoes/postmark_simulado.py` | RF03.1, RF13, RF22 |
| CMP07 Acesso a Dados | `acesso_dados/` + `migrations/` | PostgreSQL no PDF → SQLite no protótipo |
| CMP08 Funções por evento | `functions_python/handlers.py` + `integracoes/eventos.py` | Azure Functions simuladas localmente |
| Integrações | `integracoes/` | Auth0, Stripe, Postmark e Vault simulados |
| Implantação | `deploy/` | Dockerfile e job Nomad |

## Divergências conhecidas (protótipo acadêmico, PDF 2.8 e 10.5)
- **Backend em Python** (pedido do usuário) em vez de Java; mantém as mesmas três camadas.
- **SQLite** no lugar de PostgreSQL: o acesso está isolado em `acesso_dados/`, então trocar o driver não afeta as outras camadas.
- **Auth0, Stripe, Postmark, Vault e Azure Functions são simulados**; nenhum serviço externo é chamado.
- A baixa de estoque ocorre dentro da transação de registro do pedido (7.7), não na função por evento.
- O tema claro/noturno é guardado no navegador (localStorage); as demais preferências são por usuário e cifradas.
- A API usa `/api/v1/pedidos/{id}/reembolso` com o id do **item** do pedido (cada item tem status próprio, RF23).
