"""The real runtime starter of `aieos launch` (task TASK-132, contract AC1 to AC8), standard library only.

starter(env) is the starter that the entry line of cli.py passes to launcher.launch_outside: it is called with the
launcher's environment copy (exactly AIEOS_SESSION_ID, AIEOS_ROOT and AIEOS_BASE), starts the pinned Claude Code program
through ONE process form and waits for it to end. It is a caller of the launcher, not part of the core: it imports no
module of aieos_bootstrap, writes no event, calls no governor, reconcile, done or writer function and adds no acceptance
logic. Before any process starts it refuses (StarterError) an env out of form, a starter environment without PATH, and an
executable or runtime file that is missing, is not a regular file or whose SHA-256 differs from the pinned one; a target
that does not end in .exe (a .cmd or .bat file included) is refused outright. The process is started with no shell,
standard input closed, the root as its working directory and a fixed timeout; the runtime's output is inherited, not
captured. A timeout or a non-zero exit raises StarterError, which launch_outside records before it ends the session.
Stated limits: the file can change between the hash check and the start; a permission prompt the runtime denies is not
detected here; child processes the runtime started may survive its termination; a session longer than the timeout is
ended by it (no lease renewal); a new version of the desktop app changes the folder name and the hash, so the starter
refuses until a new pin is decided. Each pinned name below is bound once, to a constant string."""

import hashlib
import ntpath
import os
import re
import subprocess
from pathlib import Path

EXE_PATH = 'C:\\Users\\Admin\\AppData\\Roaming\\Claude\\claude-code\\2.1.321\\d0e23af87588\\claude.exe'
EXE_SHA256 = 'e6dae5fc45902b15751f2591a02f51760351c4788c5fd8291b3f1443d40c13a4'
PROMPT = ('Call the AIEOS tool get_work_order of the connected aieos MCP server, do the work its Work Order describes '
          'within its limits, and stop when it is done.')
MCP_FILE = 'C:\\Users\\Admin\\AIEOS-runtime\\claude-mcp.json'
MCP_SHA256 = 'cbfc039cd668ca362c5713ad5498a3c18eeca7a59505363756e303c81035f882'
SETTINGS_FILE = 'C:\\Users\\Admin\\AIEOS-runtime\\claude-settings.json'
SETTINGS_SHA256 = 'bb9c8724b7e24955f07ea185b045008adcf313dfe9ecc9268a3023c9e75bf26b'

# the environment of the process (AC6): the three variables of the launcher's copy, then the listed variables of the
# starter's own environment that are present; nothing else is passed
ENV_FROM_LAUNCHER = ('AIEOS_SESSION_ID', 'AIEOS_ROOT', 'AIEOS_BASE')
ENV_FROM_PROCESS = ('PATH', 'SYSTEMROOT', 'SYSTEMDRIVE', 'COMSPEC', 'PATHEXT', 'USERPROFILE', 'APPDATA',
                    'LOCALAPPDATA', 'TEMP', 'TMP')


class StarterError(Exception):
    """The starter refused to start the runtime, or the runtime did not end well."""


def _launcher_value(env, key):
    try:
        found = env[key]
    except (KeyError, IndexError, TypeError):
        raise StarterError('the launcher environment lacks ' + key) from None
    if type(found) is not str:
        raise StarterError(key + ' is not a string')
    return found


def _check_env(env):
    """The three values of the launcher's environment, each checked for its form (AC1)."""
    session = _launcher_value(env, 'AIEOS_SESSION_ID')
    if re.fullmatch(r'[A-Za-z0-9._-]{1,128}', session) is None:
        raise StarterError('AIEOS_SESSION_ID is out of form')
    root = _launcher_value(env, 'AIEOS_ROOT')
    if not ntpath.isabs(root):
        raise StarterError('AIEOS_ROOT is not an absolute path')
    base = _launcher_value(env, 'AIEOS_BASE')
    if re.fullmatch(r'[0-9a-f]{40}', base) is None:
        raise StarterError('AIEOS_BASE is not 40 lowercase hexadecimal characters')
    return {'AIEOS_SESSION_ID': session, 'AIEOS_ROOT': root, 'AIEOS_BASE': base}


def _check_file(path, digest, what):
    """A regular file whose SHA-256 is the pinned one; the bytes are read once, for the hash only (AC2, AC3)."""
    target = Path(path)
    if not target.is_file():
        raise StarterError(what + ' is missing or is not a regular file')
    if hashlib.sha256(target.read_bytes()).hexdigest() != digest:
        raise StarterError(what + ' has another SHA-256 than the pinned one')


def _child_environment(values):
    child = dict(values)
    for key in ENV_FROM_PROCESS:
        if key in os.environ:
            child[key] = os.environ[key]
    return child


def starter(env):
    """Start the pinned runtime once and wait for it; return None; raise StarterError for any refusal or failure."""
    values = _check_env(env)
    if 'PATH' not in os.environ:
        raise StarterError('the starter environment has no PATH')
    if ntpath.splitext(EXE_PATH)[1] != '.exe':
        raise StarterError('the executable does not end in .exe')
    _check_file(EXE_PATH, EXE_SHA256, 'the executable')
    _check_file(MCP_FILE, MCP_SHA256, 'the MCP file')
    _check_file(SETTINGS_FILE, SETTINGS_SHA256, 'the settings file')
    child = _child_environment(values)
    try:
        result = subprocess.run([EXE_PATH, '-p', PROMPT, '--permission-prompts', 'none', '--strict-mcp-config',
                                 '--mcp-config', MCP_FILE, '--settings', SETTINGS_FILE],
                                shell=False, stdin=subprocess.DEVNULL, cwd=values['AIEOS_ROOT'], env=child,
                                timeout=6600, check=False)
    except subprocess.TimeoutExpired:
        raise StarterError('the runtime did not end within 6600 seconds') from None
    if result.returncode != 0:
        raise StarterError('the runtime ended with exit code ' + str(result.returncode))
    return None
