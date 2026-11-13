<p align="center">
  <a href="README.ja.md">日本語</a> | <a href="README.zh.md">中文</a> | <a href="README.es.md">Español</a> | <a href="README.fr.md">Français</a> | <a href="README.hi.md">हिन्दी</a> | <a href="README.md">English</a> | <a href="README.pt-BR.md">Português (BR)</a>
</p>

<p align="center">
  <img src="https://raw.githubusercontent.com/mcp-tool-shop-org/brand/main/logos/xrpl-camp/readme.png" width="400" alt="XRPL Camp">
</p>

<p align="center">
  <a href="https://github.com/mcp-tool-shop-org/xrpl-camp/actions/workflows/ci.yml"><img src="https://github.com/mcp-tool-shop-org/xrpl-camp/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://pypi.org/project/xrpl-camp/"><img src="https://img.shields.io/pypi/v/xrpl-camp?label=PyPI" alt="PyPI version"></a>
  <a href="https://www.npmjs.com/package/@mcptoolshop/xrpl-camp"><img src="https://img.shields.io/npm/v/@mcptoolshop/xrpl-camp?label=npm" alt="npm version"></a>
  <a href="https://codecov.io/gh/mcp-tool-shop-org/xrpl-camp"><img src="https://codecov.io/gh/mcp-tool-shop-org/xrpl-camp/branch/main/graph/badge.svg" alt="Coverage"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue" alt="MIT License"></a>
  <a href="https://mcp-tool-shop-org.github.io/xrpl-camp/"><img src="https://img.shields.io/badge/Landing_Page-live-blue" alt="Landing Page"></a>
</p>

Impara le basi di XRP Ledger in un’unica sessione. Nessuna registrazione. Nessun denaro reale. Solo tu e il registro contabile.

La maggior parte dei tutorial sulla blockchain insegna concetti. XRPL Camp ti permette di metterli in pratica: crea un portafoglio, alimentalo, scrivi una nota permanente in un libro mastro pubblico, verificala in modo indipendente e vai via con una registrazione che chiunque può confrontare con il libro mastro stesso. L'intero processo richiede circa dieci minuti.

Progettato per workshop, aule e studio individuale. Il flusso guidato riprende da dove si era interrotto, una lezione fallita interrompe l'esecuzione invece di fingere che tutto sia andato bene e nulla afferma che sia successo qualcosa che non è successo.

## Perché questo invece di un tutorial generico?

- **Transazioni reali, non diapositive.** Scrivi su un libro mastro reale. Quando la lezione 5 dice "verificalo tu stesso", ti fornisce un hash e un link a un esploratore che chiunque può controllare.
- **Il tuo pagamento crea un account.** La lezione 4 non è un trasferimento di prova: alimenta un secondo account che non esisteva un momento prima e le cui chiavi sono anche tue.
- **Il fallimento fa parte del programma.** `xrpl-camp try` provoca intenzionalmente errori sulla rete attiva, quindi ti mostra quali errori comporterebbero una perdita di denaro e quali sono gratuiti, *prima* che tu prema il pulsante di invio.
- **Prova che puoi effettivamente verificare.** Il pacchetto di prova indica transazioni reali e `proof verify --online` chiede al libro mastro se queste transazioni sono avvenute. Nessuno può falsificare questa parte.
- **Sicuro per progettazione.** Solo Testnet. Il test XRP non ha valore. Il tuo seed non lascia mai il tuo dispositivo. Nessun telemetria, nessuna analisi, nessun account.

## Installazione

**Non è necessario Python** (scarica un binario precompilato):

```bash
npx @mcptoolshop/xrpl-camp start
```

Con Python (3.11, 3.12 o 3.13):

```bash
pipx install xrpl-camp
```

In Docker, per workshop in cui l'installazione è la parte più difficile:

```bash
docker run --rm -it -v "$PWD:/work" ghcr.io/mcp-tool-shop-org/xrpl-camp start
```

> Monta un volume. Tutto ciò che crei (portafoglio, certificato, pacchetto di prova) viene scritto in `/work` e un contenitore smontato lo elimina all'uscita. L'immagine ti avvisa se hai dimenticato qualcosa.

## Avvio rapido

```bash
xrpl-camp start
```

Sei lezioni, in ordine, con ripresa in caso di riavvio:

1. **Modello mentale:** cos'è XRPL, chiesto alla rete attiva invece che affermato.
2. **Crea portafoglio:** genera una coppia di chiavi Testnet; il seed rimane sul tuo dispositivo.
3. **Finanzia il portafoglio:** ottieni XRP di prova gratuiti dal faucet e perché una parte di essi non è spendibile.
4. **Invia pagamento:** scrivi la tua nota nel libro mastro, in un pagamento che crea un account.
5. **Verifica transazione:** cerca ciò che hai scritto e confrontalo con ciò che hai digitato.
6. **Certificato:** una registrazione che conservi e che puoi provare.

