<p align="center">
  <a href="README.ja.md">日本語</a> | <a href="README.zh.md">中文</a> | <a href="README.md">English</a> | <a href="README.fr.md">Français</a> | <a href="README.hi.md">हिन्दी</a> | <a href="README.it.md">Italiano</a> | <a href="README.pt-BR.md">Português (BR)</a>
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

Lanzador binario genérico para npm que se descarga desde GitHub. Descarga archivos binarios específicos de la plataforma desde las versiones de GitHub, los almacena localmente, verifica las sumas de verificación SHA256 y los ejecuta con la transmisión completa de argumentos.

Diseñado para que las interfaces de línea de comandos (CLI) de Python (o cualquier binario compilado) tengan una distribución de `npx` sin dependencias.

## Seguridad y modelo de amenazas

`npm-launcher` descarga y ejecuta binarios. Aquí está lo que toca y lo que no:

- **Red:** Solo HTTPS, a `github.com` y al CDN de GitHub. No hay otros destinos.
- **Sistema de archivos:** Escribe solo en la caché local (`~/.cache/mcptoolshop/` o `%LOCALAPPDATA%\mcptoolshop\`). No modifica archivos del sistema ni lee fuera de la caché.
- **Verificación:** Cada binario se verifica contra SHA256 de un archivo `checksums-<version>.txt` en la misma versión. Las discrepancias interrumpen la ejecución y eliminan el archivo descargado.
- **Sin telemetría.** No hay manejo de secretos. No se almacenan ni transmiten credenciales.
- **Permisos:** No se requieren permisos adicionales más allá del acceso normal del usuario al sistema de archivos y al HTTPS de salida.

## Cómo funciona

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

## Instalación

```bash
npm install @mcptoolshop/npm-launcher
```

Este paquete es una biblioteca para paquetes de envoltura; los usuarios finales instalan el envoltura (por ejemplo, `npx @mcptoolshop/sovereignty`), no esto directamente.

## Contrato de configuración

Los envolturas pasan JSON puro a través de `MCPTOOLSHOP_LAUNCH_CONFIG`. Sin funciones, sin trucos.

| Campo | Requerido | Ejemplo | Descripción |
|------------|----------|------------------------|--------------------------------------|
| `toolName` | sí | `"sovereignty"`        | Nombre base del binario |
| `owner`    | sí | `"mcp-tool-shop-org"`  | Organización/usuario de GitHub |
| `repo`     | sí | `"sovereignty"`        | Nombre del repositorio de GitHub |
| `version`  | sí | `"1.4.0"`              | Semver (sin prefijo `v`) |
| `tag`      | no       | `"v1.4.0"`             | Etiqueta de Git (por defecto a `v<version>`) |
| `quiet`    | no       | `true`                 | Suprimir mensajes de progreso |

## Convención de nombres de archivos

Bloqueado. Todas las herramientas siguen el mismo patrón:

```
<toolName>-<version>-<os>-<arch><ext>
```

| Plataforma | Archivo de ejemplo |
|---------------|--------------------------------------|
| Linux x64 | `sovereignty-1.4.0-linux-x64`        |
| macOS ARM | `sovereignty-1.4.0-darwin-arm64`     |
| macOS Intel | `sovereignty-1.4.0-darwin-x64`       |
| Windows x64 | `sovereignty-1.4.0-win-x64.exe`     |

Archivo de sumas de verificación: `checksums-<version>.txt` (formato de GNU coreutils).

## Creación de un envoltura

Un envoltura es un paquete npm pequeño (~3 archivos):

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

Consulte `examples/` para obtener plantillas de envoltura completas y flujo de trabajo de CI.

## Variables de entorno

| Variable | Efecto |
|----------|--------|
| `MCPTOOLSHOP_LAUNCHER_QUIET=1` | Suprimir mensajes de progreso (los errores aún se imprimen) |

## Plataformas compatibles

- Linux x64
- macOS ARM64 (Apple Silicon)
- macOS x64 (Intel)
- Windows x64

## Ubicación de la caché

| OS      | Ruta |
|---------|----------------------------------------------|
| Linux | `~/.cache/mcptoolshop/<tool>/<version>/`     |
| macOS | `~/.cache/mcptoolshop/<tool>/<version>/`     |
| Windows | `%LOCALAPPDATA%\mcptoolshop\<tool>\<version>\` |

---

Creado por <a href="https://mcp-tool-shop.github.io/">MCP Tool Shop</a>
