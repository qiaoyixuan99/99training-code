import os
import re
import json
import ssl
import email
import mailbox
import sqlite3
import imaplib
import shutil
from email import policy
from email.utils import parsedate_to_datetime, getaddresses
from datetime import datetime, date
from pathlib import Path

from flask import Flask, request, jsonify, render_template, g
from email_reply_parser import EmailReplyParser

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent
MAIL_DIR = BASE_DIR / "maildir"
MAIL_DIR.mkdir(exist_ok=True)
CONFIG_PATH = BASE_DIR / "config.json"


def load_config():
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def save_config(cfg):
    CONFIG_PATH.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")


# ── Database path by email ────────────────────────────────────────────
def get_db_path():
    """Return database path based on configured email address."""
    cfg = load_config()
    email_addr = cfg.get("email", "")
    if email_addr:
        safe = re.sub(r"[^a-zA-Z0-9]", "_", email_addr)
        return BASE_DIR / f"{safe}.db"
    return BASE_DIR / "emails.db"


def migrate_old_db():
    """Rename old emails.db to email-specific name if configured.
    Only migrates if the target DB does NOT already exist — never overwrites
    existing data, to prevent data loss caused by leftover emails.db shadows."""
    old_db = BASE_DIR / "emails.db"
    new_db = get_db_path()
    if old_db.exists() and old_db != new_db:
        if new_db.exists():
            # Target already has the real database — just remove the stale old_db
            try:
                old_db.unlink()
            except Exception:
                pass
        else:
            try:
                shutil.move(str(old_db), str(new_db))
            except Exception:
                pass  # Don't fail startup over migration


migrate_old_db()


# ── Database ─────────────────────────────────────────────────────────
def init_db_tables(db):
    db.executescript("""
        CREATE TABLE IF NOT EXISTS emails (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id  TEXT UNIQUE NOT NULL,
            in_reply_to TEXT,
            refs        TEXT,
            subject     TEXT,
            sender_name TEXT,
            sender_addr TEXT,
            recipients  TEXT,
            body_plain  TEXT,
            body_clean  TEXT,
            date        TEXT,
            thread_id   TEXT,
            created_at  TEXT DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS check_log (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            check_date  TEXT NOT NULL,
            checked_at  TEXT DEFAULT (datetime('now','localtime'))
        );

        CREATE INDEX IF NOT EXISTS idx_emails_thread_id ON emails(thread_id);
        CREATE INDEX IF NOT EXISTS idx_emails_date ON emails(date);
    """)
    db.commit()


def get_db():
    if "db" not in g:
        db_path = get_db_path()
        g.db = sqlite3.connect(str(db_path), detect_types=sqlite3.PARSE_DECLTYPES)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA journal_mode=WAL")
        g.db.execute("PRAGMA foreign_keys=ON")
        init_db_tables(g.db)
    return g.db


@app.teardown_appcontext
def close_db(exc):
    db = g.pop("db", None)
    if db:
        db.close()


# ── Helpers ──────────────────────────────────────────────────────────
def _norm(s):
    if not s:
        return ""
    return s.strip().lstrip("<").rstrip(">").strip()


def parse_email_date(d):
    if not d:
        return ""
    try:
        dt = parsedate_to_datetime(d)
        return dt.isoformat(" ", "seconds")
    except Exception:
        return d.strip()


def extract_plain_text(msg):
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    try:
                        return payload.decode(charset, errors="replace")
                    except Exception:
                        return payload.decode("utf-8", errors="replace")
        return ""
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or "utf-8"
            try:
                return payload.decode(charset, errors="replace")
            except Exception:
                return payload.decode("utf-8", errors="replace")
        return ""


def clean_email_body(raw):
    if not raw:
        return ""
    parsed = EmailReplyParser.read(raw)
    text = parsed.reply or raw

    lines = text.split("\n")
    cleaned = []
    for line in lines:
        s = line.strip()
        if s.lower().startswith(("-- ", "---", "_____", "sent from my", "get outlook for",
                                 "this email and any files transmitted", "confidential",
                                 "disclaimer", "this message is intended", "重要通知",
                                 "本邮件及附件", "自动回复", "auto reply", "out of office",
                                 "note: this is an automated", "this e-mail is confidential",
                                 "the information in this email", "if you are not the intended",
                                 "please consider the environment")):
            continue
        cleaned.append(line)
    return "\n".join(cleaned).strip()


