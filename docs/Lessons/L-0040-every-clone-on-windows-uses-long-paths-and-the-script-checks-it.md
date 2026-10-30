# L-0040: Every clone of this repository on Windows is made with core.longpaths stored in the clone, and the script checks it

Rule: Make every scratch clone of the repository with `git clone -c core.longpaths=true` (the option after the subcommand, so it is stored in the clone's own config), check `git config --local --get core.longpaths` in the clone before any other command there, and run no git command in a clone made without it.

- Status: active
- Category: technical
- Binding: record only. Related: D-1635, D-1577, D-3633, D-3896.

## Pattern
docs/History holds file names that are longer than the Windows path limit; a plain clone stops at the checkout ("Filename too long", "unable to checkout working tree"). `git -c core.longpaths=true clone` applies the setting to the clone process only and does not store it in the new clone, so the later commands in the clone would fail again.

## Occurrences
- **2026-10-30 (session 578ea88b, D-3895, D-3896, D-3897).** The first clone script (no long paths) stopped with seven "Filename too long" errors; the decision agent corrected the form (`git clone -c core.longpaths=true`, a check after `cd`); the retry cloned clone104r2 and the failed folder was kept.

## Why it happens
The earlier sessions' scripts carried the setting in their briefs and notes, not in the clone script, and the decision agent approved the script without the setting.

## Prevention and detection
- Copy the clone script from a script that has the setting and its check; read the script's clone line before the dry run.
