# DEF-0004: Trust-boundary measurements (A14 step 3)

- Status: resumed (2026-10-06)
- Opened: 2026-10-05 (../History/2026-10/2026-10-04-1817-idea-to-cs3v2.md)
- Deferred by: owner. The authorization table at transcript :814 (see the source notes in the session History) marks "Đo probes / đánh dấu MEASURED" as "NO". No measurement was authorized at the end of the session.
- Decision group: B (group B, item 4 of the decision agent's lists; DM A30, A31; Claude never sets MEASURED)

## What
A14 step 3 covers the measurements P-CRED, P-GH, P-LOC and C13 defined in the MP. Their results decide the DM section C rows. The known parts:
- **P-CRED baseline,** at the minimal level of A39: does Claude run inside the owner's Windows session? Under MP §1.5 and §6, the baseline must run, and its finding be approved, before the owner chooses a hardening configuration. The detailed probe checklist stays out of the public repository (MP §1.3).
- **P-GH.**
  - Claude proposed not to run it before P-GH-3, P-GH-4 and P-GH-7 are updated for A34 (:3539; see DEF-0005).
  - Whether a token with the `workflow` scope can change workflow files is to be measured, not assumed.
- **Owner-side preparation** listed at :939:
  - rulesets R1/R2/R3 configured, disabled, for P-GH-1 (DM B16);
  - a signing key with user presence (A23, C14).
- **C6:** the hook behaviour of the installed Claude Code needs a live test: SessionStart after compaction, and Stop-hook loop protection.
- **C15 and P6** depend on the results (see DEF-0009).

## Why deferred
- Each measurement is the owner's decision (A30 to A32).
- On 2026-10-05 Claude deferred the P-CRED baseline, deciding under the owner's delegation (:3802; decision C, :3834).
- The v3 draft of the minimal baseline was not adopted.

## Resume when
The owner authorizes a specific measurement in their own words.

## Depends on
- DEF-0005 (MP fixes).
- The owner's time to run or supervise the authoritative run (A30).

## Log
- 2026-10-05: MP written and committed in 238fae0 (:749, :939).
- 2026-10-05: P-CRED minimal baseline drafted v1 to v3; v3 was shown in chat only (:3677), then deferred (:3834).
- 2026-10-06: the owner said yes to the minimal baseline scope ("đồng ý tất cả.", :4443), recorded as A39 in 79f5a39. Still no measurement authorized.
- 2026-10-06 (session 02bd7476): the owner wrote (:1299), about the questions and the baseline file Claude had sent: "những câu hỏi này hay file lần kiểm tra bào mật đầu tiên chẳng có ý nghĩa gì. Phiên bản Claude hay thông tin về máy chẳng để làm cái gì. ĐỪNG BAO GIỜ HỎI LẠI VỀ VẤN ĐỀ NÀY, NÓ KHÔNG ĐI VÀO TRỌNG TÂM CÔNG VIỆC LÀ BUILD AIEOS, giống như việc tôi yêu cầu Agent phải kiểm soát Claude để Claude làm đúng công việc, không được sai hướng, không lan man. Vậy mà giờ Agent lại đang đi sai hướng, lan man, vòng vo" Status: set aside by the owner (2026-10-06). Claude does not raise this again; it reopens only if the owner raises it in their own words (decision file D-038). ../History/2026-10/2026-10-06-2149-new-duties-and-owner-refocus.md
- 2026-10-06 (session 02bd7476): the owner wrote "hãy hoàn thành nốt đi, hãy làm đầy đủ" (:1711), quoting Claude's account of A14 steps 1-4, and "Hãy hoàn thành đi" (:1723). Status: resumed (2026-10-06) (decision file D-043; DM A45). Next: the A39 minimal P-CRED baseline, run by the owner (A30). ../History/2026-10/2026-10-06-2309-a14-steps-2-to-4.md