def parse_eml_bytes(raw_bytes):
    """Parse email from raw bytes (in-memory, no file write needed)."""
    import io
    msg = email.message_from_binary_file(io.BytesIO(raw_bytes), policy=policy.default)

    mid = _norm(msg.get("Message-ID", ""))
    irt = _norm(msg.get("In-Reply-To", ""))
    refs = (msg.get("References", "") or msg.get("In-Reply-To", "") or "").strip()

    from_header = msg.get("From", "")
    sender_name, sender_addr = "", ""
    if from_header:
        parsed = getaddresses([from_header])
        if parsed:
            sender_name, sender_addr = parsed[0]

    to_header = msg.get("To", "")
    cc_header = msg.get("Cc", "")
    recipients = ", ".join(a for _, a in getaddresses([to_header, cc_header]) if a)

    body = extract_plain_text(msg)

    return {
        "message_id":  mid,
        "in_reply_to": irt,
        "references":  refs,
        "subject":     msg.get("Subject", "(no subject)"),
        "sender_name": sender_name or sender_addr,
        "sender_addr": sender_addr,
        "recipients":  recipients,
        "body_plain":  body,
        "body_clean":  clean_email_body(body),
        "date":        parse_email_date(msg.get("Date", "")),
    }, raw_bytes


def parse_eml(filepath):
    with open(filepath, "rb") as f:
        msg = email.message_from_binary_file(f, policy=policy.default)

    mid = _norm(msg.get("Message-ID", ""))
    irt = _norm(msg.get("In-Reply-To", ""))
    refs = (msg.get("References", "") or msg.get("In-Reply-To", "") or "").strip()

    from_header = msg.get("From", "")
    sender_name, sender_addr = "", ""
    if from_header:
        parsed = getaddresses([from_header])
        if parsed:
            sender_name, sender_addr = parsed[0]

    to_header = msg.get("To", "")
    cc_header = msg.get("Cc", "")
    recipients = ", ".join(a for _, a in getaddresses([to_header, cc_header]) if a)

    body = extract_plain_text(msg)

    return {
        "message_id":  mid,
        "in_reply_to": irt,
        "references":  refs,
        "subject":     msg.get("Subject", "(no subject)"),
        "sender_name": sender_name or sender_addr,
        "sender_addr": sender_addr,
        "recipients":  recipients,
        "body_plain":  body,
        "body_clean":  clean_email_body(body),
        "date":        parse_email_date(msg.get("Date", "")),
    }


def parse_msg_file(filepath):
    try:
        import extract_msg
    except ImportError:
        return None
    m = extract_msg.Message(str(filepath))
    mid = _norm(m.messageId or "")
    irt = _norm(m.inReplyTo or "")
    refs = (m.references or m.inReplyTo or "").strip()
    body = m.body or ""
    return {
        "message_id":  mid,
        "in_reply_to": irt,
        "references":  refs,
        "subject":     m.subject or "(no subject)",
        "sender_name": m.sender or "",
        "sender_addr": m.sender or "",
        "recipients":  m.to or "",
        "body_plain":  body,
        "body_clean":  clean_email_body(body),
        "date":        parse_email_date(str(m.date) if m.date else ""),
    }


def parse_mbox(filepath):
    results = []
    try:
        mb = mailbox.mbox(str(filepath))
    except Exception:
        return results
    for msg in mb:
        mid = _norm(msg.get("Message-ID", ""))
        irt = _norm(msg.get("In-Reply-To", ""))
        refs = (msg.get("References", "") or msg.get("In-Reply-To", "") or "").strip()
        from_header = msg.get("From", "")
        sender_name, sender_addr = "", ""
        if from_header:
            parsed = getaddresses([from_header])
            if parsed:
                sender_name, sender_addr = parsed[0]
        to_header = msg.get("To", "")
        cc_header = msg.get("Cc", "")
        recipients = ", ".join(a for _, a in getaddresses([to_header, cc_header]) if a)
        body = extract_plain_text(msg)
        results.append({
            "message_id":  mid,
            "in_reply_to": irt,
            "references":  refs,
            "subject":     msg.get("Subject", "(no subject)"),
            "sender_name": sender_name or sender_addr,
            "sender_addr": sender_addr,
            "recipients":  recipients,
            "body_plain":  body,
            "body_clean":  clean_email_body(body),
            "date":        parse_email_date(msg.get("Date", "")),
        })
    return results


