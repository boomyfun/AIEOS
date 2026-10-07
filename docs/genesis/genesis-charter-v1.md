# AIEOS Genesis Charter, version 1

> **Status: Genesis instance 1 (Genesis version 1), draft, not ratified.** A14 step 8, started under A51 item (3) (`decision-matrix.md` (DM), section F, row F6). Written under decisions of the decision agent (A41; decision file D-121); not an owner decision. Names (A53): gov-AIEOS is what is used to build AIEOS; AIEOS is the product.
> The instance consists of this charter and its ratification record. The ratification record lies outside this charter, because it records this charter's SHA-256 (`genesis-model.md` §2, §6, §7). Until that record exists, nothing here is bound.
> Pinned commit: `02b7a5db6f0102c1d9267f368c80e052fbe1c8ab`, GitHub main when this charter was generated (DM revision 27). Every SHA-256 below is computed by the generator, not typed: of a file at that commit; of one line of a file at that commit (the SHA-256 of the whole line's UTF-8 bytes, any leading "| " or "- " included, without its line end); or of the DM section E extract described in section 4.
> Effect: advisory. The minimal P-CRED baseline is FAIL, and C13 is FAIL by implication (DM section D; C2, C13); every authority claim recorded or bound here, the owner's or a delegated one, is at most advisory (A31, A41; `genesis-model.md` §8); a delegated one stays advisory even if P-CRED later passes (A41; A55; CR-002 part 1). No boundary implementation is ratified as a trust boundary (A14; `genesis-model.md` §4).

## 1. This instance

- Genesis version: 1. Previous version: none.
- Verifiers bind to the Genesis version and its hash and to the immutable identities of item 9a; never to a repository name, an owner display name or login, a branch or a tag (A27).
- No owner signing key is created or bound (A49), and no integrity anchor is established (C11, TBD). This instance therefore claims neither cryptographic integrity nor an authenticated ratification; this is lasting, not temporary (`genesis-model.md` §6).
- The model this instance follows is `genesis-model.md` revision 5 (item 8).

## 2. The bound set

The items are those of the bound set whose list the owner decided, without the signing key (A49; `genesis-model.md` §3). "Delegated approval" means an approval of the decision agent in the owner's place under A51, with the status DELEGATED and advisory effect (DM section F).

| # | Item | Bound | SHA-256 | Record |
|---|---|---|---|---|
| 1 | Concept hash + errata hash | `AIEOS-concept.md` (v0.5, A22) | 19cfa266334aa20d1ac1bc15f5cf92d0fc6d3bbbd98c13cfcb42ad6fd5a8357c | the concept stays byte-identical (A22) |
| 1 | (errata) | `docs/pre-genesis/CR-001-concept-errata.md` | 6aeda7c8eb457876de258bd10726466ca758c3d7d69b455a984df62a63fa38b1 | approved by the owner; E4 and E10 open (DEF-0018, DEF-0008) |
| 1 | (errata) | `docs/pre-genesis/CR-002-concept-errata.md` | 9c2c58af4922c4b9ee260150010d6e58e17bb7bb8aa34805b24d2c3bbf85bbf8 | approved by the owner (A52), with the dated marker of A54 point 4 |
| 2 | Constitution | `docs/pre-genesis/constitution.md` revision 3 | 16e78d30214082d1248369b910b051e7e4c48929036fced1488acc2f3efcf836 | delegated approval (advisory), DM section F, row F1 (D-112) |
| 3 | Authority model | section 3 of this charter | — | the rows and files bound there |
| 4 | Governance-boundary abstraction + "every label must be measured" | section 4 of this charter | — | the rows and lines bound there |
| 5 | Assurance model | `docs/pre-genesis/assurance-model.md` revision 4 | 04a6a815e0a7e0554bc24136ca604fd5aa29c222f43efab8bac2047ea093fe46 | delegated approval (advisory), DM section F, row F2 (D-113) |
| 6 | Conformance methodology + initial scenario-set hash | `docs/pre-genesis/conformance-methodology.md` revision 3 | a11928199da9b908fad5805b44d341b21f961f0bc925350b0d46ac9adc454c87 | delegated approval (advisory), DM section F, row F4 (D-115) |
| 6 | (initial scenario set, set version 1) | `docs/pre-genesis/conformance-scenarios-initial.md` revision 3, 30 scenarios | 5081bfbcdb644ab7cdf158a9019bf6159e76c3dd7c761ef129e70a3cc8c07e9c | delegated approval (advisory), DM section F, row F4 (D-115); each scenario's row hash in section 5 |
| 7 | Bootstrap governor identity + succession rule | definition and succession rule: `genesis-model.md` §3.3 (its hash at item 8); detailed specification (A50): `docs/pre-genesis/governor-spec.md` revision 3 | aa52f59bcae766a75097452c039ae8d3daaf0667929d00826c17df23df59d961 | delegated approval (advisory), DM section F, row F3 (D-114); the governor's identity, a content hash of its code, does not exist yet: code comes from step 9 (A14) |
| 8 | Change classes + amendment procedure | `docs/pre-genesis/genesis-model.md` revision 5 (§5; also §3.3); DM row B1 (proposed) | 574230b260505fa88b3c9fdcf86f388d8e17434a92e6d3e285dc1e2300466b46 (file); 7dc53b59c6f53f455176bd25fbefc1770aa88a37461024fdee11cf5432352d40 (row B1) | delegated approval (advisory), DM section F, row F5 (D-116) |
| 9a | A27 identities | immutable repository id `1404293138`; immutable owner id `317226245` | — | read once with the GitHub API, read-only (D-121); the accounts are named in DM row A24, which is not an identity binding (A27) |
| 9b | A27 signing-key fingerprints | dropped (A49) | — | — |

## 3. Item 3: the authority model

Bound: these DM rows, each by its row-line hash, CR-002 by its file hash (parts 1, 4 and 8 named), and the DM file. The rows govern. Two entries are additions to the sources that `genesis-model.md` §3 row 3 lists, which predate them: A55 (it records that the delegation enters this instance) and the DM file hash (D-121). The DM file hash fixes the version in which these rows are read; it binds no other row, and no PROPOSED or TBD row becomes an assumption by it (DM rule 1).

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
| `docs/pre-genesis/CR-002-concept-errata.md` (parts 1, 4 and 8) | 9c2c58af4922c4b9ee260150010d6e58e17bb7bb8aa34805b24d2c3bbf85bbf8 |
| `docs/pre-genesis/decision-matrix.md` | 0fc8c0cc7087f73aa8673f71712b50b622ae900a940ac6050e7735453704955b |

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

## 5. Item 6: the initial scenario set, set version 1

The set is the file bound in section 2 with these 30 scenarios, each bound by its row-line hash and, for the defaults its rows use, by the file hash (D-115). The file's own header line "Set version 0 (draft)" describes it before this instance; this instance binds it as set version 1 (A49; methodology §4).

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

The status sentences inside the bound documents (for example "proposed, not ratified", "not approved yet" or "Set version 0 (draft)") describe each document as of its own revision line. Their delegated approval is recorded in DM section F, rows F1 to F5; from ratification, their binding is recorded in this instance. From then on, the DM section F rows and this instance govern over those sentences. The DM's own header ("Nothing in this file is a Genesis fact") keeps applying to every DM row except those bound in sections 2 to 4.

## 7. Carried notes

- Answered by A55, although the bound texts still list them as open: whether the A41 delegation continues once AIEOS governs its own build and whether it enters this instance (`assurance-model.md` §10 point 7; `genesis-model.md` §9 points 5 and 7). `genesis-model.md` §9 point 4 (the constitution) is answered by DM section F, row F1.
- Still the owner's: the open points of `assurance-model.md` §10, points 1 to 5, except that the decision agent approves raising a low- or medium-risk class to L2 (A54 point 2); CR-001 E4 and E10; the integrity anchor (C11).
- A change to the assurance model (item 5) after it is ratified stays the owner's until the owner says otherwise (`genesis-model.md` §5 point 3, proposed, fail closed).
- The rules that set the governor's owner-kept act input for acts not yet covered (`governor-spec.md` §11 point 9) are written and approved before step 9 (D-114).
- No code before step 9 (A14).

## 8. Ratification

- Not yet ratified. For gov-AIEOS, the decision agent ratifies this instance in the owner's place (A51 item (3); A54 point 1). The owner's answer on the delegation, which `genesis-model.md` §7 requires first, is recorded in A55. The owner keeps what the bound rows of section 3 keep.
- The ratification record will name who ratified, the date, the transcript line and this charter's SHA-256, and will be kept outside this charter (by practice, a decision file and a DM row; D-121). It is advisory while P-CRED is FAIL (A31); a delegated ratification stays advisory even if P-CRED later passes (A41; A55; CR-002 part 1).
- Appearing in this charter makes no PROPOSED or TBD row an assumption (DM rule 1). Only the yes of ratification makes PROPOSED content bound here DECIDED (the owner's yes) or DELEGATED (the decision agent's yes under A51); TBD rows stay TBD until measured (DM rule 2) (`genesis-model.md` §7).
