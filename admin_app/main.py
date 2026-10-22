"""担当者用：問い合わせの受け取りと一覧（Flet）

担当者のパソコンで動かすアプリ。インターネットには公開しない。
「受け取る」を押すと、R2 の受信箱(inbox/)にある問い合わせを
手元のデータベース(SQLite)に移し、R2 からは消す。
個人情報を Cloudflare に長く置かないための仕組み。

R2 への接続情報は、環境変数か ~/.config/cloudflare/pages.env（cf-publish と同じファイル）で渡す。
コードやフォーム側には絶対に書かない:
  CLOUDFLARE_ACCOUNT_ID Cloudflare のアカウントID（cf-publish と同じ名前）
  R2_ACCESS_KEY_ID      R2 の APIトークンのアクセスキーID
  R2_SECRET_ACCESS_KEY  R2 の APIトークンのシークレット
  R2_BUCKET             バケット名（既定: contact-inbox）
"""

import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path

import boto3
import flet as ft

DB_PATH = Path(os.getenv("CONTACT_DB_PATH", Path(__file__).resolve().parent / "data" / "contacts.db"))
BUCKET = os.getenv("R2_BUCKET", "contact-inbox")
ASSETS_DIR = str(Path(__file__).resolve().parent.parent / "form_app" / "assets")  # フォントはフォームと共通

CATEGORY_LABELS = {"php_update": "PHPの更新", "rebuild": "作り直し", "study": "勉強会", "other": "その他"}


# ---- R2（S3互換API） ------------------------------------------------------
ENV_FILE = Path.home() / ".config" / "cloudflare" / "pages.env"


def load_env_file(path: Path = ENV_FILE) -> None:
    """KEY=VALUE の設定ファイルを読む。環境変数に同じ名前があれば、そちらを優先する。"""
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def r2_client():
    load_env_file()
    account = os.getenv("CLOUDFLARE_ACCOUNT_ID") or os.getenv("R2_ACCOUNT_ID")
    if not os.getenv("R2_ENDPOINT") and not account:
        raise KeyError("CLOUDFLARE_ACCOUNT_ID")
    endpoint = os.getenv("R2_ENDPOINT") or f"https://{account}.r2.cloudflarestorage.com"
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        region_name="auto",
    )


# ---- 手元のデータベース ----------------------------------------------------
def get_db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """CREATE TABLE IF NOT EXISTS contacts (
            id TEXT PRIMARY KEY, received_at TEXT NOT NULL, name TEXT NOT NULL, email TEXT NOT NULL,
            company TEXT NOT NULL, phone TEXT NOT NULL DEFAULT '', category TEXT NOT NULL,
            message TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'new')"""
    )
    # 電話番号の列が無い古いデータベースには、列を足す
    if "phone" not in [c["name"] for c in conn.execute("PRAGMA table_info(contacts)")]:
        conn.execute("ALTER TABLE contacts ADD COLUMN phone TEXT NOT NULL DEFAULT ''")
    return conn


def receive_from_r2(client=None) -> int:
    """R2 の受信箱を手元に移す。手元への保存が済んだものだけ R2 から消す。"""
    s3 = client or r2_client()
    moved = 0
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=BUCKET, Prefix="inbox/"):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            rec = json.loads(s3.get_object(Bucket=BUCKET, Key=key)["Body"].read())
            with get_db() as conn:
                conn.execute(
                    "INSERT OR IGNORE INTO contacts (id, received_at, name, email, company, phone, category, message)"
                    " VALUES (?,?,?,?,?,?,?,?)",
                    (rec["id"], rec["received_at"], rec["name"], rec["email"], rec.get("company", ""),
                     rec.get("phone", ""), rec["category"], rec["message"]),
                )
            s3.delete_object(Bucket=BUCKET, Key=key)
            moved += 1
    return moved


def load(only_new: bool) -> list[sqlite3.Row]:
    with get_db() as conn:
        sql = "SELECT * FROM contacts" + (" WHERE status = 'new'" if only_new else "")
        return conn.execute(sql + " ORDER BY received_at DESC").fetchall()


def set_status(contact_id: str, status: str):
    with get_db() as conn:
        conn.execute("UPDATE contacts SET status = ? WHERE id = ?", (status, contact_id))


def local_time(iso: str) -> str:
    return datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone().strftime("%Y/%m/%d %H:%M")


# ---- 画面 -----------------------------------------------------------------
def main(page: ft.Page):
    page.title = "問い合わせ（担当者用）"
    page.fonts = {"NotoSansJP": "fonts/NotoSansJP-Regular.ttf"}
    page.theme = ft.Theme(color_scheme_seed="#0E5F57", font_family="NotoSansJP")
    page.padding = 16

    only_new = ft.Switch(label="未対応だけ表示", value=True)
    count = ft.Text()
    notice = ft.Text()
    items = ft.ListView(expand=True, spacing=8)

    def card(r: sqlite3.Row) -> ft.Control:
        is_new = r["status"] == "new"

        def toggle(e):
            set_status(r["id"], "done" if is_new else "new")
            refresh()

        return ft.Card(
            content=ft.Container(
                padding=14,
                content=ft.Column(
                    spacing=6,
                    controls=[
                        ft.Row(
                            [
                                ft.Text(r["name"], weight=ft.FontWeight.BOLD, size=16),
                                ft.Text(r["company"] or "", color=ft.Colors.ON_SURFACE_VARIANT),
                                ft.Text(CATEGORY_LABELS.get(r["category"], r["category"]), color=ft.Colors.PRIMARY),
                            ],
                            wrap=True,
                            spacing=12,
                        ),
                        ft.Text(f"{local_time(r['received_at'])}　受付番号 {r['id']}　{r['email']}"
                                + (f"　{r['phone']}" if r["phone"] else ""),
                                size=12, selectable=True, color=ft.Colors.ON_SURFACE_VARIANT),
                        ft.Text(r["message"], selectable=True),
                        ft.Row(
                            [ft.FilledButton(content="対応済みにする", on_click=toggle) if is_new
                             else ft.OutlinedButton(content="未対応に戻す", on_click=toggle)]
                        ),
                    ],
                ),
            )
        )

    def refresh(e=None):
        rows = load(only_new.value)
        items.controls = [card(r) for r in rows] or [ft.Text("表示する問い合わせはありません。")]
        count.value = f"{len(rows)}件"
        page.update()

    def receive(e):
        try:
            n = receive_from_r2()
            notice.value = f"{n}件を受け取りました" if n else "新しい問い合わせはありません"
            notice.color = None
        except KeyError as err:
            notice.value = f"R2への接続情報（環境変数 {err.args[0]}）が設定されていません"
            notice.color = ft.Colors.ERROR
        except Exception:
            notice.value = "R2から受け取れませんでした。接続情報と通信状況を確認してください"
            notice.color = ft.Colors.ERROR
        refresh()

    only_new.on_change = refresh

    page.add(
        ft.Row(
            [ft.Text("問い合わせ", size=22, weight=ft.FontWeight.BOLD), count, only_new,
             ft.FilledButton(content="受け取る", icon=ft.Icons.DOWNLOAD, on_click=receive), notice],
            wrap=True,
            spacing=16,
        ),
        items,
    )
    refresh()


if __name__ == "__main__":
    ft.run(main, assets_dir=ASSETS_DIR)