def scan_maildir():
    results = []
    for entry in sorted(os.listdir(MAIL_DIR)):
        fp = MAIL_DIR / entry
        if not fp.is_file():
            continue
        try:
            if entry.lower().endswith(".eml"):
                parsed = parse_eml(fp)
                if parsed and parsed["message_id"]:
                    results.append(parsed)
            elif entry.lower().endswith(".msg"):
                parsed = parse_msg_file(fp)
                if parsed and parsed["message_id"]:
                    results.append(parsed)
            elif entry.lower().endswith(".mbox") or entry.lower().endswith(".mbx"):
                parsed_list = parse_mbox(fp)
                for p in parsed_list:
                    if p["message_id"]:
                        results.append(p)
        except Exception:
            continue
    return results


def build_threads():
    db = get_db()
    rows = db.execute("SELECT id, message_id, refs, date FROM emails ORDER BY date").fetchall()
    root_of = {}
    for r in rows:
        mid = _norm(r["message_id"])
        refs = r["refs"] or ""
        parent_ids = [_norm(x) for x in refs.split() if x.strip()]
        parent_ids = [p for p in parent_ids if p]
        thread_root = mid
        for pid in parent_ids:
            if pid in root_of:
                thread_root = root_of[pid]
                break
        root_of[mid] = thread_root
    for r in rows:
        mid = _norm(r["message_id"])
        db.execute("UPDATE emails SET thread_id=? WHERE id=?", (root_of.get(mid, mid), r["id"]))
    db.commit()


def today_str():
    return date.today().isoformat()


MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def to_imap_date(iso_date):
    """Convert 'YYYY-MM-DD' to 'DD-Mon-YYYY' for IMAP search."""
    try:
        y, m, d = iso_date.split("-")
        return f"{int(d):02d}-{MONTH_NAMES[int(m)-1]}-{y}"
    except Exception:
        return iso_date


def get_existing_message_ids():
    """Return set of all Message-IDs already in the database."""
    db = get_db()
    rows = db.execute("SELECT message_id FROM emails").fetchall()
    return {_norm(r["message_id"]) for r in rows}


# ── IMAP ────────────────────────────────────────────────────────────
IMAP_SERVERS = {
    "qq.com":       ("imap.qq.com", 993),
    "foxmail.com":  ("imap.qq.com", 993),
    "gmail.com":    ("imap.gmail.com", 993),
    "163.com":      ("imap.163.com", 993),
    "126.com":      ("imap.126.com", 993),
    "yeah.net":     ("imap.yeah.net", 993),
    "outlook.com":  ("outlook.office365.com", 993),
    "hotmail.com":  ("outlook.office365.com", 993),
    "live.com":     ("outlook.office365.com", 993),
    "aliyun.com":   ("imap.aliyun.com", 993),
    "sohu.com":     ("imap.sohu.com", 993),
    "sina.com":     ("imap.sina.com", 993),
    "exmail.qq.com":       ("imap.exmail.qq.com", 993),
    "qiye.163.com":        ("imap.qiye.163.com", 993),
    "qiye.aliyun.com":     ("imap.qiye.aliyun.com", 993),
    "henglihydraulics.com": ("imap.qiye.163.com", 993),
}

ENTERPRISE_FALLBACKS = [
    ("outlook.office365.com", 993),
    ("imap.exmail.qq.com", 993),
    ("imap.qiye.163.com", 993),
]


def guess_imap_server(email_addr):
    domain = email_addr.rsplit("@", 1)[-1].lower()
    if domain in IMAP_SERVERS:
        return IMAP_SERVERS[domain]
    return ("outlook.office365.com", 993)


def _imap_fetch_data(conn, num):
    typ, data = conn.fetch(num, "(RFC822)")
    if typ != "OK":
        return None
    for item in data:
        if isinstance(item, tuple):
            raw = item[1]
            if isinstance(raw, bytes):
                return raw.rstrip(b"\r\n").rstrip(b")").rstrip(b"\r\n")
    return None


