<p align="center">
  <a href="README.ja.md">日本語</a> | <a href="README.zh.md">中文</a> | <a href="README.md">English</a> | <a href="README.fr.md">Français</a> | <a href="README.hi.md">हिन्दी</a> | <a href="README.it.md">Italiano</a> | <a href="README.pt-BR.md">Português (BR)</a>
</p>

<p align="center">
  <img src="https://raw.githubusercontent.com/mcp-tool-shop-org/brand/main/logos/xrpl-camp/readme.png" width="400" alt="XRPL Camp">
</p>

<p align="center">
  <a href="https://github.com/mcp-tool-shop-org/xrpl-camp/actions/workflows/ci.yml"><img src="https://github.com/mcp-tool-shop-org/xrpl-camp/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://pypi.org/project/xrpl-camp/"><img src="https://img.shields.io/pypi/v/xrpl-camp?label=PyPI" alt="PyPI version"></a>
  <a href="https://www.npmjs.com/package/@mcptoolshop/xrpl-camp"><img src="https://img.shields.io/npm/v/@mcptoolshop/xrpl-camp?label=npm" alt="npm version"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue" alt="MIT License"></a>
  <a href="https://mcp-tool-shop-org.github.io/xrpl-camp/"><img src="https://img.shields.io/badge/Landing_Page-live-blue" alt="Landing Page"></a>
</p>

Aprenda sobre el XRP Ledger en una sola sesión. Sin cuentas. Sin dinero real. Solo usted y el libro mayor.

La mayoría de los tutoriales de blockchain enseñan conceptos. XRPL Camp le permite _ponerlos en práctica_: crear una billetera, financiarla, escribir una nota permanente en un libro mayor público, verificarla de forma independiente y obtener un registro que cualquiera pueda consultar en el propio libro mayor. Todo el proceso dura unos diez minutos.

Diseñado para talleres, aulas y estudio individual. El flujo guiado se reanuda donde lo dejó, una lección fallida detiene la ejecución en lugar de fingir, y nada afirma que haya ocurrido algo que no sucedió.

## ¿Por qué esto en lugar de un tutorial genérico?

- **Transacciones reales, no diapositivas.** Escribe en un libro mayor real. Cuando la lección 5 dice "verifíquelo usted mismo", le proporciona un hash y un enlace a un explorador que cualquiera puede consultar.
- **Su pago crea una cuenta.** La lección 4 no es una transferencia de prueba; financia una segunda cuenta que no existía un momento antes, y cuyas claves también son suyas.
- **El fracaso es parte del plan de estudios.** `xrpl-camp try` provoca fallos a propósito en la red activa, luego le muestra qué fallos habrían tenido un costo y cuáles son gratuitos, *antes* de que presione enviar.
- **Prueba de que realmente puede verificar.** El paquete de prueba nombra transacciones reales y `proof verify --online` pregunta al libro mayor si realmente ocurrieron. Nadie puede falsificar esa parte.
- **Seguro por diseño.** Solo testnet. El XRP de prueba no tiene valor. Su semilla nunca sale de su máquina. Sin telemetría, sin análisis, sin cuentas.

## Instalación

**No se requiere Python** (descarga un binario precompilado):

```bash
npx @mcptoolshop/xrpl-camp start
```

Con Python:

```bash
pipx install xrpl-camp
```

En Docker, para talleres donde la instalación es lo más difícil:

```bash
docker run --rm -it -v "$PWD:/work" ghcr.io/mcp-tool-shop-org/xrpl-camp start
```

> Monte un volumen. Todo lo que cree (billetera, certificado, paquete de prueba) se escribe en `/work`, y un contenedor desmontado lo elimina al salir. La imagen le indica si se olvidó.

## Inicio rápido

```bash
xrpl-camp start
```

Seis lecciones, en orden, que se reanudan si reinicia:

1. **Modelo mental:** qué es el XRPL, preguntado a la red activa en lugar de afirmado.
2. **Crear billetera:** generar un par de claves de Testnet; la semilla permanece en su máquina.
3. **Financiar billetera:** XRP de prueba gratuito del grifo y por qué parte de él no se puede gastar.
4. **Enviar pago:** escriba su nota en el libro mayor, en un pago que crea una cuenta.
5. **Verificar transacción:** busque lo que escribió y compárelo con lo que escribió.
6. **Certificado:** un registro que guarda y puede probar.

