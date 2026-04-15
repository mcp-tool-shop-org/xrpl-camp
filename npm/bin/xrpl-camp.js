#!/usr/bin/env node
"use strict";

process.env.MCPTOOLSHOP_LAUNCH_CONFIG = JSON.stringify({
  toolName: "xrpl-camp",
  owner: "mcp-tool-shop-org",
  repo: "xrpl-camp",
  version: "1.3.1",
  tag: "v1.3.1",
});

require("@mcptoolshop/npm-launcher/bin/mcptoolshop-launch.js");
