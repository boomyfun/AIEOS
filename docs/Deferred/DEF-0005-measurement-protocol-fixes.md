# DEF-0005: Measurement-protocol and WSL-era text to fix before measuring

- Status: open
- Opened: 2026-10-05 (../History/2026-10/2026-10-04-1817-idea-to-cs3v2.md)
- Deferred by: Claude (proposal, not a decision). MP changes were left until measurement planning (:4439).
- Decision group: B. Any change to the measurement protocol is group B, item 4. P6 is a section P row, item 6.

## What
These MP changes were drafted in CS-3 v1, which was never executed. CS-3 v2 changed only the DM. Line numbers refer to MP revision 3.
- §1.3: an exception for the minimal baseline (A39).
- Custody of the P-CRED artifact: MP:94 conflicts with MP:122 (§1.7).
- Probes that target `main`: MP:47 conflicts with P-GH-3.
- Native-runtime wording at MP:38 and MP:118 (A38); §0.4; the environment fingerprint.
- P-GH-3, P-GH-4 and P-GH-7 updated for A34 (token scopes kept).
- A P-GH-5 variant in which the agent edits the workflow file itself (REG-0-lite closure record).
- A general legend for "Superseded" markers, and a restructured MP §2.0.
- An owner question still open: the public detail level of the environment fingerprint, at the catalogue level drafted in CS-3 v1 or another level (:4237). CS-3 v1 was dropped, so it was never answered.

In the DM, the section C rows and P6 are still written for WSL2, although A38 records a native runtime (:4237).

## Why deferred
Claude stated at :4439 that these changes would wait until measurement is actually planned, and that the owner would be asked then.

## Resume when
When measurement planning starts (DEF-0004).

## Depends on
- DEF-0004.
- The CS-3 v1 drafts in `%USERPROFILE%\AIEOS-REG0-lite\CS` (`CS-3-plan.json`, `CS-3-mp.diff.txt`) can serve as a starting point.

## Log
- 2026-10-05: issues found in the next-step analysis (:3615) and in CS-3 v1 (:4237, :4344).
- 2026-10-06: kept out of CS-3 v2.
- 2026-10-06 (session 02bd7476): the owner wrote (:1299), about the questions and the baseline file Claude had sent: "những câu hỏi này hay file lần kiểm tra bào mật đầu tiên chẳng có ý nghĩa gì. Phiên bản Claude hay thông tin về máy chẳng để làm cái gì. ĐỪNG BAO GIỜ HỎI LẠI VỀ VẤN ĐỀ NÀY, NÓ KHÔNG ĐI VÀO TRỌNG TÂM CÔNG VIỆC LÀ BUILD AIEOS, giống như việc tôi yêu cầu Agent phải kiểm soát Claude để Claude làm đúng công việc, không được sai hướng, không lan man. Vậy mà giờ Agent lại đang đi sai hướng, lan man, vòng vo" Status: set aside by the owner (2026-10-06). Claude does not raise this again; it reopens only if the owner raises it in their own words (decision file D-038). ../History/2026-10/2026-10-06-2149-new-duties-and-owner-refocus.md
- 2026-10-06 (session 02bd7476): the owner wrote "hãy hoàn thành nốt đi, hãy làm đầy đủ" (:1711), quoting Claude's account of A14 steps 1-4, and "Hãy hoàn thành đi" (:1723). Status: resumed (2026-10-06) (decision file D-043; DM A45). Applied in measurement-protocol revision 4: the native-runtime wording of the fingerprint (MP:38, without new fields) and of the §1.6 cross-check (MP:118), the §1.3 exception for the minimal baseline (A39), the P-GH-4 note and P-GH-7 variant 6 (A34). Applied in DM revision 12: dated notes on section C rows C1, C2, C3, C6, C8 and C15 for the native runtime (A38); their statuses stay TBD. Still open, as Claude's proposals not adopted: the §0.4 exception for attempts on `main` (MP:47), the §1.7 custody rule (MP:122), the two new P-GH-3 rows, the Claude Code configuration fields in the fingerprint; also the P-GH-5 variant, the "Superseded" legend and the §2.0 restructure, and the P6 and P-LOC WSL wording; the owner question on the public detail level of the environment fingerprint (:4237), never answered. ../History/2026-10/2026-10-06-2309-a14-steps-2-to-4.md
- 2026-10-07 (session 02bd7476): after Claude's review of A14 steps 1-5 found step 2 complete only for the baseline, the owner wrote "làm theo đề xuất đi" (:2085) to Claude's proposal to finish the P-LOC wording first. Measurement-protocol revision 5 re-phrases §3 (P-LOC) for the native runtime (A38): heading, P-LOC-3, P-LOC-5, P-LOC-6; WSL stays a hardening option. Still open: the Claude proposals listed above, the P-GH-5 variant, the legend, the §2.0 restructure and the P6 wording. ../History/2026-10/2026-10-07-0019-a14-review-and-p-loc.md
- 2026-10-07 (session 2963e747): no work on this item is active after A46, so its status goes from resumed to open. Still open: the §0.4 exception for attempts on `main` (MP:47), the §1.7 custody rule (MP:122), the two new P-GH-3 rows, the Claude Code configuration fields in the fingerprint, the P-GH-5 variant, the "Superseded" legend, the §2.0 restructure, the P6 wording, and the owner question on the public detail level of the environment fingerprint (:4237), never answered. Added: MP §6 (its last line), §1.1 and §1.5 still read as if hardening and every measurement come before the later A14 steps; A44 and A46, the owner's later words, changed that. These wait until measurement planning resumes; Claude does not raise them (decision file D-038). Decision files D-055, D-056. ../History/2026-10/2026-10-07-0100-a14-steps-1-5-audit.md
