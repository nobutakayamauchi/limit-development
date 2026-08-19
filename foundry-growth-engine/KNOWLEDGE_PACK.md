# Knowledge Pack v2

FGEのKnowledgeは「作者の全部を覚えさせるファイル」ではない。

目的は、**同じEvidenceを、誰向け・何の文脈で・どう説明するかを外付けすること**。

```text
Evidence = 起きた事実
Core     = 分類・変換の共通処理
Knowledge= 安定した意味・用語・文章方針
Review   = 公開責任
```

## 一番扱いやすい書き方

巨大な自由文を1本入れるより、次の順で構造化する。

### 1. SAFETY

Knowledgeが使ってよい範囲を先に固定する。

- public only
- KnowledgeはEvidenceにない出来事を捏造しない
- 非公開の健康・法律・家族・顧客・秘密情報を推測しない

### 2. PUBLIC CONTEXT

頻繁には変わらない本人・組織の判断基準だけを書く。

例:

- AIは目的ではなく、現場の面倒を減らす手段
- 新造は最後。既存資産を先に探す
- 失敗と修正も開発記録に残す

今日だけの事情や一時的な指示はここへ入れない。

### 3. VOICE

「作者っぽい単語集」より、文章の判断ルールを書く。

良い例:

- 非エンジニアを先に理解させる
- 最初の一文で意味を伝える
- 専門用語だけで説明を終えない
- 失敗を隠さないが、失敗自慢にはしない
- 根拠のない最上級を使わない

### 4. PROJECT PROFILE

制作物ごとに最低3点だけ持つ。

```text
killer_copy       = 一言で何者か
public_description= 何をするものか
why_it_matters    = なぜ必要か
```

新レポの壁打ち結果は、まずここへ追加する。

### 5. TERM REPLACEMENT

技術語を一般向けに読むための辞書。

例:

```text
journal      -> 開発日誌
navigation   -> 導線
review gate  -> 公開前レビュー
fallback     -> 予備表示
```

### 6. SURGICAL REWRITE RULE

重要な出来事だけ、Evidenceのパターンに対して人間が確認した説明を固定する。

これは強いので乱用しない。

```text
pattern -> type / title / summary / article_score
```

通常の変更はProject Profile + Voiceで処理し、商品公開・大きな方針変更・説明事故を直した時などだけRuleを追加する。

## 入れない方がいいもの

- 今日だけの気分
- 長い自伝
- GitHubから取れる事実のコピー
- 非公開の個人事情
- 推測で補った理由
- 「この言い回しを必ず使え」の大量指定

Knowledgeが大きくなりすぎたら、Coreを賢くしたのではなく**作者をハードコードし直している**可能性がある。

## PLAINとの関係

`knowledge.plain.json` は作者情報を持たない基準線。

```text
same Evidence
   ├─ PLAIN      -> Coreの素の出力
   └─ KNOWLEDGE  -> 公開文脈を足した出力
```

通常運用ではKNOWLEDGE版をレビュー候補にする。
PLAIN版は同じrunで必ず生成し、比較用baselineとしてartifactへ残す。

重要:

```text
KNOWLEDGE BETTER != CORE CHANGED
PLAIN AVAILABLE == KNOWLEDGE REPLACEABLE
```

Knowledgeを外した瞬間に元へ戻れなければ、Knowledge PackではなくCoreへの焼き込みになっている。

## 更新フロー

```text
新レポ / 新制作物
  ↓
壁打ち
  ↓
Project Profile
  ↓
必要なら用語辞書
  ↓
重要イベントだけRewrite Rule
  ↓
PLAIN / KNOWLEDGEを比較
  ↓
人間レビュー
```

この構成なら、別の作者・会社へ渡す時はKnowledge Packだけ交換できる。
