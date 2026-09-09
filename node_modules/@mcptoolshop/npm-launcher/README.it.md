<p align="center">
  <a href="README.ja.md">日本語</a> | <a href="README.zh.md">中文</a> | <a href="README.es.md">Español</a> | <a href="README.fr.md">Français</a> | <a href="README.hi.md">हिन्दी</a> | <a href="README.md">English</a> | <a href="README.pt-BR.md">Português (BR)</a>
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

Un launcher binario generico per GitHub, compatibile con npm. Scarica i file binari specifici per la piattaforma da GitHub Releases, li memorizza localmente, verifica gli hash SHA256 e li esegue, passando tutti gli argomenti.

Progettato per consentire alle interfacce a riga di comando (CLI) Python (o a qualsiasi binario compilato) di avere una distribuzione `npx` senza dipendenze.

## Sicurezza e modello di minacce

`npm-launcher` scarica ed esegue binari. Ecco cosa tocca e cosa non tocca:

- **Rete:** Solo HTTPS, verso `github.com` e la CDN di GitHub. Nessuna altra destinazione.
- **File system:** Scrive solo nella cache locale (`~/.cache/mcptoolshop/` o `%LOCALAPPDATA%\mcptoolshop\`). Non modifica file di sistema né legge al di fuori della cache.
- **Verifica:** Ogni binario viene controllato rispetto all'hash SHA256 presente in un file `checksums-<version>.txt` nella stessa release. In caso di incongruenze, l'esecuzione viene interrotta e il file scaricato viene eliminato.
- **Nessuna telemetria.** Nessuna gestione di segreti. Nessuna credenziale memorizzata o trasmessa.
- **Permessi:** Non sono richiesti permessi speciali, oltre all'accesso normale al file system dell'utente e alla possibilità di effettuare connessioni HTTPS in uscita.

## Come funziona

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

## Installazione

```bash
npm install @mcptoolshop/npm-launcher
```

Questo pacchetto è una libreria per pacchetti wrapper: gli utenti finali installano il wrapper (ad esempio, `npx @mcptoolshop/sovereignty`), non questo direttamente.

## Contratto di configurazione

I wrapper passano solo JSON tramite la variabile `MCPTOOLSHOP_LAUNCH_CONFIG`. Nessuna funzione, nessuna magia.

| Campo | Obbligatorio | Esempio | Descrizione |
|------------|----------|------------------------|--------------------------------------|
| `toolName` | sì | `"sovereignty"`        | Nome base del binario |
| `owner`    | sì | `"mcp-tool-shop-org"`  | Organizzazione/utente GitHub |
| `repo`     | sì | `"sovereignty"`        | Nome del repository GitHub |
| `version`  | sì | `"1.4.0"`              | Semver (senza il prefisso `v`) |
| `tag`      | no       | `"v1.4.0"`             | Tag Git (il valore predefinito è `v<versione>`) |
| `quiet`    | no       | `true`                 | Sopprimi i messaggi di avanzamento |

## Convenzione di denominazione dei file

Fissato. Tutti gli strumenti seguono lo stesso schema:

```
<toolName>-<version>-<os>-<arch><ext>
```

| Piattaforma | File di esempio |
|---------------|--------------------------------------|
| Linux x64 | `sovereignty-1.4.0-linux-x64`        |
| macOS ARM | `sovereignty-1.4.0-darwin-arm64`     |
| macOS Intel | `sovereignty-1.4.0-darwin-x64`       |
| Windows x64 | `sovereignty-1.4.0-win-x64.exe`     |

File degli hash: `checksums-<versione>.txt` (formato GNU coreutils).

## Creazione di un wrapper

Un wrapper è un piccolo pacchetto npm (circa 3 file):

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

Consulta la cartella `examples/` per modelli di wrapper completi e per il flusso di lavoro CI.

## Variabili d'ambiente

| Variabile | Effetto |
|----------|--------|
| `MCPTOOLSHOP_LAUNCHER_QUIET=1` | Sopprimi i messaggi di avanzamento (gli errori vengono comunque visualizzati) |

## Piattaforme supportate

- Linux x64
- macOS ARM64 (Apple Silicon)
- macOS x64 (Intel)
- Windows x64

## Posizione della cache

| OS      | Percorso |
|---------|----------------------------------------------|
| Linux | `~/.cache/mcptoolshop/<tool>/<version>/`     |
| macOS | `~/.cache/mcptoolshop/<tool>/<version>/`     |
| Windows | `%LOCALAPPDATA%\mcptoolshop\<tool>\<version>\` |

---

Creato da <a href="https://mcp-tool-shop.github.io/">MCP Tool Shop</a>
