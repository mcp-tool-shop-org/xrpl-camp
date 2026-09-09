<p align="center">
  <a href="README.ja.md">日本語</a> | <a href="README.zh.md">中文</a> | <a href="README.es.md">Español</a> | <a href="README.fr.md">Français</a> | <a href="README.hi.md">हिन्दी</a> | <a href="README.it.md">Italiano</a> | <a href="README.md">English</a>
</p>

<p align="center">
  <img src="https://raw.githubusercontent.com/mcp-tool-shop-org/brand/main/logos/npm-launcher/readme.png" width="400" alt="npm-launcher" />
</p>

<p align="center">
  <a href="https://github.com/mcp-tool-shop-org/npm-launcher/actions"><img src="https://github.com/mcp-tool-shop-org/npm-launcher/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://www.npmjs.com/package/@mcptoolshop/npm-launcher"><img src="https://img.shields.io/npm/v/@mcptoolshop/npm-launcher" alt="npm version"></a>
  <a href="https://github.com/mcp-tool-shop-org/npm-launcher/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue" alt="License"></a>
  <a href="https://mcp-tool-shop-org.github.io/npm-launcher/"><img src="https://img.shields.io/badge/Landing_Page-live-blue" alt="Landing Page"></a>
</p>

Lançador binário genérico para o npm, compatível com o GitHub. Ele baixa arquivos binários específicos para cada plataforma a partir das versões do GitHub, os armazena localmente, verifica as somas de verificação SHA256 e os executa, passando todos os argumentos.

Criado para que CLIs em Python (ou qualquer binário compilado) tenham uma distribuição `npx` sem dependências.

## Segurança e Modelo de Ameaças

O `npm-launcher` baixa e executa binários. Veja o que ele acessa e o que não acessa:

- **Rede:** Apenas HTTPS, para `github.com` e a CDN do GitHub. Nenhum outro destino.
- **Sistema de arquivos:** Escreve apenas no cache local (`~/.cache/mcptoolshop/` ou `%LOCALAPPDATA%\mcptoolshop\`). Não modifica arquivos do sistema nem lê dados fora do cache.
- **Verificação:** Cada binário é verificado em relação à soma SHA256 de um arquivo `checksums-<versão>.txt` na mesma versão. Se houver incompatibilidades, a execução é interrompida e o arquivo baixado é excluído.
- **Sem telemetria.** Sem tratamento de segredos. Nenhuma credencial é armazenada ou transmitida.
- **Permissões:** Nenhuma permissão especial é necessária, além do acesso normal do usuário ao sistema de arquivos e à conexão HTTPS de saída.

## Como Funciona

```
npx @mcptoolshop/sovereignty tutorial
        │
        ▼
  wrapper sets config JSON
        │
        ▼
  npm-launcher resolves platform (linux-x64, darwin-arm64, etc.)
        │
        ▼
  checks local cache (~/.cache/mcptoolshop/<tool>/<version>/)
        │
        ├─ cached → run binary
        │
        └─ not cached:
             fetch checksums-<version>.txt from GitHub Release
             download <tool>-<version>-<os>-<arch>[.exe]
             verify SHA256
             cache + chmod +x
             run binary
```

## Instalação

```bash
npm install @mcptoolshop/npm-launcher
```

Este pacote é uma biblioteca para pacotes de wrapper. Os usuários finais instalam o wrapper (por exemplo, `npx @mcptoolshop/sovereignty`), e não este pacote diretamente.

## Contrato de Configuração

Os wrappers passam JSON puro através de `MCPTOOLSHOP_LAUNCH_CONFIG`. Sem funções, sem "mágica".

| Campo | Obrigatório | Exemplo | Descrição |
|------------|----------|------------------------|--------------------------------------|
| `toolName` | sim | `"sovereignty"`        | Nome base do binário |
| `owner`    | sim | `"mcp-tool-shop-org"`  | Organização/usuário do GitHub |
| `repo`     | sim | `"sovereignty"`        | Nome do repositório do GitHub |
| `version`  | sim | `"1.4.0"`              | Semver (sem o prefixo `v`) |
| `tag`      | no       | `"v1.4.0"`             | Tag do Git (o padrão é `v<versão>`) |
| `quiet`    | no       | `true`                 | Suprimir mensagens de progresso |

## Convenção de Nomenclatura de Arquivos

Fixa. Todas as ferramentas seguem o mesmo padrão:

```
<toolName>-<version>-<os>-<arch><ext>
```

| Plataforma | Arquivo de Exemplo |
|---------------|--------------------------------------|
| Linux x64 | `sovereignty-1.4.0-linux-x64`        |
| macOS ARM | `sovereignty-1.4.0-darwin-arm64`     |
| macOS Intel | `sovereignty-1.4.0-darwin-x64`       |
| Windows x64 | `sovereignty-1.4.0-win-x64.exe`     |

Arquivo de checksums: `checksums-<versão>.txt` (formato GNU coreutils).

## Criando um Wrapper

Um wrapper é um pacote npm pequeno (~3 arquivos):

**package.json:**
```json
{
  "name": "@mcptoolshop/sovereignty",
  "version": "1.4.0",
  "bin": { "sovereignty": "bin/sovereignty.js" },
  "dependencies": { "@mcptoolshop/npm-launcher": "^1.0.0" }
}
```

**bin/sovereignty.js:**
```js
#!/usr/bin/env node
process.env.MCPTOOLSHOP_LAUNCH_CONFIG = JSON.stringify({
  toolName: "sovereignty",
  owner: "mcp-tool-shop-org",
  repo: "sovereignty",
  version: "1.4.0",
});
require("@mcptoolshop/npm-launcher/bin/mcptoolshop-launch.js");
```

Veja a pasta `examples/` para modelos de wrappers completos e fluxo de trabalho de CI.

## Variáveis de Ambiente

| Variável | Efeito |
|----------|--------|
| `MCPTOOLSHOP_LAUNCHER_QUIET=1` | Suprimir mensagens de progresso (erros ainda são exibidos) |

## Plataformas Suportadas

- Linux x64
- macOS ARM64 (Apple Silicon)
- macOS x64 (Intel)
- Windows x64

## Localização do Cache

| OS      | Caminho |
|---------|----------------------------------------------|
| Linux | `~/.cache/mcptoolshop/<tool>/<version>/`     |
| macOS | `~/.cache/mcptoolshop/<tool>/<version>/`     |
| Windows | `%LOCALAPPDATA%\mcptoolshop\<tool>\<version>\` |

---

Criado por <a href="https://mcp-tool-shop.github.io/">MCP Tool Shop</a>
