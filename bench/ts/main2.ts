// Round 2's entry: `node main2.ts <round-2 input document>` prints the whole round-2 document in one write and exits 0;
// on any failure it prints nothing to standard output and exits non-zero (the document is built before the write).

import { readFileSync } from 'node:fs';
import process from 'node:process';
import { runMain2 } from './r2_document.ts';

const result = runMain2(process.argv.slice(2), (path: string): Uint8Array => readFileSync(path));
if (result.stderr !== '') process.stderr.write(result.stderr);
if (result.stdout !== '') process.stdout.write(result.stdout);
process.exitCode = result.code;
