#!/usr/bin/env node
"use strict";

const { launch, printCachePath, clearCache } = require("../src/index");

// --version and --help work without config (intercepted early)
const earlyArg = process.argv[2];

if (earlyArg === "--version" || earlyArg === "-V") {
  const pkg = require("../package.json");
  console.log(`mcptoolshop-launch ${pkg.version}`);
  process.exit(0);
}

if (earlyArg === "--help" || earlyArg === "-h") {
  const pkg = require("../package.json");
  console.log(`mcptoolshop-launch v${pkg.version}

Generic GitHub-release binary launcher with cache + SHA256 verification.

USAGE (direct):
  mcptoolshop-launch [OPTIONS]

USAGE (via wrapper):
  Set MCPTOOLSHOP_LAUNCH_CONFIG as JSON, then run mcptoolshop-launch [-- args...]

OPTIONS:
  --version, -V          Print version and exit
  --help, -h             Show this help and exit
  --print-cache-path     Show cache directory for configured tool
  --clear-cache          Remove cached binaries for configured tool

CONFIG (via MCPTOOLSHOP_LAUNCH_CONFIG env var):
  toolName  (required)   Binary base name, e.g. "sovereignty"
  owner     (required)   GitHub org/user, e.g. "mcp-tool-shop-org"
  repo      (required)   GitHub repo name
  version   (required)   Semver without v prefix, e.g. "1.4.0"
  tag       (optional)   Git tag, defaults to "v<version>"
  quiet     (optional)   Suppress progress messages

DOCS: ${pkg.homepage || "https://github.com/mcp-tool-shop-org/npm-launcher"}`);
  process.exit(0);
}

// Wrappers pass config as JSON via environment variable.
const raw = process.env.MCPTOOLSHOP_LAUNCH_CONFIG;
if (!raw) {
  process.stderr.write(
    "Error: MCPTOOLSHOP_LAUNCH_CONFIG is not set.\n" +
    "This binary is meant to be called by an @mcptoolshop wrapper package.\n"
  );
  process.exit(2);
}

let config;
try {
  config = JSON.parse(raw);
} catch {
  process.stderr.write(
    "Error: MCPTOOLSHOP_LAUNCH_CONFIG is not valid JSON.\n"
  );
  process.exit(2);
}

// Validate required fields
const required = ["toolName", "owner", "repo", "version"];
const missing = required.filter((k) => !config[k]);
if (missing.length > 0) {
  process.stderr.write(
    `Error: Missing required config fields: ${missing.join(", ")}\n`
  );
  process.exit(2);
}

// Launcher-level commands (intercepted before binary launch)
const arg1 = process.argv[2];

if (arg1 === "--print-cache-path") {
  printCachePath(config);
  process.exit(0);
}

if (arg1 === "--clear-cache") {
  clearCache(config);
  process.exit(0);
}

launch(config, process.argv).catch((err) => {
  process.stderr.write(`${err.message || String(err)}\n`);
  process.exit(1);
});