## Comandos

| Comando | Qué hace |
|---------|-------------|
| `xrpl-camp start` | Flujo guiado a través de las 6 lecciones (se reanuda automáticamente) |
| `xrpl-camp start --memo "..."` | Proporcione el mensaje de la lección 4 por adelantado, para ejecuciones programadas o no interactivas |
| `xrpl-camp read` | Sus entradas, leídas **del libro mayor**, no de esta máquina |
| `xrpl-camp read <address>` | Lo que otra persona escribió. Sin clave, sin inicio de sesión, sin permiso |
| `xrpl-camp read <hash>` | Una transacción completa |
| `xrpl-camp try` | Provocar un fallo a propósito en la red activa. No firma nada, no cuesta nada |
| `xrpl-camp status` | Lista de verificación del progreso, con tiempos |
| `xrpl-camp status --detail` | Vista del facilitador: billetera, punto final, directorio de estado, siguiente paso |
| `xrpl-camp wallet create` / `show` | Crear o mostrar su billetera de Testnet |
| `xrpl-camp fund` | Financie su billetera a través del grifo de Testnet |
| `xrpl-camp send --memo "hello"` | Envíe un pago de nota a su buzón |
| `xrpl-camp verify --tx <hash>` | Verifique una transacción que **usted** envió |
| `xrpl-camp certificate` | Genere el certificado + paquete de prueba |
| `xrpl-camp proof verify <file>` | Verifique el hash de un paquete de prueba. Completamente fuera de línea |
| `xrpl-camp proof verify <file> --online` | También pregunte al libro mayor si las transacciones realmente ocurrieron |
| `xrpl-camp proof verify <folder>` | Verifique cada paquete en una carpeta, para facilitadores |
| `xrpl-camp reset` | Borre todo el estado (requiere escribir `RESET`) |
| `xrpl-camp self-check` | Diagnostique su entorno **y** su conexión con el libro mayor |
| `xrpl-camp support-bundle` | Escriba un archivo ZIP de diagnóstico para informes de errores |

Banderas globales: `--version`, `--dry-run`, `--yes` (no interactivo), `--verbose` (detalles técnicos sobre errores).

## Lo que obtendrá al final

- Una billetera de Testnet financiada, local y ignorada por Git
- Una **segunda cuenta que no existía hasta que su pago la creó**, y cuyas claves también son suyas
- Una nota que eligió, registrada permanentemente y legible de forma independiente
- Un certificado (`xrpl_camp_certificate.json`): seguro para compartir, sin claves privadas
- Un paquete de prueba (`xrpl_camp_proof_pack.json`): que nombra transacciones reales que cualquiera puede resolver

## Acerca de esa prueba

El paquete de prueba contiene un hash SHA-256. Ese hash detecta una edición accidental. **No** es una firma, y por sí solo no prueba que el paquete sea genuino; cualquiera puede cambiar un campo y volver a calcular el hash con la misma función pública que utiliza esta herramienta.

Lo que no se puede falsificar es el libro mayor:

```bash
xrpl-camp proof verify xrpl_camp_proof_pack.json --online
```

Este resuelve cada transacción que nombra el paquete y verifica que exista, que fue enviada por la dirección del paquete, que contiene la nota que afirma el paquete y que se cerró correctamente. Un paquete con una dirección reescrita pasa la verificación de hash fuera de línea y falla esta.

Dos detalles que vale la pena conocer, porque ambos son fáciles de equivocarse:

- La verificación siempre consulta el Testnet público (o `--rpc-url`), **nunca** el punto final que se indica dentro del paquete. Un paquete falsificado puede nombrar un servidor que controla su autor.
- El XRPL Testnet se restablece periódicamente. Cuando eso sucede, las transacciones honestas dejan de resolverse. El paquete registra el índice del libro mayor de cada transacción, por lo que un restablecimiento se informa como *no verificable* (salida 3) en lugar de como fraude (salida 1).

