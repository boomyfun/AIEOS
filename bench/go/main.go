// Command aieosbench is the Go port of the stack benchmark (round 1): run as `<binary> <fixture document>`, it
// prints the decision records of the governor's and the Resume Check's fixture cases as one document in the
// canonical text, byte-equal to the reference document, or exits non-zero and prints nothing to standard output.
package main

import "os"

func main() {
	os.Exit(run(os.Args[1:], os.ReadFile, os.Stdout, os.Stderr))
}