## Comandi

| Comando | Cosa fa |
|---------|-------------|
| `xrpl-camp start` | Flusso guidato attraverso tutte le 6 lezioni (riprende automaticamente) |
| `xrpl-camp start --memo "..."` | Fornisci il messaggio della lezione 4 in anticipo, per esecuzioni scriptate o non interattive |
| `xrpl-camp read` | Le tue voci, lette **dal libro mastro** (e non da questa macchina) |
| `xrpl-camp read <address>` | Ciò che qualcun altro ha scritto. Nessuna chiave, nessun accesso, nessuna autorizzazione |
| `xrpl-camp read <hash>` | Una transazione completa |
| `xrpl-camp try` | Provoca intenzionalmente un errore sulla rete attiva. Non firma nulla, non costa nulla |
| `xrpl-camp reserve` | Crea e distruggi un NFT per osservare il blocco e il ritorno della riserva del proprietario |
| `xrpl-camp status` | Elenco di controllo dei progressi, con i tempi |
| `xrpl-camp status --detail` | Vista per il facilitatore: portafoglio, endpoint, directory di stato, passaggio successivo |
| `xrpl-camp wallet create` / `show` | Crea o visualizza il tuo portafoglio Testnet |
| `xrpl-camp fund` | Finanzia il tuo portafoglio tramite il faucet Testnet |
| `xrpl-camp send --memo "hello"` | Invia un pagamento con una nota alla tua casella di posta |
| `xrpl-camp verify --tx <hash>` | Verifica una transazione **che hai** inviato |
| `xrpl-camp certificate` | Genera il certificato + pacchetto di prova (`--format text` aggiunge un ricordo `.txt`) |
| `xrpl-camp proof verify <file>` | Verifica l'hash di un pacchetto di prova. Completamente offline |
| `xrpl-camp proof verify <file> --online` | Chiedi anche al libro mastro se le transazioni sono realmente avvenute (`--record` aggiunge una ricevuta datata) |
| `xrpl-camp proof verify <folder>` | Verifica tutti i pacchetti in una cartella, per i facilitatori |
| `xrpl-camp reset` | Cancella tutti i dati (richiede la digitazione di `RESET`) |
| `xrpl-camp self-check` | Diagnostica il tuo ambiente **e** la tua connessione al libro mastro |
| `xrpl-camp support-bundle` | Crea un file ZIP diagnostico per i rapporti sugli errori |

Flag globali: `--version`, `--dry-run`, `--yes` (non interattivo), `--verbose` (dettagli tecnici sugli errori).

## Cosa otterrai

- Un portafoglio Testnet finanziato, locale e ignorato da Git
- Un **secondo account che non esisteva fino a quando il tuo pagamento non l'ha creato** e le cui chiavi sono anche tue
- Una nota che hai scelto, registrata in modo permanente e leggibile in modo indipendente
- Un certificato (`xrpl_camp_certificate.json`): sicuro da condividere, senza chiavi private
- Un pacchetto di prova (`xrpl_camp_proof_pack.json`): che indica transazioni reali che chiunque può risolvere

## A proposito di questa prova

Il pacchetto di prova contiene un hash SHA-256. Questo hash rileva una modifica accidentale. **Non** è una firma e, di per sé, non dimostra che il pacchetto sia autentico: chiunque può modificare un campo e ricalcolare l'hash con la stessa funzione pubblica utilizzata da questo strumento.

Ciò che non può essere falsificato è il libro mastro:

```bash
xrpl-camp proof verify xrpl_camp_proof_pack.json --online
```

Questo risolve ogni transazione indicata dal pacchetto e verifica che esista, che sia stata inviata dall'indirizzo del pacchetto, che contenga la nota che il pacchetto afferma e che sia stata completata con successo. Un pacchetto con un indirizzo riscritto supera il controllo offline dell'hash e fallisce questo.

Due dettagli importanti da conoscere, perché è facile sbagliare:

- La verifica interroga sempre il Testnet pubblico (o `--rpc-url`), **mai** l'endpoint indicato all'interno del pacchetto. Un pacchetto contraffatto può indicare un server controllato dal suo autore.
- Il XRPL Testnet viene periodicamente reimpostato (il prossimo è previsto per il 2026-11-25). Quando ciò accade, le transazioni oneste smettono di essere risolte. Se l'endpoint non contiene il libro mastro in cui è stata registrata una transazione, il risultato è *non verificabile* (codice di uscita 3), non una frode (codice di uscita 1) e l'output indica su cosa si basa: un reset annunciato (`history_signal: announced`) o solo il numero del libro mastro del pacchetto (`pack_claim`, visualizzato come **UNCONFIRMED**). Nessuno dei due è un risultato positivo.

