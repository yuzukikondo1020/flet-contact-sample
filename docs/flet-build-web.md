# flet build web の入れ方（Windows・Mac・Linux）

問い合わせフォームを `flet build web` で書き出せるようにしておくための手順です。初回は大きな部品を取ってくるので、勉強会の前日までに一度動かしてください。分からない所は、エラーの文をそのまま Claude に貼れば教えてもらえます。

## 全員共通

Flutter SDK は自分で入れなくて大丈夫です。`flet build web` を初めて動かしたときに、Flet が自動で `ホームフォルダ/flutter/<版>` に入れます。そのぶん初回は時間がかかり、ディスクも 3〜4GB ほど使います（Windows で Flutter SDK が 3.1GB、Flet の部品が 0.25GB でした）。

1. Python 3.12 以上を入れます。
2. 見本（このリポジトリ）のいちばん上のフォルダで、Flet を入れます。Mac と Linux は、下の各 OS の手順で作る仮想環境の中で入れます。

   ```bash
   pip install -r form_app/requirements.txt
   ```

3. 下の Windows・Mac・Linux のうち、自分の OS の準備をします。
4. フォームのフォルダで、一度書き出してみます。

   ```bash
   cd form_app
   flet build web --base-url contact
   ```

5. 最後に「Successfully built your web app!」と出て、`build/web/` ができれば準備完了です。

2回目からは、取ってきた部品を使うので数分で終わります。

## Windows

自分で入れるのは Git for Windows だけです。Flutter が Git を使うためです。この手順は Windows 11 で実際に試しました（Flet 1.0.5）。

1. [Git for Windows](https://git-scm.com/download/win) を入れます。入っているかは、ターミナルで `git --version` と打って確かめられます。
2. 長いパスを使えるようにしておきます。

   ```bash
   git config --global core.longpaths true
   ```

3. 見本は `C:\work` のような、浅いフォルダに置きます。

つまずきやすい所：

- 「Filename too long」や「unable to open database file」と出る。Windows のパスの長さの制限です。深いフォルダや、長い名前のフォルダの中で作業すると起きます。上の2と3で防げます。
- 出力を別のコマンドにつなぐと、「UnicodeEncodeError: 'cp932'」で落ちる。日本語の Windows の文字コードのせいです。環境変数 `PYTHONUTF8=1` を付けると動きます。ふつうにターミナルで打つぶんには起きません。

## Mac

自分で入れるのは、Xcode のコマンドラインツールと、新しい Python です。Mac mini（Apple シリコン、macOS 26.2、Flet 1.0.5）で実際に試しました。

1. Xcode のコマンドラインツールを入れます。Flutter が使う Git などが入っています。Xcode そのもの（大きいアプリ）は、Web に書き出すだけなら要りません。

   ```bash
   xcode-select --install
   ```

   確かめる画面が出たら「インストール」を押します。すでに入っていれば、そのように表示されます。

2. uv（Python を入れる道具）で Python 3.12 を入れ、見本のフォルダに仮想環境を作ります。Mac にはもともと Python 3.9 が入っていますが、古くて使えません。

   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   uv venv --python 3.12 --seed .venv
   . .venv/bin/activate
   pip install -r form_app/requirements.txt
   ```

   uv は、Homebrew を使っているなら `brew install uv` でも入ります（試したのはこちら）。

つまずきやすい所：

- Homebrew の Python（python@3.12、python@3.13）は、macOS 26.2 では仮想環境を作るところで「ensurepip … returned non-zero exit status」と出て失敗しました（2026年10月24日、入れ直しても同じ）。Python の部品が macOS の部品と合っていないためです。上の uv で入れた Python なら動きます。
- python.org のインストーラーで入れた Python でもよいはずですが、試していません。
- Intel の Mac は、今は使えますが、Flutter がこの先の版で対応をやめる予定です。
- この Mac には Flutter SDK がもともと入っていたので、初回に取ってくるところは試せていません。書き出しは約40秒でした。

## Linux

Flutter が使う道具を、パッケージで入れます。Ubuntu など Debian 系なら、次のとおりです。

```bash
sudo apt-get update -y
sudo apt-get install -y curl git unzip xz-utils zip libglu1-mesa python3-venv
```

ほかのディストリビューションでは、同じ名前のパッケージ（curl、git、unzip、xz-utils、zip、libglu1-mesa）を入れます。python3-venv は、下の「仮想環境」を作るためのものです。WSL の Ubuntu 24.04（Flet 1.0.5）で実際に試しました。

つまずきやすい所：

- 「externally-managed-environment」と出て pip で入れられない。Ubuntu 24.04 などでは、システムの Python に直接入れられません。仮想環境を作ってから入れます。

  ```bash
  python3 -m venv .venv
  . .venv/bin/activate
  pip install -r form_app/requirements.txt
  ```

- 「detected dubious ownership in repository at '…/flutter/<版>'」と出て書き出しが止まる。root で動かしているときに起きます（WSL では、初めの利用者が root のことがあります）。メッセージに出ているコマンドを打ってから、もう一度書き出します。

  ```bash
  git config --global --add safe.directory ~/flutter/<版>
  ```

- デスクトップアプリ向けの clang、cmake、libgtk-3-dev などは、Web に書き出すだけなら要りません。
- 2回目の書き出しは、WSL の Ubuntu で約1分40秒、GitHub Actions の Ubuntu で約3分でした。

## 困ったとき・間に合わないとき

- **エラーが出たとき**：エラーの文をそのまま Claude に貼って、「`flet build web` でこう出ました」と聞きます。Claude Code があれば、入れる作業も任せられます。勉強会の質問は Flet の日本語チャンネル（[Discord](https://discord.gg/u4ZJNM67Pj)）で受けます。
- **Flutter を入れたくないとき**：`flet publish` なら Flutter が要りません。書き出しは速いかわりに、ページを開いたときの読み込みは遅くなります。

  ```bash
  flet publish main.py -a assets --base-url contact --distpath ../site/contact
  ```

- **自分のパソコンで書き出さないとき**：GitHub に置いた見本を push すると、GitHub Actions が `flet build web` して Cloudflare Pages に公開します。やり方は [README](../README.md) の「GitHub Actions で公開する」にあります。

## 参考にしたページ

- [Flet：Publish](https://flet.dev/docs/publish/)（Flutter SDK が自動で入ること）
- [Flet：Static website](https://flet.dev/docs/publish/web/static-website/)（flet build web と flet publish の違い）
- [Flutter：Install Flutter manually](https://docs.flutter.dev/install/manual)（OS ごとに要るもの）
- [Flutter：Set up Linux development](https://docs.flutter.dev/platform-integration/linux/setup)（デスクトップ向けだけに要るもの）

（2026年10月24日時点）
