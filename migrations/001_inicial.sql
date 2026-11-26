-- Esquema inicial da Cherish. Nenhum dado sensivel (CPF, cartao, chave PIX) tem coluna (RNF03 / RN06).
CREATE TABLE IF NOT EXISTS usuarios (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  nome TEXT NOT NULL,
  email TEXT NOT NULL UNIQUE,              -- RN01
  telefone TEXT NOT NULL,
  tipo TEXT NOT NULL CHECK (tipo IN ('comum','vendedor')),
  endereco_padrao TEXT,
  senha_hash TEXT NOT NULL,
  foto TEXT,
  status TEXT NOT NULL DEFAULT 'ativo'
);
CREATE TABLE IF NOT EXISTS preferencias (
  usuario_id INTEGER PRIMARY KEY REFERENCES usuarios(id) ON DELETE CASCADE,
  dados_cifrados TEXT NOT NULL             -- JSON cifrado pelo Vault (RNF04)
);
CREATE TABLE IF NOT EXISTS produtos (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  vendedor_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
  nome TEXT NOT NULL,
  descricao TEXT NOT NULL,
  categoria TEXT NOT NULL DEFAULT 'Geral',
  preco REAL NOT NULL CHECK (preco >= 0),
  promocao_pct INTEGER NOT NULL DEFAULT 0,
  estoque INTEGER NOT NULL DEFAULT 0 CHECK (estoque >= 0),
  imagens TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL DEFAULT 'ativo'
);
CREATE TABLE IF NOT EXISTS comprovantes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  produto_id INTEGER NOT NULL REFERENCES produtos(id) ON DELETE CASCADE,
  tipo TEXT NOT NULL, referencia TEXT NOT NULL, data TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS itens_carrinho (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
  produto_id INTEGER NOT NULL REFERENCES produtos(id) ON DELETE CASCADE,
  quantidade INTEGER NOT NULL DEFAULT 1,
  UNIQUE (usuario_id, produto_id)          -- carrinho individual (RF34)
);
CREATE TABLE IF NOT EXISTS pedidos (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  comprador_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
  endereco_entrega TEXT NOT NULL, data_hora TEXT NOT NULL, total REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS itens_pedido (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  pedido_id INTEGER NOT NULL REFERENCES pedidos(id) ON DELETE CASCADE,
  produto_id INTEGER NOT NULL REFERENCES produtos(id),
  nome_produto TEXT NOT NULL,
  preco_unitario REAL NOT NULL, quantidade INTEGER NOT NULL,
  status TEXT NOT NULL DEFAULT 'Pendente'
    CHECK (status IN ('Entregue','Pendente','Perdido','Reembolso solicitado')),
  local_atual TEXT NOT NULL DEFAULT 'Fortaleza, Ceará - Centro de distribuição',
  previsao TEXT NOT NULL,
  entregador_ok INTEGER NOT NULL DEFAULT 0, cliente_ok INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS pagamentos (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  comprador_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
  pedido_id INTEGER REFERENCES pedidos(id),
  forma TEXT NOT NULL CHECK (forma IN ('pix','cartao')),
  status TEXT NOT NULL DEFAULT 'pendente',  -- pendente, aprovado, recusado, expirado
  valor REAL NOT NULL,
  referencia_stripe TEXT NOT NULL UNIQUE,   -- idempotencia (7.7)
  expira_em TEXT, endereco TEXT NOT NULL,
  itens_json TEXT NOT NULL, codigo_pix TEXT, recibo_enviado INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS reembolsos (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  item_pedido_id INTEGER NOT NULL UNIQUE REFERENCES itens_pedido(id),  -- RN02
  status TEXT NOT NULL DEFAULT 'solicitado', data TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS avaliacoes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  produto_id INTEGER NOT NULL REFERENCES produtos(id) ON DELETE CASCADE,
  usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
  nota INTEGER NOT NULL CHECK (nota BETWEEN 1 AND 5),
  comentario TEXT NOT NULL DEFAULT '', exibir_nome INTEGER NOT NULL DEFAULT 1, data TEXT NOT NULL,
  UNIQUE (produto_id, usuario_id)
);
CREATE TABLE IF NOT EXISTS acessos_recentes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
  produto_id INTEGER NOT NULL REFERENCES produtos(id) ON DELETE CASCADE,
  data TEXT NOT NULL, UNIQUE (usuario_id, produto_id)
);
CREATE TABLE IF NOT EXISTS notificacoes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  vendedor_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
  pedido_id INTEGER, mensagem TEXT NOT NULL, lida INTEGER NOT NULL DEFAULT 0, data TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS emails_enviados (   -- caixa de saida do Postmark simulado
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  destinatario TEXT NOT NULL, assunto TEXT NOT NULL, corpo TEXT NOT NULL, data TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS tokens_senha (
  token TEXT PRIMARY KEY, usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE, expira_em TEXT NOT NULL
);
