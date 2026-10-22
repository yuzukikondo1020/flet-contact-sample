"""フォームの入力欄と、受付Worker が保存する欄がそろっているかのテスト。受付Worker を起動しなくても動く。

フォームにだけ欄を足すと、受付Worker がその欄を黙って捨ててしまうため、ここで気づけるようにする。
"""
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent


def form_fields():
    src = (ROOT / "form_app" / "main.py").read_text(encoding="utf-8")
    block = re.search(r"^\s*fields = \{(.*?)\}", src, re.M | re.S).group(1)
    return set(re.findall(r'"(\w+)":', block))


def worker_fields():
    src = (ROOT / "worker" / "src" / "index.js").read_text(encoding="utf-8")
    block = re.search(r"const TEXT_FIELDS = \{(.*?)\};", src, re.S).group(1)
    return set(re.findall(r"^\s*(\w+):", block, re.M))


def test_form_and_worker_have_same_text_fields():
    assert form_fields() == worker_fields()


def test_admin_saves_every_text_field():
    src = (ROOT / "admin_app" / "main.py").read_text(encoding="utf-8")
    insert = re.search(r"INSERT OR IGNORE INTO contacts \(([^)]*)\)", src).group(1)
    assert worker_fields() <= {c.strip() for c in insert.split(",")}
