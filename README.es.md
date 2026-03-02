<p align="center">
  <a href="README.ja.md">日本語</a> | <a href="README.zh.md">中文</a> | <a href="README.md">English</a> | <a href="README.fr.md">Français</a> | <a href="README.hi.md">हिन्दी</a> | <a href="README.it.md">Italiano</a> | <a href="README.pt-BR.md">Português (BR)</a>
</p>

<p align="center">
  <img src="https://raw.githubusercontent.com/mcp-tool-shop-org/brand/main/logos/xrpl-camp/readme.png" width="400" alt="XRPL Camp">
</p>

<p align="center">
  <a href="https://github.com/mcp-tool-shop-org/xrpl-camp/actions/workflows/ci.yml"><img src="https://github.com/mcp-tool-shop-org/xrpl-camp/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue" alt="MIT License"></a>
  <a href="https://mcp-tool-shop-org.github.io/xrpl-camp/"><img src="https://img.shields.io/badge/Landing_Page-live-blue" alt="Landing Page"></a>
</p>

Aprende sobre el Ledger de XRP en una sola sesión. Sin cuentas. Sin dinero real. Solo tú y el ledger.

XRPL Camp te guía a través de 6 lecciones, desde "¿qué es un ledger?" hasta una billetera con fondos, un pago confirmado y un certificado portátil, en aproximadamente 10 minutos.

## Instalación

```bash
pipx install xrpl-camp
```

O con pip:

```bash
pip install xrpl-camp
```

## Inicio rápido

```bash
xrpl-camp start
```

Esto ejecuta el flujo guiado a través de las 6 lecciones:

1. **Modelo mental** — Qué es el XRPL (cuentas, saldos, transacciones, mensajes)
2. **Crear billetera** — Genera un par de claves de Testnet
3. **Fondear billetera** — Obtén XRP de prueba gratuitos desde el "faucet"
4. **Enviar pago** — Escribe un mensaje al ledger (pago a ti mismo, 1 unidad)
5. **Verificar transacción** — Busca lo que escribiste
6. **Certificado** — Obtén un registro portátil y verificable de lo que hiciste

## Comandos

| Comando | Lo que hace |
|---------|-------------|
| `xrpl-camp start` | Flujo guiado a través de las 6 lecciones |
| `xrpl-camp start --dry-run` | Realiza el flujo completo sin llamadas a la red |
| `xrpl-camp wallet create` | Crea una billetera de Testnet |
| `xrpl-camp wallet show` | Muestra la dirección de tu billetera |
| `xrpl-camp fund` | Fondear tu billetera a través del "faucet" de Testnet |
| `xrpl-camp fund --dry-run` | Ver lo que haría el "fondear", sin conexión a la red |
| `xrpl-camp send --memo "hello"` | Envía un pago a ti mismo con un mensaje personalizado |
| `xrpl-camp send --dry-run` | Simula el pago |
| `xrpl-camp verify --tx <hash>` | Verifica una transacción en el ledger |
| `xrpl-camp certificate` | Genera certificado + paquete de prueba |
| `xrpl-camp reset` | Borra todo el estado (requiere confirmación manual) |

## Lo que obtendrás

- Una billetera de Testnet con fondos (`.xrpl-camp/wallet.json` — local, ignorada por Git)
- Un pago confirmado en el Testnet de XRPL
- Un informe de verificación que muestra exactamente lo que el ledger registró
- Un certificado (`xrpl_camp_certificate.json`) — seguro para compartir, sin claves privadas
- Un paquete de prueba (`xrpl_camp_proof_pack.json`) — con integridad verificable, con hash SHA-256

## Modo de prueba

Cada comando que se conecta a la red admite `--dry-run`. Imprime lo que sucedería sin realizar ninguna llamada a la red ni cambiar el estado. Útil para generar confianza y depurar.

## Paquete de prueba

El paquete de prueba es un registro con integridad verificable de todo lo que hiciste:

- Dirección de la billetera y red
- Marcas de tiempo de finalización de la lección
- IDs de transacciones con URL de explorador
- Versión de la herramienta
- Hash SHA-256 de todo el contenido

Cualquiera puede verificar el hash para confirmar que el archivo no se ha editado.

## Anulación del punto final

Por defecto, XRPL Camp utiliza el nodo público de Testnet de XRPL. Para usar un punto final diferente:

```bash
export XRPL_CAMP_RPC_URL="https://your-node:51234/"
xrpl-camp fund
```

## Seguridad

Tu semilla (clave privada) se almacena localmente y nunca se incluye en el certificado o el paquete de prueba.
Esta herramienta solo utiliza el **Testnet** de XRPL — el XRP de prueba no tiene valor real.
No hay telemetría, ni análisis, ni "envío de información" — las únicas llamadas a la red se realizan al Testnet de XRPL.

Consulta [SECURITY.md](SECURITY.md) para obtener más detalles.

## Modelo de amenazas

| Amenaza | Mitigación |
|--------|-----------|
| Fuga de la semilla a través del certificado | La generación del certificado excluye explícitamente la semilla; verificación de seguridad `certificate_has_seed()` |
| Fuga de la semilla a través del paquete de prueba | La generación del paquete de prueba excluye la semilla; verificación de seguridad `proof_pack_has_seed()` |
| Semilla en Git | `.xrpl-camp/` está ignorada por Git; `wallet show` nunca muestra la semilla |
| Reutilización de la semilla de Testnet en Mainnet | Se muestra una advertencia durante la creación de la billetera |
| Exposición del contenido del mensaje | Todos los mensajes son públicos por diseño; se advierte a los usuarios antes de enviar |
| Manipulación del paquete de prueba | Hash de integridad SHA-256; `verify_proof_pack()` detecta modificaciones |

## Desarrollo

```bash
git clone https://github.com/mcp-tool-shop-org/xrpl-camp.git
cd xrpl-camp
uv sync --dev
uv run ruff check .
uv run pytest tests/ -v
```

## Licencia

MIT

---

Creado por [MCP Tool Shop](https://mcp-tool-shop.github.io/).
