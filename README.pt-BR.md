<p align="center">
  <a href="README.ja.md">日本語</a> | <a href="README.zh.md">中文</a> | <a href="README.es.md">Español</a> | <a href="README.fr.md">Français</a> | <a href="README.hi.md">हिन्दी</a> | <a href="README.it.md">Italiano</a> | <a href="README.md">English</a>
</p>

<p align="center">
  <img src="https://raw.githubusercontent.com/mcp-tool-shop-org/brand/main/logos/xrpl-camp/readme.png" width="400" alt="XRPL Camp">
</p>

<p align="center">
  <a href="https://github.com/mcp-tool-shop-org/xrpl-camp/actions/workflows/ci.yml"><img src="https://github.com/mcp-tool-shop-org/xrpl-camp/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue" alt="MIT License"></a>
  <a href="https://mcp-tool-shop-org.github.io/xrpl-camp/"><img src="https://img.shields.io/badge/Landing_Page-live-blue" alt="Landing Page"></a>
</p>

Aprenda sobre o XRPL (XRP Ledger) em uma única sessão. Sem contas. Sem dinheiro real. Apenas você e o ledger.

O XRPL Camp o guia por 6 lições — desde "o que é um ledger?" até uma carteira com saldo, um pagamento confirmado e um certificado portátil — em cerca de 10 minutos.

## Instalação

```bash
pipx install xrpl-camp
```

Ou com pip:

```bash
pip install xrpl-camp
```

## Início Rápido

```bash
xrpl-camp start
```

Isso executa o fluxo guiado por todas as 6 lições:

1. **Modelo Mental** — O que é o XRPL (contas, saldos, transações, mensagens)
2. **Criar Carteira** — Gere um par de chaves para a Testnet
3. **Adicionar Saldo** — Obtenha XRP de teste gratuitos a partir da "faucet" (serviço que fornece pequenas quantidades de criptomoedas para testes)
4. **Enviar Pagamento** — Escreva uma mensagem para o ledger (pagamento para si mesmo, 1 "gota")
5. **Verificar Transação** — Veja o que você escreveu
6. **Certificado** — Obtenha um registro portátil e verificável do que você fez

## Comandos

| Comando | O que ele faz |
|---------|-------------|
| `xrpl-camp start` | Fluxo guiado por todas as 6 lições |
| `xrpl-camp start --dry-run` | Executa o fluxo completo sem chamadas de rede |
| `xrpl-camp wallet create` | Cria uma carteira para a Testnet |
| `xrpl-camp wallet show` | Exibe o endereço da sua carteira |
| `xrpl-camp fund` | Adiciona saldo à sua carteira através da "faucet" da Testnet |
| `xrpl-camp fund --dry-run` | Simula o que adicionar saldo faria, sem chamadas de rede |
| `xrpl-camp send --memo "hello"` | Envia um pagamento para si mesmo com uma mensagem personalizada |
| `xrpl-camp send --dry-run` | Simula o pagamento |
| `xrpl-camp verify --tx <hash>` | Verifica uma transação no ledger |
| `xrpl-camp certificate` | Gera certificado + pacote de provas |
| `xrpl-camp reset` | Limpa todo o estado (requer confirmação manual) |

## O que você obtém

- Uma carteira da Testnet com saldo (`.xrpl-camp/wallet.json` — local, ignorada pelo Git)
- Um pagamento confirmado na XRPL Testnet
- Um relatório de verificação mostrando exatamente o que o ledger registrou
- Um certificado (`xrpl_camp_certificate.json`) — seguro para compartilhar, sem chaves privadas
- Um pacote de provas (`xrpl_camp_proof_pack.json`) — com detecção de adulteração, hash SHA-256

## Modo de Teste (Dry-Run)

Todos os comandos que acessam a rede suportam `--dry-run`. Ele imprime o que aconteceria sem fazer chamadas de rede ou alterar o estado. Útil para ganhar confiança e depurar.

## Pacote de Provas

O pacote de provas é um registro inviolável de tudo o que você fez:

- Endereço da carteira e rede
- Marcas de tempo de conclusão das lições
- IDs de transações com URLs do explorador
- Versão da ferramenta
- Hash SHA-256 do conteúdo inteiro

Qualquer pessoa pode verificar o hash para confirmar que o arquivo não foi editado.

## Substituição do Endpoint

Por padrão, o XRPL Camp usa o nó público da XRPL Testnet. Para usar um endpoint diferente:

```bash
export XRPL_CAMP_RPC_URL="https://your-node:51234/"
xrpl-camp fund
```

## Segurança

Sua "seed" (chave privada) é armazenada localmente e nunca é incluída no certificado ou no pacote de provas.
Esta ferramenta usa apenas a **Testnet** do XRPL — o XRP de teste não tem valor real.
Não há telemetria, não há análise, não há envio de dados — as únicas chamadas de rede são para a XRPL Testnet.

Veja [SECURITY.md](SECURITY.md) para detalhes.

## Modelo de Ameaças

| Ameaça | Mitigação |
|--------|-----------|
| Vazamento da "seed" através do certificado | A geração do certificado exclui explicitamente a "seed"; verificação de segurança `certificate_has_seed()` |
| Vazamento da "seed" através do pacote de provas | A geração do pacote de provas exclui a "seed"; verificação de segurança `proof_pack_has_seed()` |
| "Seed" no Git | `.xrpl-camp/` é ignorada pelo Git; o comando `wallet show` nunca exibe a "seed" |
| Reutilização da "seed" da Testnet na Mainnet | Um aviso é exibido durante a criação da carteira |
| Exposição do conteúdo da mensagem | Todas as mensagens são públicas por design; os usuários são avisados antes de enviar |
| Adulteração do pacote de provas | Hash de integridade SHA-256; `verify_proof_pack()` detecta modificações |

## Desenvolvimento

```bash
git clone https://github.com/mcp-tool-shop-org/xrpl-camp.git
cd xrpl-camp
uv sync --dev
uv run ruff check .
uv run pytest tests/ -v
```

## Licença

MIT

---

Desenvolvido por [MCP Tool Shop](https://mcp-tool-shop.github.io/).
