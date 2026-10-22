"""問い合わせフォームの見本（Flet）

`flet publish main.py` または `flet build web` で静的Webアプリとして書き出すと、
このPythonはお客さまのブラウザの中（Pyodide / WebAssembly）で動く。
公開Webサーバーはファイルを配るだけで、プログラムは動かさない。
"""

import asyncio
import json
import re
import sys

import flet as ft

from config import API_URL

IS_BROWSER = sys.platform == "emscripten"
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

CATEGORIES = [
    ("php_update", "PHPの更新について"),
    ("rebuild", "作り直しの相談"),
    ("study", "勉強会について"),
    ("other", "その他"),
]


async def post_json(url: str, data: dict) -> tuple[int, dict]:
    """JSONを送って (ステータスコード, 返ってきたJSON) を返す。"""
    body = json.dumps(data, ensure_ascii=False)
    if IS_BROWSER:
        # ブラウザの中で動いているときは、ブラウザの fetch を使う
        from pyodide.http import pyfetch

        res = await pyfetch(url, method="POST", headers={"Content-Type": "application/json"}, body=body)
        try:
            payload = await res.json()
        except Exception:
            payload = {}
        return res.status, payload

    # パソコンで試しに動かすとき（flet run）は標準ライブラリで送る
    import urllib.error
    import urllib.request

    def _send():
        req = urllib.request.Request(
            url, data=body.encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                return r.status, json.loads(r.read() or b"{}")
        except urllib.error.HTTPError as e:
            try:
                return e.code, json.loads(e.read() or b"{}")
            except Exception:
                return e.code, {}

    return await asyncio.to_thread(_send)


def main(page: ft.Page):
    page.title = "お問い合わせ"
    page.theme_mode = ft.ThemeMode.LIGHT
    # 日本語フォントを同梱する（CDNを使わない書き出しでは、これがないと日本語が□になる。
    # また、同梱しないと漢字が中国語の字形で表示されることがある）
    page.fonts = {"NotoSansJP": "fonts/NotoSansJP-Regular.ttf"}
    page.theme = ft.Theme(color_scheme_seed="#0E5F57", font_family="NotoSansJP")
    page.scroll = ft.ScrollMode.AUTO
    page.padding = 16

    # ---- 入力欄 ----
    name = ft.TextField(label="お名前（必須）", max_length=50, autofill_hints=ft.AutofillHint.NAME)
    email = ft.TextField(
        label="メールアドレス（必須）",
        max_length=254,
        keyboard_type=ft.KeyboardType.EMAIL,
        autofill_hints=ft.AutofillHint.EMAIL,
    )
    company = ft.TextField(label="会社名・屋号（任意）", max_length=100)
    phone = ft.TextField(
        label="電話番号（任意）",
        max_length=20,
        keyboard_type=ft.KeyboardType.PHONE,
        autofill_hints=ft.AutofillHint.TELEPHONE_NUMBER,
        # 数字とハイフンだけ入力できる
        input_filter=ft.InputFilter(regex_string=r"[0-9-]", allow=True),
    )
    category = ft.Dropdown(
        label="ご用件（必須）",
        options=[ft.DropdownOption(key=k, text=t) for k, t in CATEGORIES],
        expand=True,
    )
    message = ft.TextField(label="内容（必須）", multiline=True, min_lines=5, max_lines=10, max_length=2000)
    consent = ft.Checkbox(label="入力した個人情報を、このお問い合わせへの回答のためだけに使うことに同意します")
    consent_error = ft.Text(color=ft.Colors.ERROR, size=12, visible=False)
    status = ft.Text(color=ft.Colors.ERROR, visible=False)
    sending = ft.ProgressRing(width=20, height=20, stroke_width=2, visible=False)
    submit = ft.FilledButton(content="送信する")

    fields = {"name": name, "email": email, "company": company, "phone": phone, "message": message}

    def clear_errors():
        for f in fields.values():
            f.error = None
        category.error_text = None
        consent.error = False
        consent_error.visible = False
        status.visible = False

    def set_error(key: str, msg: str):
        if key in fields:
            fields[key].error = msg
        elif key == "category":
            category.error_text = msg
        elif key == "consent":
            consent.error = True  # Checkboxは赤くするだけなので、文言は下のTextに出す
            consent_error.value = msg
            consent_error.visible = True

    def check_locally() -> bool:
        """見た目のための事前チェック。本当のチェックは受付APIで必ずやり直す。"""
        ok = True
        if not (name.value or "").strip():
            set_error("name", "お名前を入力してください"); ok = False
        if not EMAIL_RE.match((email.value or "").strip()):
            set_error("email", "メールアドレスの形式が正しくありません"); ok = False
        if not category.value:
            set_error("category", "ご用件を選んでください"); ok = False
        if not (message.value or "").strip():
            set_error("message", "内容を入力してください"); ok = False
        if not consent.value:
            set_error("consent", "同意が必要です"); ok = False
        return ok

    def show_status(msg: str):
        status.value = msg
        status.visible = True

    async def on_submit(e):
        clear_errors()
        if not check_locally():
            page.update()
            return

        submit.disabled = True
        sending.visible = True
        page.update()

        data = {
            "name": name.value.strip(),
            "email": email.value.strip(),
            "company": (company.value or "").strip(),
            "phone": (phone.value or "").strip(),
            "category": category.value,
            "message": message.value.strip(),
            "consent": bool(consent.value),
        }
        try:
            code, res = await post_json(API_URL, data)
        except Exception:
            code, res = 0, {}

        submit.disabled = False
        sending.visible = False

        if code == 201:
            show_done(res.get("id", ""))
        elif code == 422 and isinstance(res.get("detail"), list):
            # 受付APIが見つけた入力の問題を、該当する欄に表示する
            for d in res["detail"]:
                loc = d.get("loc", [])
                key = loc[-1] if loc else ""
                set_error(str(key), str(d.get("msg", "")).removeprefix("Value error, "))
            show_status("入力内容を確認してください")
        elif code == 429:
            show_status(res.get("detail", "しばらくしてからもう一度お試しください"))
        else:
            show_status("送信できませんでした。通信状況を確認して、もう一度お試しください")
        page.update()

    submit.on_click = on_submit

    form = ft.Column(
        controls=[
            ft.Text("お問い合わせ", size=26, weight=ft.FontWeight.BOLD),
            ft.Text("内容を確認のうえ、2営業日以内にメールでご連絡します。"),
            name,
            email,
            company,
            phone,
            ft.Row([category]),
            message,
            consent,
            consent_error,
            ft.Row([submit, sending], spacing=12, tight=True),
            status,
        ],
        spacing=14,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
    )

    done = ft.Column(visible=False, spacing=14)

    def show_done(contact_id: str):
        form.visible = False
        done.controls = [
            ft.Text("送信しました", size=26, weight=ft.FontWeight.BOLD),
            ft.Text("お問い合わせありがとうございます。2営業日以内にメールでご連絡します。"),
            ft.Text(f"受付番号：{contact_id}", selectable=True, weight=ft.FontWeight.BOLD),
            ft.OutlinedButton(content="もう一件送る", on_click=reset),
        ]
        done.visible = True

    def reset(e):
        for f in fields.values():
            f.value = ""
        category.value = None
        consent.value = False
        clear_errors()
        done.visible = False
        form.visible = True
        page.update()

    page.add(ft.Container(content=ft.Column([form, done]), width=640))


if __name__ == "__main__":
    ft.run(main)
