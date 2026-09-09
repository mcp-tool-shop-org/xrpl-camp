"use strict";

/**
 * Quiet-aware logging to stderr.
 * Respects MCPTOOLSHOP_LAUNCHER_QUIET=1 env var or config.quiet flag.
 */

let _quiet = false;

function setQuiet(val) {
  _quiet = !!val;
}

function isQuiet() {
  return _quiet || process.env.MCPTOOLSHOP_LAUNCHER_QUIET === "1";
}

function info(msg) {
  if (!isQuiet()) {
    process.stderr.write(msg + "\n");
  }
}

function error(msg) {
  // Errors always print, even in quiet mode
  process.stderr.write(msg + "\n");
}

module.exports = { setQuiet, isQuiet, info, error };
