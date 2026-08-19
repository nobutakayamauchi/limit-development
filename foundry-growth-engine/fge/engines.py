from __future__ import annotations

class RuleBasedPublicWriter:
    """Default zero-secret writer. Replace this slot with another writer/LLM later."""
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
