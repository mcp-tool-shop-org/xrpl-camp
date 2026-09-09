---
title: Reference
description: Every command, flag, environment variable and exit code.
sidebar:
  order: 4
---

## Global flags

| Flag | Effect |
|------|--------|
| `--version` | Print the installed version and exit |
| `--dry-run` | Simulate everything in this run: no network calls, no disk writes |
| `--yes`, `-y` | Non-interactive: never wait for a keypress. `reset` still asks |
| `--verbose` | Include the technical detail behind an error |
| `--help` | Show help for any command |

## The guided flow

```bash
xrpl-camp start
xrpl-camp start --memo "your message"     # supply lesson 4's memo up front
xrpl-camp start --dry-run                 # full walkthrough, nothing sent or written
```

Resumes where you left off. A failed lesson halts the run and tells you how to continue.

`--memo` matters for scripted and piped runs: without a terminal the tool cannot ask you what to write, and a permanent ledger entry should not silently become a machine-generated string.

## Reading the ledger

```bash
xrpl-camp read                      # your entries, fetched from the ledger
xrpl-camp read rSomeAddress...      # somebody else's public history
xrpl-camp read <64-hex-hash>        # one transaction, in full
```

None of this reads local state. `read` with no argument still goes to the network — the point is that the ledger remembers, not that the tool does.

## Breaking things on purpose

```bash
xrpl-camp try
```

Seven deliberate failures against the live network via the `simulate` facility. Nothing is signed, nothing is submitted, and it costs zero drops. Ends with a receipt showing which failures would have reached the ledger and charged you.

## Individual lessons

```bash
xrpl-camp wallet create
xrpl-camp wallet show
xrpl-camp fund
xrpl-camp send --memo "hello"
xrpl-camp verify --tx <hash>
xrpl-camp certificate
```

`verify` credits lesson 5 only for a transaction you sent. It will still show you anyone's transaction — it just will not pretend you wrote it.

## Progress and diagnostics

```bash
xrpl-camp status                 # checklist with timings
xrpl-camp status --detail        # wallet, endpoint, state directory, next step
xrpl-camp status --json          # machine-readable
xrpl-camp self-check             # environment AND a real connection probe
xrpl-camp support-bundle         # diagnostic zip, home path and username redacted
```

`self-check` exits non-zero when something is actually wrong, including an unreachable endpoint. It previously reported nine cheerful OK lines against a server returning 500 to every request.

## Proof

```bash
xrpl-camp proof verify <file>                    # hash only, zero network calls
xrpl-camp proof verify <file> --online           # also ask the ledger
xrpl-camp proof verify <file> --online --rpc-url https://your-node:51234/
xrpl-camp proof verify <folder> --online         # a whole workshop at once
xrpl-camp proof verify <file> --json
```

See [Proof Pack](/xrpl-camp/handbook/proof-pack/) for what each result means.

## Starting over

```bash
xrpl-camp reset      # requires typing RESET
```

## Environment variables

| Variable | Effect |
|----------|--------|
| `XRPL_CAMP_RPC_URL` | RPC endpoint. Checked against the server's network before signing |
| `XRPL_CAMP_ALLOW_ANY_NETWORK` | Set to `1` to skip that check. Only if you know what you are pointing at |
| `XRPL_CAMP_HOME` | Where state lives. Defaults to `./.xrpl-camp` |
| `XRPL_CAMP_RETRIES` | Attempts for retryable network calls (1–5, default 3) |
| `NO_COLOR` | Honoured |

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | User error — bad input, missing wallet, a contradicted proof pack |
| 2 | Runtime error — corrupt state, unreachable network, refused endpoint |
| 3 | Partial — the check ran but could not reach a verdict either way |

Every failure prints a stable error code you can quote in a bug report, a plain-language message, and something to try next. No stack traces; `--verbose` adds the technical detail underneath.

## Docker

```bash
docker run --rm -it -v "$PWD:/work" ghcr.io/mcp-tool-shop-org/xrpl-camp start
```

Mount `/work`. Everything the tool writes goes there, and an unmounted container discards it on exit — the image says so if you forget.
