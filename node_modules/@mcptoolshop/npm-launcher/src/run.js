"use strict";

const { spawnSync } = require("child_process");

/**
 * Execute a binary with inherited stdio.
 * Returns the exit code.
 */
function runBinary(binPath, args) {
  const result = spawnSync(binPath, args, { stdio: "inherit" });
  if (result.error) throw result.error;
  return result.status ?? 1;
}

module.exports = { runBinary };
