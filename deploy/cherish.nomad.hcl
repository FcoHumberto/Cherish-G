# Job do HashiCorp Nomad (seção 8). Várias instâncias para atender RNF05; segredos vêm do Vault.
job "cherish" {
  datacenters = ["dc1"]
  group "web" {
    count = 3
    network { port "http" { to = 8000 } }
    task "app" {
      driver = "docker"
      config { image = "cherish:latest" ports = ["http"] }
      env { CHERISH_DEMO = "0" }
      # vault { policies = ["cherish"] }  # injete CHERISH_VAULT_KEY, CHERISH_SECRET, STRIPE_WEBHOOK_SECRET
      resources { cpu = 500 memory = 256 }
      service { name = "cherish" port = "http" check { type = "http" path = "/produtos" interval = "15s" timeout = "3s" } }
    }
  }
}
