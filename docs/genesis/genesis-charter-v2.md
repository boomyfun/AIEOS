# AIEOS Genesis Charter, version 2

> **Status: Genesis instance 2 (Genesis version 2), draft, not ratified.** A Genesis amendment (`genesis-model.md` §5) that carries the owner's answers of 2026-10-08 recorded in `decision-matrix.md` (DM) row A59. Written under decisions of the decision agent (A41; decision files D-165, D-168 and D-169); not an owner decision. Names (A53): gov-AIEOS is what is used to build AIEOS; AIEOS is the product.
> The instance consists of this charter and its ratification record. The ratification record lies outside this charter, because it records this charter's SHA-256 (`genesis-model.md` §2, §6, §7). Until that record exists, nothing here is bound, and Genesis version 1 stays in force.
> Pins. Every SHA-256 below is computed by the generator, not typed: of a file, of one line of a file (the SHA-256 of the whole line's UTF-8 bytes, any leading "| " or "- " included, without its line end), or of the DM section E extract described in section 4. (1) The items this amendment does not change are bound as of commit `c084f1475052bb0af0c40fbc0302666b4da966e9`, GitHub main when this charter was generated; the generator checked that each of them there equals its version-1 binding. (2) The files this amendment changes (items 1, 5, 6 and 7, and CR-002 in item 3) are bound by the SHA-256 of their new contents; the ratification record names the commit that adds them, which is one isolated change (`genesis-model.md` §5 point 1). (3) Item 3's DM rows and the DM file are read at version 1's pinned commit `02b7a5db6f0102c1d9267f368c80e052fbe1c8ab`, as in version 1 (section 3).
> Effect: advisory. The minimal P-CRED baseline is FAIL, and C13 is FAIL by implication (DM section D; C2, C13); every authority claim recorded or bound here, the owner's or a delegated one, is at most advisory (A31, A41; `genesis-model.md` §8); a delegated one stays advisory even if P-CRED later passes (A41; A55; CR-002 part 1). No boundary implementation is ratified as a trust boundary (A14; `genesis-model.md` §4).
> Who ratifies (`genesis-model.md` §5 point 3; CR-002 parts 4 and 8; A54 points 1 and 3; decision D-169 C6): the owner's yes on the exact texts of the changed files and on the changed bindings of this charter, item 3 included; then the decision agent ratifies this instance in the owner's place (A51 item (3)) only for the items that are unchanged from version 1.

## 1. This instance

- Genesis version: 2. Previous version: 1, `docs/genesis/genesis-charter-v1.md`, SHA-256 81ccfce88ac616cf31c0fa1a78932c7e1582fda47622b1c095ce329bf23c085d, ratified in the owner's place as recorded in DM row F8 (decision file D-126). This version records that hash, so the versions form a chain (A27; `genesis-model.md` §5 point 4).
- What this amendment changes: item 1 (CR-001: E4 and E10 get their texts; CR-002: dated notes in parts 4, 5, 7 and 8), item 3 (the hash of CR-002 only), item 5 (`assurance-model.md` revision 5), item 6 (`conformance-scenarios-initial.md` revision 4: set version 2, with ACC-16 and ACC-17) and item 7 (`governor-spec.md` revision 5). Nothing else changes. Both of the owner's answers recorded in A59 are carried in this one amendment, because they came in one message and one approved drafting plan (decision D-165); it is one isolated change in that sense (`genesis-model.md` §5 point 1).
- Verifiers bind to the Genesis version and its hash and to the immutable identities of item 9a; never to a repository name, an owner display name or login, a branch or a tag (A27).
- No owner signing key is created or bound (A49), and no integrity anchor is established (C11, TBD). This instance therefore claims neither cryptographic integrity nor an authenticated ratification; this is lasting, not temporary (`genesis-model.md` §6).
- The model this instance follows is `genesis-model.md` revision 5 (item 8).

## 2. The bound set

The items are those of the bound set whose list the owner decided, without the signing key (A49; `genesis-model.md` §3). "Delegated approval" means an approval of the decision agent in the owner's place under A51, with the status DELEGATED and advisory effect (DM section F).

| # | Item | Bound | SHA-256 | Record |
|---|---|---|---|---|
| 1 | Concept hash + errata hash | `AIEOS-concept.md` (v0.5, A22) | 19cfa266334aa20d1ac1bc15f5cf92d0fc6d3bbbd98c13cfcb42ad6fd5a8357c | unchanged; the concept stays byte-identical (A22) |
| 1 | (errata) | `docs/pre-genesis/CR-001-concept-errata.md`, with the dated notes of this amendment | c1b38babc1fad92ba152a30987b81ed11f516e267aee98666c8bdf75549db6e5 | changed by this amendment: E4 and E10 get their texts (A59); takes effect with the owner's yes on its exact text |
| 1 | (errata) | `docs/pre-genesis/CR-002-concept-errata.md`, with the dated notes of this amendment | 446c8523339a11c62ada936ba4b3001cde26dc5e3eac6ea234b78cec13b4a3e1 | changed by this amendment: notes in part 4 limits 4 and 6, the paragraph after the limits, "Chỗ hở đã vá", K4, part 7 and part 8 (A59); takes effect with the owner's yes on its exact text; the A54 point 4 marker is kept |
| 2 | Constitution | `docs/pre-genesis/constitution.md` revision 3 | 16e78d30214082d1248369b910b051e7e4c48929036fced1488acc2f3efcf836 | unchanged; delegated approval (advisory), DM section F, row F1 (D-112) |
| 3 | Authority model | section 3 of this charter | — | the rows and files bound there; CR-002's hash changes with item 1 |
| 4 | Governance-boundary abstraction + "every label must be measured" | section 4 of this charter | — | unchanged; the rows and lines bound there |
| 5 | Assurance model | `docs/pre-genesis/assurance-model.md` revision 5 | 945615316968a5c064bf88be71add9271bbb9f95692eaa22582b6020fa69cb85 | changed by this amendment (sections 2, 3, 5, 8 and 10; A59); takes effect with the owner's yes on its exact text (`genesis-model.md` §5 point 3) |
| 6 | Conformance methodology + initial scenario-set hash | `docs/pre-genesis/conformance-methodology.md` revision 3 | a11928199da9b908fad5805b44d341b21f961f0bc925350b0d46ac9adc454c87 | unchanged; delegated approval (advisory), DM section F, row F4 (D-115) |
| 6 | (initial scenario set, set version 2) | `docs/pre-genesis/conformance-scenarios-initial.md` revision 4, 32 scenarios | 6b5c0666a1f364f5ecec9ad516c9a749969a1963f4e5dbef566adcbc8c80e24d | changed by this amendment: ACC-16 and ACC-17 added (A59); the 30 scenarios of set version 1 unchanged, each row byte-equal; takes effect with the owner's yes on its exact text (A54 point 3; decision D-169); each scenario's row hash in section 5 |
| 7 | Bootstrap governor identity + succession rule | definition and succession rule: `genesis-model.md` §3.3 (its hash at item 8); detailed specification (A50): `docs/pre-genesis/governor-spec.md` revision 5 | 423a1f3743b124bab7e672f7be5615e18f2a178d9b9991587d5aaa9f6ea37cea | changed by this amendment (sections 3.2, 3.3, 4 rule 3 and 11; A59); takes effect with the owner's yes on its exact text (CR-002 part 4 limit 8); the governor's identity, a content hash of its code, does not exist yet: code comes from step 9 (A14) |
| 8 | Change classes + amendment procedure | `docs/pre-genesis/genesis-model.md` revision 5 (§5; also §3.3); DM row B1 (proposed) | 574230b260505fa88b3c9fdcf86f388d8e17434a92e6d3e285dc1e2300466b46 (file); 7dc53b59c6f53f455176bd25fbefc1770aa88a37461024fdee11cf5432352d40 (row B1) | unchanged; delegated approval (advisory), DM section F, row F5 (D-116) |
| 9a | A27 identities | immutable repository id `1404293138`; immutable owner id `317226245` | — | unchanged; read once with the GitHub API, read-only (D-121); the accounts are named in DM row A24, which is not an identity binding (A27) |
| 9b | A27 signing-key fingerprints | dropped (A49) | — | — |

## 3. Item 3: the authority model

Bound: these DM rows, each by its row-line hash, read at version 1's pinned commit `02b7a5db6f0102c1d9267f368c80e052fbe1c8ab`, as version 1 binds them; CR-002 by its new file hash (parts 1, 4 and 8 named); and the DM file at that commit. The rows govern. Version 1's two additions to the sources of `genesis-model.md` §3 row 3, A55 and the DM file hash, are kept. The DM file hash fixes the version in which these rows are read; it binds no other row, and no PROPOSED or TBD row becomes an assumption by it (DM rule 1). The generator checked that each of these row lines is byte-equal at commit `c084f1475052bb0af0c40fbc0302666b4da966e9`. A59 is not bound here: it records the owner's answers on evidence, not on who may approve what; its texts are bound in items 1, 5, 6 and 7.

| Bound | SHA-256 |
|---|---|
| DM row A21 | b776b081830aac7ab97f6b752a7f3f01583710000462bf2c305cd3384c101a9a |
| DM row A27 | 049b5c8fd611da4b95507a631c81fbf8f043bc326bf82c477cb3fcd1915a799d |
| DM row A28 | 060ee0639238e744e2f7b44f8a5e879c580c5ff27a78d56ae741d329ab1560d5 |
| DM row A31 | 806dc4972def2368131e40248ced7725628d144217a83d9642301ba733ccf39b |
| DM row A36 | ed239b7f24fe28a90a910c6b5a070f1cd4f46cefb6312e039692b4a06a26d148 |
| DM row A41 | 169b04be2ad3e3c31fdbfad87884193cfb97244562fbe0855cd9b898fb297912 |
| DM row A49 | 84af41db6c455cc82baf5d80328f98bde2b7d22c9c5f59edce5110d409538599 |
| DM row A51 | 2d931dae9d93da06a7d22337c49d62e67490a6eef2f974aa01c66d832078d6bd |
| DM row A52 | 64bab502668705b82092bceff4099c5ffc5ec15659c14e9c48e0f9ee3e497555 |
| DM row A54 | f9e3d067e9ffe51de090f18adddcdbea36daccd6ee708b468ca26f7d6699758e |
| DM row A55 | 454e10a6ed123a6afc74c5d8dfc5d0a8fd3dfe82471661158f8c9278b45ed75e |
| `docs/pre-genesis/CR-002-concept-errata.md` (parts 1, 4 and 8) | 446c8523339a11c62ada936ba4b3001cde26dc5e3eac6ea234b78cec13b4a3e1 |
| `docs/pre-genesis/decision-matrix.md` (at `02b7a5d`) | 0fc8c0cc7087f73aa8673f71712b50b622ae900a940ac6050e7735453704955b |

Summary (Claude's wording, not normative; the bound rows govern):
- The authority chain is A21: Authority Role → Human Principal → Authentication / Signing Mechanism → Authority Action → Recorded Evidence. With no signing key, the mechanism is authentication only (A49). The decision agent is not a Human Principal (`genesis-model.md` §3.2).
- For gov-AIEOS, the decision agent (A41) approves in the owner's place, as A51, A52 (CR-002) and A54 set that delegation; under A54 point 2 it may approve raising a low- or medium-risk class to L2 with metrics and a change request. The delegation continues once AIEOS governs its own build, and it is part of this instance (A55). Its approvals are delegated approvals, recorded "decided by: decision agent (A41, A51)", advisory, and never evidence of human authority (A41).
- What stays the owner's includes (not complete; the bound rows govern): the acts A51 item (4) keeps; CR-002 part 4 limits 5 and 8; a change to item 1 or item 3 of this charter and any other change to who may approve what (CR-002 part 8; A54 point 1); and what A54 point 2 keeps (the auto-accept policy, "sufficient assurance", any wider bound, and the use of L2 while P-CRED or C13 is not PASS).
- The owner's own words always prevail. The owner can narrow or revoke the delegation in one sentence, with effect from then on; what was approved before stays (A41; CR-002 part 1). Binding the delegation in this instance does not weaken that one-sentence revocation, which keeps immediate effect (A55).

## 4. Item 4: the governance-boundary abstraction and the label rule

| Bound | SHA-256 |
|---|---|
| DM row A2 | 064204f53cac3c96eb9c3b0326fd3b52d998123a6a217c7b1d0fd81071e23d94 |
| DM row A4 | 1fd371f238bbd799c2bd18bffa299f9f47646795a3383262995e383435ed614d |
| DM row A25 | 074772200c7d198913d21abfeaf706e56c3591d0bd1539310d3879841c2f5da1 |
| DM row A26 | 27ef58bdadc94214b2e6632fb8103cc28d7293071a6ddc006af9d9cd5050884c |
| DM row A29 | 8a4849fca6343a0dceb5e1789325055234cfbd5564507f75a8eb9c62d110b0fe |
| DM section E: the lines from its heading "## E. Trust concerns are separate" through the blank line before the "---" that precedes section F, the "---" excluded, joined with line ends, with a final line end | 50b53956148cec47bab2c82b89162802c5dc1d017d7f520d988f41e66ee86dcc |
| DM label line "**preventive** — …" (the whole line) | fdbc3a0162eed9d006e94a4433e0b06a63faa2aa34cd64155cc149a2b0cf3788 |
| DM label line "**detective** — …" (the whole line) | e4390f4132209af0164a1aa78f696b6d92888564d4a0ec7901c9d7fb5814986e |
| DM label line "**advisory** — …" (the whole line) | 617bfe2a0668589b1682e9476b584abbb8b0c3caf279e81d9c3e5ef5a154e6b4 |
| DM label line "**manual** — …" (the whole line) | 036b8d072aaa35f233933c3b86984caf522d769c7545e996d8e4c2bac9e0de8a |

- The abstraction is bound; no implementation of it is ratified as a trust boundary (A14). The active boundary implementation (A2) is recorded as the current implementation, unmeasured, and its effect is advisory (`genesis-model.md` §4, §8).
- "Every label must be measured" is bound as a rule, not as a claim that labels are measured: every governance label this instance carries is the measured one or, if unmeasured, advisory (`genesis-model.md` §8). The TBD statuses of DM section E are not assumptions (DM rule 1).
- A29 is bound as an invariant and a target; for gov-AIEOS it is unmet by design, like C13 (A51 item (7); `genesis-model.md` §8).

## 5. Item 6: the initial scenario set, set version 2

The set is the file bound in section 2 with these 32 scenarios, each bound by its row-line hash and, for the defaults its rows use, by the file hash. Set version 1 (version 1 of this charter) had the first 30; their rows are byte-equal here. ACC-16 and ACC-17 are new. The file's own header line "Set version 0 (draft)" describes it before version 1; this instance binds it as set version 2 (A49; methodology §4).

| Scenario | SHA-256 of its row |
|---|---|
| ACC-01 | 5d8f9e4949dfe0f9bab7612a8af6a907185e45afdea865800a0598ddf97b0eab |
| ACC-02 | acca9804935cb92745d1320bef416e68bb2f334b0a490bc7011272f3923b69d9 |
| ACC-03 | 0330bbd061c9bfaeaa2a61c380c2191121777c2e997dff7016da1aa04b46b0aa |
| ACC-04 | b7a17689c4a74f8c3ea7640204c9386208a6e39c1881cf53a6eb9fb6cd7a30e5 |
| ACC-05 | 9d74c678dc59404176a519843d3fc34019da2349385c3da47ccc398287605800 |
| ACC-06 | cdcd4e3790c9fb292bab04e29214da77d3d471c62dc1c72ebbe58613c28eaacd |
| ACC-07 | 1722d7aed842bcdbcfb775d6c5472536ca45353491f42224dfee916e0ce1c4a1 |
| ACC-08 | b28b27bc7dfd36c75434a596725a3f0d6b4e6cbb1c2b9dd2824ea7d9f6439247 |
| ACC-09 | 163469a768df50e026c73df09f48a10874610dce42557474e1eca2008281b2cf |
| ACC-10 | 5cbc91bc2b2835ed7305b44b18fad9866e630ac32b7a9d4ace0e953a4eb602b1 |
| ACC-11 | 813d8017323e2d0d80b1de310277a1edc24dc4763cc56787040a2ab7735a0450 |
| ACC-12 | 273a971140920da022f04788ad5d3720636b247f317101b4f58457a4aa44907a |
| ACC-13 | 95056ff8e30ef9b6374830b30f94180811443c33a291a1ee07575ceb3bb9733e |
| ACC-14 | 8c1fcdea20f6ac1b9f8b5fe15efc0f8ce61d95acf2eb910a14d8e955eb644070 |
| ACC-15 | f5faf48c3c017815b325d9d55041aef7da123431be4a934fd6de478aecb557c9 |
| ACC-16 | 71f3bfca8ed71889327b73080c968ef21c6ac442f4157ad82de2a01093448981 |
| ACC-17 | 5b5b56095d5e2bdc0560f49a7bc7f75c6b76fe7866d17ebd487ed8cb8a496e5c |
| RISK-01 | d04e8131768256470e2f2ab872bd18023dc90b9d45bf6853156bdea68c2b06f2 |
| RC-01 | 9e9a059a1c965aa238c7ca84970956088445d5d908b632621324f63eb248a2cb |
| RC-02 | c4b4e0157262949fb6df4b209befe61a5c4fe8bd7c4c4da7a4ba995d22981519 |
| RC-03 | be8acbb5a0c71e8f329c4de519938a724153c5a364244220634f89a6a38d9325 |
| RC-04 | f1bb3392d501b6979010b4acbb021ae4f90c1c436bed5717810ae5b8c6998a4c |
| RC-05 | e9f386b406635813a709c451b8e728690f943b47856ca61ff0ca2122a986365c |
| RC-06 | 210b7e3eedf5937528c770933ad8c7b16d3d3704ba6f4b25baad78af481ffe67 |
| RC-07 | fefafdb1fb979a5aa9049d2813f6ea06e4bfdbcaae3d8cbf55b108f22cec1870 |
| RC-08 | 4025f7ed95bd2f27243df91ccad198eba8dd08a5fcf13fd3f04b1cbd8ba08ade |
| RC-09 | 18e36fc54d02478676485f8e264f4d0a29ae2ee94310c0bf031243960fc47e8c |
| RC-10 | 9352557108a1fe2fe3ab25d33a90928c528a3ed29513a697ab0911b8c024c424 |
| RC-11 | d2238379b8b5aebb96596e9478e85d01635d92151713d60c3f6b76f30192e3e7 |
| ADV-01 | 5aa89d9e65411894a588f358e73bf3fdbf4ebe0c613109065072727b9af067a6 |
| ADV-02 | d11a86217d650c426e5f3897c5cd797af656d610db573aeae4a6184292652742 |
| ADV-03 | fe60656f47f037327cd11384f1d7d1b9ac3848344235d63e2cb00c1cac606926 |

## 6. Status sentences inside the bound documents

The status sentences inside the bound documents (for example "proposed, not ratified", "not approved yet", "Set version 0 (draft)", or a dated note that says it takes effect with the owner's yes) describe each document as of its own revision line or note. Their approval is recorded in DM section F, rows F1 to F5, and for the changes of this amendment in its ratification record; from ratification, their binding is recorded in this instance. From then on, the ratification records, the DM section F rows and this instance govern over those sentences. The DM's own header ("Nothing in this file is a Genesis fact") keeps applying to every DM row except those bound in sections 2 to 4.

## 7. Carried notes

- Answered by A59 and this amendment, although bound texts that this amendment does not change still say otherwise: `constitution.md` §2 ("Paths are named by role, because the layout is open"), §4, last point ("No entry here is cross-model; that entry stays open (CR-001 E10)"), and §5 point 2 (the paths of every scope, "once the layout is settled"); `genesis-model.md` §3, row 1 ("approved by the owner with E4 and E10 open"). For gov-AIEOS, the cross-model entry is met as CR-001 E10, as amended here, states; the layout is CR-001 E4's, as amended here. For AIEOS projects, E10 stays open.
- Answered by A55, although the bound texts still list them as open: whether the A41 delegation continues once AIEOS governs its own build and whether it enters this instance (`assurance-model.md` §10 point 7; `genesis-model.md` §9 points 5 and 7). `genesis-model.md` §9 point 4 (the constitution) is answered by DM section F, row F1.
- Not bound, and changed by their own requests after this amendment: the Master Plan (§4 M2, §6, §9, §10; its count of the Verification scenarios), the risk rules (`docs/specs/risk-rules-gov-aieos.md` §5, §7 point 1), specification 2's layout part (DM row F12) and DM rows B3, B4 and B7.
- Still the owner's: the open points of `assurance-model.md` §10, points 2 to 5, except that the decision agent approves raising a low- or medium-risk class to L2 (A54 point 2); for AIEOS projects, CR-001 E10; the integrity anchor (C11).
- A change to the assurance model (item 5) after it is ratified stays the owner's until the owner says otherwise (`genesis-model.md` §5 point 3, proposed, fail closed).
- Answered by A56, although version 1 of this charter (section 7) and `governor-spec.md` §11 point 9 still list them as to be written: no further rules for the governor's owner-kept act input are added; such acts are recognised by the constitution's existing path rules and by the task contract's declaration (A56; `docs/specs/spec-02-aieos-file-format.md` §5.1, `owner_kept_act`).
- No code before step 9 (A14).

## 8. Ratification

- Not yet ratified. The owner's yes on the exact texts of the changed files and on the changed bindings of this charter, item 3 included, comes first (decision D-169 C6); then the decision agent ratifies this instance in the owner's place for the items that are unchanged from version 1 (A51 item (3); A54 point 1). The owner keeps what the bound rows of section 3 keep.
- The ratification record will name who ratified what, the date, the transcript lines, this charter's SHA-256 and the commit that adds the changed files, and will be kept outside this charter (by practice, a decision file and a DM row; D-121). It is advisory while P-CRED is FAIL (A31); a delegated ratification stays advisory even if P-CRED later passes (A41; A55; CR-002 part 1).
- Appearing in this charter makes no PROPOSED or TBD row an assumption (DM rule 1). Only the yes of ratification makes PROPOSED content bound here DECIDED (the owner's yes) or DELEGATED (the decision agent's yes under A51); TBD rows stay TBD until measured (DM rule 2) (`genesis-model.md` §7).
