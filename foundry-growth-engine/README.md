# FOUNDRY GROWTH ENGINE

> 通称: **仕事してください。**
>
> **仕事してください。公開直前まで、こっちでやっときます。**

## Goal

仕事中に発生した文字・音声・写真・GitHub上の変更などから「何をしたか」を拾い、一般の人にも分かる更新情報へ変換し、必要に応じて個別記事・開発日誌・SNS投稿まで再編する。

公開前には必ずレビューを提示し、人間が **投稿 / 修正 / 記録だけ** を選ぶ。

## Non-goals

- 勝手に公開しない。
- GitHubのコミット文や技術用語をそのまま一般向け更新情報として出さない。
- 個人の書き癖をCoreに焼き込まない。
- 特定CMS・SNS依存の処理をCoreに焼き込まない。

## Architecture

```text
INPUT
  text / voice / photo / work log / GitHub events
        ↓
[ Input Adapter ]
        ↓
┌──────────────────────────┐
│ FOUNDRY GROWTH CORE      │
│                          │
│ normalize                │
│ detect meaningful change │
│ classify                 │
│ rewrite for humans       │
│ score article intent     │
│ build update/article     │
│ build daily journal      │
│ build SNS drafts         │
│ review gate              │
└──────────────────────────┘
       ↙              ↘
[ Knowledge Pack ]   [ Output Adapter ]
                          ↓
              GitHub Pages / CMS / SNS
```

## Core invariants

1. **Core is plain.** User/company-specific knowledge is external.
2. **Knowledge is replaceable.** 担当者交代時はKnowledge Packを交換できる。
3. **Adapters are replaceable.** 接続先変更でCoreを改造しない。
4. **Public release requires human approval.** 自動生成 != 自動公開。
5. **No-change hours do not create noise.** 変更がなければ最終確認時刻のみ更新する。
6. **Raw evidence survives.** UPDATEや日誌を作っても元記録は消さない。
7. **Core changes last.** 新SNS等はまずAdapter/Engine差し替えで吸収し、それでも足りない時のみCoreを変更する。

## Four operator intents

入力時またはレビュー時の人間の意図は最小4系統で扱う。

- **AUTO** — 入力量・密度・新規性・具体性からシステムが判断。
- **RECORD_ONLY** — 記録だけ。記事化しない。
- **FORCE_ARTICLE** — 情報量が少なくても記事候補へ昇格。
- **REVIEW_DECISION** — 投稿 / 修正 / 記録だけ。

## Article-intent learning

固定文字数だけでは判定しない。

```text
article_intent =
  input_volume
+ deviation_from_personal_baseline
+ density
+ novelty
+ specificity
+ external_value
+ explicit_user_intent
```

ユーザーが記事候補に対して `投稿 / 修正 / 記録だけ` を選んだ履歴をKnowledge側へ反映し、提案精度を改善する。

学習結果はCoreへ混ぜない。

## Knowledge layers

```text
ORGANIZATION
  brand rules / names / prohibited disclosures

PRODUCT
  products / projects / terminology / status

OPERATOR
  writing preference / article threshold / learned decisions

SESSION
  this-time-only instruction
```

すべて着脱可能とし、少なくとも次を提供する。

- CHANGE
- RESET TO PLAIN
- EXPORT
- IMPORT
- ARCHIVE
- CLONE

## Output classes

### UPDATE
短い一次公開記録。一般語で「何が変わったか」を伝える。

例:

> 機能追加｜WebAI Bridgeに購入後のAI設定機能を追加しました。

### ARTICLE / PRESS RELEASE
新製品、新プロジェクト、大きな機能変更など、外部価値が高いものを個別記事化。

### DEVELOPMENT JOURNAL
その日のUPDATE群を材料に再編集した日誌。UPDATE自体は保持する。

### INDEX
過去のUPDATE / ARTICLE / JOURNALを検索できる索引。

主な検索軸:

- free text
- project
- type
- date
- tag

### SNS DRAFT
記事・UPDATEを各SNS向けAdapterで再編した公開前ドラフト。

## Update board behavior

- 1時間に1回データを取得して再編する。
- 意味のある変更があった時だけUPDATEを追加する。
- 変更がなければ `最終確認 HH:MM / 変更なし / 監視継続中` の時刻だけ更新する。
- 技術ログは一般向けの短い分類へ翻訳する。

初期分類:

- 機能追加
- 機能変更
- 機能削除
- 新プロジェクト
- プロジェクト終了
- 新製品
- 製品終了
- 研究・検証
- 方針変更

## GitHub Pages adapter v0

最初のDogfood対象。

予定出力:

```text
/updates/
/articles/
/journal/
/archive/
/data/updates.json
/data/articles.json
/data/journals.json
```

トップには最新更新ボードと最新5日分の日誌タイトルを表示し、それ以前は検索可能なINDEXへ送る。

## Review gate

公開前の最後のUIは極力小さくする。

```text
レビューこれです。投稿しますか？

[ 投稿 ] [ 修正 ] [ 記録だけ ]
```

`投稿` のみOutput Adapterへ公開許可を渡す。

## Safety guard

公開前レビューは仕様上の必須機能。

理由:

- 機密情報
- 個人情報
- 写真への意図しない映り込み
- 誤認識
- 社外秘の数値
- 不適切な自動要約

を人間が最後に止めるため。

## Adapter contract direction

Output Adapterは概ね次の能力で統一する。

```text
preview(content)
publish_update(update)
publish_article(article)
publish_journal(journal)
publish_social(draft)
read_existing_content(query)
```

Input Adapterは概ね次へ正規化する。

```text
source_id
captured_at
actor
text
media[]
source_type
project_hint
explicit_intent
raw_evidence_ref
```

## v0 success criteria

1. GitHub上の実変更を1時間単位で取り込める。
2. 技術コミットを一般向けUPDATEへ変換できる。
3. 無変更時は時刻だけ更新できる。
4. UPDATEから日次JOURNALを生成できる。
5. 最新5日 + 過去INDEXを表示できる。
6. 個別記事候補を作れる。
7. レビューゲートで `投稿 / 修正 / 記録だけ` を選べる。
8. Knowledge Packを外してPlain Coreへ戻せる。
9. GitHub Pages AdapterをCoreから分離できている。
10. 元記録から公開物まで追跡可能である。

## Product explanation

**仕事してください。公開直前まで、こっちでやっときます。**

仕事中の文字入力・音声・作業記録から「何をしたか」を拾い、必要に応じてホームページの更新情報、個別記事、日誌、SNS投稿へ再編します。公開前にレビューを出すので、投稿 / 修正 / 記録だけを選ぶだけです。
