// The only declarations of node's built-in modules that the port uses (no declarations package is fetched).

declare module 'node:fs' {
  export function readFileSync(path: string): Uint8Array;
}

declare module 'node:process' {
  interface Writable {
    write(chunk: string): boolean;
  }
  interface Process {
    argv: string[];
    stdout: Writable;
    stderr: Writable;
    exitCode: number | undefined;
  }
  const process: Process;
  export default process;
}
