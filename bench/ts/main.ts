// The entry: `node main.ts <fixture document>` prints the port's whole document in one write and exits 0; on any
// failure it prints nothing to standard output and exits non-zero (the document is built before the write).

import { readFileSync } from 'node:fs';
import process from 'node:process';
import { runMain } from './export.ts';

const result = runMain(process.argv.slice(2), (path: string): Uint8Array => readFileSync(path));
if (result.stderr !== '') process.stderr.write(result.stderr);
if (result.stdout !== '') process.stdout.write(result.stdout);
process.exitCode = result.code;
