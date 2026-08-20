#!/usr/bin/env node
import { requireOk, pass, fail } from "./delivery-utils.mjs";

const runDir = process.argv[2];
if (!runDir) fail("usage: release-check.mjs <run-dir>");
const data = requireOk(runDir, "release-check");
if (data.secretsFound !== 0) fail("secrets found in release tree");
if (data.license !== "MIT") fail("LICENSE must be MIT");
pass("release-check: ok");
