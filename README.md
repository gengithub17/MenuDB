# MenuDB

料理と原材料を管理するメニューデータベースアプリケーションです。

## 機能一覧

- **料理検索**: 原材料やジャンルで料理を検索
  - あいまい検索: 指定した原材料のいずれかを含む料理を検索
  - 完全一致検索: 指定した原材料を全て含む料理を検索
- **料理管理**: 料理の登録・編集・削除
- **原材料管理**: 原材料の登録・削除
- **ジャンルフィルタリング**: 和風、洋風、中華など8種類のジャンルで絞り込み

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

1. トップページで原材料やジャンルを選択
2. 検索モード（あいまい/完全一致）を選択
3. 「検索」ボタンをクリック

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
│   ├── routes.py        # ルーティング
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

## 設定

### 環境変数

| 変数名 | デフォルト値 | 説明 |
|--------|-------------|------|
| FLASK_ENV | production | 実行環境 (development/production) |
| FLASK_DEBUG | 0 | デバッグモード (0/1) |
| DATABASE_PATH | /app/data/menudb.db | データベースファイルのパス |
| SECRET_KEY | (自動生成) | Flask秘密鍵 |

### アプリケーション設定

| 設定項目 | 値 | 説明 |
|---------|-----|------|
| ITEMS_PER_PAGE | 10 | 1ページあたりの表示件数 |
| MAX_GENRES_PER_DISH | 2 | 料理あたりの最大ジャンル数 |
| MAX_INGREDIENTS_PER_DISH | 10 | 料理あたりの最大原材料数 |
| MAX_MEMO_LENGTH | 500 | メモの最大文字数 |

## 開発者向け情報

### テスト環境の起動

```bash
docker-compose --profile test up web-test
```

テスト環境は http://localhost:5001 でアクセス可能です。

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
