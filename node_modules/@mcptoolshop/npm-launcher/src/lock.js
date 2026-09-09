"use strict";

const fs = require("fs");
const path = require("path");

const LOCK_STALE_MS = 60_000; // consider lock stale after 60s
const LOCK_POLL_MS = 500;
const LOCK_MAX_WAIT_MS = 30_000;

/**
 * Acquire a simple file lock. Returns a release function.
 * If the lock is held, polls until available or times out.
 * Stale locks (older than LOCK_STALE_MS) are broken automatically.
 */
async function acquireLock(cacheDir, assetName) {
  const lockPath = path.join(cacheDir, `.${assetName}.lock`);
  const start = Date.now();

  while (true) {
    try {
      // O_CREAT | O_EXCL — fails if file exists
      const fd = fs.openSync(lockPath, "wx");
      fs.writeSync(fd, String(process.pid));
      fs.closeSync(fd);

      // Return release function
      return () => {
        try { fs.unlinkSync(lockPath); } catch {}
      };
    } catch (err) {
      if (err.code !== "EEXIST") throw err;

      // Check for stale lock
      try {
        const stat = fs.statSync(lockPath);
        if (Date.now() - stat.mtimeMs > LOCK_STALE_MS) {
          // Stale — break it
          try { fs.unlinkSync(lockPath); } catch {}
          continue;
        }
      } catch {
        // Lock disappeared between check and stat — retry
        continue;
      }

      // Check timeout
      if (Date.now() - start > LOCK_MAX_WAIT_MS) {
        throw new Error(
          `Timed out waiting for lock: ${lockPath}\n` +
          `  Hint: Another download may be in progress. Delete the lock file to retry.`
        );
      }

      // Wait and retry
      await new Promise((r) => setTimeout(r, LOCK_POLL_MS));
    }
  }
}

module.exports = { acquireLock };
