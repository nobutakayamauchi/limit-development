from __future__ import annotations

from dataclasses import replace
import re


class HumanEditorV0:
    """Conservative public-copy editor.

    /human is an editing pass, not a fact generator. It may reorder, shorten and
    connect facts already present in Update/Evidence/Knowledge, but it must not
    invent implementation details, outcomes, numbers or motives.
    """

    name = "human-editor-v0"

    def __init__(self, knowledge=None):
        self.knowledge = knowledge or {}

    def _profile(self, project):
        profiles = self.knowledge.get("project_profiles", {})
        return profiles.get(project, {}) if isinstance(profiles, dict) else {}

    def _clean(self, text):
        text = re.sub(r"\s+", " ", str(text or "")).strip()
        text = re.sub(r"。{2,}", "。", text)
        text = re.sub(r"しました。しました。", "しました。", text)
        return text

    def _sentences(self, text):
        text = self._clean(text)
        if not text:
            return []
        parts = [p.strip() for p in re.split(r"(?<=。)", text) if p.strip()]
        out = []
        seen = set()
        for p in parts:
            key = re.sub(r"[\s。]", "", p)
            if key and key not in seen:
                seen.add(key)
                out.append(p)
        return out

    def _human_summary(self, update, evidence_text=""):
        sentences = self._sentences(update.summary)
        profile = self._profile(update.project)
        purpose = self._clean(profile.get("public_description"))
        why = self._clean(profile.get("why_it_matters"))

        # Keep explicit event wording first. The stable project context comes second.
        fact = sentences[0] if sentences else f"{update.title}。"
        if not fact.endswith("。"):
            fact += "。"

        context = ""
        for candidate in sentences[1:] + [why, purpose]:
            candidate = self._clean(candidate)
            if not candidate:
                continue
            if candidate in fact or candidate == fact:
                continue
            context = candidate
            break

        # A human editor should not repeat the title as a robotic sentence if the
        # existing summary already explains the same change more naturally.
        title_key = re.sub(r"[\s。、]", "", update.title)
        fact_key = re.sub(r"[\s。、]", "", fact)
        if title_key and fact_key.startswith(title_key) and len(sentences) > 1:
            fact = sentences[0]

        if context:
            if not context.endswith("。"):
                context += "。"
            return self._clean(f"{fact} {context}")
        return self._clean(fact)

    def edit_update(self, update, evidence_text=""):
        title = self._clean(update.title).rstrip("。")
        summary = self._human_summary(update, evidence_text)
        return replace(update, title=title, summary=summary)

    def edit_updates(self, updates, evidence_by_source=None):
        evidence_by_source = evidence_by_source or {}
        out = []
        for update in updates:
            ev = evidence_by_source.get(update.source_id)
            out.append(self.edit_update(update, getattr(ev, "text", "")))
        return out


def humanize_updates(updates, evidence_by_source=None, knowledge=None):
    return HumanEditorV0(knowledge).edit_updates(updates, evidence_by_source)