def _create_ssl_context():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def fetch_imap_emails(server, port, email_addr, auth_code, folder="INBOX", limit=None,
                      since_date=None, before_date=None, skip_existing=True):
    """
    Fetch emails from IMAP server.
    If skip_existing is True, skip emails whose Message-ID is already in the database.
    Returns (fetched_count, results_list, skipped_count).
    """
    import socket

    # Get existing Message-IDs for dedup
    existing_ids = set()
    if skip_existing:
        try:
            existing_ids = get_existing_message_ids()
        except Exception:
            pass  # If DB not accessible, download everything

    try:
        ctx = _create_ssl_context()
        conn = imaplib.IMAP4_SSL(server, int(port), ssl_context=ctx, timeout=30)
    except imaplib.IMAP4.error as e:
        raise RuntimeError(
            f"无法连接到 {server}:{port}\n请确认服务器地址和端口正确。\n"
            f"常见企业邮箱服务器：\n"
            f"  Microsoft 365 → outlook.office365.com:993\n"
            f"  腾讯企业邮箱 → imap.exmail.qq.com:993\n"
            f"  网易企业邮箱 → imap.qiye.163.com:993\n"
            f"原始错误：{e}"
        )
    except socket.timeout:
        raise RuntimeError(f"连接 {server}:{port} 超时，请检查网络或防火墙设置")
    except socket.gaierror as e:
        raise RuntimeError(
            f"无法解析服务器地址 {server}\n该邮件服务器不存在，请手动填写正确的 IMAP 服务器地址。\n"
            f"常见企业邮箱服务器：\n"
            f"  Microsoft 365 → outlook.office365.com:993\n"
            f"  腾讯企业邮箱 → imap.exmail.qq.com:993\n"
            f"  网易企业邮箱 → imap.qiye.163.com:993\n"
            f"原始错误：{e}"
        )
    except Exception as e:
        raise RuntimeError(f"连接失败: {e}")

    try:
        conn.login(email_addr, auth_code)
    except imaplib.IMAP4.error as e:
        conn.logout()
        err = str(e)
        if "AUTHENTICATIONFAILED" in err.upper() or "LOGIN" in err.upper():
            raise RuntimeError(
                f"登录失败：授权码或密码错误。请确认：\n"
                f"1. 邮箱已开启 IMAP 服务\n2. 使用的是授权码而非邮箱密码\n"
                f"3. 授权码没有复制错误\n\n原始错误: {err}"
            )
        raise RuntimeError(f"登录失败: {err}")

    try:
        conn.select(folder, readonly=False)
    except imaplib.IMAP4.error as e:
        conn.logout()
        raise RuntimeError(f"无法打开文件夹 '{folder}': {e}")

    # Build IMAP search criteria
    criteria = []
    if since_date:
        criteria.append(f'SINCE "{to_imap_date(since_date)}"')
    if before_date:
        criteria.append(f'BEFORE "{to_imap_date(before_date)}"')

    if criteria:
        search_criteria = " ".join(criteria)
    else:
        # No date limit - search all
        search_criteria = "ALL"

    typ, msg_ids = conn.search(None, f'({search_criteria})')
    if typ != "OK":
        conn.logout()
        return 0, [], 0

    id_list = msg_ids[0].split()
    if not id_list:
        conn.logout()
        return 0, [], 0

    # Apply limit if specified (from newest first)
    if limit and len(id_list) > limit:
        id_list = id_list[-limit:]

    fetched = 0
    skipped = 0
    results = []
    for num in id_list:
        try:
            raw_bytes = _imap_fetch_data(conn, num)
            if not raw_bytes:
                continue

            # Parse in-memory first to get Message-ID for dedup check
            parsed, _ = parse_eml_bytes(raw_bytes)
            if not parsed or not parsed["message_id"]:
                continue

            mid_norm = _norm(parsed["message_id"])
            if skip_existing and mid_norm in existing_ids:
                skipped += 1
                continue

            # Save to maildir
            ts = int(datetime.now().timestamp() * 1000)
            filename = f"imap_{email_addr.replace('@','_')}_{ts}_{num.decode()}.eml"
            filepath = MAIL_DIR / filename
            filepath.write_bytes(raw_bytes)

            results.append(parsed)
            fetched += 1
        except Exception:
            continue

    conn.logout()
    return fetched, results, skipped


