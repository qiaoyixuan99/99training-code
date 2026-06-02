import os
import re
import json
import ssl
import email
import mailbox
import sqlite3
import imaplib
from email import policy
from email.utils import parsedate_to_datetime, getaddresses
from datetime import datetime, date
from pathlib import Path
from functools import wraps
from contextlib import contextmanager

from flask import Flask, request, jsonify, render_template, g
from email_reply_parser import EmailReplyParser

app = Flask(__name__)

# ── Config ──────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "emails.db"
MAIL_DIR = BASE_DIR / "maildir"          # fetched emails saved here as .eml
MAIL_DIR.mkdir(exist_ok=True)
CONFIG_PATH = BASE_DIR / "config.json"   # IMAP credentials storage

def load_config():
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}

def save_config(cfg):
    CONFIG_PATH.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")

# ── Database ─────────────────────────────────────────────────────────
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(str(DB_PATH), detect_types=sqlite3.PARSE_DECLTYPES)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA journal_mode=WAL")
        g.db.execute("PRAGMA foreign_keys=ON")
    return g.db

@app.teardown_appcontext
def close_db(exc):
    db = g.pop("db", None)
    if db:
        db.close()

def init_db():
    db = sqlite3.connect(str(DB_PATH))
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
    """)
    db.commit()
    db.close()

# run once at import
init_db()

# ── Helpers ──────────────────────────────────────────────────────────

def _norm(s):
    """Strip angle-brackets and whitespace."""
    if not s:
        return ""
    return s.strip().lstrip("<").rstrip(">").strip()

def parse_email_date(d):
    """Try hard to turn a date header into an ISO string."""
    if not d:
        return ""
    try:
        dt = parsedate_to_datetime(d)
        return dt.isoformat(" ", "seconds")
    except Exception:
        return d.strip()

def extract_plain_text(msg):
    """Walk a multipart message and return the first text/plain payload."""
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
    """Use email_reply_parser to pull out the real reply, then strip sigs."""
    if not raw:
        return ""
    # EmailReplyParser.read returns EmailMessage; .reply extracts the reply text
    parsed = EmailReplyParser.read(raw)
    text = parsed.reply or raw

    # strip trailing signature blocks (common patterns)
    lines = text.split("\n")
    cleaned = []
    for line in lines:
        s = line.strip()
        # Skip common disclaimer / automatic markers
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

def parse_eml(filepath):
    """Parse a single .eml file → dict of fields."""
    with open(filepath, "rb") as f:
        msg = email.message_from_binary_file(f, policy=policy.default)

    mid  = _norm(msg.get("Message-ID", ""))
    irt  = _norm(msg.get("In-Reply-To", ""))
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
    """Parse a .msg file via extract_msg → dict of fields."""
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
    """Parse an mbox file → list of dicts."""
    results = []
    try:
        mb = mailbox.mbox(str(filepath))
    except Exception:
        return results

    for msg in mb:
        mid  = _norm(msg.get("Message-ID", ""))
        irt  = _norm(msg.get("In-Reply-To", ""))
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
    """Walk MAIL_DIR, parse new files, return list of email dicts."""
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
    """Recompute thread_id for every email based on References chains."""
    db = get_db()

    # fetch all emails ordered by date
    rows = db.execute("SELECT id, message_id, refs, date FROM emails ORDER BY date").fetchall()

    # map message_id → first_id_in_chain  (the "root" of that chain)
    root_of = {}   # msg_id → root_msg_id

    for r in rows:
        mid = _norm(r["message_id"])
        refs = r["refs"] or ""

        # collect every referenced message-id
        parent_ids = [_norm(x) for x in refs.split() if x.strip()]
        parent_ids = [p for p in parent_ids if p]

        # find the earliest ancestor we already know
        thread_root = mid  # default: self is root
        for pid in parent_ids:
            if pid in root_of:
                thread_root = root_of[pid]
                break

        root_of[mid] = thread_root

    # write back
    for r in rows:
        mid = _norm(r["message_id"])
        db.execute("UPDATE emails SET thread_id=? WHERE id=?", (root_of.get(mid, mid), r["id"]))
    db.commit()

def today_str():
    return date.today().isoformat()

# ── IMAP fetch ──────────────────────────────────────────────────────
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
    # 企业邮箱
    "exmail.qq.com":       ("imap.exmail.qq.com", 993),
    "qiye.163.com":        ("imap.qiye.163.com", 993),
    "qiye.aliyun.com":     ("imap.qiye.aliyun.com", 993),
    # 特定企业域名
    "henglihydraulics.com": ("imap.qiye.163.com", 993),
}

ENTERPRISE_FALLBACKS = [
    ("outlook.office365.com", 993),   # Microsoft 365
    ("imap.exmail.qq.com", 993),       # 腾讯企业邮箱
    ("imap.qiye.163.com", 993),        # 网易企业邮箱
]

def guess_imap_server(email_addr):
    domain = email_addr.rsplit("@", 1)[-1].lower()
    if domain in IMAP_SERVERS:
        return IMAP_SERVERS[domain]
    # For unknown enterprise domains, suggest Microsoft 365 as most common
    return ("outlook.office365.com", 993)

def _imap_fetch_data(conn, num):
    """Robustly extract raw bytes from IMAP fetch response."""
    typ, data = conn.fetch(num, "(RFC822)")
    if typ != "OK":
        return None
    # data structure: [(b'num (RFC822 {size}', b'raw...'), b')'] or similar
    for item in data:
        if isinstance(item, tuple):
            # item[1] is the raw email bytes
            raw = item[1]
            if isinstance(raw, bytes):
                # sometimes there's a trailing ) byte
                return raw.rstrip(b"\r\n").rstrip(b")").rstrip(b"\r\n")
    return None

def _create_ssl_context():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def fetch_imap_emails(server, port, email_addr, auth_code, folder="INBOX"):
    """Connect to IMAP, fetch unseen emails, save as .eml to MAIL_DIR."""
    import socket
    socket.gaierror  # ensure gaierror is accessible
    try:
        ctx = _create_ssl_context()
        conn = imaplib.IMAP4_SSL(server, int(port), ssl_context=ctx, timeout=30)
    except imaplib.IMAP4.error as e:
        raise RuntimeError(
            f"无法连接到 {server}:{port}\n"
            f"请确认服务器地址和端口正确。\n"
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
            f"无法解析服务器地址 {server}\n"
            f"该邮件服务器不存在，请手动填写正确的 IMAP 服务器地址。\n"
            f"可在邮箱网页版设置中查找 IMAP 服务器信息，或咨询公司 IT。\n"
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
            raise RuntimeError(f"登录失败：授权码或密码错误。请确认：\n1. 邮箱已开启 IMAP 服务\n2. 使用的是授权码而非邮箱密码\n3. 授权码没有复制错误\n\n原始错误: {err}")
        raise RuntimeError(f"登录失败: {err}")

    try:
        conn.select(folder, readonly=False)
    except imaplib.IMAP4.error as e:
        conn.logout()
        raise RuntimeError(f"无法打开文件夹 '{folder}': {e}")

    # search unseen
    typ, msg_ids = conn.search(None, "UNSEEN")
    if typ != "OK":
        conn.logout()
        return 0, []

    id_list = msg_ids[0].split()
    if not id_list:
        conn.logout()
        return 0, []

    fetched = 0
    results = []

    for num in id_list:
        try:
            raw_bytes = _imap_fetch_data(conn, num)
            if not raw_bytes:
                continue

            ts = int(datetime.now().timestamp() * 1000)
            filename = f"imap_{email_addr.replace('@','_')}_{ts}_{num.decode()}.eml"
            filepath = MAIL_DIR / filename
            filepath.write_bytes(raw_bytes)

            parsed = parse_eml(filepath)
            if parsed and parsed["message_id"]:
                results.append(parsed)
                fetched += 1
        except Exception:
            continue

    conn.logout()
    return fetched, results

# ── API Routes ───────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/status")
def api_status():
    """Return whether today's check has been done and summary counts."""
    db = get_db()
    row = db.execute(
        "SELECT * FROM check_log WHERE check_date=? ORDER BY checked_at DESC LIMIT 1",
        (today_str(),)
    ).fetchone()

    total = db.execute("SELECT COUNT(*) as c FROM emails").fetchone()["c"]
    thread_count = db.execute(
        "SELECT COUNT(DISTINCT thread_id) as c FROM emails WHERE thread_id IS NOT NULL"
    ).fetchone()["c"]

    return jsonify({
        "checked_today":       row is not None,
        "last_check_date":     row["check_date"] if row else None,
        "total_emails":        total,
        "total_threads":       thread_count,
    })

