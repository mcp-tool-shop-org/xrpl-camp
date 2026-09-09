"use strict";

const https = require("https");
const fs = require("fs");
const { pipeline } = require("stream");
const { promisify } = require("util");

const streamPipeline = promisify(pipeline);

const UA = "mcptoolshop-launcher";
const MAX_REDIRECTS = 5;
const TIMEOUT_MS = 30_000; // 30s per request

/**
 * GET a URL, following redirects. Returns { status, body }.
 */
function get(url, headers = {}, redirectsLeft = MAX_REDIRECTS) {
  return new Promise((resolve, reject) => {
    const opts = {
      headers: { "User-Agent": UA, ...headers },
      timeout: TIMEOUT_MS,
    };
    const req = https.get(url, opts, (res) => {
      if (
        res.statusCode >= 300 &&
        res.statusCode < 400 &&
        res.headers.location
      ) {
        if (redirectsLeft <= 0) {
          reject(new Error(`Too many redirects for ${url}`));
          return;
        }
        res.resume();
        resolve(get(res.headers.location, headers, redirectsLeft - 1));
        return;
      }

      const chunks = [];
      res.on("data", (d) => chunks.push(d));
      res.on("end", () =>
        resolve({ status: res.statusCode || 0, body: Buffer.concat(chunks) })
      );
      res.on("error", reject);
    });
    req.on("timeout", () => {
      req.destroy();
      reject(new Error(`Request timed out after ${TIMEOUT_MS / 1000}s: ${url}`));
    });
    req.on("error", reject);
  });
}

/**
 * Download a URL to a local file, following redirects.
 * Writes to a .tmp file first, then renames on success (atomic).
 */
function downloadToFile(url, outPath, headers = {}, redirectsLeft = MAX_REDIRECTS) {
  const tmpPath = outPath + ".tmp";
  return new Promise((resolve, reject) => {
    const opts = {
      headers: { "User-Agent": UA, ...headers },
      timeout: TIMEOUT_MS,
    };
    const req = https.get(url, opts, (res) => {
      if (
        res.statusCode >= 300 &&
        res.statusCode < 400 &&
        res.headers.location
      ) {
        if (redirectsLeft <= 0) {
          reject(new Error(`Too many redirects for ${url}`));
          return;
        }
        res.resume();
        downloadToFile(res.headers.location, outPath, headers, redirectsLeft - 1)
          .then(resolve)
          .catch(reject);
        return;
      }

      if (res.statusCode !== 200) {
        res.resume();
        reject(new Error(`Download failed (HTTP ${res.statusCode}): ${url}`));
        return;
      }

      const file = fs.createWriteStream(tmpPath);
      streamPipeline(res, file)
        .then(() => {
          // Atomic: rename .tmp to final path only after full write
          fs.renameSync(tmpPath, outPath);
          resolve();
        })
        .catch((err) => {
          // Clean up partial download
          try { fs.unlinkSync(tmpPath); } catch {}
          reject(err);
        });
    });
    req.on("timeout", () => {
      req.destroy();
      try { fs.unlinkSync(tmpPath); } catch {}
      reject(new Error(`Download timed out after ${TIMEOUT_MS / 1000}s: ${url}`));
    });
    req.on("error", (err) => {
      try { fs.unlinkSync(tmpPath); } catch {}
      reject(err);
    });
  });
}

/**
 * Build a GitHub Release asset download URL.
 */
function releaseAssetUrl(owner, repo, tag, assetName) {
  return `https://github.com/${owner}/${repo}/releases/download/${tag}/${assetName}`;
}

module.exports = { get, downloadToFile, releaseAssetUrl };
