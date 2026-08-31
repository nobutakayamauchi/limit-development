# Public Catalog Contract

ONE PHONE FOUNDRY の商品棚・制作物・研究物カードは `data/catalog.json` を表示します。

`public-catalog.yml` が毎時、公開 GitHub リポジトリを取得して次の順で `data/catalog.json` を再生成します。

1. `sales-catalog/data/products.json` の `status: for_sale` を商品として取り込む
2. 各公開リポジトリの `.foundry/public.json` を制作物・研究物として取り込む
3. `data/catalog-seed.json` の editorial 設定で表示文言と順番を整える
4. 既存の legacy 公開物だけ `static_items` で補完する

## 新しい制作物・研究物を自動表示する

対象リポジトリに `.foundry/public.json` を置きます。

```json
{
  "id": "example-research",
  "name": "EXAMPLE RESEARCH",
  "status": "research",
  "kind": "RESEARCH",
  "cats": ["research"],
  "short": "E",
  "killer": "一言で何をするものか。",
  "summary": "公開カード用の短い説明。",
  "url": "https://github.com/nobutakayamauchi/example-research",
  "priority": 120
}
```

`status` は `public`, `published`, `research`, `for_sale` のいずれかを公開対象として扱います。`hidden` またはマニフェスト無しのリポジトリはカードへ自動追加しません。

この明示マニフェスト方式にする理由は、リポジトリが存在するだけで「商品」「完成した研究」と誤認して公開しないためです。

## 商品

販売商品は `sales-catalog/data/products.json` を正本とします。`status: for_sale` になった商品は次回同期で ONE PHONE FOUNDRY の商品棚へ入り、販売停止したものは自動で外れます。

## 表示側

- トップのスライドカード: `assets/home.js` が `data/catalog.json` を読む
- 制作物・研究物・商品一覧: `works/index.html` が同じ `data/catalog.json` を読む

表示側で別々のカード一覧を持たないため、トップと一覧の食い違いを防ぎます。
