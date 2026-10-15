package main

// The JSON values of the port, a strict reader of them, and the canonical text of conformance.canonical_text.
//
// Values read from the fixture document are:
//   nil (null), bool, *big.Int (an integer; Python's ints have no bound), string, []any and *Obj (an object that
//   keeps its keys in document order).
// Records built by the port are map[string]any; canonText sorts the keys of both object kinds.

import (
	"errors"
	"fmt"
	"math/big"
	"sort"
	"strings"
	"unicode/utf8"
)

// Obj is a JSON object that keeps its keys in the order of the document.
type Obj struct {
	keys []string
	vals map[string]any
}

func newObj() *Obj { return &Obj{vals: map[string]any{}} }

// Get is Python's dict.get: the value and whether the key is present.
func (o *Obj) Get(k string) (any, bool) {
	v, ok := o.vals[k]
	return v, ok
}

// Val is Python's dict.get(k): the value, or nil when the key is absent.
func (o *Obj) Val(k string) any { return o.vals[k] }

// Has is Python's "k in o".
func (o *Obj) Has(k string) bool {
	_, ok := o.vals[k]
	return ok
}

// Keys are the keys in document order.
func (o *Obj) Keys() []string { return o.keys }

// Set adds or replaces a key (used by the tests to build documents).
func (o *Obj) Set(k string, v any) {
	if _, ok := o.vals[k]; !ok {
		o.keys = append(o.keys, k)
	}
	o.vals[k] = v
}

// Del removes a key (used by the tests to build documents).
func (o *Obj) Del(k string) {
	if _, ok := o.vals[k]; !ok {
		return
	}
	delete(o.vals, k)
	out := o.keys[:0]
	for _, x := range o.keys {
		if x != k {
			out = append(out, x)
		}
	}
	o.keys = out
}

// keysAre is Python's set(o) == {keys...} (the keys given are distinct).
func (o *Obj) keysAre(keys ...string) bool {
	if len(o.keys) != len(keys) {
		return false
	}
	for _, k := range keys {
		if !o.Has(k) {
			return false
		}
	}
	return true
}

// The bounds of the reader. Python's int() refuses a decimal text of more than 4300 digits (its default
// int_max_str_digits), so json.loads refuses such a number; the depth bound stands for Python's recursion limit
// (a stated limit: a document nested deeper is refused, where Python may refuse it a little later or earlier).
const (
	maxIntDigits = 4300
	maxDepth     = 512
)

var errNotJSON = errors.New("not one JSON value")

type reader struct {
	s     []byte
	i     int
	depth int
}

// parseJSON reads one JSON value as json.loads does with conformance._loads's hooks: a repeated key, a number with
// a fraction or an exponent, and NaN or the infinities are refused. A string escape that leaves a lone surrogate is
// refused too, since no Go string holds one (such a text is never canonical, so no fixture document has one).
func parseJSON(data []byte) (any, error) {
	if !utf8.Valid(data) {
		return nil, errors.New("the text is not UTF-8")
	}
	r := &reader{s: data}
	r.ws()
	v, err := r.value()
	if err != nil {
		return nil, err
	}
	r.ws()
	if r.i != len(r.s) {
		return nil, fmt.Errorf("%w: extra data at byte %d", errNotJSON, r.i)
	}
	return v, nil
}

func (r *reader) ws() {
	for r.i < len(r.s) {
		switch r.s[r.i] {
		case ' ', '\t', '\n', '\r':
			r.i++
		default:
			return
		}
	}
}

func (r *reader) fail(what string) error {
	return fmt.Errorf("%w: %s at byte %d", errNotJSON, what, r.i)
}

func (r *reader) value() (any, error) {
	if r.i >= len(r.s) {
		return nil, r.fail("unexpected end")
	}
	switch c := r.s[r.i]; {
	case c == '{':
		return r.object()
	case c == '[':
		return r.array()
	case c == '"':
		return r.str()
	case c == '-' || (c >= '0' && c <= '9'):
		return r.number()
	case r.lit("true"):
		return true, nil
	case r.lit("false"):
		return false, nil
	case r.lit("null"):
		return nil, nil
	}
	return nil, r.fail("unexpected character")
}

func (r *reader) lit(word string) bool {
	if strings.HasPrefix(string(r.s[r.i:min(len(r.s), r.i+len(word))]), word) {
		r.i += len(word)
		return true
	}
	return false
}

func (r *reader) enter() error {
	r.depth++
	if r.depth > maxDepth {
		return r.fail("nested too deeply")
	}
	return nil
}

