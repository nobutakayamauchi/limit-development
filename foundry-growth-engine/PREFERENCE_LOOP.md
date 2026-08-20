# Preference Loop v0

Preference Loop sits after Knowledge Distiller and turns repeated human evaluation into a reversible preference state.

```text
CHAT observations
  ↓
Knowledge Distiller
  ↓
CHAT-LEARNED Knowledge
  ↓
Shadow output
  ↓
structured human evaluation
  ↓
Preference Loop
  ↓
SHADOW / ACTIVE / DORMANT
```

## Why

Chat-derived Knowledge tells FGE what patterns may describe the operator. It does not prove that using those patterns actually improves public writing. Preference Loop adds that missing second half: use the candidate, evaluate the result, and accumulate evidence over time.

## Evaluation axes

Each evaluation scores four axes from `-2` to `+2`:

- `voice_fit`: does it sound like the intended operator for this surface?
- `readability`: is it easy to read?
- `factual_fidelity`: did personality/context stay faithful to the source facts?
- `task_fit`: is the tone/context useful for this output type?

Factual fidelity and task fit are weighted more heavily than personality. A sentence that sounds right but bends the facts must not win.

## Stages

### SHADOW

Default state. The rule may appear only in the experimental Preference candidate so it can collect feedback. It is not promoted into CURRENT KNOWLEDGE.

### ACTIVE

Enough positive structured feedback has accumulated, including factual-fidelity and task-fit gates. ACTIVE means **eligible for explicit promotion**. It still does not silently modify CURRENT KNOWLEDGE or unattended publication.

### DORMANT

Negative factual-fidelity or overall feedback suppresses the rule from the experimental writer. Its history remains in `preference_rule_catalog` so a bad preference does not disappear without trace.

## Surface awareness

Feedback records keep scores by surface, for example `journal`, `sns`, `lp`, `technical`, and `readme`. v0 records this split and exposes it for review. It does not yet automatically apply separate personalities per surface; that remains a later promotion decision.

## Privacy / safety boundary

Preference feedback in v0 is structured metadata only. Free-text fields such as comments, corrections, or raw chat are rejected by the loader. This prevents a preference store from becoming a second private-text database.

```text
FACTS = Evidence
MEANING CANDIDATE = Knowledge Distiller
QUALITY EVIDENCE = Preference Loop ratings
EDITING = /human
PUBLICATION = existing publication boundary
```

PLAIN remains untouched and regeneratable throughout the loop.
