# DEF-0005: Measurement-protocol and WSL-era text to fix before measuring

- Status: set aside by the owner (2026-10-06)
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
