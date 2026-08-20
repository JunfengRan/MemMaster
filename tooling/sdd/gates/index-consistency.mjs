#!/usr/bin/env node
import { requireOk, pass, fail } from "./delivery-utils.mjs";

const runDir = process.argv[2];
if (!runDir) fail("usage: index-consistency.mjs <run-dir>");
const data = requireOk(runDir, "index-consistency");
if (!data.manifestHash) fail("index-consistency.json missing manifestHash");
if (data.orphanEdges !== 0) fail("orphan graph edges must be 0");
pass("index-consistency: ok");