func (r *reader) object() (any, error) {
	if err := r.enter(); err != nil {
		return nil, err
	}
	defer func() { r.depth-- }()
	r.i++ // '{'
	o := newObj()
	r.ws()
	if r.i < len(r.s) && r.s[r.i] == '}' {
		r.i++
		return o, nil
	}
	for {
		r.ws()
		if r.i >= len(r.s) || r.s[r.i] != '"' {
			return nil, r.fail("a key is not a string")
		}
		k, err := r.str()
		if err != nil {
			return nil, err
		}
		key := k.(string)
		if o.Has(key) {
			return nil, r.fail("a repeated key")
		}
		r.ws()
		if r.i >= len(r.s) || r.s[r.i] != ':' {
			return nil, r.fail("no colon")
		}
		r.i++
		r.ws()
		v, err := r.value()
		if err != nil {
			return nil, err
		}
		o.Set(key, v)
		r.ws()
		if r.i >= len(r.s) {
			return nil, r.fail("unexpected end")
		}
		if r.s[r.i] == ',' {
			r.i++
			continue
		}
		if r.s[r.i] == '}' {
			r.i++
			return o, nil
		}
		return nil, r.fail("no comma or closing brace")
	}
}

func (r *reader) array() (any, error) {
	if err := r.enter(); err != nil {
		return nil, err
	}
	defer func() { r.depth-- }()
	r.i++ // '['
	out := []any{}
	r.ws()
	if r.i < len(r.s) && r.s[r.i] == ']' {
		r.i++
		return out, nil
	}
	for {
		r.ws()
		v, err := r.value()
		if err != nil {
			return nil, err
		}
		out = append(out, v)
		r.ws()
		if r.i >= len(r.s) {
			return nil, r.fail("unexpected end")
		}
		if r.s[r.i] == ',' {
			r.i++
			continue
		}
		if r.s[r.i] == ']' {
			r.i++
			return out, nil
		}
		return nil, r.fail("no comma or closing bracket")
	}
}

func isDigit(c byte) bool { return c >= '0' && c <= '9' }

func (r *reader) number() (any, error) {
	start := r.i
	if r.s[r.i] == '-' {
		r.i++
	}
	if r.i >= len(r.s) || !isDigit(r.s[r.i]) {
		return nil, r.fail("a malformed number")
	}
	digits := r.i
	if r.s[r.i] == '0' {
		r.i++
	} else {
		for r.i < len(r.s) && isDigit(r.s[r.i]) {
			r.i++
		}
	}
	if r.i < len(r.s) && (r.s[r.i] == '.' || r.s[r.i] == 'e' || r.s[r.i] == 'E') {
		return nil, r.fail("a number with a fraction or an exponent")
	}
	if r.i-digits > maxIntDigits {
		return nil, r.fail("an integer of more than 4300 digits")
	}
	n, ok := new(big.Int).SetString(string(r.s[start:r.i]), 10)
	if !ok {
		return nil, r.fail("a malformed number")
	}
	return n, nil
}

func hex4(b []byte) (rune, bool) {
	if len(b) < 4 {
		return 0, false
	}
	var v rune
	for _, c := range b[:4] {
		v <<= 4
		switch {
		case c >= '0' && c <= '9':
			v |= rune(c - '0')
		case c >= 'a' && c <= 'f':
			v |= rune(c-'a') + 10
		case c >= 'A' && c <= 'F':
			v |= rune(c-'A') + 10
		default:
			return 0, false
		}
	}
	return v, true
}

func (r *reader) str() (any, error) {
	r.i++ // '"'
	var b strings.Builder
	for {
		if r.i >= len(r.s) {
			return nil, r.fail("an unterminated string")
		}
		c := r.s[r.i]
		switch {
		case c == '"':
			r.i++
			return b.String(), nil
		case c < 0x20:
			return nil, r.fail("a control character in a string")
		case c != '\\':
			b.WriteByte(c)
			r.i++
			continue
		}
		r.i++
		if r.i >= len(r.s) {
			return nil, r.fail("an unterminated escape")
		}
		e := r.s[r.i]
		r.i++
		switch e {
		case '"', '\\', '/':
			b.WriteByte(e)
		case 'b':
			b.WriteByte('\b')
		case 'f':
			b.WriteByte('\f')
		case 'n':
			b.WriteByte('\n')
		case 'r':
			b.WriteByte('\r')
		case 't':
			b.WriteByte('\t')
		case 'u':
			u, ok := hex4(r.s[r.i:])
			if !ok {
				return nil, r.fail("a malformed \\u escape")
			}
			r.i += 4
			if u >= 0xd800 && u <= 0xdbff {
				if r.i+1 < len(r.s) && r.s[r.i] == '\\' && r.s[r.i+1] == 'u' {
					lo, ok := hex4(r.s[r.i+2:])
					if ok && lo >= 0xdc00 && lo <= 0xdfff {
						r.i += 6
						b.WriteRune(0x10000 + (u-0xd800)<<10 + (lo - 0xdc00))
						continue
					}
				}
				return nil, r.fail("a lone surrogate")
			}
			if u >= 0xdc00 && u <= 0xdfff {
				return nil, r.fail("a lone surrogate")
			}
			b.WriteRune(u)
		default:
			return nil, r.fail("an unknown escape")
		}
	}
}

