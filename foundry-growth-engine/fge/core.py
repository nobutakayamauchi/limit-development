from __future__ import annotations

from dataclasses import dataclass, asdict, field
import hashlib
import json
import re
from typing import Iterable

PUBLIC_TYPES = (
    "機能追加", "機能変更", "機能削除", "新プロジェクト", "プロジェクト終了",
    "新製品", "製品終了", "研究・検証", "方針変更",
)
INTENT_AUTO = "AUTO"
INTENT_RECORD_ONLY = "RECORD_ONLY"
INTENT_FORCE_ARTICLE = "FORCE_ARTICLE"

@dataclass(frozen=True)
class Evidence:
    source_id: str
    captured_at: str
    actor: str
    text: str
    source_type: str = "unknown"
    project_hint: str = ""
    explicit_intent: str = INTENT_AUTO
    raw_evidence_ref: str = ""
    media: tuple[str, ...] = ()

@dataclass
class Update:
    id: str
    source_id: str
    captured_at: str
    type: str
    project: str
    title: str
    summary: str
    tags: list[str] = field(default_factory=list)
    raw_evidence_ref: str = ""
    article_score: float = 0.0
    article_candidate: bool = False
    review_status: str = "pending"
    def to_dict(self): return asdict(self)

@dataclass
class ArticleDraft:
    id: str
    update_id: str
    captured_at: str
    project: str
    title: str
    dek: str
    body: str
    tags: list[str]
    review_status: str = "pending"
    def to_dict(self): return asdict(self)

@dataclass
class Journal:
    date: str
    title: str
    summary: str
    update_ids: list[str]
    projects: list[str]
    types: list[str]
    tags: list[str]
    def to_dict(self): return asdict(self)

def _stable_id(prefix, value):
    return f"{prefix}-{hashlib.sha256(value.encode()).hexdigest()[:12]}"

def load_knowledge(path):
    if not path: return {}
    with open(path, encoding="utf-8") as f: data = json.load(f)
    if not isinstance(data, dict): raise ValueError("knowledge pack must be a JSON object")
    return data

def _match_rule(text, knowledge):
    for rule in knowledge.get("rewrite_rules", []):
        p = rule.get("pattern", "")
        if p and re.search(p, text, flags=re.I): return rule
    return None

def classify(text, rule=None):
    if rule and rule.get("type") in PUBLIC_TYPES: return rule["type"]
    patterns = [
        ("新製品", r"\b(release|launch|product)\b|新製品|リリース"),
        ("製品終了", r"\b(discontinue|sunset product)\b|製品終了"),
        ("新プロジェクト", r"\b(new project|scaffold|bootstrap|init project)\b|新プロジェクト|発足"),
        ("プロジェクト終了", r"\b(archive project|sunset project|end project)\b|プロジェクト終了|廃止"),
        ("機能削除", r"\b(remove|delete|drop|deprecat)\w*\b|削除|廃止"),
        ("研究・検証", r"\b(test|verify|experiment|benchmark|probe|audit|da\b|meteor)\b|検証|実験|監査"),
        ("機能追加", r"\b(add|create|introduce|implement|enable|support)\w*\b|追加|実装"),
        ("機能変更", r"\b(fix|update|change|polish|refactor|revert|restore|align|improve)\w*\b|修正|変更|更新|復元"),
        ("方針変更", r"\b(docs?|readme|policy|direction|strategy|clarify|document)\w*\b|方針|説明"),
    ]
    for label, p in patterns:
        if re.search(p, text.lower(), flags=re.I): return label
    return "機能変更"

def detect_project(text, project_hint, knowledge):
    if project_hint: return project_hint
    for item in knowledge.get("project_aliases", []):
        p = item.get("pattern", "")
        if p and re.search(p, text, flags=re.I): return item.get("project") or "FOUNDRY"
    return knowledge.get("organization", {}).get("default_project", "FOUNDRY")

