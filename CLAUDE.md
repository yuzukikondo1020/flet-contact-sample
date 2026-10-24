# この場所の決まり
- 言語は Python。画面は Flet。TypeScript・Node・PHP は使わない。
- Python は `.venv` の仮想環境を使う。本体に `pip install` しない。
- 依存は最小にする。標準ライブラリで足りる物に外の部品を足さない。
- 公開は `flet publish` で静的サイトにする。サーバーで動く物は作らない。
- Flet の部品名・引数は推測しない。flet MCP の get_api で確かめてから書く。
- 上の決まりに合わない物が要ると思ったら、作らずに止まって言う。
- 例外：`worker/` の受付Worker（Cloudflare Worker の JavaScript）は、このまま直してよい。Node や npm の部品は足さず、公開は cf-publish で行う。
