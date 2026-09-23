# MenuDB

料理と原材料を管理するメニューデータベースアプリケーションです。

## 機能一覧

- **料理検索**: 原材料やジャンルで料理を検索
  - あいまい検索: 指定した原材料のいずれかを含む料理を検索
  - 完全一致検索: 指定した原材料を全て含む料理を検索
  - トップページにアクセスした時点でデフォルト設定（検索モード・表示件数）で即座に結果を表示（後述）
- **料理管理**: 料理の登録・編集・削除
- **原材料管理**: 原材料の登録・削除
- **ジャンルフィルタリング**: 和風、洋風、中華など8種類のジャンルで絞り込み
- **JSON API (`/api/v1`)**: 検索・登録・編集・削除など画面上の操作を外部スクリプトからも実行可能（後述）

## 技術スタック

| 種別 | 技術 |
|------|------|
| バックエンド | Flask 3.0 |
| データベース | SQLite |
| フロントエンド | Bootstrap 5, Bootstrap Icons |
| コンテナ | Docker, Docker Compose |

## 必要環境

- Docker
- Docker Compose

## セットアップ手順

### 1. リポジトリのクローン

```bash
git clone <repository-url>
cd MenuDB
```

### 2. アプリケーションの起動

```bash
docker-compose up -d web
```

### 3. ブラウザでアクセス

http://localhost:5000

## 使い方

### 料理を検索する

1. トップページにアクセスすると、デフォルト設定（検索モード・表示件数）で全料理が即座に一覧表示される
2. 原材料やジャンルを選択し、必要に応じて検索モード（あいまい/完全一致）・表示件数を変更して「検索」ボタンをクリック
3. 「この設定をデフォルトにする」ボタンで、現在の検索モード・表示件数を次回アクセス時のデフォルトとして保存できる（ログイン経由でのアクセス時のみ、ユーザーごとに保存。それ以外はアプリ全体のデフォルトが使われる）

### 料理を登録する

1. 「編集モード」に切り替え
2. 「料理を追加」ボタンをクリック
3. 料理名、ジャンル、原材料、難易度を入力
4. 「登録」ボタンをクリック

### 原材料を登録する

1. ヘッダーの「原材料管理」をクリック
2. 「原材料を追加」ボタンをクリック
3. 原材料名とカテゴリを選択
4. 「登録」ボタンをクリック

## ディレクトリ構成

```
MenuDB/
├── app/
│   ├── __init__.py      # アプリケーションファクトリ
│   ├── config.py        # 設定
│   ├── models.py        # データモデル
│   ├── routes.py        # ルーティング（HTML画面）
│   ├── api.py           # /api/v1 JSON API
│   ├── services.py      # 画面・APIで共有するCRUD/検索ロジック
│   ├── forms.py         # フォーム定義
│   ├── templates/       # HTMLテンプレート
│   └── static/          # CSS、favicon等
├── data/                # データベースファイル
├── tests/               # テストコード
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

## データモデル

### エンティティ関係図

```
┌─────────────────────┐     ┌─────────────────────┐
│ ingredient_categories│     │     dish_genres     │
│─────────────────────│     │─────────────────────│
│ id                  │     │ id                  │
│ name                │     │ name                │
│ display_order       │     └──────────┬──────────┘
└──────────┬──────────┘                │
           │                           │ 多対多
           │ 1対多                     │
           ▼                           ▼
┌─────────────────────┐     ┌─────────────────────┐
│     ingredients     │     │       dishes        │
│─────────────────────│     │─────────────────────│
│ id                  │◄───►│ id                  │
│ name                │ 多  │ name                │
│ category_id         │ 対  │ difficulty          │
│ display_order       │ 多  │ memo                │
└─────────────────────┘     │ created_at          │
                            │ updated_at          │
                            └─────────────────────┘
```

### マスターデータ

**原材料カテゴリ** (固定)
| ID | 名前 |
|----|------|
| 1 | 肉 |
| 2 | 魚介 |
| 3 | 野菜 |
| 4 | 加工食品 |
| 5 | 既製品 |

**料理ジャンル** (固定)
| ID | 名前 |
|----|------|
| 1 | 和風 |
| 2 | 洋風 |
| 3 | 中華 |
| 4 | パスタ |
| 5 | 麺 |
| 6 | 海鮮 |
| 7 | 汁物 |
| 8 | 副菜 |

### その他のテーブル

| テーブル | 説明 |
|---------|------|
| `api_keys` | `/api/v1` 用に発行されたAPIキー（ハッシュ化して保存、ユーザー1人につき常に1件） |
| `user_search_settings` | ユーザーごとのデフォルト検索設定（検索モード・表示件数） |

## 設定

### 環境変数

| 変数名 | デフォルト値 | 説明 |
|--------|-------------|------|
| FLASK_ENV | production | 実行環境 (development/production) |
| FLASK_DEBUG | 0 | デバッグモード (0/1) |
| DATABASE_PATH | /app/data/menudb.db | データベースファイルのパス |
| SECRET_KEY | (自動生成) | Flask秘密鍵 |
| JWT_AUTH_ENABLED | false | 有効にすると、`X-Auth-Request-Email`ヘッダーへの信頼をやめ、`Authorization: Bearer <IDトークン>`をKeycloakの公開鍵で署名検証してログインユーザーを判定する(後述) |
| JWT_ISSUER | (未設定) | 検証時に一致を要求するissuer。例: `https://auth.genserver.net/realms/main` |
| JWT_AUDIENCE | (未設定) | 検証時に一致を要求するaudience(KeycloakクライアントID)。例: `MenuDB` |
| JWT_JWKS_URL | (未設定) | 署名検証用の公開鍵(JWKS)取得先。例: `https://auth.genserver.net/realms/main/protocol/openid-connect/certs` |

