# /human editor v0

`/human` is the final **editing** pass between structured FGE updates and downstream public drafts.

```text
Git / Work Record Evidence
        ↓
FGE Core
        ↓
Knowledge / Chat-learned Knowledge
        ↓
compact hourly public units
        ↓
[/human editor v0]
        ↓
UPDATE
 ├─ ARTICLE
 ├─ JOURNAL
 └─ SNS draft
        ↓
Human Review Gate
```

## Goal

Make mechanically correct FGE copy easier to read without turning the editor into another source of truth.

The editor may:

- remove duplicated sentences;
- repair awkward sentence joins;
- shorten or reorder already-known public context;
- keep the event statement before stable project context;
- feed the same edited UPDATE into ARTICLE / JOURNAL / SNS so public forms do not drift apart.

The editor may **not**:

- invent a motive, implementation detail, result, number or actor;
- change project/type/source identity;
- remove the raw evidence reference;
- convert private chat into public facts;
- bypass the existing `投稿 / 修正 / 記録だけ` Review Gate.

## Invariants

```text
/HUMAN != FACT GENERATOR
/HUMAN != KNOWLEDGE STORE
/HUMAN != PUBLISHER

FACTS = Evidence
MEANING = Knowledge
EDITING = /human
PUBLICATION = Human Review Gate
```

`Update.id`, `source_id`, `raw_evidence_ref`, `project`, and `type` remain unchanged by the pass.

## Modes kept for regression

The hourly review artifact compares the same Git evidence in five surfaces:

1. PLAIN
2. CURRENT KNOWLEDGE
3. CHAT-LEARNED
4. CURRENT KNOWLEDGE + `/human`
5. CHAT-LEARNED + `/human`

The two `/human` surfaces are experimental review candidates in v0. They are not silently promoted to the production publish path.

## Why the pass occurs before JOURNAL

A previous FGE shape could improve an UPDATE while JOURNAL/SNS continued to use different wording. v0 deliberately edits the UPDATE first, then derives ARTICLE/JOURNAL/SNS from that same edited unit. This keeps one public wording lineage while preserving the original Evidence separately.