@app.route("/api/check-new", methods=["POST"])
def api_check_new():
    """Scan for new emails. Skip if already checked today."""
    db = get_db()
    if db.execute("SELECT 1 FROM check_log WHERE check_date=?", (today_str(),)).fetchone():
        return jsonify({"status": "cached", "message": "今天已是最新数据，无需重复检查"})

    # scan maildir
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

    # rebuild threads
    build_threads()

    # log the check
    db.execute("INSERT INTO check_log (check_date) VALUES (?)", (today_str(),))
    db.commit()

    return jsonify({
        "status":   "updated",
        "message":  f"检查完成，新增 {inserted} 封邮件",
        "new_count": inserted,
    })

@app.route("/api/threads")
def api_threads():
    """Return thread summaries sorted by latest reply."""
    db = get_db()
    threads = db.execute("""
        SELECT thread_id,
               MIN(subject) as subject,
               COUNT(*)    as msg_count,
               MAX(date)   as latest_date,
               (SELECT GROUP_CONCAT(DISTINCT sender_name) FROM emails e2 WHERE e2.thread_id = e.thread_id) as participants
        FROM emails e
        WHERE thread_id IS NOT NULL
        GROUP BY thread_id
        ORDER BY MAX(date) DESC
    """).fetchall()

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
    """Return all messages in a thread sorted by time."""
    db = get_db()
    msgs = db.execute("""
        SELECT * FROM emails
        WHERE thread_id=?
        ORDER BY date
    """, (thread_id,)).fetchall()

    result = []
    for m in msgs:
        result.append({
            "id":          m["id"],
            "message_id":  m["message_id"],
            "subject":     m["subject"] or "(no subject)",
            "sender_name": m["sender_name"] or "",
            "sender_addr": m["sender_addr"] or "",
            "recipients":  m["recipients"] or "",
            "body_plain":  m["body_plain"] or "",
            "body_clean":  m["body_clean"] or "",
            "date":        m["date"] or "",
        })
    return jsonify(result)

