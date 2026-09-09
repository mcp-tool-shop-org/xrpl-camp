"use strict";

const SUPPORTED = {
  "linux-x64":    { os: "linux",  arch: "x64",   ext: "" },
  "darwin-arm64": { os: "darwin", arch: "arm64", ext: "" },
  "darwin-x64":   { os: "darwin", arch: "x64",   ext: "" },
  "win32-x64":    { os: "win",   arch: "x64",   ext: ".exe" },
};

function resolveTarget() {
  const key = `${process.platform}-${process.arch}`;
  const target = SUPPORTED[key];
  if (!target) {
    const supported = Object.keys(SUPPORTED)
      .map((k) => k.replace("win32", "windows"))
      .join(", ");
    let hint = "";
    if (process.platform === "darwin" && process.arch !== "arm64" && process.arch !== "x64") {
      hint = "\n  Hint: On Apple Silicon, try running under Rosetta: arch -x86_64 npx ...";
    }
    if (process.platform === "linux" && process.arch === "arm64") {
      hint = "\n  Hint: linux-arm64 is not yet supported. x64 binaries may work under QEMU/box64.";
    }
    throw new Error(
      `Unsupported platform: ${process.platform}/${process.arch}\n` +
      `  Supported: ${supported}${hint}`
    );
  }
  return target;
}

module.exports = { resolveTarget, SUPPORTED };
