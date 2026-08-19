# FGE Work Record Protocol v0

Status: `FROZEN / EXECUTABLE_V1.1 / DA_PASS / COUNTER_DA_PASS`

This protocol is the provider-neutral intake boundary for **FOUNDRY GROWTH ENGINE（仕事してください。）**.

The AI/provider is replaceable. The durable record format is the contract.

```text
ChatGPT / Codex / Claude / future AI / field capture
                  ↓
           Work Record v0
                  ↓
        durable Git work ledger
                  ↓
                  FGE
```

## 1. Core rule

The AI conversation is a temporary working buffer.

Git (or another adapter-backed durable ledger) is the persistent work memory.

```text
AI CHAT != DURABLE MEMORY
SAVE CLAIM != SAVE RECEIPT
SOURCE SEALED != PUBLICATION APPROVED
```

The system must not tell the user a session is safely saved unless the relevant source record and required media/evidence exist outside the AI conversation.

## 2. Default logical location

```text
.fge/records/YYYY/MM/DD/<timestamp>-<record_id>.json
```

This is a logical protocol path, not a requirement to use a public repository.

### Privacy boundary

Sensitive work defaults to a **private work ledger**.

```text
PRIVATE WORK LEDGER
      ↓
     FGE
      ↓
REVIEW GATE
      ↓
PUBLIC SITE / CMS / SNS
```

A public repo is acceptable only when the raw work record is intentionally public-safe.

## 3. Required Work Record fields

```json
{
  "schema": "fge.work-record/v0",
  "record_id": "wr_...",
  "session_id": "day_2026-08-19_...",
  "session_sequence": 1,
  "content_scope": "DELTA",
  "record_type": "CHECKPOINT",
  "captured_at": "2026-08-19T12:30:00+09:00",
  "source_type": "AI_SESSION",
  "source_adapter": "codex",
  "project": "FOUNDRY GROWTH ENGINE",
  "summary": "Work Record input adapterを追加した。",
  "evidence_refs": [],
  "explicit_intent": "AUTO",
  "session_state": "OPEN"
}
```

### Enumerations

`record_type`

```text
CHECKPOINT
ARTICLE_CHECKPOINT
END_DAY
AUTO_EVENT
```

`content_scope`

```text
DELTA
SNAPSHOT
```

DAY SESSION checkpoints should normally use `DELTA`, meaning material since the previous durable record. This prevents repeated checkpoints from becoming repeated public updates.

`source_type`

```text
AI_SESSION
GIT_EVENT
FIELD_CAPTURE
MANUAL_IMPORT
```

`explicit_intent`

```text
AUTO
RECORD_ONLY
FORCE_ARTICLE
```

`session_state`

```text
OPEN
SEALED
```

Only `END_DAY` may seal a DAY SESSION.

## 4. Optional fields

Use only when they preserve material information.

```text
actor
changes[]
why
result
before_after
metrics{}
media_refs[]
article_instruction
open_loops[]
next_action
parent_record_id
related_record_ids[]
tags[]
privacy_class
```

Missing evidence must remain missing/UNKNOWN. An Intake Adapter must not invent data just to fill a field.

## 5. Media rule

Large photo/audio/video bytes do not need to live in Git.

```text
Work Record
   └─ media_refs[]
          ↓
 durable private file/object/media store
```

A media reference should preserve enough to find the asset again and, when useful, verify it:

```text
kind
uri / path / object_id / ref
captured_at
optional hash
privacy_class
```

If required media exists only inside an AI chat, the session is not safely sealed.

## 6. Save Receipt

A Save Receipt is returned by the Intake Adapter/executor after durable persistence. It is not embedded as a self-referential commit SHA in the record itself.

Example:

```json
{
  "status": "COMMITTED",
  "record_id": "wr_...",
  "record_path": ".fge/records/...json",
  "session_id": "day_...",
  "session_sequence": 1,
  "session_state": "OPEN",
  "commit_sha": "abcdef...",
  "media_state": "PERSISTED",
  "saved_at": "2026-08-19T12:31:00+09:00"
}
```

`media_state`

```text
NONE
REFERENCED
PERSISTED
INCOMPLETE
```

`status`

```text
COMMITTED
LOCAL_ONLY
```

Only `COMMITTED` with a non-empty `commit_sha` is a durable Git Save Receipt. `LOCAL_ONLY` explicitly means the record exists in the local working tree but durable Git persistence has not completed.

No `保存しました` claim without a durable receipt.

---

# DAY SESSION Protocol v0

The normal user-facing operation is deliberately only three commands.

## A. 「ここまで保存」

Normalize to:

```text
CHECKPOINT
content_scope = DELTA
session_state = OPEN
```

Behavior:

