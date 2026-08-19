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
        """Do not publish awkward half-English commit subjects as human copy.

        A few product acronyms are fine, but if most of the subject is still an
        English engineering sentence we fall back to a stable project headline.
        """
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

    def rewrite(self, text, project, category, rule=None):
        # Surgical rules stay highest priority because they are reviewed knowledge,
        # not guesses made from a commit subject.
        if rule:
            return self.plain.rewrite(text, project, category, rule)

        profile = self._profile(project)
        if not profile:
            return self.plain.rewrite(text, project, category, None)

        title = self._headline(text, project, category)
        purpose = str(profile.get("public_description") or "").strip()
        why = str(profile.get("why_it_matters") or "").strip()

        # Keep the event statement conservative. Knowledge may add stable context,
        # but it must not fabricate implementation details that Evidence did not contain.
        first = f"{title}しました。" if title.endswith(("修正", "追加", "整理", "復元", "改善", "検証")) else self.plain.rewrite(text, project, category, None)[1]
        context = why or purpose
        if context and context not in first:
            return title, f"{first}{context}"
        return title, first
