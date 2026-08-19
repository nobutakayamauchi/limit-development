from __future__ import annotations

import re


class RuleBasedPublicWriter:
    """Default zero-secret writer. This is the PLAIN behavior contract."""

    name = "rule-based-v0"

    def rewrite(self, text, project, category, rule=None):
        if rule:
            return rule.get("title") or f"{project}を更新", rule.get("summary") or f"{project}に関する変更を反映しました。"
        mapping = {
            "機能追加": (f"{project}に機能を追加", f"{project}で新しい機能を使えるようにしました。"),
            "機能削除": (f"{project}の機能を整理", f"{project}で不要になった機能を削除しました。"),
            "新プロジェクト": (f"{project}を開始", f"{project}の新しい取り組みを開始しました。"),
            "プロジェクト終了": (f"{project}を終了", f"{project}の役割を見直し、プロジェクトを終了しました。"),
            "新製品": (f"{project}を公開", f"{project}を新しく公開しました。"),
            "製品終了": (f"{project}の提供を終了", f"{project}の提供を終了しました。"),
            "研究・検証": (f"{project}を検証", f"{project}が実際の利用条件で成立するか検証しました。"),
            "方針変更": (f"{project}の方針を更新", f"{project}の説明や運用方針を更新しました。"),
            "機能変更": (f"{project}を改善", f"{project}の使い勝手や安定性に関わる変更を行いました。"),
        }
        return mapping[category]


class KnowledgeAwarePublicWriter:
    """Adds replaceable public context without changing the PLAIN core contract.

    Knowledge can explain stable purpose, vocabulary and why a change matters.
    Event facts still come only from Evidence / explicit rewrite rules.
    """

    name = "knowledge-aware-v1"

    ACTIONS = (
        (r"^(?:fix|repair)\b[:\s-]*", "修正"),
        (r"^(?:add|create|implement|enable|support)\b[:\s-]*", "追加"),
        (r"^(?:remove|delete|drop)\b[:\s-]*", "整理"),
        (r"^(?:revert|restore)\b[:\s-]*", "復元"),
        (r"^(?:update|change|polish|refactor|align|improve)\b[:\s-]*", "改善"),
        (r"^(?:document|docs?|clarify)\b[:\s-]*", "整理"),
        (r"^(?:test|verify|benchmark|audit|probe)\b[:\s-]*", "検証"),
    )

    def __init__(self, knowledge):
        self.knowledge = knowledge or {}
        self.plain = RuleBasedPublicWriter()

    def _profile(self, project):
        profiles = self.knowledge.get("project_profiles", {})
        if isinstance(profiles, dict):
            return profiles.get(project) or {}
        return {}

    def _replace_terms(self, text):
        replacements = self.knowledge.get("public_voice", {}).get("term_replacements", {})
        out = text
        if isinstance(replacements, dict):
            for src, dst in sorted(replacements.items(), key=lambda kv: len(kv[0]), reverse=True):
                out = re.sub(re.escape(src), str(dst), out, flags=re.I)
        out = re.sub(r"\s+", " ", out).strip(" :-")
        return out

    def _subject_and_action(self, text):
        raw = re.sub(r"^\[[^\]]+\]\s*", "", text.strip())
        raw = re.sub(r"^[a-z]+(?:\([^)]*\))?!?:\s*", "", raw, flags=re.I)
        for pattern, action in self.ACTIONS:
            if re.search(pattern, raw, flags=re.I):
                subject = re.sub(pattern, "", raw, count=1, flags=re.I)
                return self._replace_terms(subject), action
        return self._replace_terms(raw), ""

    def _subject_is_public_japanese(self, subject):
        """Do not publish awkward half-English commit subjects as human copy."""
        jp = re.findall(r"[ぁ-んァ-ヶ一-龥]", subject)
        ascii_words = re.findall(r"[A-Za-z]{2,}", subject)
        return len(jp) >= 4 and len(ascii_words) <= 2

    def _headline(self, text, project, category):
        subject, action = self._subject_and_action(text)
        if (
            action
            and 2 <= len(subject) <= 72
            and self._subject_is_public_japanese(subject)
            and not re.search(r"\b[0-9a-f]{12,}\b", subject, flags=re.I)
        ):
            suffix = {
                "修正": "を修正",
                "追加": "を追加",
                "整理": "を整理",
                "復元": "を復元",
                "改善": "を改善",
                "検証": "を検証",
            }[action]
            return f"{subject}{suffix}"
        return self.plain.rewrite(text, project, category, None)[0]

    def _context(self, profile, category):
        by_type = profile.get("context_by_type", {})
        if isinstance(by_type, dict) and by_type.get(category):
            return str(by_type[category]).strip()
        purpose = str(profile.get("public_description") or "").strip()
        why = str(profile.get("why_it_matters") or "").strip()
        if category in {"機能変更", "方針変更", "研究・検証", "機能削除"}:
            return purpose or why
        return why or purpose

    def _learned_context(self, text, project):
        matches = []
        for item in self.knowledge.get("learned_context_rules", []):
            pattern = str(item.get("pattern", "")).strip()
            context = str(item.get("public_context", "")).strip()
            projects = item.get("projects", [])
            if not pattern or not context:
                continue
            if projects and project not in projects:
                continue
            if re.search(pattern, text, flags=re.I):
                matches.append((float(item.get("confidence", 0)), int(item.get("observation_count", 0)), context))
        if not matches:
            return ""
        return max(matches, key=lambda x: (x[0], x[1]))[2]

    def rewrite(self, text, project, category, rule=None):
        learned = self._learned_context(text, project)
        if rule:
            title, summary = self.plain.rewrite(text, project, category, rule)
            if learned and learned not in summary:
                summary = f"{summary}{learned}"
            return title, summary

        profile = self._profile(project)
        if not profile:
            return self.plain.rewrite(text, project, category, None)

        title = self._headline(text, project, category)
        first = f"{title}しました。" if title.endswith(("修正", "追加", "整理", "復元", "改善", "検証")) else self.plain.rewrite(text, project, category, None)[1]
        context = learned or self._context(profile, category)
        if context and context not in first:
            return title, f"{first}{context}"
        return title, first
