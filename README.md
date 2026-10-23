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
- Cloudflare のアカウント（無料）

```bash
pip install -r form_app/requirements.txt -r admin_app/requirements.txt cf-publish
```

Cloudflare への公開には [cf-publish](https://pypi.org/project/cf-publish/) を使います。Python だけで公開できるので、Node.js は要りません（本番で連続送信の制限を付けるときだけ、Node.js 20 以上が要ります）。

## 手元で動かす

**1. フォームを起動する**

```bash
cd form_app
flet run --web --port 8550 main.py
```

ブラウザにフォームが開きます。空のまま送信すると、入力していない欄が赤くなります。送信先（受付Worker）がまだ無いので、入力して送信すると「送信できませんでした」と出ます。これで正常です。

**2. 受付Worker も手元で動かす（任意）**

受付Worker を手元で試すときだけ、Node.js 20 以上が必要です。

```bash
cd worker
npx wrangler@4.147.0 dev --port 8787
```

この状態でフォームから送信すると、「送信しました」と受付番号が出ます。

**3. テストを動かす（任意）**（受付Worker を手元で起動したまま）

```bash
pip install pytest boto3 "moto[server]"
python -m pytest tests
```

続けて動かすと、受付Worker の連続送信の制限（60秒に5件）に引っかかって失敗します。1分おいてから動かしてください。

## Cloudflare に公開する

以下では、サイトの名前（Pages のプロジェクト名）を `my-site` とします。公開後のURLは `https://my-site.pages.dev` です。ほかの人と重ならない名前にしてください。

### 1. Cloudflare の鍵を用意する

1. Cloudflare の画面右上のアイコン →「My Profile」→「API Tokens」→「Create Token」→「Custom token」で、次の3つの権限を付けたトークンを作ります。
   - Account ／ Cloudflare Pages ／ Edit
   - Account ／ Workers Scripts ／ Edit
   - Account ／ Workers R2 Storage ／ Edit
2. 次のファイルを作り、トークンとアカウントID（Cloudflare の画面の「Account home」などに表示されます）を書きます。
   - Windows：`C:\Users\<ユーザー名>\.config\cloudflare\pages.env`
   - Mac・Linux：`~/.config/cloudflare/pages.env`

   ```
   CLOUDFLARE_API_TOKEN=ここにトークン
   CLOUDFLARE_ACCOUNT_ID=ここにアカウントID
   ```

このファイルは自分のパソコンにだけ置きます。GitHub や Discord に貼らないでください。

### 2. 受付Worker を公開する

```bash
cd worker
cf-publish worker deploy . --var ALLOWED_ORIGINS=https://my-site.pages.dev --workers-dev
```

- 保存先のバケット `contact-inbox` が無ければ、このとき一緒に作られます。
- 最後に表示される `https://contact-receiver.<サブドメイン>.workers.dev` が受付Worker のURLです。メモしておきます。
- `--workers-dev` は、受付Worker をインターネットから呼べるようにする指定です。

**連続送信の制限を付ける（Node.js 20 以上が必要）**

cf-publish は、`wrangler.toml` に書いた連続送信の制限（`ratelimits`）を送りません。制限を付けるときは、続けて wrangler で公開し直します。wrangler は `pages.env` を読まないので、先に中身を環境変数に読み込みます。

Windows（PowerShell）:

```powershell
Get-Content "$HOME\.config\cloudflare\pages.env" | ForEach-Object { $k, $v = $_ -split '=', 2; if ($v) { Set-Item "env:$k" $v.Trim() } }
npx wrangler@4.147.0 deploy --var ALLOWED_ORIGINS:https://my-site.pages.dev
```

Mac・Linux:

```bash
set -a; . ~/.config/cloudflare/pages.env; set +a
npx wrangler@4.147.0 deploy --var ALLOWED_ORIGINS:https://my-site.pages.dev
```

- 「last updated via the script API」という警告が出ますが、cf-publish で公開したものを上書きするという意味なので、そのまま進めて構いません。
- 制限が効き始めるまで、数分かかります。また、きっちり5件では止まりません（Cloudflare の中の複数の機械が別々に数えるため）。大量の送信を減らすためのものと考えてください。
- このあと受付Worker を公開し直すときも、wrangler を使います。cf-publish で公開し直すと、制限が外れることがあります。

### 3. フォームを書き出す

`form_app/config.py` の `API_URL` を、手順2のURLに `/api/contact` を付けたものに書き換えます。

```python
API_URL = "https://contact-receiver.<サブドメイン>.workers.dev/api/contact"
```

書き出して、お知らせページの `contact` フォルダに入れます。

```bash
cd form_app
flet build web --base-url contact
```

`build/web/` の中身を `site/contact/` にコピーします。

- `flet build web` は初回に Flutter SDK を自動で取得するため、時間がかかります。前日までに一度動かしておいてください。OS ごとの準備は [docs/flet-build-web.md](docs/flet-build-web.md) にあります。
- Flutter SDK を入れたくない場合は、`flet publish main.py -a assets --base-url contact --distpath ../site/contact` でも書き出せます。
- 手元で書き出さずに、GitHub の上で書き出して公開することもできます（下の「GitHub Actions で公開する」）。

### 4. お知らせページとフォームを公開する

いちばん上のフォルダ（`README.md` がある場所）に戻って実行します。

```bash
cf-publish site --project my-site
```

`https://my-site.pages.dev` を開き、「お問い合わせ」から送信します。「送信しました」と受付番号が出れば成功です。

- フォームを開いてから使えるようになるまで、10〜15秒かかります。そのあいだ、日本語が □ で表示されます。Python（Pyodide）と日本語フォントを読み込んでいるためで、故障ではありません。
- cf-publish が最後に表示する `https://<英数字>.my-site.pages.dev` からは送信できません。受付Worker が受け付けるのは、手順2の `ALLOWED_ORIGINS` に書いた `https://my-site.pages.dev` からの送信だけです。

### 5. 担当者用アプリで受け取る

1. Cloudflare の画面の「R2」→「Manage API Tokens」で、R2 用のトークンを作ります（権限：オブジェクトの読み取りと書き込み、対象：`contact-inbox` だけ）。手順1のトークンとは別物です。
2. 表示されたアクセスキーIDとシークレットを、手順1の `pages.env` に書き足します。

   ```
   R2_ACCESS_KEY_ID=ここにアクセスキーID
   R2_SECRET_ACCESS_KEY=ここにシークレット
   ```

3. 担当者用アプリを起動して「受け取る」を押します。

   ```bash
   cd admin_app
   python main.py
   ```

R2 の問い合わせが手元に移り、R2 からは消えます。

## GitHub Actions で公開する（手元に Flutter SDK を入れない場合）

手順3・4の代わりに使えます。`site/` か `form_app/` を変えて main に push すると、GitHub の上でフォームを書き出し（`flet build web`）、Pages に公開します（`.github/workflows/deploy-pages.yml`）。手順1・2（鍵と受付Worker）は、先に手元で済ませておきます。

1. このリポジトリを自分の GitHub に置きます（Fork するか、新しいリポジトリに push する）。Fork したときは、「Actions」タブで Actions を有効にします。
2. リポジトリの「Settings」→「Secrets and variables」→「Actions」で、次の4つを登録します。

   | 種類 | 名前 | 値 |
   | --- | --- | --- |
   | Variables | `PAGES_PROJECT` | Pages のプロジェクト名（例：`my-site`） |
   | Variables | `API_URL` | 手順2のURLに `/api/contact` を付けたもの |
   | Secrets | `CLOUDFLARE_API_TOKEN` | `pages.env` と同じトークン |
   | Secrets | `CLOUDFLARE_ACCOUNT_ID` | `pages.env` と同じアカウントID |

3. main に push します。「Actions」タブの「お知らせページとフォームを公開する」→「Run workflow」で、手で動かすこともできます。
4. 終わったら `https://my-site.pages.dev` を開いて、送信を試します。

- `form_app/config.py` は書き換えなくて構いません。Actions が `API_URL` を書き込んでから書き出します。
- 初回は Flutter SDK を取ってくるので、数分かかります。2回目からは取っておいたものを使います。
- Variables を登録するまでは、書き出しまでで止まり、公開はしません。プルリクエストでも書き出しだけをします。書き出したものは、Actions の画面の「site」からダウンロードして確かめられます。
- R2 の鍵（`R2_ACCESS_KEY_ID`、`R2_SECRET_ACCESS_KEY`）は GitHub に登録しません。担当者のパソコンにだけ置きます。
- 受付Worker は、ここでは公開しません。連続送信の制限を付けるため、手順2のとおり手元の wrangler で公開します。

## 安全のための決まりごと

- **フォーム側（`form_app/`）にはURL以外を書かない。** ブラウザに配られるファイルは誰でも中身を読めます。
- **R2 の APIトークンは担当者のパソコンにだけ置く。** フォームにも、受付Worker にも、Git にも入れません。対象のバケットを `contact-inbox` だけに絞ります。
- **入力チェックは受付Worker で必ずやり直す。** フォーム側のチェックは表示のためだけです。
- **受付Worker は機能を増やさない。** 受け取って保存するだけにします。一覧を返す、削除する、といった機能は付けません。
- **問い合わせのデータベースを Git に入れない。** `admin_app/data/` には個人情報が入ります。`.gitignore` で除いてあるので、消さないでください。
- **フォームに欄を足すときは、受付Worker（`TEXT_FIELDS`）と担当者用アプリにも足す。** 受付Worker は知らない欄を黙って捨てます。`tests/test_fields_match.py` が、そろっていないと失敗します。
- **問い合わせを R2 に長く置かない。** こまめに「受け取る」を押します。次回は、受け取り先を社内の Debian サーバーにします。

## 受付Worker がしているチェック

- 必須項目、文字数、メールアドレスの形式、電話番号が数字とハイフンだけか、ご用件が決められた選択肢か、同意にチェックがあるか
- 制御文字（目に見えない特殊な文字）を取り除く
- 許可したサイト以外からのブラウザ経由の送信を拒否する
- 同じ送信元からの連続送信を制限する（60秒に5件。`wrangler.toml` の `ratelimits`）。**cf-publish で公開した場合、この設定は送られません。** 本番で制限するときは、手順2の「連続送信の制限を付ける」のとおり wrangler で公開し直してください
- 16KBを超える送信を拒否する
- `/api/contact` への POST 以外には応えない

## 確認済みのこと・まだのこと（2026年10月22日時点、Flet 1.0.5 / cf-publish 0.3.1）

| 項目 | 状態 |
| --- | --- |
| 受付Worker のチェック（テスト16件、`wrangler dev`） | 確認済み |
| フォーム・受付Worker・担当者用アプリの入力欄がそろっている（テスト2件） | 確認済み |
| 担当者用アプリの受け取り処理（テスト5件、S3互換エミュレーター） | 確認済み |
| フォームの表示、エラー表示、送信 → 受付Worker → R2 保存 | 確認済み（Flet の Web サーバーモードで実際のブラウザから） |
| 担当者用アプリで受け取り、R2 から消える | 確認済み（S3互換エミュレーターと、本物の R2 で） |
| cf-publish で受付Worker と Pages を本物の Cloudflare に公開する | 確認済み（Windows で） |
| 静的に書き出したフォームを本物の Pages から開いて送信する（Pyodide 上の動作、ブラウザからの CORS） → 受付Worker → R2 → 担当者用アプリ | 確認済み（電話番号まで届くことも） |
| 上の通しの確認を、`flet build web` と `flet publish` の両方で書き出したフォームで行う | 確認済み |
| 本番での連続送信の制限（wrangler で公開し直す） | 確認済み（効き始めまで数分。効き方はゆるく、30回続けて送ると11回目あたりから一部が断られた） |

## フォントについて

日本語を正しく表示するため、`form_app/assets/fonts/` に Noto Sans JP を同梱しています（SIL Open Font License 1.1）。同梱しないと、外部CDNを使わない書き出しでは日本語が表示されません。また、漢字が中国語の字形で表示されることがあります。

## ライセンス

コードは MIT License です（`LICENSE`）。同梱フォントは SIL Open Font License 1.1 です（`form_app/assets/fonts/OFL.txt`）。
