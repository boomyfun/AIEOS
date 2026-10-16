package main

// Python's text forms that round 2's findings and lines are made of: repr() and str() of a JSON value (for "%r" and
// "%s"), json.dumps(..., sort_keys=True, separators=(',', ':'), ensure_ascii=True) (eventlog._canonical), str.strip()
// and str.lower() as recovery.trailers uses them, and the SHA-256 hex digest of a UTF-8 text (crypto/sha256).

import (
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"math/big"
	"sort"
	"strings"
	"unicode"
)

// stop is raised (as a panic) where the port fails closed: a call or case it cannot compute, or one where the
// Python would build a text that names a Python type or holds a message of Python's own library (the brief's section 6.3).
// buildRound2 turns it, and any other panic, into an error.
type stop struct{ why string }

func failClosed(format string, a ...any) {
	panic(stop{fmt.Sprintf(format, a...)})
}

// hexDigest is hashlib.sha256(text.encode('utf-8')).hexdigest().
func hexDigest(text string) string {
	h := sha256.Sum256([]byte(text))
	return hex.EncodeToString(h[:])
}

// pyRepr is Python's repr() of a JSON value as round 2 reads it (dict keys in document order).
func pyRepr(v any) string {
	switch x := v.(type) {
	case nil:
		return "None"
	case bool:
		if x {
			return "True"
		}
		return "False"
	case *big.Int:
		return x.String()
	case int:
		return fmt.Sprintf("%d", x)
	case string:
		return pyStrRepr(x)
	case []any:
		parts := make([]string, len(x))
		for i, e := range x {
			parts[i] = pyRepr(e)
		}
		return "[" + strings.Join(parts, ", ") + "]"
	case *Obj:
		parts := make([]string, len(x.keys))
		for i, k := range x.keys {
			parts[i] = pyStrRepr(k) + ": " + pyRepr(x.vals[k])
		}
		return "{" + strings.Join(parts, ", ") + "}"
	}
	failClosed("no repr for a value of type %T", v)
	return ""
}

// pyStr is Python's str() of a JSON value ("%s"): a string itself, any other value its repr.
func pyStr(v any) string {
	if s, ok := v.(string); ok {
		return s
	}
	return pyRepr(v)
}

// pyStrRepr is Python's repr() of a str: single quotes unless the text holds ' and no ", the quote and the backslash
// escaped, \t \n \r, \xNN, \uNNNN or \UNNNNNNNN for a character that is not printable. Printability is Go's
// unicode.IsPrint, the same classes as Python's str.isprintable (a stated limit: their Unicode versions may differ;
// a printable non-ASCII character is never in the ASCII output, so such a text fails closed in any case).
func pyStrRepr(s string) string {
	quote := '\''
	if strings.ContainsRune(s, '\'') && !strings.ContainsRune(s, '"') {
		quote = '"'
	}
	var b strings.Builder
	b.WriteRune(quote)
	for _, r := range s {
		switch {
		case r == quote || r == '\\':
			b.WriteByte('\\')
			b.WriteRune(r)
		case r == '\t':
			b.WriteString(`\t`)
		case r == '\n':
			b.WriteString(`\n`)
		case r == '\r':
			b.WriteString(`\r`)
		case r < 0x20 || r == 0x7f:
			fmt.Fprintf(&b, `\x%02x`, r)
		case r < 0x7f:
			b.WriteRune(r)
		case unicode.IsPrint(r):
			b.WriteRune(r)
		case r <= 0xff:
			fmt.Fprintf(&b, `\x%02x`, r)
		case r <= 0xffff:
			fmt.Fprintf(&b, `\u%04x`, r)
		default:
			fmt.Fprintf(&b, `\U%08x`, r)
		}
	}
	b.WriteRune(quote)
	return b.String()
}

// pyDumps is json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).
func pyDumps(v any) string {
	var b strings.Builder
	dumpValue(&b, v)
	return b.String()
}

func dumpString(b *strings.Builder, s string) {
	b.WriteByte('"')
	for _, r := range s {
		switch {
		case r == '"':
			b.WriteString(`\"`)
		case r == '\\':
			b.WriteString(`\\`)
		case r == '\b':
			b.WriteString(`\b`)
		case r == '\f':
			b.WriteString(`\f`)
		case r == '\n':
			b.WriteString(`\n`)
		case r == '\r':
			b.WriteString(`\r`)
		case r == '\t':
			b.WriteString(`\t`)
		case r >= ' ' && r <= '~':
			b.WriteRune(r)
		case r > 0xffff:
			r -= 0x10000
			fmt.Fprintf(b, `\u%04x\u%04x`, 0xd800+(r>>10), 0xdc00+(r&0x3ff))
		default:
			fmt.Fprintf(b, `\u%04x`, r)
		}
	}
	b.WriteByte('"')
}

func dumpObject(b *strings.Builder, keys []string, get func(string) any) {
	sorted := append([]string(nil), keys...)
	sort.Strings(sorted)
	b.WriteByte('{')
	for i, k := range sorted {
		if i > 0 {
			b.WriteByte(',')
		}
		dumpString(b, k)
		b.WriteByte(':')
		dumpValue(b, get(k))
	}
	b.WriteByte('}')
}

func dumpValue(b *strings.Builder, v any) {
	switch x := v.(type) {
	case nil:
		b.WriteString("null")
	case bool:
		if x {
			b.WriteString("true")
		} else {
			b.WriteString("false")
		}
	case *big.Int:
		b.WriteString(x.String())
	case int:
		fmt.Fprintf(b, "%d", x)
	case string:
		dumpString(b, x)
	case []any:
		b.WriteByte('[')
		for i, e := range x {
			if i > 0 {
				b.WriteByte(',')
			}
			dumpValue(b, e)
		}
		b.WriteByte(']')
	case *Obj:
		dumpObject(b, x.keys, x.Val)
	case map[string]any:
		keys := make([]string, 0, len(x))
		for k := range x {
			keys = append(keys, k)
		}
		dumpObject(b, keys, func(k string) any { return x[k] })
	default:
		failClosed("no JSON text for a value of type %T", v)
	}
}

// sameText is a text that two JSON values share exactly when Python's canonical JSON texts of them are equal (their
// keys sorted, true, 1 and "1" apart): the canonical text of conformance.canon, which is such a text.
func sameText(v any) string {
	s, err := canonString(v)
	if err != nil {
		failClosed("%v", err)
	}
	return s
}

// pyIsSpace is Python's str.isspace() for one character.
func pyIsSpace(r rune) bool {
	switch {
	case r >= '\t' && r <= '\r', r >= 0x1c && r <= 0x20, r == 0x85, r == 0xa0, r == 0x1680,
		r >= 0x2000 && r <= 0x200a, r == 0x2028, r == 0x2029, r == 0x202f, r == 0x205f, r == 0x3000:
		return true
	}
	return false
}

// pyStrip is Python's str.strip() with no argument.
func pyStrip(s string) string {
	return strings.TrimFunc(s, pyIsSpace)
}

// pyLower is Python's str.lower(): Go's simple lower-case mapping, with the one unconditional mapping of Unicode's
// special casing to more than one character (U+0130 to "i" and U+0307). Python's final-sigma rule maps a capital
// sigma to another non-ASCII letter, which matches no trailer key either way.
func pyLower(s string) string {
	var b strings.Builder
	for _, r := range s {
		if r == 0x130 {
			b.WriteString("i\xcc\x87") // "i" and U+0307 in UTF-8
			continue
		}
		b.WriteRune(unicode.ToLower(r))
	}
	return b.String()
}
