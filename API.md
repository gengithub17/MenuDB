# MenuDB API (`/api/v1`)

画面（ブラウザ）でできる操作 — 料理・原材料の検索・登録・編集・削除 — を、外部スクリプトからJSON形式で利用するためのAPIです。

## 認証

MenuDBは通常、SSO（Keycloak + oauth2-proxyなど）のログインセッションでブラウザアクセスを保護しています。しかし外部スクリプトは対話的なログイン（ブラウザでのOIDC認証フロー）を完了できないため、`/api/v1/*` はセッションではなく**APIキー**で認証します。

### 1. APIキーを発行する

1. ブラウザで通常どおりログインした状態で `/account/api-key` にアクセスする
2. 「発行する」ボタンを押すと、新しいAPIキーが**画面に一度だけ**表示される
   - キーの実体はハッシュ化してDBに保存されるため、画面を閉じると二度と表示されない。無くした場合は再発行する
   - 有効期限は発行から **`API_KEY_EXPIRY_HOURS`（デフォルト1時間）**。切れたら再発行が必要
   - 1ユーザーにつき常に有効なキーは1つ。再発行すると古いキーは即座に失効する
   - ログインユーザーを識別できない経路（後述のリバースプロキシ構成に依存）からアクセスした場合は発行できない

### 2. APIキーを使ってリクエストする

リクエストヘッダー `X-API-Key` に発行したキーを指定する。

```bash
curl -H "X-API-Key: <発行したキー>" https://menu.genserver.net/api/v1/dishes
```

キーが無い・不正・期限切れの場合は `401 Unauthorized` が返る。

```json
{"error": "invalid or missing X-API-Key"}
```

## エンドポイント一覧

料理・原材料の `to_dict()` 形式のJSONを返す。ページネーション付き一覧は `{"items": [...], "page", "per_page", "total", "pages"}` の形式。

### 料理 (dishes)

| メソッド | パス | 説明 |
|---------|------|------|
| GET | `/api/v1/dishes` | 検索・一覧 |
| GET | `/api/v1/dishes/<id>` | 詳細 |
| POST | `/api/v1/dishes` | 登録 |
| PUT | `/api/v1/dishes/<id>` | 更新 |
| DELETE | `/api/v1/dishes/<id>` | 削除 |

**GET `/api/v1/dishes` のクエリパラメータ**

| パラメータ | 説明 |
|-----------|------|
| `ingredient_ids` | 原材料IDのカンマ区切り（例: `1,2,3`） |
| `genre_ids` | ジャンルIDのカンマ区切り |
| `mode` | `fuzzy`（いずれかを含む、既定）/ `exact`（全て含む） |
| `page` | ページ番号（既定 1） |
| `per_page` | 1ページの件数（既定は `ITEMS_PER_PAGE` 設定値） |

```bash
curl -H "X-API-Key: $KEY" \
  "https://menu.genserver.net/api/v1/dishes?ingredient_ids=1,2&mode=fuzzy&per_page=20"
```

**POST/PUT のリクエストボディ**（JSON）

```json
{
  "name": "親子丼",
  "difficulty": 2,
  "memo": "ふわとろ卵で",
  "genre_ids": [1],
  "ingredient_ids": [3, 11, 30]
}
```

`name`（1〜100文字必須）、`difficulty`（1〜5必須）、`memo`（500文字以内、任意）、`genre_ids`（`MAX_GENRES_PER_DISH`件まで）、`ingredient_ids`（`MAX_INGREDIENTS_PER_DISH`件まで）。違反時は `400` と `{"error": "..."}` を返す。

### 原材料 (ingredients)

| メソッド | パス | 説明 |
|---------|------|------|
| GET | `/api/v1/ingredients` | 一覧（`q`: 名前の部分一致検索、`category_id`: 分類で絞り込み） |
| GET | `/api/v1/ingredients/<id>` | 詳細（使用している料理の件数 `usage` を含む） |
| POST | `/api/v1/ingredients` | 登録（`{"name": "...", "category_id": 1}`。同名が既にある場合は`400`） |
| DELETE | `/api/v1/ingredients/<id>` | 削除（使用中の料理からも自動的に外れる） |

画面に編集機能がないため、原材料の更新APIはありません。

### マスタデータ

| メソッド | パス | 説明 |
|---------|------|------|
| GET | `/api/v1/genres` | 料理ジャンル一覧 |
| GET | `/api/v1/categories` | 原材料分類一覧 |

## 参考メモ: 認証プロキシ配下にAPIパスを追加したときにやったこと

このアプリはoauth2-proxy + nginxでブラウザアクセスをSSO保護していますが、外部スクリプトは対話的なログインを完了できないため、`/api/v1` だけは別の認証（APIキー）に切り替える必要がありました。ここは私の環境（oauth2-proxy + nginx の `auth_request` 構成）でつまずいた点のメモです。他の認証プロキシやインフラ構成では事情が異なるはずなので、あくまで一例・参考情報として読んでください（この通りにすれば動くことを保証するものではありません）。

私の場合、次の2点でハマりました。

- oauth2-proxyの `skip_auth_regex` を設定しただけでは効かなかった。nginxの `auth_request` は認証チェックのために `/oauth2/auth` という固定パスへ内部的にサブリクエストを投げる仕組みで、oauth2-proxy側からは常にそのパスしか見えないため、クライアントが本来アクセスしたいパス（`/api/v1/dishes` など）を別途ヘッダーで伝えてやる必要がありました。私の場合は `X-Forwarded-Uri` ヘッダーを追加したら解決しましたが、認証プロキシの種類やバージョンによって必要なヘッダー名は変わり得るので、使っているものの公式ドキュメントを確認するのが確実だと思います。

- 設定ファイルをDockerの単一ファイルbind mount（`./oauth2-proxy.cfg:/etc/.../oauth2-proxy.cfg:ro` のような形式）で渡していたため、ホスト側でファイルを書き換えてもコンテナ内では古い内容のままになる、ということが私の環境では起きました（編集ツールがファイルをその場編集ではなく置き換える形で保存していたためのようです）。`reload` シグナルだけでなく、コンテナ自体を再起動して反映されているか確認する、という一手間が必要でした。

なお、認証プロキシ側で経路を素通りさせるようにした部分は、当然ながらノーガード状態になるので、そのパスはアプリ側（今回で言えばAPIキーのチェック）で必ず別途保護しています。