# ── Routes ───────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/status")
def api_status():
    db = get_db()
    cfg = load_config()
    row = db.execute(
        "SELECT * FROM check_log WHERE check_date=? ORDER BY checked_at DESC LIMIT 1",
        (today_str(),)
    ).fetchone()
    total = db.execute("SELECT COUNT(*) as c FROM emails").fetchone()["c"]
    thread_count = db.execute(
        "SELECT COUNT(DISTINCT thread_id) as c FROM emails WHERE thread_id IS NOT NULL"
    ).fetchone()["c"]

    # Determine the earliest email date for the date picker
    earliest = db.execute("SELECT MIN(date) as d FROM emails WHERE date != ''").fetchone()
    earliest_date = earliest["d"][:10] if earliest and earliest["d"] else ""

    return jsonify({
        "checked_today":    row is not None,
        "last_check_date":  row["check_date"] if row else None,
        "total_emails":     total,
        "total_threads":    thread_count,
        "default_date_from": cfg.get("default_date_from", ""),
        "default_date_to":  cfg.get("default_date_to", ""),
        "last_fetch_date":  cfg.get("last_fetch_date", None),
        "imap_configured":  bool(cfg.get("email") and cfg.get("auth_code")),
        "earliest_date":    earliest_date,
        "db_name":          get_db_path().name,
    })