// ---------------------------------------------------------------------------------------------------------------
// The canonical text (conformance.canon and conformance.canonical_text)

// canonicalText is conformance.canonical_text: the canonical text of one value with its final LF.
func canonicalText(v any) ([]byte, error) {
	var b strings.Builder
	if err := canon(&b, v, 0); err != nil {
		return nil, err
	}
	b.WriteByte('\n')
	return []byte(b.String()), nil
}

// canonString is the canonical text of one value without the final LF.
func canonString(v any) (string, error) {
	var b strings.Builder
	if err := canon(&b, v, 0); err != nil {
		return "", err
	}
	return b.String(), nil
}

func canonKey(b *strings.Builder, s string) {
	b.WriteByte('"')
	for _, ch := range s {
		switch {
		case ch == '"' || ch == '\\':
			b.WriteByte('\\')
			b.WriteRune(ch)
		case ch < 0x20:
			fmt.Fprintf(b, "\\u%04x", ch)
		default:
			b.WriteRune(ch)
		}
	}
	b.WriteByte('"')
}

func canonObject(b *strings.Builder, keys []string, get func(string) any, indent int) error {
	if len(keys) == 0 {
		b.WriteString("{}")
		return nil
	}
	sorted := append([]string(nil), keys...)
	sort.Strings(sorted) // byte order of UTF-8 is the order of code points, as Python's sorted
	pad := strings.Repeat(" ", indent+2)
	b.WriteString("{\n")
	for n, k := range sorted {
		if n > 0 {
			b.WriteString(",\n")
		}
		b.WriteString(pad)
		canonKey(b, k)
		b.WriteString(": ")
		if err := canon(b, get(k), indent+2); err != nil {
			return err
		}
	}
	b.WriteString("\n" + strings.Repeat(" ", indent) + "}")
	return nil
}

func canonList(b *strings.Builder, n int, at func(int) any, indent int) error {
	if n == 0 {
		b.WriteString("[]")
		return nil
	}
	pad := strings.Repeat(" ", indent+2)
	b.WriteString("[\n")
	for i := 0; i < n; i++ {
		if i > 0 {
			b.WriteString(",\n")
		}
		b.WriteString(pad)
		if err := canon(b, at(i), indent+2); err != nil {
			return err
		}
	}
	b.WriteString("\n" + strings.Repeat(" ", indent) + "]")
	return nil
}

func canon(b *strings.Builder, v any, indent int) error {
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
		canonKey(b, x)
	case *Obj:
		return canonObject(b, x.keys, x.Val, indent)
	case map[string]any:
		keys := make([]string, 0, len(x))
		for k := range x {
			keys = append(keys, k)
		}
		return canonObject(b, keys, func(k string) any { return x[k] }, indent)
	case []any:
		return canonList(b, len(x), func(i int) any { return x[i] }, indent)
	case []string:
		return canonList(b, len(x), func(i int) any { return x[i] }, indent)
	case []map[string]any:
		return canonList(b, len(x), func(i int) any { return x[i] }, indent)
	default:
		return fmt.Errorf("a value of type %T has no canonical form", v)
	}
	return nil
}

// ---------------------------------------------------------------------------------------------------------------
// Python's equality of two JSON values (==), used where the Python compares values that may not be strings.

func pyEq(a, b any) bool {
	switch x := a.(type) {
	case nil:
		return b == nil
	case bool:
		switch y := b.(type) {
		case bool:
			return x == y
		case *big.Int:
			return boolInt(x).Cmp(y) == 0
		}
		return false
	case *big.Int:
		switch y := b.(type) {
		case bool:
			return x.Cmp(boolInt(y)) == 0
		case *big.Int:
			return x.Cmp(y) == 0
		}
		return false
	case string:
		y, ok := b.(string)
		return ok && x == y
	case []any:
		y, ok := b.([]any)
		if !ok || len(x) != len(y) {
			return false
		}
		for i := range x {
			if !pyEq(x[i], y[i]) {
				return false
			}
		}
		return true
	case *Obj:
		y, ok := b.(*Obj)
		if !ok || len(x.keys) != len(y.keys) {
			return false
		}
		for _, k := range x.keys {
			yv, ok := y.Get(k)
			if !ok || !pyEq(x.vals[k], yv) {
				return false
			}
		}
		return true
	}
	return false
}

func boolInt(v bool) *big.Int {
	if v {
		return big.NewInt(1)
	}
	return big.NewInt(0)
}
