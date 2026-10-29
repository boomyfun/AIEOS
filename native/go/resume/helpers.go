package main

// The helpers of bench/go's records.go and governor.go that the Resume Check calls, copied unchanged (TASK-101).

import (
	"crypto/sha256"
	"encoding/hex"
	"math/big"
	"regexp"
	"sort"
)

var (
	reHex64   = regexp.MustCompile(`^[0-9a-f]{64}$`)
	reCommit  = regexp.MustCompile(`^(?:[0-9a-f]{40}|[0-9a-f]{64})$`)
	reTask    = regexp.MustCompile(`^TASK-[0-9]+$`)
	reVersion = regexp.MustCompile(`^v[0-9]+$`)
	reGate    = regexp.MustCompile(`^G[0-9]+$`)
)

// isStr is records._is_str (and governor._text: every Go string is valid UTF-8): a non-empty string.
func isStr(v any) bool {
	s, ok := v.(string)
	return ok && s != ""
}

// isStrList is records._is_str_list: a list of non-empty strings.
func isStrList(v any) bool {
	l, ok := v.([]any)
	if !ok {
		return false
	}
	for _, x := range l {
		if !isStr(x) {
			return false
		}
	}
	return true
}

// matches is records._matches: a string that the pattern matches in full.
func matches(re *regexp.Regexp, v any) bool {
	s, ok := v.(string)
	return ok && re.MatchString(s)
}

// in is records._in (and "v in tuple" for a tuple of strings): a string that is one of the values.
func in(values []string, v any) bool {
	s, ok := v.(string)
	if !ok {
		return false
	}
	for _, x := range values {
		if x == s {
			return true
		}
	}
	return false
}

func strEq(v any, s string) bool {
	x, ok := v.(string)
	return ok && x == s
}

func isCount(v any) bool {
	n, ok := v.(*big.Int)
	return ok && n.Sign() >= 0
}

func contains(list []string, s string) bool {
	for _, x := range list {
		if x == s {
			return true
		}
	}
	return false
}

func sortedSet(items []string) []string {
	seen := map[string]bool{}
	out := []string{}
	for _, s := range items {
		if !seen[s] {
			seen[s] = true
			out = append(out, s)
		}
	}
	sort.Strings(out)
	return out
}

func sha256Hex(s string) string {
	h := sha256.Sum256([]byte(s))
	return hex.EncodeToString(h[:])
}

func strsToAny(l []string) []any {
	out := make([]any, 0, len(l))
	for _, s := range l {
		out = append(out, s)
	}
	return out
}
