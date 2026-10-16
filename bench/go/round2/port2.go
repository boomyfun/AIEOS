// Command round2 is the Go port's round-2 program of the stack benchmark: run as `port2 <round-2 input document>`,
// it prints the event log's append results and the reconcile results as one document in the canonical text,
// byte-equal to the round-2 reference document, or exits non-zero and prints nothing to standard output.
package main

import "os"

func main() {
	os.Exit(run2(os.Args[1:], os.ReadFile, os.Stdout, os.Stderr))
}
