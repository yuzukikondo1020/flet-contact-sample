// 問い合わせ受付（Cloudflare Worker）
//
// 役割はひとつだけ: フォームから届いたデータを検証し、R2 に保存する。
// ・一覧を返す・削除する等の機能は作らない（担当者は admin_app から R2 を直接読む）
// ・ブラウザ側の入力チェックは信用せず、ここで必ずやり直す
// ・エラーの形はフォーム側(form_app)が欄ごとに表示できる形にそろえている

const MAX_BODY_BYTES = 16 * 1024;
const EMAIL_RE = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;
const PHONE_RE = /^[0-9-]+$/;
// 改行(\n)とタブ(\t)は残し、それ以外の目に見えない制御文字を取り除く
const CONTROL_CHARS_RE = /[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]/g;
const CATEGORIES = ["php_update", "rebuild", "study", "other"];

// 欄ごとの決まり: [必須か, 最大文字数]
const TEXT_FIELDS = {
  name: [true, 50],
  email: [true, 254],
  company: [false, 100],
  phone: [false, 20],
  message: [true, 2000],
};

function allowedOrigins(env) {
  return (env.ALLOWED_ORIGINS || "").split(",").map((s) => s.trim()).filter(Boolean);
}

function corsHeaders(origin, env) {
  if (origin && allowedOrigins(env).includes(origin)) {
    return {
      "Access-Control-Allow-Origin": origin,
      "Access-Control-Allow-Methods": "POST",
      "Access-Control-Allow-Headers": "Content-Type",
      "Access-Control-Max-Age": "86400",
      Vary: "Origin",
    };
  }
  return { Vary: "Origin" };
}

function json(data, status, headers) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json; charset=utf-8", ...headers },
  });
}

function validate(body) {
  const errors = [];
  const clean = {};
  const fail = (field, msg) => errors.push({ loc: ["body", field], msg });

  if (typeof body !== "object" || body === null || Array.isArray(body)) {
    return { errors: [{ loc: ["body"], msg: "送信内容の形式が正しくありません" }] };
  }

  for (const [field, [required, max]] of Object.entries(TEXT_FIELDS)) {
    const raw = body[field] ?? "";
    if (typeof raw !== "string") { fail(field, "文字列で送ってください"); continue; }
    const v = raw.replace(CONTROL_CHARS_RE, "").trim();
    if (required && !v) { fail(field, "入力してください"); continue; }
    if (v.length > max) { fail(field, `${max}文字以内で入力してください`); continue; }
    clean[field] = v;
  }
  if (clean.email !== undefined && !EMAIL_RE.test(clean.email)) {
    fail("email", "メールアドレスの形式が正しくありません");
  }
  if (clean.phone && !PHONE_RE.test(clean.phone)) {
    fail("phone", "電話番号は数字とハイフンで入力してください");
  }
  if (!CATEGORIES.includes(body.category)) {
    fail("category", "ご用件を選んでください");
  } else {
    clean.category = body.category;
  }
  if (body.consent !== true) {
    fail("consent", "個人情報の取り扱いへの同意が必要です");
  }
  return { errors, clean };
}

function newId() {
  return crypto.randomUUID().replace(/-/g, "").slice(0, 8).toUpperCase();
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const origin = request.headers.get("Origin");
    const cors = corsHeaders(origin, env);

    if (url.pathname !== "/api/contact") {
      return json({ detail: "Not Found" }, 404, cors);
    }
    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: cors });
    }
    if (request.method !== "POST") {
      return json({ detail: "Method Not Allowed" }, 405, { ...cors, Allow: "POST" });
    }
    // ブラウザからの送信は、許可したサイトからのものだけ受け付ける
    if (origin && !allowedOrigins(env).includes(origin)) {
      return json({ detail: "このサイトからの送信は受け付けていません" }, 403, cors);
    }

    // 連続送信の制限（wrangler.toml の ratelimits を wrangler で送ったときだけ有効）
    if (env.RATE_LIMITER) {
      const ip = request.headers.get("CF-Connecting-IP") || "unknown";
      const { success } = await env.RATE_LIMITER.limit({ key: ip });
      if (!success) {
        return json({ detail: "短時間に送信が続いています。しばらくしてからお試しください" }, 429, cors);
      }
    }

    const length = Number(request.headers.get("Content-Length") || 0);
    if (length > MAX_BODY_BYTES) {
      return json({ detail: "送信内容が大きすぎます" }, 413, cors);
    }
    const text = await request.text();
    if (new TextEncoder().encode(text).length > MAX_BODY_BYTES) {
      return json({ detail: "送信内容が大きすぎます" }, 413, cors);
    }

    let body;
    try {
      body = JSON.parse(text);
    } catch {
      return json({ detail: [{ loc: ["body"], msg: "送信内容の形式が正しくありません" }] }, 422, cors);
    }

    const { errors, clean } = validate(body);
    if (errors.length) {
      return json({ detail: errors }, 422, cors);
    }

    const id = newId();
    const received_at = new Date().toISOString().replace(/\.\d{3}Z$/, "Z");
    const record = { id, received_at, ...clean };
    // 受信箱(inbox/)に1件1ファイルで置く。担当者のアプリが受け取ったら消す
    await env.INBOX.put(`inbox/${received_at}_${id}.json`, JSON.stringify(record), {
      httpMetadata: { contentType: "application/json; charset=utf-8" },
    });

    return json({ id, received_at }, 201, cors);
  },
};
