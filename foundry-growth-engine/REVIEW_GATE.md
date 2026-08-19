# Review Gate

> **レビューこれです。投稿しますか？**

FOUNDRY GROWTH ENGINE v0 は **自動生成 != 自動公開** を破らない。

| Human intent | GitHub v0 action |
|---|---|
| 投稿 | 生成物をPRに載せ、レビュー後にMerge |
| 修正 | PRまたはKnowledge Packを修正して再生成 |
| 記録だけ | 公開PRへ昇格しない。raw evidenceは保持 |

GitHub Pagesは静的ホスティングなので、公開サイト上のボタンから直接GitHubへ書き込むために認証トークンをブラウザへ置く設計は採用しない。
将来、認証済みReview Adapterを追加しても、この3状態と「投稿だけが公開権限を渡す」というCore invariantは変えない。