La verificación fuera de línea sigue siendo el valor predeterminado y no realiza llamadas a la red, por lo que todavía funciona en un avión o en una máquina de aula con acceso restringido.

## Modo de prueba

```bash
xrpl-camp start --dry-run
```

Sin llamadas a la red, sin escrituras en el disco y sin resultados engañosos: la lección 6 se niega explícitamente a generar artefactos. El modo de prueba puede *leer* el estado existente, pero nunca modifica nada.

## Punto final y estado

```bash
export XRPL_CAMP_RPC_URL="https://your-node:51234/"
```

La herramienta rechaza los puntos finales que no puede confirmar que son de Testnet, antes de firmar nada. Establezca `XRPL_CAMP_ALLOW_ANY_NETWORK=1` solo si comprende a qué está apuntando.

El estado se guarda de forma predeterminada en `./.xrpl-camp`; una sesión pertenece a la carpeta en la que se ejecutó. `XRPL_CAMP_HOME` anula esto, y `xrpl-camp status --detail` imprime la ruta absoluta resuelta.

## Seguridad

Su semilla se guarda localmente en `.xrpl-camp/wallet.json` (solo para el propietario en POSIX) y nunca se incluye en el certificado o en el paquete de prueba; la generación se niega a escribir un artefacto que contenga una.

De forma predeterminada, esta herramienta utiliza la red de prueba XRPL, donde las pruebas de XRP no tienen valor real, y rechaza los puntos finales que no son de la red de prueba a menos que se desactive explícitamente. No hay telemetría, ni análisis, ni comunicación con un servidor central.

Consulte [SECURITY.md](SECURITY.md).

## Modelo de amenazas

| Amenaza | Mitigación |
|--------|-----------|
| La semilla se filtró en un artefacto | La generación ejecuta una comprobación de la semilla basada en `decode_seed` de xrpl-py y **se niega a escribir el archivo** si falla. |
| La semilla se incluyó en git | `.xrpl-camp/` está ignorado por git *en este repositorio*; el estado se escribe en su directorio de trabajo, así que añádalo a su propio `.gitignore`. |
| La semilla es legible por otros usuarios | Archivo de la billetera 0600, directorio de estado 0700 en POSIX |
| Un usuario introduce un secreto en un memo público | El texto del memo se analiza en busca de cadenas con formato de semilla y se rechaza antes de enviarlo. |
| Se reutiliza una semilla de la red de prueba en la red principal | Se advierte al crear la billetera; la herramienta rechaza los puntos finales que no son de la red de prueba de forma predeterminada. |
| Manipulación del paquete de prueba | SHA-256 detecta ediciones superficiales; `--online` detecta una falsificación que se ha vuelto a sellar preguntando al libro mayor. |
| Verificación contra el punto final de un atacante | `--online` nunca utiliza el punto final que se indica en el paquete que se está probando. |
| Los diagnósticos filtran su identidad | `support-bundle` elimina el directorio de inicio y el nombre de la cuenta. |

## Para talleres y aulas

- **Un comando por alumno.** `npx`, `pipx` o el contenedor; no hay configuración compartida.
- **El fracaso es gratuito.** `xrpl-camp try` enseña los modos de fallo sin gastar nada, por lo que un alumno que rompe algo a propósito aprende más que uno que no lo hace.
- **Triaje del facilitador.** `status --detail` muestra la billetera, el punto final y el directorio de estado. `self-check` comprueba la conexión real en lugar de informar de un "OK" esperanzador.
- **Verifique toda la sala a la vez.** `proof verify <folder> --online` comprueba el paquete de cada alumno con el libro mayor.
- **Los límites de velocidad son reales.** Si treinta personas acceden a un mismo grifo, este se saturará; la herramienta reintenta con retroceso y lo indica en lugar de culpar a su wifi.

## Desarrollo

```bash
git clone https://github.com/mcp-tool-shop-org/xrpl-camp.git
cd xrpl-camp
uv sync --dev
bash scripts/verify.sh     # lint + tests + build + smoke
```

## Licencia

MIT

---

Creado por [MCP Tool Shop](https://mcp-tool-shop.github.io/)
