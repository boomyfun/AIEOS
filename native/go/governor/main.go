// Command aieosnative is the native governor in shadow (TASK-100; m8-plan.md sections 1 to 5): run as
// `<binary> <fixture document>`, it prints the decision records of the governor's round-1 fixture cases as one
// document in the canonical text, byte-equal to the governor-only reference document, or exits non-zero and prints
// nothing to standard output. It decides nothing: it writes no record, and only the advisory workflow aieos-native.yml
// reads its output.
package main

import "os"

func main() {
	os.Exit(run(os.Args[1:], os.ReadFile, os.Stdout, os.Stderr))
}
