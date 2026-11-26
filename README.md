# Cherish — plataforma de comércio eletrônico (protótipo)

Implementação em **Python (Flask)** da especificação *Cherish-Specs.pdf*, em arquitetura de três camadas.

## Executar
```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py                                        # http://127.0.0.1:5000
```
Contas de demonstração (senha `cherish123`): `vendedor@cherish.demo` e `comprador@cherish.demo`.
Testes: `python -m unittest discover -s tests -t .`

## Estrutura
```
cherish/
├── app.py                 # entrada; semeia dados fictícios e agenda a expiração do PIX
├── semear.py              # usuários e produtos de demonstração
├── apresentacao/          # CAMADA 1 — telas e controladores
│   ├── rotas/             #   contas, produtos, pedidos
│   ├── templates/         #   HTML (Jinja)
│   └── static/            #   css, js, img (logo e ícones de tema), uploads
├── negocio/               # CAMADA 2 — regras: contas, produtos, recomendacoes, pedidos, notificacoes, validacoes
├── acesso_dados/          # CAMADA 3 — conexão e repositórios (SQL)
├── integracoes/           # adaptadores: Auth0, Stripe, Postmark, Vault (simulados) e barramento de eventos
├── functions_python/      # funções orientadas a eventos (recibo, notificação, expiração do PIX)
├── migrations/            # esquema versionado
├── tests/                 # testes automatizados (Apêndice B)
├── docs/                  # mapa especificação → código e divergências
└── deploy/                # Dockerfile e job Nomad
```
Cada camada só chama a vizinha: `apresentacao → negocio → acesso_dados`; chamadas externas passam por `integracoes/`.

## Roteiro de demonstração
1. Entre como comprador, abra um produto, adicione ao carrinho (botão "Carrinho de Compras" aparece no canto superior direito).
2. Continue → endereço (com sugestões e endereço salvo) → recibo → pagamento. CPF de teste `529.982.247-25`; cartão `4242 4242 4242 4242` (final `0002` é recusado).
3. No PIX, use "Simular pagamento" (o QR expira em 10 min). Veja o e-mail do recibo em *Perfil → Caixa de saída*.
4. Como vendedor, em *Meus Produtos → produto* atualize a localização, marque como perdido ou confirme como entregador; o comprador pede o reembolso (uma única vez) ou confirma o recebimento.
5. *Perfil → Configurações → Acessibilidade*: fonte, itens por página e cores (presets ou HEX) para cada categoria de botão.

## Segurança
CPF, cartão e chave PIX nunca são gravados (RNF03). Senhas usam hash; preferências ficam cifradas (Fernet, simulando o Vault). Para uso real, defina `CHERISH_SECRET`, `CHERISH_VAULT_KEY`, `CHERISH_AUTH_SECRET` e `STRIPE_WEBHOOK_SECRET` e não defina `CHERISH_DEMO`.