def article_intent_score(evidence, category, rule, knowledge):
    if evidence.explicit_intent == INTENT_RECORD_ONLY: return 0.0
    if evidence.explicit_intent == INTENT_FORCE_ARTICLE: return 1.0
    if rule and "article_score" in rule: return max(0.0, min(1.0, float(rule["article_score"])))
    base = max(40, int(knowledge.get("operator", {}).get("baseline_chars", 180)))
    n = len(evidence.text.strip())
    volume = min(1.0, n / (base * 3))
    deviation = min(1.0, max(0.0, n - base) / (base * 2))
    novelty = {"新製品":1.0,"新プロジェクト":.95,"製品終了":.9,"プロジェクト終了":.85,"機能追加":.65,"方針変更":.55,"機能削除":.5,"研究・検証":.5,"機能変更":.35}.get(category,.35)
    specificity = min(1.0, (.35 if re.search(r"\d", evidence.text) else 0) + (.25 if "/" in evidence.text or "#" in evidence.text else 0) + (.4 if len(evidence.text.split()) >= 8 else .15))
    return round(max(0.0, min(1.0, .22*volume + .18*deviation + .34*novelty + .26*specificity)), 3)

def _knowledge_writer_enabled(knowledge):
    return bool(knowledge) and knowledge.get("mode") == "KNOWLEDGE" and bool(knowledge.get("project_profiles"))

def build_update(evidence, knowledge=None):
    knowledge = knowledge or {}
    rule = _match_rule(evidence.text, knowledge)
    category = classify(evidence.text, rule)
    project = detect_project(evidence.text, evidence.project_hint, knowledge)
    from .engines import KnowledgeAwarePublicWriter, RuleBasedPublicWriter
    writer = KnowledgeAwarePublicWriter(knowledge) if _knowledge_writer_enabled(knowledge) else RuleBasedPublicWriter()
    title, summary = writer.rewrite(evidence.text, project, category, rule)
    score = article_intent_score(evidence, category, rule, knowledge)
    threshold = float(knowledge.get("operator", {}).get("article_threshold", .72))
    tags = sorted(set([project, category] + (rule.get("tags", []) if rule else [])))
    return Update(_stable_id("upd", evidence.source_id), evidence.source_id, evidence.captured_at, category, project, title, summary, tags, evidence.raw_evidence_ref, score, score >= threshold and evidence.explicit_intent != INTENT_RECORD_ONLY)

def build_article(update, evidence, knowledge=None):
    knowledge = knowledge or {}
    rule = _match_rule(evidence.text, knowledge)
    detail = rule.get("article_detail") if rule else None
    if not detail and _knowledge_writer_enabled(knowledge):
        profile = knowledge.get("project_profiles", {}).get(update.project, {})
        description = str(profile.get("public_description") or "").strip()
        why = str(profile.get("why_it_matters") or "").strip()
        pieces = [update.summary, description, why]
        detail = "\n\n".join(x for x in pieces if x)
    if not detail:
        detail = f"{update.summary}\n\n今回の変更は『{update.type}』として記録されています。元の作業記録は公開物とは分離して保持し、必要なら技術的な根拠まで追跡できます。"
    return ArticleDraft(_stable_id("art", update.id), update.id, update.captured_at, update.project, update.title, update.summary, detail, update.tags)

def build_journals(updates: Iterable[Update]):
    by = {}
    for u in updates: by.setdefault(u.captured_at[:10], []).append(u)
    out = []
    for day in sorted(by, reverse=True):
        items = sorted(by[day], key=lambda u: u.captured_at, reverse=True)
        projects = sorted({u.project for u in items}); types = sorted({u.type for u in items}); tags = sorted({t for u in items for t in u.tags})
        title = items[0].title if len(items) == 1 else f"{projects[0]}ほか、{len(items)}件の更新"
        out.append(Journal(day, title, " / ".join(u.title for u in items[:4]), [u.id for u in items], projects, types, tags))
    return out

def build_sns_drafts(update):
    base = f"{update.title}\n\n{update.summary}"
    tag = re.sub(r"[^0-9A-Za-z一-龥ぁ-んァ-ンー]", "", update.project)
    return {"plain": base, "x": f"{base}\n\n#{tag}"}

def search_documents(updates, articles, journals):
    docs = []
    for u in updates: docs.append({"kind":"UPDATE","id":u.id,"date":u.captured_at[:10],"title":u.title,"summary":u.summary,"project":u.project,"type":u.type,"tags":u.tags,"href":f"../updates/#u-{u.id}"})
    for a in articles: docs.append({"kind":"ARTICLE","id":a.id,"date":a.captured_at[:10],"title":a.title,"summary":a.dek,"project":a.project,"type":"記事候補","tags":a.tags,"href":f"../articles/{a.id}.html"})
    for j in journals: docs.append({"kind":"JOURNAL","id":f"journal-{j.date}","date":j.date,"title":j.title,"summary":j.summary,"project":", ".join(j.projects),"type":"開発日誌","tags":j.tags,"href":f"../journal/{j.date}.html"})
    return docs