1. capture material since the previous durable checkpoint where possible;
2. persist a Work Record;
3. persist or verify required media refs;
4. return Save Receipt / commit SHA;
5. continue the same DAY SESSION.

Success UX:

```text
保存しました。
commit: <sha>
セッションは継続中です。
```

## B. 「これ一本」

Normalize to:

```text
ARTICLE_CHECKPOINT
explicit_intent = FORCE_ARTICLE
session_state = OPEN
```

Behavior:

1. persist the source material as a Work Record;
2. preserve any article instruction;
3. create or trigger an ARTICLE review candidate;
4. do not close the DAY SESSION;
5. continue accepting later work/photos/voice.

The daily JOURNAL may later summarize/link the article. It should not regenerate a second full article from the same source record.

## C. 「今日は終わり」

Normalize to:

```text
END_DAY
session_state = SEALED
```

Behavior:

1. persist remaining DELTA material;
2. reference earlier checkpoint records where useful;
3. verify required raw evidence/media no longer exists only inside chat;
4. obtain a durable Save Receipt;
5. trigger/regenerate the daily JOURNAL + INDEX review candidate;
6. mark the source session SEALED.

### Important distinction

A sealed source session is reconstructable without the chat.

It is **not** automatically published.

```text
END_DAY
→ SOURCE SEALED
→ review candidate can be regenerated
→ 投稿 / 修正 / 記録だけ
→ only 投稿 authorizes public output
```

Derived ARTICLE/JOURNAL/INDEX content is regenerable from the durable source ledger. A renderer failure does not need to make the AI conversation the last surviving copy again.

## 7. Provider capability contract

An Intake Adapter must state what it can really do.

```text
READ_ONLY_CHAT
WRITE_CAPABLE_GIT_AGENT
FIELD_CAPTURE_ADAPTER
MANUAL_EXPORT_BRIDGE
```

A read-only chat must not pretend it wrote Git. It must hand off to a write-capable bridge or report that persistence is incomplete.

Git-capable environments may satisfy the write path directly when authorized.

## 8. FGE publication intent

`RECORD_ONLY` means source history only.

It must not become a public UPDATE, ARTICLE or JOURNAL candidate merely because the record exists.

`FORCE_ARTICLE` means article candidate despite low input volume. It still does not authorize publication.

## 9. Executable reference implementation v1.1

Canonical executor:

```text
foundry-growth-engine/scripts/day_session.py
```

The executor is provider-neutral. An AI/agent maps operator intent onto one of three subcommands:

```text
checkpoint  → CHECKPOINT
article     → ARTICLE_CHECKPOINT / FORCE_ARTICLE
end-day     → END_DAY / SEALED
```

Reference invocation:

```bash
python foundry-growth-engine/scripts/day_session.py checkpoint \
  --repo <work-ledger> \
  --project "<project>" \
  --summary "<delta>" \
  --source-adapter <adapter> \
  --commit
```

The executor MUST:

1. auto-increment `session_sequence` inside a session;
2. fail closed if an existing ledger has duplicate sequence numbers;
3. reject any attempt to reopen a SEALED session;
4. reject `END_DAY` when required media is `INCOMPLETE`;
5. validate the resulting ledger through the existing `WorkRecordFileAdapter`;
6. when `--commit` is used, commit only the newly created Work Record path;
7. leave unrelated staged changes untouched;
8. return `COMMITTED` only after a successful Git commit and verified commit boundary;
9. roll back the newly created Work Record if the commit fails;
10. never perform public publication.

Repo-local agent instructions may wrap this executor, but provider-specific behavior must stay outside FGE Core.

Current repo-local skill:

```text
.agents/skills/fge-work-session/SKILL.md
```

## 10. v0 anti-SimCity boundary

This protocol does **not** authorize:

- a custom session database;
- a custom scheduler;
- a provider-specific FGE Core fork;
- a new media-storage service;
- a new native app;
- automatic public publication;
- resurrection of the old Vlog editing/rendering stack.

Those responsibilities must independently survive a later Raison d'être / DA / Counter-DA.

## 11. Current reuse map

```text
Existing FGE Core           REUSE
Existing Review Gate        REUSE
Existing hourly compaction  REUSE
Work Record file contract   REUSE / FROZEN
Work Record Input Adapter   REUSE
DAY SESSION executor        BUILD / MINIMAL
Repo-local agent skill      ADAPT / MINIMAL
NAGI checkpoint semantics   EXTRACT
NAGI whole planner          KILL for standard route
Vlog camera/audio capture   OPTIONAL EXTRACT later
Vlog edit/render stack      KILL
Event-driven Git detection  NOT_REQUIRED v1 / WATCH
Media store                 EXTERNAL / adapter-selected
CapCut                      EXTERNAL later
```
