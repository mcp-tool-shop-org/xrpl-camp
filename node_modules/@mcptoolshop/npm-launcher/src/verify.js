"use strict";

const crypto = require("crypto");
const fs = require("fs");

/**
 * Compute SHA256 hex digest of a file.
 */
function sha256File(filePath) {
  const hash = crypto.createHash("sha256");
  const data = fs.readFileSync(filePath);
  hash.update(data);
  return hash.digest("hex");
}

/**
 * Parse a checksums.txt file (GNU coreutils format).
 * Each line: "<sha256>  <filename>"
 * Returns Map<filename, sha256hex>.
 */
function parseChecksumsTxt(buf) {
  const text = buf.toString("utf8");
  const map = new Map();
  for (const line of text.split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed) continue;
    // two-space separator is the GNU coreutils convention
    const m = trimmed.match(/^([a-fA-F0-9]{64})\s{1,2}(.+)$/);
    if (!m) continue;
    map.set(m[2].trim(), m[1].toLowerCase());
  }
  return map;
}

/**
 * Verify a file's SHA256 matches the expected hex digest.
 * Throws on mismatch.
 */
function verifySha256(filePath, expectedHex) {
  const actual = sha256File(filePath);
  if (actual !== expectedHex.toLowerCase()) {
    throw new Error(
      `SHA256 mismatch for ${filePath}\n` +
      `  Expected: ${expectedHex}\n` +
      `  Actual:   ${actual}`
    );
  }
}

module.exports = { sha256File, parseChecksumsTxt, verifySha256 };
