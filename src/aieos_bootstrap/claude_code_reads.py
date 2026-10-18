"""The Claude Code adapter's read-path extraction (task TASK-065; specification 5 revision 3, section 6's table row
"Observed read-set", sections 7 and 11 point 8; specification 2 revision 6, section 6.2 and section 10 point 13).

One pure function, called only by its tests:

``read_paths(stdin_bytes)``: from the bytes Claude Code would write to a PostToolUse hook's standard input after a
file-reading tool call to the list of paths that call read, the list that aieos_bootstrap.read_set_record.observe
takes, or "uncovered" with a reason. It returns a mapping with exactly result, reason, findings and read_paths.

The parse (AC1). The bytes are parsed as strictly as TASK-062's entry parses them (claude_code_hook.py, its entry):
bytes only, no byte-order mark, strict UTF-8, one JSON value with no duplicate key and no NaN or Infinity constant,
whose parse does not raise RecursionError (deep nesting), and a JSON object. The parse is restated here, not imported
from claude_code_hook's private helpers. Of the hook input only tool_name and tool_input are read; hook_event_name,
session_id, cwd, transcript_path, tool_response and every other key are not read, so placed on another hook event the
function gives the same result (placed on PreToolUse it would return the path before the read: over-inclusive).

The tools (AC2, AC3; specification 5 section 11 point 8, the read hook point's coverage):
- Read is covered: tool_input.file_path, a non-empty string, is the one path read, and the result is [file_path].
- Uncovered, reason "tool", listed as uncovered and never as an empty read: Grep and Glob (a search tool whose reads
  are not attributable: their input names a pattern and a folder, not the files read, and Grep does read file
  contents), Bash and PowerShell (reads by a shell command are not seen), every name beginning "mcp__", the subagent
  tools Task and Agent, and every other name, Write, Edit, MultiEdit and NotebookEdit among them (an Edit reads the
  file it changes; not taken here, a limit).
- A partial read (tool_input.offset or limit present) counts as a read of the whole path: the over-inclusive side,
  which is the fail-safe side for a read-set.
- A failed read is not seen: tool_response is not read, so the path is still returned (over-inclusive). The hooks
  documentation (summarised by a web-reading tool on 2026-10-18: a summary, not the page) says PostToolUse "Runs
  immediately after a tool completes successfully" and that failed calls go to a separate event,
  PostToolUseFailure, which this function is not meant for; placed there, it would return the path of a failed read.

The path (AC2). The path is the raw string of tool_input.file_path: not normalised, resolved, case-folded, stripped or
checked against any root, write-set or the disk, as TASK-064 records it. Specification 2 section 10 point 13 (the form
of read_paths) stays open. The alternative not chosen is claude_code.normalise_path(root, None, path), which would in
effect settle point 13 and make a relative path uncovered.

What this shows, and what it does not (AC6):
- The PostToolUse input form is cited from documentation and unmeasured (C6, the owner's to measure): the
  documentation says the input includes tool_input and tool_response, with tool_name in its example; Read's tool_input
  fields file_path, offset and limit are given in its PreToolUse section, and file-tool paths in PostToolUse arrive in
  the same format as for PreToolUse. That Read's file_path is in that input is so inferred from the documentation, not
  stated there for Read.
- The tool names are those seen in this project's transcripts, supported live only for Bash; in session 1947b313 a
  hook with matcher "*" did not refuse Read calls it was written to refuse (decisions D-1202 and D-1203), so whether a
  hook fires for Read is unknown and the live evidence is negative.
- A result is a lower bound at best (specification 5 line 73): the hook may not fire, may not cover a tool and cannot
  show its own completeness; the record built from these paths is kept and not used (specification 5 line 72).
- Gathering the paths across hook calls, the hook process and its context, placing the hook and choosing its matcher
  stay out (part CC-3, the owner's; specification 5 section 11 points 7 and 10).

Purity (AC7): it imports only the standard library's json module and nothing of aieos_bootstrap; it opens no file,
starts no process, reads no standard input, prints nothing, reads no clock or environment and makes no network or
model call. It keeps no state, and no exception escapes.
"""

import json

RESULT_KEYS = ('result', 'reason', 'findings', 'read_paths')
COVERED_TOOL = 'Read'
SEARCH_TOOLS = ('Grep', 'Glob')
SHELL_TOOLS = ('Bash', 'PowerShell')
SUBAGENT_TOOLS = ('Task', 'Agent')


def _result(result, reason, findings=(), paths=()):
    return {'result': result, 'reason': reason, 'findings': list(findings), 'read_paths': list(paths)}


def _uncovered(reason, finding):
    return _result('uncovered', reason, [finding])


def _no_duplicates(pairs):
    keys = [k for k, _ in pairs]
    if len(set(keys)) != len(keys):
        raise ValueError('a duplicate key')
    return dict(pairs)


def _no_constant(name):
    raise ValueError('a refused constant')


def _tool_class(tool):
    if tool in SEARCH_TOOLS:
        return 'a search tool whose reads are not attributable'
    if tool in SHELL_TOOLS:
        return 'a shell tool'
    if tool.startswith('mcp__'):
        return 'an MCP tool'
    if tool in SUBAGENT_TOOLS:
        return 'a subagent tool'
    return 'a tool not covered'


def _read_paths(stdin_bytes):
    if not isinstance(stdin_bytes, bytes):
        return _uncovered('argument', 'stdin_bytes is not a bytes object')
    if stdin_bytes.startswith(b'\xef\xbb\xbf'):
        return _uncovered('input_bytes', 'the input starts with a byte-order mark')
    try:
        text = stdin_bytes.decode('utf-8', 'strict')
    except UnicodeDecodeError:
        return _uncovered('input_bytes', 'the input is not UTF-8')
    try:
        value = json.loads(text, object_pairs_hook=_no_duplicates, parse_constant=_no_constant)
    except (ValueError, RecursionError):
        return _uncovered('input_json', 'the input is not one JSON value without duplicate keys or constants')
    if not isinstance(value, dict):
        return _uncovered('input_shape', 'the input is not a JSON object')
    tool = value.get('tool_name')
    inp = value.get('tool_input')
    if not isinstance(tool, str) or not isinstance(inp, dict):
        return _uncovered('input', 'tool_name is not a string or tool_input is not an object')
    if tool != COVERED_TOOL:
        return _uncovered('tool', _tool_class(tool))
    path = inp.get('file_path')
    if not isinstance(path, str) or not path:
        return _uncovered('input', 'tool_input.file_path is missing, empty or not a string')
    return _result('read', 'read', (), [path])


def read_paths(stdin_bytes):
    """The paths a file-reading tool call read, from a PostToolUse hook's input bytes (AC1 to AC4). No exception
    escapes."""
    try:
        return _read_paths(stdin_bytes)
    except Exception as e:  # noqa: BLE001 - AC4: any exception becomes a result, its type only
        return _uncovered('entry', '%s raised inside read_paths' % type(e).__name__)
