# /human editor v0

`/human` is the final **editing** pass between structured FGE updates and downstream public forms.

```text
Evidence
  ↓
FGE Core
  ↓
Knowledge
  ↓
compact hourly public units
  ↓
[/human editor v0]
  ↓
UPDATE
  ├─ JOURNAL
  ├─ ARTICLE
  └─ SNS draft
```

## Goal

Make mechanically correct FGE copy easier to read without turning the editor into another source of truth.

The editor may remove duplication, repair awkward sentence joins, reorder already-known public context, and turn a mechanical daily list into a readable JOURNAL lead. It may not invent a motive, implementation detail, result, number, actor, or private fact.

## Invariants

```text
/HUMAN != FACT GENERATOR
/HUMAN != KNOWLEDGE STORE
/HUMAN != AUTHORITY TO DISCLOSE PRIVATE DATA

FACTS = Evidence
MEANING = Knowledge
EDITING = /human
```

`Update.id`, `source_id`, `raw_evidence_ref`, `project`, and `type` remain unchanged by the pass.

## Publication boundary

There are two different publication paths and they intentionally remain different.

### Hourly public UPDATE / JOURNAL

```text
already-public Git evidence only
  ↓
CURRENT KNOWLEDGE
  ↓
/human
  ↓
UPDATE / JOURNAL
  ↓
automatic hourly public board
```

This path may use `/human` automatically because `--git-only` excludes Work Records and ARTICLE generation. The source facts are already public repository activity; `/human` only edits that public-safe text.

### ARTICLE / SNS / Work Record

These still end at the existing Human Review Gate:

```text
[ 投稿 ] [ 修正 ] [ 記録だけ ]
```

Private/session material does not become automatically public merely because `/human` exists.

## Chat-learned boundary

The review artifact compares five surfaces from the same Git evidence:

1. PLAIN
2. CURRENT KNOWLEDGE
3. CHAT-LEARNED
4. CURRENT KNOWLEDGE + `/human`
5. CHAT-LEARNED + `/human`

`CURRENT KNOWLEDGE + /human` is the intended hourly UPDATE/JOURNAL presentation path.

`CHAT-LEARNED + /human` remains experimental until its distilled context is reviewed and promoted into the normal Knowledge pack. Raw chat is not copied into public Knowledge by `/human`.

## Why the pass occurs before JOURNAL

The edited UPDATE is the common public wording lineage. JOURNAL, ARTICLE and SNS drafts are then derived from that same edited unit instead of each inventing their own explanation. Raw Evidence remains separate and traceable.
