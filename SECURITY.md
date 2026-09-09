# Security

## Seed Handling

XRPL Camp creates a **Testnet wallet** with a cryptographic seed (private key), and a second
"mailbox" wallet that lesson 4's payment brings into existence. Both seeds are yours.

- Seeds are stored locally in `.xrpl-camp/wallet.json` and `.xrpl-camp/mailbox.json`
- On POSIX those files are `0600` and the directory is `0700`
- Certificate and proof-pack generation runs a seed check built on xrpl-py's own `decode_seed`
  and **refuses to write the file** if a seed is present — it fails closed rather than warning
- Memo text is scanned for seed-shaped strings *before* submission, because a memo is permanent
  and public and there is no taking one back
- `xrpl-camp wallet show` displays your address, never your seed
- `xrpl-camp support-bundle` redacts your home directory and account name

### Where state lives

State is written to `./.xrpl-camp` — **the directory you ran the tool in**, not a fixed home
location. That is deliberate: a sitting belongs to its folder, so two workshops in two folders do
not collide.

It also means the `.gitignore` in *this* repository does not protect *your* directory. If you run
xrpl-camp inside a git repository of your own, add `.xrpl-camp/` to that repository's
`.gitignore`. `xrpl-camp status --detail` prints the resolved absolute path, and `XRPL_CAMP_HOME`
overrides the location if you want state somewhere specific.

## Testnet by default, and enforced

XRPL Camp **defaults to** the XRPL Testnet, where test XRP has no real value.

This is not merely a default. `XRPL_CAMP_RPC_URL` lets you point the tool at another endpoint, and
before signing anything the tool checks the server's `network_id` and refuses one it cannot confirm
is a test network. `XRPL_CAMP_ALLOW_ANY_NETWORK=1` opts out of that check; set it only if you
understand exactly what you are pointing at.

The certificate and proof pack record the endpoint actually used, so an artifact cannot claim
"testnet" about a run that went somewhere else.

**Never use a Testnet seed on Mainnet.** If you do, anyone who had access to your Testnet seed
could spend your real funds.

## What the proof pack does and does not prove

The proof pack carries a SHA-256 hash over its own contents. That hash detects an accidental edit.

It is **not a signature**. Anyone can change a field and recompute the hash using the same public
function this tool uses — this was demonstrated during development, and the marketing claim that
the pack "can't be faked" was false and has been removed.

What cannot be faked is the ledger. `xrpl-camp proof verify <file> --online` resolves every
transaction the pack names and checks it exists, was sent by the pack's address, carries the
claimed memo, and closed successfully.

Two properties of that check are security-relevant:

- It queries the public Testnet, or an endpoint you supply with `--rpc-url`. It **never** queries
  the endpoint named inside the pack being checked, because a forged pack can name a server its
  author controls.
- A transaction that does not resolve is not automatically fraud. The XRPL Testnet is periodically
  reset, and honest transactions vanish with it. The pack records each transaction's ledger index
  so a reset is reported as *unverifiable* (exit 3), distinct from *contradicted* (exit 1).

Offline verification makes no network calls and remains the default.

## What Gets Shared

| Data | Where | Public? |
|------|-------|---------|
| Address | Certificate, proof pack, ledger | Yes — safe to share |
| Seed | `.xrpl-camp/` only | **No — never share** |
| Transactions | XRPL Testnet | Yes — permanent and public |
| Memos | XRPL Testnet | Yes — permanent and public |
| Endpoint used | Proof pack | Yes |
| Certificate / proof pack | Files you keep | Yes — safe to share |

## No telemetry

There is no analytics, no phone-home, and no crash reporting. The only network calls go to the
XRPL endpoint in use and the Testnet faucet. `xrpl-camp self-check` shows you which endpoint that
is and whether it is reachable.

## Supported Versions

Security fixes land on the latest released version. This is a teaching tool on a test network;
there are no long-term support branches.

| Version | Supported |
|---------|-----------|
| 1.4.x   | Yes |
| < 1.4   | No — upgrade |

## Reporting

If you find a security issue, please open a GitHub issue at
<https://github.com/mcp-tool-shop-org/xrpl-camp/issues> or email
64996768+mcp-tool-shop@users.noreply.github.com.

Because this tool is Testnet-only and holds no funds of value, there is no embargo process. A
public issue is fine and usually faster.