### JWT検証によるログインユーザー判定(オプション機能)

`X-Auth-Request-Email`ヘッダーは、手前のリバースプロキシ(oauth2-proxy)が付与した値をアプリ側で
一切検証せずに信用する設計になっている。ネットワーク経路がoauth2-proxy以外から遮断されている限りは
安全だが、その前提が崩れると任意のユーザーへのなりすましが可能になってしまう(詳細な経緯は
運用側のセキュリティ調査メモを参照)。

`JWT_AUTH_ENABLED=true`にすると、この判定を`X-Auth-Request-Email`ヘッダーではなく、
リクエストに付与された`Authorization: Bearer <IDトークン>`をKeycloakの公開鍵(JWKS)で
署名検証した結果に切り替える。ネットワーク経路に依存せず、署名を偽造できない限りなりすませない。

- 有効化には、oauth2-proxy側で`pass_authorization_header = true`を設定し、IDトークンを
  アプリまで転送する必要がある(oauth2-proxy.cfgへの1行追加のみ。Keycloak側の設定変更は不要)
- `JWT_AUTH_ENABLED`が`true`の間は`X-Auth-Request-Email`ヘッダーへのフォールバックは行わない
  (トークンが無い・検証に失敗した場合は常に未ログイン扱い)
- `JWT_ISSUER`・`JWT_AUDIENCE`・`JWT_JWKS_URL`のいずれかが未設定の場合も、エラーログを出した上で
  常に未ログイン扱いになる(fail closed)
- 既定は`false`(無効)。oauth2-proxy側の設定変更と足並みを揃えて有効化することを想定した
  オプトイン機能

### アプリケーション設定

| 設定項目 | 値 | 説明 |
|---------|-----|------|
| ITEMS_PER_PAGE | 10 | 1ページあたりの表示件数（検索デフォルトの表示件数としても使用） |
| MAX_GENRES_PER_DISH | 2 | 料理あたりの最大ジャンル数 |
| MAX_INGREDIENTS_PER_DISH | 10 | 料理あたりの最大原材料数 |
| MAX_MEMO_LENGTH | 500 | メモの最大文字数 |
| DEFAULT_SEARCH_MODE | fuzzy | ユーザー固有の設定が無い場合の検索デフォルトモード |
| API_KEY_EXPIRY_HOURS | 1 | APIキーの有効期限（発行から何時間で失効するか） |

## API (`/api/v1`)

画面でできる操作（検索・登録・編集・削除）を外部スクリプトから利用するためのJSON APIを提供しています。
認証方法・エンドポイント一覧・利用例は [API.md](API.md) を参照してください。

## 開発者向け情報

### テスト環境の起動

```bash
docker-compose --profile test up web-test
```

テスト環境は http://localhost:5001 でアクセス可能です。

### ログイン状態のローカル再現(開発環境限定)

本番はoauth2-proxy + nginxがログインユーザーのメールアドレスを`X-Auth-Request-Email`ヘッダーで
アプリに渡しますが、ローカルの`docker-compose`にはこのプロキシが無いため、素の状態ではブックマークの
登録・検索デフォルト設定の保存・APIキー発行など、ログインユーザーに紐づく機能を確認できません。

`web-test`サービスは`DEV_FAKE_USER_EMAIL`環境変数(既定値: `test@example.com`)を設定しており、
ヘッダーが無い場合はこのメールアドレスでログイン済みとして動作します。この設定は`DevelopmentConfig`/
`TestingConfig`にのみ存在し、`ProductionConfig`には定義されていないため、本番環境には一切影響しません。

### コンテナの停止

```bash
docker-compose down
```

### ログの確認

```bash
docker-compose logs -f web
```

### データベースの初期化

データベースファイルを削除して再起動すると、マスターデータが自動的に再作成されます。

```bash
rm data/menudb.db
docker-compose restart web
```

## Acknowledgments

このプロジェクトのコードの大部分は [Claude](https://www.anthropic.com/claude)（Anthropic社のAIアシスタント）を使用して生成されました。

## License

MIT License - 詳細は [LICENSE](LICENSE) を参照してください。
