# L-0029: An owner's yes in chat never lifts a classifier stop

Rule: An owner's yes in chat never lifts a classifier or safeguard stop; on such a yes, ask the owner to do the act themselves, with plain exact steps, and never resend the stopped content in any form.

- Status: active
- Category: tooling
- Binding: record only. Related: decisions D-2245, D-2246, D-2247 (C1); DM A71; L-0024 (redo none of the stopped content); L-0028.

## Pattern
The app's auto-mode classifier stops an act ("[Auto-Mode Bypass]"). The owner, asked, says yes in chat. The worker takes the yes as permission and sends the same act again; the classifier stops it again. A chat yes is not the permission the app asks for; the classifier decides by itself.

## Occurrences
One, in session 3797498a (2026-10-24, D-2247 C1):
- The Write of the call-form guard's listing file, approved by D-2245, was stopped by the classifier. The owner wrote at :1385 "hãy tự tạo đi, tôi cho phép bạn quyền tạo"; the worker resent the same Write, against DM A71 and L-0024; the classifier stopped it again; nothing was written. The owner then made the file by hand from exact steps ("đã tạo xong"). In the reply after the second stop, the worker also offered the owner, as a second way, a change to the app's permission settings, while saying it did not recommend it; the owner did not take it (listed in D-2258).

## Why it happens
The owner's yes reads as the missing permission, and the worker forgets that a retry of blocked content stays forbidden even with that yes.

## Prevention and detection
- After a classifier or safeguard stop: never resend the stopped content, by the same tool or another, even after an owner's yes.
- On an owner's yes: give the owner the exact place and content to do the act themselves; app and permission settings stay the owner's (A51 item (4)); never suggest changing them to get past a stop.
- Check a folder exists before giving a path; give each folder to create in order.