@app.route("/api/imap-config", methods=["GET", "POST"])
def api_imap_config():
    """GET: return current IMAP config (masked). POST: save config."""
    if request.method == "GET":
        cfg = load_config()
        email_addr = cfg.get("email", "")
        server = cfg.get("server", "")
        port = cfg.get("port", "")
        has_cred = bool(cfg.get("auth_code"))
        return jsonify({
            "email":    email_addr,
            "server":   server,
            "port":     port,
            "has_auth": has_cred,
        })

    data = request.get_json() or {}
    cfg = load_config()

    email_addr = (data.get("email") or "").strip()
    auth_code  = (data.get("auth_code") or "").strip()
    server     = (data.get("server") or "").strip()
    port       = data.get("port")

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
    return jsonify({
        "status": "ok",
        "message": f"配置已保存（{server}:{port}）",
        "server": server,
        "port": port,
    })

@app.route("/api/imap-test", methods=["POST"])
def api_imap_test():
    """Test IMAP connection only — does not count toward daily limit."""
    cfg = load_config()
    if not cfg.get("email") or not cfg.get("auth_code"):
        return jsonify({"status": "error", "message": "请先填写邮箱和授权码"}), 400

    try:
        fetched, results = fetch_imap_emails(
            cfg["server"], int(cfg.get("port", 993)),
            cfg["email"], cfg["auth_code"]
        )
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

    # Show preview of found emails without saving
    preview = []
    for em in results[:5]:
        preview.append({
            "subject": em["subject"],
            "from": em["sender_name"],
            "date": em["date"],
        })

    return jsonify({
        "status":  "ok",
        "message": f"连接成功！发现 {fetched} 封未读邮件",
        "found":   fetched,
        "preview": preview,
    })

@app.route("/api/imap-fetch", methods=["POST"])
def api_imap_fetch():
    """Fetch & save emails from IMAP. Checks daily limit for IMAP specifically."""
    db = get_db()
    cfg = load_config()

    if not cfg.get("email") or not cfg.get("auth_code"):
        return jsonify({"status": "error", "message": "请先配置邮箱和授权码"}), 400

    # Only check daily limit if explicitly requested (not for test)
    force = request.get_json(silent=True) or {}
    if not force.get("force") and db.execute(
        "SELECT 1 FROM check_log WHERE check_date=? AND checked_at LIKE '%IMAP%'",
        (today_str(),)
    ).fetchone():
        return jsonify({"status": "cached", "message": "今天已从服务器获取过最新数据，无需重复检查"})

    try:
        fetched, results = fetch_imap_emails(
            cfg["server"], int(cfg.get("port", 993)),
            cfg["email"], cfg["auth_code"]
        )
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

    # insert into DB
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
    build_threads()

    # log IMAP check
    db.execute(
        "INSERT INTO check_log (check_date, checked_at) VALUES (?, ?)",
        (today_str(), f"IMAP {datetime.now().isoformat()}")
    )
    db.commit()

    return jsonify({
        "status":    "updated",
        "message":   f"从服务器获取 {fetched} 封邮件，新增入库 {inserted} 封",
        "fetched":   fetched,
        "new_count": inserted,
    })

@app.route("/api/import-sample", methods=["POST"])
def api_import_sample():
    """Generate sample data for demo / testing."""
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
            "body_plain":  (
                "张三你好，\n\n"
                "我这边前端模块已完成80%，预计本周五可以交付测试。\n\n"
                "李四\n"
                "> 大家好，\n"
                "> 请各位更新一下Q3项目的进度情况。\n"
                "> 谢谢，\n"
                "> 张三"
            ),
            "body_clean":  "",
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
            "body_plain":  (
                "后端API已全部完成，正在写单元测试。\n"
                "另外数据库迁移脚本还需要review一下。\n\n"
                "王五\n"
                "> 我这边前端模块已完成80%，预计本周五可以交付测试。\n"
                "> 李四"
            ),
            "body_clean":  "",
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
            "body_plain":  (
                "好的，收到。\n\n"
                "李四，前端完成后先内部演示一下。\n"
                "王五，迁移脚本我明天review。\n\n"
                "大家辛苦了！\n"
                "张三\n"
                "> 后端API已全部完成，正在写单元测试。\n"
                "> 另外数据库迁移脚本还需要review一下。\n"
                "> 王五"
            ),
            "body_clean":  "",
            "date":        "2025-08-10 16:00:00",
        },
    ]

    # clean sample bodies
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

# ── Main ──
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=False)