@app.route("/api/check-new", methods=["POST"])
def api_check_new():
    db = get_db()
    if db.execute("SELECT 1 FROM check_log WHERE check_date=?", (today_str(),)).fetchone():
        return jsonify({"status": "cached", "message": "今天已是最新数据，无需重复检查"})

    emails = scan_maildir()
    inserted = 0
    for em in emails:
        try:
            cur = db.execute("""
                INSERT OR IGNORE INTO emails
                    (message_id, in_reply_to, refs, subject,
                     sender_name, sender_addr, recipients,
                     body_plain, body_clean, date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                em["message_id"], em["in_reply_to"], em["references"], em["subject"],
                em["sender_name"], em["sender_addr"], em["recipients"],
                em["body_plain"], em["body_clean"], em["date"],
            ))
            if cur.rowcount:
                inserted += cur.rowcount
        except Exception:
            continue
    db.commit()
    build_threads()
    db.execute("INSERT INTO check_log (check_date) VALUES (?)", (today_str(),))
    db.commit()
    return jsonify({"status": "updated", "message": f"检查完成，新增 {inserted} 封邮件", "new_count": inserted})


@app.route("/api/threads")
def api_threads():
    db = get_db()
    date_from = request.args.get("date_from", "")
    date_to = request.args.get("date_to", "")

    where_clauses = ["thread_id IS NOT NULL"]
    params = []
    if date_from:
        where_clauses.append("date >= ?")
        params.append(date_from)
    if date_to:
        where_clauses.append("date <= ?")
        params.append(date_to + " 23:59:59")

    where = " AND ".join(where_clauses)
    threads = db.execute(f"""
        SELECT thread_id,
               MIN(subject) as subject,
               COUNT(*)    as msg_count,
               MAX(date)   as latest_date,
               (SELECT GROUP_CONCAT(DISTINCT sender_name) FROM emails e2 WHERE e2.thread_id = e.thread_id) as participants
        FROM emails e
        WHERE {where}
        GROUP BY thread_id
        ORDER BY MAX(date) DESC
    """, params).fetchall()
    result = []
    for t in threads:
        result.append({
            "thread_id":    t["thread_id"],
            "subject":      t["subject"] or "(no subject)",
            "msg_count":    t["msg_count"],
            "latest_date":  t["latest_date"] or "",
            "participants": t["participants"] or "",
        })
    return jsonify(result)


@app.route("/api/thread/<thread_id>")
def api_thread_detail(thread_id):
    """Return all messages in a thread sorted by time (lightweight, no body)."""
    db = get_db()
    msgs = db.execute("""
        SELECT id, message_id, in_reply_to, refs, subject,
               sender_name, sender_addr, recipients, date
        FROM emails
        WHERE thread_id=?
        ORDER BY date
    """, (thread_id,)).fetchall()

    result = []
    for m in msgs:
        result.append({
            "id":          m["id"],
            "message_id":  m["message_id"],
            "in_reply_to": m["in_reply_to"] or "",
            "refs":        m["refs"] or "",
            "subject":     m["subject"] or "(no subject)",
            "sender_name": m["sender_name"] or "",
            "sender_addr": m["sender_addr"] or "",
            "recipients":  m["recipients"] or "",
            "date":        m["date"] or "",
        })
    return jsonify(result)


@app.route("/api/email/<int:email_id>")
def api_email_detail(email_id):
    """Return full detail of a single email (with body)."""
    db = get_db()
    m = db.execute("""
        SELECT id, message_id, in_reply_to, refs, subject,
               sender_name, sender_addr, recipients,
               body_plain, body_clean, date
        FROM emails
        WHERE id=?
    """, (email_id,)).fetchone()

    if not m:
        return jsonify({"error": "邮件不存在"}), 404

    return jsonify({
        "id":          m["id"],
        "message_id":  m["message_id"],
        "in_reply_to": m["in_reply_to"] or "",
        "refs":        m["refs"] or "",
        "subject":     m["subject"] or "(no subject)",
        "sender_name": m["sender_name"] or "",
        "sender_addr": m["sender_addr"] or "",
        "recipients":  m["recipients"] or "",
        "body_plain":  m["body_plain"] or "",
        "body_clean":  m["body_clean"] or "",
        "date":        m["date"] or "",
    })


@app.route("/api/search")
def api_search():
    """Search emails by keyword; returns matching emails with thread_id for tree navigation."""
    q = request.args.get("q", "").strip()
    if not q or len(q) < 1:
        return jsonify([])

    db = get_db()
    pattern = f"%{q}%"
    rows = db.execute("""
        SELECT id, message_id, subject, sender_name, sender_addr, date, thread_id
        FROM emails
        WHERE subject LIKE ? OR sender_name LIKE ? OR sender_addr LIKE ?
        ORDER BY date DESC
        LIMIT 30
    """, (pattern, pattern, pattern)).fetchall()

    return jsonify([{
        "id": r["id"], "message_id": r["message_id"],
        "subject": r["subject"] or "(no subject)",
        "sender_name": r["sender_name"] or "",
        "sender_addr": r["sender_addr"] or "",
        "date": r["date"] or "", "thread_id": r["thread_id"] or "",
    } for r in rows])


@app.route("/api/imap-config", methods=["GET", "POST"])
def api_imap_config():
    if request.method == "GET":
        cfg = load_config()
        return jsonify({
            "email":    cfg.get("email", ""),
            "server":   cfg.get("server", ""),
            "port":     cfg.get("port", ""),
            "has_auth": bool(cfg.get("auth_code")),
        })
    data = request.get_json() or {}
    cfg = load_config()
    email_addr = (data.get("email") or "").strip()
    auth_code = (data.get("auth_code") or "").strip()
    server = (data.get("server") or "").strip()
    port = data.get("port")
    if not email_addr:
        return jsonify({"status": "error", "message": "邮箱地址不能为空"}), 400
    if not server:
        server, default_port = guess_imap_server(email_addr)
        if not port:
            port = default_port
    cfg["email"] = email_addr
    cfg["server"] = server
    cfg["port"] = port or 993
    if auth_code:
        cfg["auth_code"] = auth_code
    save_config(cfg)
    return jsonify({"status": "ok", "message": f"配置已保存（{server}:{port}）", "server": server, "port": port})


@app.route("/api/imap-test", methods=["POST"])
def api_imap_test():
    cfg = load_config()
    if not cfg.get("email") or not cfg.get("auth_code"):
        return jsonify({"status": "error", "message": "请先填写邮箱和授权码"}), 400
    try:
        fetched, results, skipped = fetch_imap_emails(
            cfg["server"], int(cfg.get("port", 993)),
            cfg["email"], cfg["auth_code"], limit=5,
            skip_existing=False,
        )
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

    preview = []
    for em in results:
        preview.append({"subject": em["subject"], "from": em["sender_name"], "date": em["date"]})
    return jsonify({
        "status": "ok", "message": f"连接成功！预览前 {len(preview)} 封邮件",
        "found": fetched, "preview": preview,
    })


@app.route("/api/imap-fetch", methods=["POST"])
def api_imap_fetch():
    db = get_db()
    cfg = load_config()
    if not cfg.get("email") or not cfg.get("auth_code"):
        return jsonify({"status": "error", "message": "请先配置邮箱和授权码"}), 400

    body = request.get_json(silent=True) or {}
    force = body.get("force", False)
    date_from = body.get("date_from", "")
    date_to = body.get("date_to", "")
    incremental = body.get("incremental", False)

    # Determine since_date
    if date_from:
        since_date = date_from
    elif incremental and cfg.get("last_fetch_date"):
        # Incremental: only fetch emails since last successful fetch
        since_date = cfg["last_fetch_date"]
    else:
        since_date = ""

    before_date = date_to if date_to else None

    # Daily cache check for incremental mode
    if incremental and not force and db.execute(
        "SELECT 1 FROM check_log WHERE check_date=?", (today_str(),)
    ).fetchone():
        return jsonify({"status": "cached", "message": "今天已从服务器获取过最新数据，无需重复检查"})

    # Count existing emails before fetch for comparison
    existing_count = db.execute("SELECT COUNT(*) as c FROM emails").fetchone()["c"]

    try:
        fetched, results, skipped = fetch_imap_emails(
            cfg["server"], int(cfg.get("port", 993)),
            cfg["email"], cfg["auth_code"],
            since_date=since_date,
            before_date=before_date,
            skip_existing=True,
        )
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

    inserted = 0
    for em in results:
        try:
            cur = db.execute("""
                INSERT OR IGNORE INTO emails
                    (message_id, in_reply_to, refs, subject,
                     sender_name, sender_addr, recipients,
                     body_plain, body_clean, date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                em["message_id"], em["in_reply_to"], em["references"], em["subject"],
                em["sender_name"], em["sender_addr"], em["recipients"],
                em["body_plain"], em["body_clean"], em["date"],
            ))
            if cur.rowcount:
                inserted += cur.rowcount
        except Exception:
            continue

    db.commit()
    if inserted > 0:
        build_threads()

    db.execute(
        "INSERT INTO check_log (check_date, checked_at) VALUES (?, ?)",
        (today_str(), f"IMAP {datetime.now().isoformat()}")
    )
    db.commit()

    # Update config
    cfg["last_fetch_date"] = today_str()
    if date_from:
        cfg["default_date_from"] = date_from
    if date_to:
        cfg["default_date_to"] = date_to
    save_config(cfg)

    msg_parts = [f"从服务器获取 {fetched} 封新邮件"]
    if skipped > 0:
        msg_parts.append(f"跳过 {skipped} 封已存在")
    if inserted > 0:
        msg_parts.append(f"新增入库 {inserted} 封")
    else:
        msg_parts.append("无新增邮件")

    return jsonify({
        "status": "updated",
        "message": "，".join(msg_parts),
        "fetched": fetched,
        "new_count": inserted,
        "skipped": skipped,
        "since_date": since_date,
    })


