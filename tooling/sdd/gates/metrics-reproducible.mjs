#!/usr/bin/env node
import { requireOk, pass, fail } from "./delivery-utils.mjs";

const runDir = process.argv[2];
if (!runDir) fail("usage: metrics-reproducible.mjs <run-dir>");
const data = requireOk(runDir, "metrics-reproducible");
if (!data.metricsHash) fail("metricsHash required");
if (data.handFilledNumbers === true) fail("hand-filled numbers are forbidden");
pass("metrics-reproducible: ok");
