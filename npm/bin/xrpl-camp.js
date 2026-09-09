#!/usr/bin/env node
"use strict";

// version is derived from package.json at runtime rather than duplicated
// here as a literal -- this used to be a third hand-synced copy alongside
// package.json's own "version" and pyproject.toml's, and all three have
// already drifted independently in production (live npm registry served
// 1.3.2, a version that exists nowhere in git). `tag` is intentionally
// omitted: @mcptoolshop/npm-launcher@^1.0.0 already defaults it to
// `v${config.version}`, which matches this repo's tagging convention, so
// spelling it out here was redundant duplication of something the
// dependency derives for free.
const { version } = require("../package.json");

process.env.MCPTOOLSHOP_LAUNCH_CONFIG = JSON.stringify({
  toolName: "xrpl-camp",
  owner: "mcp-tool-shop-org",
  repo: "xrpl-camp",
  version,
});

require("@mcptoolshop/npm-launcher/bin/mcptoolshop-launch.js");
