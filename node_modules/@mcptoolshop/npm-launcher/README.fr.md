<p align="center">
  <a href="README.ja.md">日本語</a> | <a href="README.zh.md">中文</a> | <a href="README.es.md">Español</a> | <a href="README.md">English</a> | <a href="README.hi.md">हिन्दी</a> | <a href="README.it.md">Italiano</a> | <a href="README.pt-BR.md">Português (BR)</a>
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

Lanceur binaire générique pour npm, compatible avec GitHub. Il télécharge les binaires spécifiques à la plateforme depuis les versions de GitHub, les met en cache localement, vérifie les sommes de contrôle SHA256 et les exécute avec la transmission complète des arguments.

Conçu pour que les interfaces en ligne de commande Python (ou tout binaire compilé) disposent d'une distribution `npx` sans dépendances.

## Sécurité et modèle de menace

`npm-launcher` télécharge et exécute des binaires. Voici ce qu'il touche et ce qu'il ne touche pas :

- **Réseau :** Uniquement HTTPS, vers `github.com` et le CDN de GitHub. Aucune autre destination.
- **Système de fichiers :** Écrit uniquement dans le cache local (`~/.cache/mcptoolshop/` ou `%LOCALAPPDATA%\mcptoolshop\`). Ne modifie pas les fichiers système et ne lit rien en dehors du cache.
- **Vérification :** Chaque binaire est vérifié par rapport à une somme de contrôle SHA256 provenant d'un fichier `checksums-<version>.txt` dans la même version. Toute incohérence interrompt l'exécution et supprime le fichier téléchargé.
- **Pas de télémétrie.** Aucune gestion de secrets. Aucune information d'identification stockée ou transmise.
- **Permissions :** Aucune permission requise, au-delà de l'accès normal aux fichiers système de l'utilisateur et de la connexion HTTPS sortante.

## Fonctionnement

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

## Installation

```bash
npm install @mcptoolshop/npm-launcher
```

Ce paquet est une bibliothèque pour les paquets d'enveloppe. Les utilisateurs finaux installent l'enveloppe (par exemple, `npx @mcptoolshop/sovereignty`), et non ce paquet directement.

## Contrat de configuration

Les enveloppes transmettent uniquement du JSON via `MCPTOOLSHOP_LAUNCH_CONFIG`. Pas de fonctions, pas de magie.

| Champ | Obligatoire | Exemple | Description |
|------------|----------|------------------------|--------------------------------------|
| `toolName` | oui | `"sovereignty"`        | Nom de base du binaire |
| `owner`    | oui | `"mcp-tool-shop-org"`  | Organisation/utilisateur GitHub |
| `repo`     | oui | `"sovereignty"`        | Nom du dépôt GitHub |
| `version`  | oui | `"1.4.0"`              | Semver (sans le préfixe `v`) |
| `tag`      | no       | `"v1.4.0"`             | Balise Git (par défaut : `v<version>`) |
| `quiet`    | no       | `true`                 | Supprimer les messages de progression |

## Convention de nommage des fichiers

Fixe. Tous les outils suivent le même schéma :

```
<toolName>-<version>-<os>-<arch><ext>
```

| Plateforme | Fichier exemple |
|---------------|--------------------------------------|
| Linux x64 | `sovereignty-1.4.0-linux-x64`        |
| macOS ARM | `sovereignty-1.4.0-darwin-arm64`     |
| macOS Intel | `sovereignty-1.4.0-darwin-x64`       |
| Windows x64 | `sovereignty-1.4.0-win-x64.exe`     |

Fichier de sommes de contrôle : `checksums-<version>.txt` (format GNU coreutils).

## Création d'une enveloppe

Une enveloppe est un petit paquet npm (environ 3 fichiers) :

**package.json :**
```json
{
  "name": "@mcptoolshop/sovereignty",
  "version": "1.4.0",
  "bin": { "sovereignty": "bin/sovereignty.js" },
  "dependencies": { "@mcptoolshop/npm-launcher": "^1.0.0" }
}
```

**bin/sovereignty.js :**
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

Consultez le répertoire `examples/` pour obtenir des modèles d'enveloppes complets et le flux de travail CI.

## Variables d'environnement

| Variable | Effet |
|----------|--------|
| `MCPTOOLSHOP_LAUNCHER_QUIET=1` | Supprimer les messages de progression (les erreurs sont toujours affichées) |

## Plateformes prises en charge

- Linux x64
- macOS ARM64 (Apple Silicon)
- macOS x64 (Intel)
- Windows x64

## Emplacement du cache

| OS      | Chemin |
|---------|----------------------------------------------|
| Linux | `~/.cache/mcptoolshop/<tool>/<version>/`     |
| macOS | `~/.cache/mcptoolshop/<tool>/<version>/`     |
| Windows | `%LOCALAPPDATA%\mcptoolshop\<tool>\<version>\` |

---

Créé par <a href="https://mcp-tool-shop.github.io/">MCP Tool Shop</a>
