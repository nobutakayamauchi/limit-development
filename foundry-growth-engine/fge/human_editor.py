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

        if not sentences:
            sentences = [f"{update.title}。"]

        # Keep every distinct sentence already present. These may contain
        # chat-learned context or hourly aggregation counts, both of which are
        # public-safe information already produced upstream and must not vanish.
        if len(sentences) == 1:
            for candidate in (why, purpose):
                candidate = self._clean(candidate)
                if candidate and candidate not in sentences[0]:
                    if not candidate.endswith("。"):
                        candidate += "。"
                    sentences.append(candidate)
                    break

        aggregation = [s for s in sentences[1:] if "同じ1時間" in s or "関連変更" in s]
        context = [s for s in sentences[1:] if s not in aggregation]
        ordered = [sentences[0], *context, *aggregation]
        return self._clean(" ".join(ordered))

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

    def edit_journals(self, journals, updates):
        """Turn the mechanical daily list into a readable daily lead.

        It only uses already-edited Update title/summary text. No new event fact
        is introduced here.
        """
        by_id = {u.id: u for u in updates}
        out = []
        for journal in journals:
            items = [by_id[i] for i in journal.update_ids if i in by_id]
            if not items:
                out.append(journal)
                continue
            lead = items[0]
            if len(items) == 1:
                title = lead.title
                summary = lead.summary
            else:
                title = f"{lead.title}、ほか{len(items)-1}件"
                quoted = "、".join(f"『{u.title}』" for u in items[1:4])
                summary = lead.summary
                if quoted:
                    summary = self._clean(f"{summary} 同じ日の開発記録として、{quoted}もまとめています。")
            out.append(replace(journal, title=title, summary=summary))
        return out


def humanize_updates(updates, evidence_by_source=None, knowledge=None):
    return HumanEditorV0(knowledge).edit_updates(updates, evidence_by_source)


def humanize_journals(journals, updates, knowledge=None):
    return HumanEditorV0(knowledge).edit_journals(journals, updates)
