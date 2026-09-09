"use strict";

const fs = require("fs");
const os = require("os");
const path = require("path");

function defaultCacheDir() {
  if (process.platform === "win32") {
    return process.env.LOCALAPPDATA
      ? path.join(process.env.LOCALAPPDATA, "mcptoolshop")
      : path.join(os.homedir(), ".cache", "mcptoolshop");
  }
  return path.join(
    process.env.XDG_CACHE_HOME || path.join(os.homedir(), ".cache"),
    "mcptoolshop"
  );
}

function toolCacheDir(toolName, version) {
  return path.join(defaultCacheDir(), toolName, version);
}

function ensureDir(dirPath) {
  fs.mkdirSync(dirPath, { recursive: true });
}

module.exports = { defaultCacheDir, toolCacheDir, ensureDir };