La verifica offline rimane l'impostazione predefinita e non effettua chiamate di rete, quindi funziona ancora su un aereo o su una macchina in un'aula con accesso limitato.

## Modalità di prova

```bash
xrpl-camp start --dry-run
```

Non vengono effettuate chiamate di rete, non vengono eseguite scritture su disco e non vengono forniti output fuorvianti: la lezione 6 rifiuta esplicitamente di generare artefatti. La modalità di prova può *leggere* lo stato esistente, ma non modifica mai nulla.

## Endpoint e stato

```bash
export XRPL_CAMP_RPC_URL="https://your-node:51234/"
```

Lo strumento rifiuta gli endpoint che non può confermare essere Testnet, prima di firmare qualsiasi cosa. Imposta `XRPL_CAMP_ALLOW_ANY_NETWORK=1` solo se comprendi a cosa ti stai riferendo.

Lo stato viene memorizzato per impostazione predefinita in `./.xrpl-camp`: una sessione appartiene alla cartella in cui è stato eseguito. `XRPL_CAMP_HOME` sovrascrive questo valore e `xrpl-camp status --detail` stampa il percorso assoluto risolto.

## Sicurezza

Il tuo seed viene memorizzato localmente in `.xrpl-camp/wallet.json` (accessibile solo al proprietario su POSIX) e non viene mai incluso nel certificato o nel pacchetto di prova: la generazione rifiuta di scrivere un artefatto che lo contenga.

Questo strumento **utilizza per impostazione predefinita** XRPL Testnet, dove il test XRP non ha un valore reale, e rifiuta gli endpoint non Testnet a meno che tu non scelga esplicitamente di non farlo. Nessun telemetria, nessuna analisi, nessuna comunicazione con server esterni.

Consulta [SECURITY.md](SECURITY.md).

## Modello di minaccia

| Minaccia | Mitigazione |
|--------|-----------|
| Seed divulgato in un artefatto | La generazione esegue un controllo del seed basato sul `decode_seed` di xrpl-py e **rifiuta di scrivere il file** se il controllo fallisce. |
| Seed aggiunto a git | `.xrpl-camp/` viene ignorato da git *in questo repository*; lo stato viene scritto nella tua directory di lavoro, quindi aggiungilo al tuo `.gitignore`. |
| Seed leggibile da altri utenti | File del portafoglio con permessi 0600, directory dello stato con permessi 0700 su POSIX. |
| Uno studente copia un segreto in una nota pubblica | Il testo della nota viene scansionato alla ricerca di stringhe simili a un seed e viene rifiutato prima dell'invio. |
| Seed Testnet riutilizzato su Mainnet | Avviso durante la creazione del portafoglio; lo strumento rifiuta per impostazione predefinita gli endpoint non Testnet. |
| Manomissione del pacchetto di prova | SHA-256 rileva modifiche casuali; `--online` rileva una falsificazione risigillata chiedendo al registro. |
| Verifica rispetto all'endpoint di un attaccante | `--online` non utilizza mai l'endpoint specificato nel pacchetto in fase di test. |
| Diagnostica che rivelano la tua identità | `support-bundle` elimina la directory home e il nome dell'account. |

## Per workshop e aule

- **Un comando per studente.** `npx`, `pipx` o il container: nessuna configurazione condivisa.
- **Il fallimento è gratuito.** `xrpl-camp try` insegna le modalità di errore senza spendere nulla, quindi uno studente che rompe qualcosa intenzionalmente impara più di uno che non lo fa.
- **Triaging del facilitatore.** `status --detail` mostra il portafoglio, l'endpoint e la directory dello stato. `self-check` verifica la connessione effettiva invece di segnalare un "OK" ottimistico.
- **Verifica l'intera aula contemporaneamente.** `proof verify <folder> --online` verifica il pacchetto di ogni studente rispetto al registro.
- **I limiti di frequenza sono reali.** Trenta persone che accedono a un singolo faucet lo sovraccaricheranno; lo strumento riprova con un intervallo crescente e lo comunica invece di incolpare la tua connessione Wi-Fi.

## Sviluppo

```bash
git clone https://github.com/mcp-tool-shop-org/xrpl-camp.git
cd xrpl-camp
uv sync --dev
bash scripts/verify.sh     # lint + tests + build + smoke
```

## Licenza

MIT

---

Creato da [MCP Tool Shop](https://mcp-tool-shop.github.io/)
