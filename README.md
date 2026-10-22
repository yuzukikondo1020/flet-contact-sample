# PHPを使わないサイトの見本（静的サイト＋Fletフォーム＋Cloudflare）

PHP も WordPress も使わずに、お知らせページと問い合わせフォームを作る見本です。
公開しているサーバーではプログラムを動かさないので、PHP の脆弱性の影響を受けません。

## 構成

```
お客さまのブラウザ
  ├─ お知らせのページ（site/、静的なHTML）
  └─ 問い合わせフォーム（form_app/、Fletで作って静的Webアプリに書き出す）
        │  Python はブラウザの中（Pyodide / WebAssembly）で動く
        ▼  送信
     受付Worker（worker/、Cloudflare Worker）
        │  入力をもう一度チェックして
        ▼
     R2 の受信箱（inbox/）
        ▲  「受け取る」で手元に移し、R2 からは消す
担当者のパソコン
  └─ 担当者用アプリ（admin_app/、Flet）── 手元の SQLite に保存
```

| フォルダ | 中身 | 動く場所 |
| --- | --- | --- |
| `site/` | お知らせのページ（HTML） | Cloudflare Pages |
| `form_app/` | 問い合わせフォーム（Flet） | Cloudflare Pages から配り、お客さまのブラウザで動く |
| `worker/` | 受付Worker（JavaScript） | Cloudflare Workers |
| `admin_app/` | 担当者用アプリ（Flet） | 担当者のパソコン |
| `tests/` | 受付Worker と担当者用アプリのテスト | 開発する人のパソコン |

## 用意するもの

- Python 3.12 以上
- Node.js 20 以上（受付Worker を `wrangler` で動かす・公開するため）
- Cloudflare のアカウント（無料）

```bash
pip install -r form_app/requirements.txt -r admin_app/requirements.txt
cd worker && npm install
```

## 手元で動かす

ターミナルを3つ開きます。

**1. 受付Worker を起動する**（R2 も手元で再現されます）

```bash
cd worker
npx wrangler dev --port 8787
```

**2. フォームを起動する**

```bash
cd form_app
flet run --web --port 8550 main.py
```

ブラウザが開いたら、入力して送信します。「送信しました」と受付番号が出れば成功です。

**3. テストを動かす**（受付Worker を起動したまま）

```bash
pip install pytest boto3 "moto[server]"
python -m pytest tests
```

手元の `wrangler dev` の R2 は担当者用アプリから読めないため、担当者用アプリは Cloudflare に公開してから試します。

## Cloudflare に公開する

### 1. R2 のバケットを作る

```bash
cd worker
npx wrangler login
npx wrangler r2 bucket create contact-inbox
```

### 2. 受付Worker を公開する

`worker/wrangler.jsonc` の `ALLOWED_ORIGINS` を、フォームを置くサイトのURL（手順4で決まる `https://<プロジェクト名>.pages.dev`）に書き換えてから公開します。

```bash
npx wrangler deploy
```

表示された `https://contact-receiver.<サブドメイン>.workers.dev` が受付Worker のURLです。

### 3. フォームを書き出す

`form_app/config.py` の `API_URL` を、手順2のURLに `/api/contact` を付けたものに書き換えます。

```bash
cd form_app
flet build web --base-url contact
```

`build/web/` の中身を `site/contact/` にコピーします。

- `flet build web` は初回に Flutter SDK を自動で取得するため、時間がかかります。
- Flutter SDK を入れたくない場合は、`flet publish main.py -a assets --base-url contact --distpath ../site/contact` でも書き出せます。

### 4. お知らせページとフォームを公開する

```bash
npx wrangler pages deploy ../site --project-name <プロジェクト名>
```

Cloudflare の画面（Workers & Pages → Pages → アップロード）から `site/` フォルダをドラッグして公開することもできます。

### 5. 担当者用アプリを設定する

Cloudflare の画面で R2 の APIトークンを作ります（権限：オブジェクトの読み取りと書き込み、対象：`contact-inbox` だけ）。表示された値を環境変数に入れて起動します。

```bash
export R2_ACCOUNT_ID=...
export R2_ACCESS_KEY_ID=...
export R2_SECRET_ACCESS_KEY=...
cd admin_app
python main.py
```

「受け取る」を押すと、R2 の問い合わせが手元に移り、R2 からは消えます。

## 安全のための決まりごと

- **フォーム側（`form_app/`）にはURL以外を書かない。** ブラウザに配られるファイルは誰でも中身を読めます。
- **R2 の APIトークンは担当者のパソコンにだけ置く。** フォームにも、受付Worker にも、Git にも入れません。対象のバケットを `contact-inbox` だけに絞ります。
- **入力チェックは受付Worker で必ずやり直す。** フォーム側のチェックは表示のためだけです。
- **受付Worker は機能を増やさない。** 受け取って保存するだけにします。一覧を返す、削除する、といった機能は付けません。
- **問い合わせを R2 に長く置かない。** こまめに「受け取る」を押します。次回は、受け取り先を社内の Debian サーバーにします。

## 受付Worker がしているチェック

- 必須項目、文字数、メールアドレスの形式、ご用件が決められた選択肢か、同意にチェックがあるか
- 制御文字（目に見えない特殊な文字）を取り除く
- 許可したサイト以外からのブラウザ経由の送信を拒否する
- 同じ送信元からの連続送信を制限する（60秒に5件。`wrangler.jsonc` の `ratelimits`）
- 16KBを超える送信を拒否する
- `/api/contact` への POST 以外には応えない

## 確認済みのこと・まだのこと（2026年10月22日時点、Flet 1.0.5 / wrangler 4.147.0）

| 項目 | 状態 |
| --- | --- |
| 受付Worker のチェック（テスト13件、`wrangler dev`） | 確認済み |
| 担当者用アプリの受け取り処理（テスト3件、S3互換エミュレーター） | 確認済み |
| フォームの表示、エラー表示、送信 → 受付Worker → R2 保存 | 確認済み（Flet の Web サーバーモードで実際のブラウザから） |
| 担当者用アプリで受け取り、R2 から消える | 確認済み（S3互換エミュレーターで） |
| 静的に書き出したフォームをブラウザで開いて送信する（Pyodide 上の動作、ブラウザからの CORS） | **未確認**。作業環境から Pyodide の配布元につながらなかったため |
| 本物の Cloudflare（Pages / Workers / R2）への公開 | **未確認** |

## フォントについて

日本語を正しく表示するため、`form_app/assets/fonts/` に Noto Sans JP を同梱しています（SIL Open Font License 1.1）。同梱しないと、外部CDNを使わない書き出しでは日本語が表示されません。また、漢字が中国語の字形で表示されることがあります。
