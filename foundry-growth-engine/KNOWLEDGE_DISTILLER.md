# Knowledge Distiller v0

Knowledge Distiller turns repeated, allowlisted chat observations into **candidate public context** without turning raw chat into permanent public Knowledge.

```text
CHAT / DAY SESSION
      ↓
allow_public_learning = true only
      ↓
Knowledge Distiller v0
      ↓
observation count + confidence
      ↓
CHAT-LEARNED Knowledge candidate
      ↓
PLAIN / CURRENT / CHAT-LEARNED comparison
      ↓
human promotion decision
```

## Boundary

```text
ONE UTTERANCE != PERSONALITY
RAW CHAT != PUBLIC KNOWLEDGE
LEARNED CONTEXT != EVENT FACT
CHAT-LEARNED != AUTO-PUBLISHED
```

The v0 engine is deterministic. It does not need an LLM or API key. The chat rules define:

- what repeated wording counts as one observation family;
- the minimum number of unique observations;
- which future Evidence topics the context can apply to;
- the exact public-safe context sentence;
- confidence growth and cap.

Only items with `allow_public_learning: true` participate. Duplicate `source_id` values count once. Raw chat text is not copied into the derived Knowledge pack; only rule IDs, counts, confidence, source references and public-safe context survive.

## Three modes

Every FGE review build now has three outputs.

1. **PLAIN** — pinned zero-operator baseline.
2. **CURRENT KNOWLEDGE** — the normal LIMIT OVER DEVELOPMENT pack.
3. **CHAT-LEARNED** — CURRENT plus promoted Distiller context.

The third mode is experimental. It is packaged for comparison but is not automatically eligible for public publish. `THREE_MODE_COMPARISON.md` shows aligned Git Evidence rendered through all three modes.

## Dogfood sample

`tests/fixtures/chat-sample.safe.jsonl` contains a small set of non-sensitive, explicitly allowlisted excerpts used to dogfood v0. It currently tests three repeated tendencies:

- repeated friction should push toward reducing manual upkeep;
- a working link is not enough if the reader cannot reach the actual content;
- operator-specific Knowledge must remain removable so PLAIN can always be recovered.

These are not treated as personality claims. They are narrow, evidence-backed editorial preferences.

## Future adapter

The production input should come from a provider-specific chat/session adapter that emits the same small observation record. The Distiller itself should remain provider-neutral and outside FGE Core.
