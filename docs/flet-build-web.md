# flet build web を使いたい人へ（任意）

勉強会では、フォームを `flet publish` で書き出します（準備資料の「動作確認」と同じ）。この資料が無くても困りません。

`flet build web` で書き出すと、Python の部品を先に詰めておくので、ページを開いたときの読み込みが速くなります。そのかわり、初回に Flutter SDK を取ってくるので時間がかかります。使いたい人だけ、ここに書いた準備を足してください。分からない所は、エラーの文をそのまま Claude に貼れば教えてもらえます。

## 全員共通

先に、勉強会の準備資料（Windows編・Mac編・Linuxに変える）のとおり、Python 3.13 の仮想環境 `.venv` を有効にして、見本の部品を入れておきます。ここまでは `flet publish` と同じです。

Flutter SDK は自分で入れなくて大丈夫です。`flet build web` を初めて動かしたときに、Flet が自動で `ホームフォルダ/flutter/<版>` に入れます。そのぶん初回は時間がかかり、ディスクも 3〜4GB ほど使います（Windows で Flutter SDK が 3.1GB、Flet の部品が 0.25GB でした）。

1. 下の Windows・Mac・Linux のうち、自分の OS の準備を足します。
2. `(.venv)` が出ている状態で、フォームのフォルダで書き出します。

   ```bash
   cd form_app
   flet build web --base-url contact
   ```

3. 最後に「Successfully built your web app!」と出て、`build/web/` ができれば完了です。`build/web/` の中身を `site/contact/` にコピーして、README の手順4のとおり公開します。

2回目からは、取ってきた部品を使うので数分で終わります。

## Windows

足すのは Git for Windows です。Flutter が Git を使うためです。Windows 11 で試しました（Flet 1.0.5、Python 3.13）。

1. [Git for Windows](https://git-scm.com/download/win) を入れます。入っているかは、PowerShell で `git --version` と打って確かめられます。
2. 長いパスを使えるようにしておきます。

   ```powershell
   git config --global core.longpaths true
   ```

つまずきやすい所：

- 「Filename too long」や「unable to open database file」と出る。Windows のパスの長さの制限です。準備資料の段2のとおり、作業フォルダを浅い場所（`$HOME\flet-study` や `C:\flet-study`）に作っていれば、まず起きません。
- 出力を別のコマンドにつなぐと、「UnicodeEncodeError: 'cp932'」で落ちる。日本語の Windows の文字コードのせいです。環境変数 `PYTHONUTF8=1` を付けると動きます。ふつうに PowerShell で打つぶんには起きません。

## Mac

足すのは Xcode のコマンドラインツールです。Flutter が使う Git などが入っています。Xcode そのもの（大きいアプリ）は要りません。

```bash
xcode-select --install
```

確かめる画面が出たら「インストール」を押します。すでに入っていれば、そのように表示されます。Mac編には「この勉強会では要らない。キャンセルでよい」とありますが、`flet build web` を使うときは入れます。

Mac mini（Apple シリコン、macOS 26.2、Flet 1.0.5）で、書き出しが約40秒で通りました。この Mac には Flutter SDK がもともと入っていたので、初回に取ってくるところは試せていません。

つまずきやすい所：

- Homebrew の Python（python@3.12、python@3.13）は、macOS 26.2 では仮想環境を作るところで「ensurepip … returned non-zero exit status」と出て失敗しました（2026年10月24日、入れ直しても同じ）。Mac編のとおり、python.org の Python を使ってください。
- 試したときは、python.org の Python の代わりに uv で入れた Python 3.12 を使いました。python.org の Python 3.13 では試していません。
- Intel の Mac は、今は使えますが、Flutter がこの先の版で対応をやめる予定です。

## Linux

Flutter が使う道具を、パッケージで足します。Debian や Ubuntu なら、次のとおりです。

```bash
sudo apt update
sudo apt install -y curl git unzip xz-utils zip libglu1-mesa
```

ほかのディストリビューションでは、同じ名前のパッケージを入れます。WSL の Ubuntu 24.04 で試しました（Flet 1.0.5）。

つまずきやすい所：

- 「detected dubious ownership in repository at '…/flutter/<版>'」と出て書き出しが止まる。root で動かしているときに起きます（WSL では、初めの利用者が root のことがあります）。メッセージに出ているコマンドを打ってから、もう一度書き出します。

  ```bash
  git config --global --add safe.directory ~/flutter/<版>
  ```

- デスクトップアプリ向けの clang、cmake、libgtk-3-dev などは、Web に書き出すだけなら要りません。
- 2回目の書き出しは、WSL の Ubuntu で約1分40秒、GitHub Actions の Ubuntu で約3分でした。

## 困ったとき

- **エラーが出たとき**：エラーの文をそのまま Claude に貼って、「`flet build web` でこう出ました」と聞きます。Claude Code があれば、入れる作業も任せられます。勉強会の質問は Flet の日本語チャンネル（[Discord](https://discord.gg/u4ZJNM67Pj)）で受けます。
- **間に合わないとき**：`flet publish` に戻します（README の手順3）。
- **自分のパソコンで書き出さないとき**：GitHub に置いた見本を push すると、GitHub Actions が `flet build web` して Cloudflare Pages に公開します。やり方は [README](../README.md) の「GitHub Actions で公開する」にあります。

## 参考にしたページ

- [Flet：Publish](https://flet.dev/docs/publish/)（Flutter SDK が自動で入ること）
- [Flet：Static website](https://flet.dev/docs/publish/web/static-website/)（flet build web と flet publish の違い）
- [Flutter：Install Flutter manually](https://docs.flutter.dev/install/manual)（OS ごとに要るもの）
- [Flutter：Set up Linux development](https://docs.flutter.dev/platform-integration/linux/setup)（デスクトップ向けだけに要るもの）

（2026年10月24日時点）
