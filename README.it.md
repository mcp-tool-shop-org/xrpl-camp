<p align="center">
  <a href="README.ja.md">日本語</a> | <a href="README.zh.md">中文</a> | <a href="README.es.md">Español</a> | <a href="README.fr.md">Français</a> | <a href="README.hi.md">हिन्दी</a> | <a href="README.md">English</a> | <a href="README.pt-BR.md">Português (BR)</a>
</p>

<p align="center">
  <img src="https://raw.githubusercontent.com/mcp-tool-shop-org/brand/main/logos/xrpl-camp/readme.png" width="400" alt="XRPL Camp">
</p>

<p align="center">
  <a href="https://github.com/mcp-tool-shop-org/xrpl-camp/actions/workflows/ci.yml"><img src="https://github.com/mcp-tool-shop-org/xrpl-camp/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue" alt="MIT License"></a>
  <a href="https://mcp-tool-shop-org.github.io/xrpl-camp/"><img src="https://img.shields.io/badge/Landing_Page-live-blue" alt="Landing Page"></a>
</p>

Impara a conoscere il ledger XRP in una sola sessione. Nessun account. Nessun denaro reale. Solo tu e il ledger.

XRPL Camp ti guida attraverso 6 lezioni, "cos'è un ledger?" fino a un portafoglio attivo, un pagamento confermato e un certificato verificabile, in circa 10 minuti.

## Installazione

```bash
pipx install xrpl-camp
```

Oppure con pip:

```bash
pip install xrpl-camp
```

## Guida Rapida

```bash
xrpl-camp start
```

Questo comando esegue la sequenza guidata attraverso tutte le 6 lezioni:

1. **Modello Concettuale** — Cosa è l'XRPL (account, saldi, transazioni, memo)
2. **Crea Portafoglio** — Genera una coppia di chiavi per la Testnet
3. **Finanzia il Portafoglio** — Ottieni XRP di prova gratuiti dal "faucet"
4. **Effettua un Pagamento** — Scrivi un memo al ledger (pagamento a te stesso, 1 goccia)
5. **Verifica la Transazione** — Controlla cosa hai scritto
6. **Certificato** — Ottieni una registrazione verificabile e portatile di ciò che hai fatto

## Comandi

| Comando | Cosa fa |
|---------|-------------|
| `xrpl-camp start` | Esegue la sequenza guidata attraverso tutte le 6 lezioni |
| `xrpl-camp start --dry-run` | Simula l'intero processo senza connessioni di rete |
| `xrpl-camp wallet create` | Crea un portafoglio per la Testnet |
| `xrpl-camp wallet show` | Mostra l'indirizzo del tuo portafoglio |
| `xrpl-camp fund` | Finanzia il tuo portafoglio tramite il "faucet" della Testnet |
| `xrpl-camp fund --dry-run` | Simula l'effetto di un finanziamento, senza connessione di rete |
| `xrpl-camp send --memo "hello"` | Effettua un pagamento a te stesso con un memo personalizzato |
| `xrpl-camp send --dry-run` | Simula il pagamento |
| `xrpl-camp verify --tx <hash>` | Verifica una transazione sul ledger |
| `xrpl-camp certificate` | Genera certificato + pacchetto di prova |
| `xrpl-camp reset` | Cancella tutti i dati (richiede conferma esplicita) |

## Cosa Ottieni

- Un portafoglio attivo per la Testnet (`.xrpl-camp/wallet.json` — locale, ignorato da git)
- Un pagamento confermato sulla XRPL Testnet
- Un rapporto di verifica che mostra esattamente ciò che il ledger ha registrato
- Un certificato (`xrpl_camp_certificate.json`) — sicuro da condividere, senza chiavi private
- Un pacchetto di prova (`xrpl_camp_proof_pack.json`) — resistente alla manomissione, con hash SHA-256

## Modalità di Test

Ogni comando che richiede una connessione supporta l'opzione `--dry-run`.  Stampa ciò che accadrebbe senza effettuare chiamate di rete o modificare lo stato. Utile per acquisire sicurezza e per il debug.

## Pacchetto di Prova

Il pacchetto di prova è una registrazione resistente alla manomissione di tutto ciò che hai fatto:

- Indirizzo del portafoglio e rete
- Timestamp di completamento delle lezioni
- ID delle transazioni con URL per l'esploratore
- Versione dello strumento
- Hash SHA-256 dell'intero contenuto

Chiunque può verificare l'hash per confermare che il file non sia stato modificato.

## Override dell'Endpoint

Per impostazione predefinita, XRPL Camp utilizza il nodo pubblico della XRPL Testnet. Per utilizzare un endpoint diverso:

```bash
export XRPL_CAMP_RPC_URL="https://your-node:51234/"
xrpl-camp fund
```

## Sicurezza

La tua "seed" (chiave privata) è memorizzata localmente e non è inclusa nel certificato o nel pacchetto di prova.
Questo strumento utilizza solo la **Testnet** di XRPL — gli XRP di prova non hanno alcun valore reale.
Nessuna telemetria, nessuna analisi, nessuna trasmissione di dati — le uniche connessioni di rete sono verso la XRPL Testnet.

Consulta [SECURITY.md](SECURITY.md) per i dettagli.

## Modello di Minaccia

| Minaccia | Mitigazione |
|--------|-----------|
| Fuga della "seed" tramite certificato | La generazione del certificato esclude esplicitamente la "seed"; controllo di sicurezza `certificate_has_seed()` |
| Fuga della "seed" tramite pacchetto di prova | La generazione del pacchetto di prova esclude la "seed"; controllo di sicurezza `proof_pack_has_seed()` |
| "Seed" in git | La directory `.xrpl-camp/` è ignorata da git; il comando `wallet show` non mostra mai la "seed" |
| Riutilizzo della "seed" della Testnet sulla Mainnet | Viene visualizzato un avviso durante la creazione del portafoglio |
| Esposizione del contenuto del memo | Tutti i memo sono pubblici per progettazione; gli utenti vengono avvertiti prima di inviare |
| Manomissione del pacchetto di prova | Hash di integrità SHA-256; `verify_proof_pack()` rileva le modifiche |

## Sviluppo

```bash
git clone https://github.com/mcp-tool-shop-org/xrpl-camp.git
cd xrpl-camp
uv sync --dev
uv run ruff check .
uv run pytest tests/ -v
```

## Licenza

MIT

---

Creato da [MCP Tool Shop](https://mcp-tool-shop.github.io/).