@app.route("/api/existing-ids")
def api_existing_ids():
    """Return count of existing emails for status display."""
    db = get_db()
    count = db.execute("SELECT COUNT(*) as c FROM emails").fetchone()["c"]
    earliest = db.execute("SELECT MIN(date) as d FROM emails WHERE date != ''").fetchone()
    latest = db.execute("SELECT MAX(date) as d FROM emails WHERE date != ''").fetchone()
    return jsonify({
        "count": count,
        "earliest_date": earliest["d"][:10] if earliest and earliest["d"] else "",
        "latest_date": latest["d"][:10] if latest and latest["d"] else "",
    })


@app.route("/api/import-sample", methods=["POST"])
def api_import_sample():
    db = get_db()
    samples = [
        {
            "message_id":  "<001@demo.local>",
            "in_reply_to": "",
            "references":  "",
            "subject":     "关于Q3项目进度的讨论",
            "sender_name": "张三",
            "sender_addr": "zhangsan@example.com",
            "recipients":  "lisi@example.com, wangwu@example.com",
            "body_plain":  "大家好，\n\n请各位更新一下Q3项目的进度情况。\n\n谢谢，\n张三",
            "body_clean":  "大家好，\n\n请各位更新一下Q3项目的进度情况。\n\n谢谢，\n张三",
            "date":        "2025-08-10 09:00:00",
        },
        {
            "message_id":  "<002@demo.local>",
            "in_reply_to": "<001@demo.local>",
            "references":  "<001@demo.local>",
            "subject":     "Re: 关于Q3项目进度的讨论",
            "sender_name": "李四",
            "sender_addr": "lisi@example.com",
            "recipients":  "zhangsan@example.com, wangwu@example.com",
            "body_plain":  "张三你好，\n\n我这边前端模块已完成80%，预计本周五可以交付测试。\n\n李四\n> 大家好，\n> 请各位更新一下Q3项目的进度情况。\n> 谢谢，\n> 张三",
            "body_clean":  "张三你好，\n\n我这边前端模块已完成80%，预计本周五可以交付测试。",
            "date":        "2025-08-10 10:30:00",
        },
        {
            "message_id":  "<003@demo.local>",
            "in_reply_to": "<002@demo.local>",
            "references":  "<001@demo.local> <002@demo.local>",
            "subject":     "Re: 关于Q3项目进度的讨论",
            "sender_name": "王五",
            "sender_addr": "wangwu@example.com",
            "recipients":  "zhangsan@example.com, lisi@example.com",
            "body_plain":  "后端API已全部完成，正在写单元测试。\n另外数据库迁移脚本还需要review一下。\n\n王五\n> 我这边前端模块已完成80%，预计本周五可以交付测试。\n> 李四",
            "body_clean":  "后端API已全部完成，正在写单元测试。\n另外数据库迁移脚本还需要review一下。",
            "date":        "2025-08-10 14:15:00",
        },
        {
            "message_id":  "<004@demo.local>",
            "in_reply_to": "<003@demo.local>",
            "references":  "<001@demo.local> <002@demo.local> <003@demo.local>",
            "subject":     "Re: 关于Q3项目进度的讨论",
            "sender_name": "张三",
            "sender_addr": "zhangsan@example.com",
            "recipients":  "lisi@example.com, wangwu@example.com",
            "body_plain":  "好的，收到。\n\n李四，前端完成后先内部演示一下。\n王五，迁移脚本我明天review。\n\n大家辛苦了！\n张三",
            "body_clean":  "好的，收到。\n\n李四，前端完成后先内部演示一下。\n王五，迁移脚本我明天review。\n\n大家辛苦了！",
            "date":        "2025-08-10 16:00:00",
        },
        {
            "message_id":  "<005@demo.local>",
            "in_reply_to": "<001@demo.local>",
            "references":  "<001@demo.local>",
            "subject":     "Re: 关于Q3项目进度的讨论",
            "sender_name": "赵六",
            "sender_addr": "zhaoliu@example.com",
            "recipients":  "zhangsan@example.com",
            "body_plain":  "张三，测试这边已经准备好了，随时可以开始。",
            "body_clean":  "张三，测试这边已经准备好了，随时可以开始。",
            "date":        "2025-08-10 11:00:00",
        },
        {
            "message_id":  "<006@demo.local>",
            "in_reply_to": "<005@demo.local>",
            "references":  "<001@demo.local> <005@demo.local>",
            "subject":     "Re: 关于Q3项目进度的讨论",
            "sender_name": "张三",
            "sender_addr": "zhangsan@example.com",
            "recipients":  "zhaoliu@example.com",
            "body_plain":  "好的赵六，等前端完成后我们统一安排测试。",
            "body_clean":  "好的赵六，等前端完成后我们统一安排测试。",
            "date":        "2025-08-10 11:30:00",
        },
    ]

    for s in samples:
        if not s["body_clean"]:
            s["body_clean"] = clean_email_body(s["body_plain"])

    inserted = 0
    for em in samples:
        try:
            cur = db.execute("""
                INSERT OR IGNORE INTO emails
                    (message_id, in_reply_to, refs, subject,
                     sender_name, sender_addr, recipients,
                     body_plain, body_clean, date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                em["message_id"], em["in_reply_to"], em["references"], em["subject"],
                em["sender_name"], em["sender_addr"], em["recipients"],
                em["body_plain"], em["body_clean"], em["date"],
            ))
            if cur.rowcount:
                inserted += cur.rowcount
        except Exception:
            continue
    db.commit()
    build_threads()
    return jsonify({"status": "ok", "inserted": inserted})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002, debug=False)
