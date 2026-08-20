#!/usr/bin/env node
import { requireOk, pass, fail } from "./delivery-utils.mjs";

const runDir = process.argv[2];
if (!runDir) fail("usage: env-doctor.mjs <run-dir>");
const data = requireOk(runDir, "env-doctor");
if (!data.node || !data.python) fail("env-doctor.json must include node and python versions");
pass("env-doctor: ok");
