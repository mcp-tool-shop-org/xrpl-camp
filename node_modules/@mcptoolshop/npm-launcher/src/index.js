"use strict";

const fs = require("fs");
const path = require("path");
const { resolveTarget } = require("./platform");
const { toolCacheDir, ensureDir } = require("./cache");
const { releaseAssetUrl, downloadToFile, get } = require("./github");
const { parseChecksumsTxt, verifySha256 } = require("./verify");
const { runBinary } = require("./run");
const { acquireLock } = require("./lock");
const { setQuiet, info } = require("./log");

/**
 * Config contract (pure JSON, no functions):
 *
 *   toolName    - binary base name, e.g. "sovereignty"
 *   owner       - GitHub org, e.g. "mcp-tool-shop-org"
 *   repo        - GitHub repo name, e.g. "sovereignty"
 *   version     - semver without v prefix, e.g. "1.4.0"
 *   tag         - git tag, default "v<version>"
 *   quiet       - suppress progress messages (default false)
 *
 * Asset naming convention (locked):
 *   binary:    <toolName>-<version>-<os>-<arch><ext>
 *   checksums: checksums-<version>.txt
 */

function assetName(toolName, version, target) {
  return `${toolName}-${version}-${target.os}-${target.arch}${target.ext}`;
}

function checksumsAssetName(version) {
  return `checksums-${version}.txt`;
}

/**
 * Ensure the binary is downloaded, verified, and cached.
 * Returns the absolute path to the executable.
 */
async function ensureBinary(config) {
  if (config.quiet) setQuiet(true);

  const target = resolveTarget();
  const tag = config.tag || `v${config.version}`;
  const asset = assetName(config.toolName, config.version, target);
  const checksumsFile = checksumsAssetName(config.version);

  const cacheDir = toolCacheDir(config.toolName, config.version);
  ensureDir(cacheDir);

  const binPath = path.join(cacheDir, asset);

  // Already cached — skip download
  if (fs.existsSync(binPath)) {
    return binPath;
  }

  // Acquire lock to prevent concurrent download races
  const releaseLock = await acquireLock(cacheDir, asset);
  try {
    // Double-check after acquiring lock (another process may have finished)
    if (fs.existsSync(binPath)) {
      return binPath;
    }

    // Download checksums
    const checksumsUrl = releaseAssetUrl(config.owner, config.repo, tag, checksumsFile);
    info(`Fetching checksums from ${config.owner}/${config.repo}@${tag}...`);

    const checksumsRes = await get(checksumsUrl);
    if (checksumsRes.status !== 200) {
      throw new Error(
        `Failed to fetch checksums (HTTP ${checksumsRes.status})\n` +
        `  URL: ${checksumsUrl}\n` +
        `  Hint: Does release ${tag} exist with a ${checksumsFile} asset?\n` +
        `  Check: https://github.com/${config.owner}/${config.repo}/releases/tag/${tag}`
      );
    }

    const checksums = parseChecksumsTxt(checksumsRes.body);
    const expected = checksums.get(asset);
    if (!expected) {
      const available = [...checksums.keys()];
      const listing = available.length > 0
        ? available.map((a) => `    - ${a}`).join("\n")
        : "    (none)";
      throw new Error(
        `No checksum found for asset: ${asset}\n` +
        `  Available assets in ${checksumsFile}:\n${listing}\n` +
        `  Hint: Is ${target.os}-${target.arch} supported for ${config.toolName} ${config.version}?\n` +
        `  Did the CI build complete for this platform?`
      );
    }

    // Download binary
    const assetUrl = releaseAssetUrl(config.owner, config.repo, tag, asset);
    info(`Downloading ${asset}...`);
    await downloadToFile(assetUrl, binPath);

    // Verify checksum — delete on mismatch so next run retries
    info("Verifying SHA256...");
    try {
      verifySha256(binPath, expected);
    } catch (err) {
      try { fs.unlinkSync(binPath); } catch {}
      throw err;
    }

    // Make executable on Unix
    if (process.platform !== "win32") {
      fs.chmodSync(binPath, 0o755);
    }

    info("Ready.");
    return binPath;
  } finally {
    releaseLock();
  }
}

/**
 * Main entry: ensure binary, then run it with argv passthrough.
 */
async function launch(config, argv) {
  const args = argv.slice(2);
  const binPath = await ensureBinary(config);
  const code = runBinary(binPath, args);
  process.exit(code);
}

/**
 * Print the cache directory for a tool+version (or the root cache dir).
 */
function printCachePath(config) {
  const { defaultCacheDir } = require("./cache");
  if (config && config.toolName && config.version) {
    console.log(toolCacheDir(config.toolName, config.version));
  } else if (config && config.toolName) {
    console.log(path.join(defaultCacheDir(), config.toolName));
  } else {
    console.log(defaultCacheDir());
  }
}

/**
 * Clear cached binaries for a tool (all versions) or a specific version.
 */
function clearCache(config) {
  const { defaultCacheDir } = require("./cache");
  let target;
  if (config && config.toolName && config.version) {
    target = toolCacheDir(config.toolName, config.version);
  } else if (config && config.toolName) {
    target = path.join(defaultCacheDir(), config.toolName);
  } else {
    target = defaultCacheDir();
  }

  if (!fs.existsSync(target)) {
    process.stderr.write(`Nothing to clear: ${target}\n`);
    return;
  }

  fs.rmSync(target, { recursive: true, force: true });
  process.stderr.write(`Cleared: ${target}\n`);
}

module.exports = { launch, ensureBinary, assetName, checksumsAssetName, printCachePath, clearCache };
