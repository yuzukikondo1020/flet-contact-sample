"""担当者アプリの「受け取る」処理のテスト。R2 の代わりに S3 互換のエミュレーター(moto)を使う。"""
import importlib
import json
import sys
from pathlib import Path

import boto3
import pytest
from moto import mock_aws


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("CONTACT_DB_PATH", str(tmp_path / "c.db"))
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")
    sys.path.insert(0, str(Path(__file__).parent.parent / "admin_app"))
    with mock_aws():
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket="contact-inbox")
        import main as admin
        importlib.reload(admin)
        yield s3, admin


def put(s3, rid, ts="2026-10-25T11:00:00Z"):
    rec = {"id": rid, "received_at": ts, "name": "山田 太郎", "email": "taro@example.jp", "company": "",
           "category": "rebuild", "message": "相談したいです"}
    s3.put_object(Bucket="contact-inbox", Key=f"inbox/{ts}_{rid}.json", Body=json.dumps(rec).encode())


def test_moves_to_local_and_deletes_from_r2(env):
    s3, admin = env
    put(s3, "AAAA0001"); put(s3, "AAAA0002", "2026-10-25T11:05:00Z")
    assert admin.receive_from_r2(s3) == 2
    assert [r["id"] for r in admin.load(only_new=True)] == ["AAAA0002", "AAAA0001"]
    assert s3.list_objects_v2(Bucket="contact-inbox").get("KeyCount") == 0


def test_receiving_twice_does_not_duplicate(env):
    s3, admin = env
    put(s3, "AAAA0001")
    admin.receive_from_r2(s3)
    put(s3, "AAAA0001")  # 同じ問い合わせがもう一度置かれても
    admin.receive_from_r2(s3)
    assert len(admin.load(only_new=False)) == 1


def test_status_toggle(env):
    s3, admin = env
    put(s3, "AAAA0001")
    admin.receive_from_r2(s3)
    admin.set_status("AAAA0001", "done")
    assert admin.load(only_new=True) == []
    assert admin.load(only_new=False)[0]["status"] == "done"
