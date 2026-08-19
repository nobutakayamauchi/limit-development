# FGE Repository Intake

新しいGitHubレポジトリは、FGEにとって「新しい公開候補が生まれた」イベントとして扱う。

```text
NEW REPO
→ FGE detects it
→ human wall-ball intake
→ CAROUSEL
→ VISUAL
→ LP
→ CTA
→ review gate
→ publish
```

## Important boundary

**NEW REPO != AUTO PUBLISH**

新レポを見つけても、FGEは勝手に商品化・LP化・公開しない。
まず `FGE intake` を作り、人間へ短い質問を返す。

質問で決めるもの:

- 制作物 / 研究物 / 商品 / 保留 / 記録だけ
- 正式名称 / 通称
- 「○○してください / やめてください」型の一言
- 非エンジニア向け説明
- 困りごと
- input / output
- 最後の人間操作
- 一枚絵
- CTA

回答後に `PRODUCT_CARD_LP_PLAYBOOK.md` の型へ流す。

## Detection

Hourly workflow runs:

```bash
python foundry-growth-engine/scripts/repo_intake.py \
  --config foundry-growth-engine/config/repo-intake.json
```

Public repos are detectable without an extra secret.
Private reposも対象にする場合だけ、repository secret `FGE_REPO_INTAKE_TOKEN` に対象GitHubアカウントのrepo一覧を読めるtokenを設定する。

Intake issue作成にはActionsの `GITHUB_TOKEN` を使う。
同じrepo名の intake issue が既にあれば再作成しない。

## Why this belongs in FGE

FGEは仕事記録をUPDATE / ARTICLE / JOURNAL / SNS draftへ変えるだけでなく、
**新しい制作物が発生した時に、公開棚へ載せるための素材を人間と確定する入口**も持つ。

ただし、公開判断は従来どおり人間に残す。
