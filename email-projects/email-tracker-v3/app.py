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

from flask import Flask, request, jsonify, render_template, g
from email_reply_parser import EmailReplyParser

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent
V2_DIR = BASE_DIR.parent / "email-tracker-v2"
DB_PATH = V2_DIR / "emails.db"
MAIL_DIR = V2_DIR / "maildir"
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


# ── Subject Normalization ──────────────────────────────────────────────

# Prefix patterns: Chinese + English reply/forward markers
# Each pattern optionally handles a preceding [TAG] like [EXTERNAL], [WARNING]
_RE_PREFIXES = [
    r'(?:\[.*?\]\s*)?(?:回复|答复|转发|回覆|通知|自动回复| Auto[-\s]?Reply)\s*[：:]\s*',
    r'(?:\[.*?\]\s*)?(?:RE|FW[D]?|AW|WG|[Rr])\s*[：:]\s*',
    r'(?:\[.*?\]\s*)?[Rr][Ee]\s*[：:]\s*',
    r'(?:\[.*?\]\s*)?[Ff][Ww][Dd]?\s*[：:]\s*',
]
_RE_PREFIX_COMBINED = re.compile(r'^(' + r'|'.join(_RE_PREFIXES) + r')+')

# Bracketed tags to strip — system/notification tags that aren't part of the real subject
_RE_BRACKET_TAG = re.compile(
    r'^\[(?:EXTERNAL|external|External|警告|WARNING|注意|NOTE|'
    r'邮件已被标记为垃圾邮件|邮件已被发件人撤回|邮件已被发件人召回|'
    r'垃圾邮件|SPAM|Auto|系统通知|System|系统邮件|自动|'
    r'邮件已被.*?(?:撤回|召回|删除|拒收|退回|屏蔽|拦截)|'
    r'Bulk|bulk|Junk|junk)\]\s*'
)


def normalize_subject(subject):
    """Strip reply/forward prefixes (and preceding [TAG]s) to get the true base subject."""
    if not subject:
        return "(no subject)"
    result = subject.strip()
    # Strip leading bracketed tags, then prefixes, repeatedly until stable
    while True:
        changed = False
        # Strip a leading bracketed tag
        m = _RE_BRACKET_TAG.match(result)
        if m:
            result = result[m.end():].strip()
            changed = True
        # Strip a leading reply/forward prefix (possibly with a [TAG] before it)
        m2 = _RE_PREFIX_COMBINED.match(result)
        if m2:
            result = result[m2.end():].strip()
            changed = True
        if not changed:
            break
    return result or "(no subject)"


# ── Database ───────────────────────────────────────────────────────────
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
    db.row_factory = sqlite3.Row
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

    # Add base_subject column if not exists (safe migration for shared DB)
    try:
        db.execute("ALTER TABLE emails ADD COLUMN base_subject TEXT")
        db.commit()
    except sqlite3.OperationalError:
        pass  # column already exists

    # Populate base_subject for rows that don't have it yet
    null_count = db.execute(
        "SELECT COUNT(*) as c FROM emails WHERE base_subject IS NULL"
    ).fetchone()["c"]
    if null_count > 0:
        rows = db.execute(
            "SELECT id, subject FROM emails WHERE base_subject IS NULL"
        ).fetchall()
        for r in rows:
            bs = normalize_subject(r["subject"])
            db.execute("UPDATE emails SET base_subject=? WHERE id=?", (bs, r["id"]))
        db.commit()
    else:
        # Refresh all base_subject values to pick up normalization improvements
        rows = db.execute("SELECT id, subject FROM emails").fetchall()
        updated = 0
        for r in rows:
            bs = normalize_subject(r["subject"])
            db.execute("UPDATE emails SET base_subject=? WHERE id=?", (bs, r["id"]))
            updated += 1
        if updated:
            db.commit()

    db.close()


init_db()


# ── Helpers ────────────────────────────────────────────────────────────
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


def parse_eml(filepath):
    with open(filepath, "rb") as f:
        msg = email.message_from_binary_file(f, policy=policy.default)
    mid = _norm(msg.get("Message-ID", ""))
    irt = _norm(msg.get("In-Reply-To", ""))
    refs = (msg.get("References", "") or msg.get("In-Reply-To", "") or "").strip()
    from_header = msg.get("From", "")
    sender_name, sender_addr = "", ""
    if from_header:
        parsed_addr = getaddresses([from_header])
        if parsed_addr:
            sender_name, sender_addr = parsed_addr[0]
    to_header = msg.get("To", "")
    cc_header = msg.get("Cc", "")
    recipients = ", ".join(a for _, a in getaddresses([to_header, cc_header]) if a)
    body = extract_plain_text(msg)
    raw_subject = msg.get("Subject", "(no subject)")
    return {
        "message_id":   mid,
        "in_reply_to":  irt,
        "references":   refs,
        "subject":      raw_subject,
        "base_subject": normalize_subject(raw_subject),
        "sender_name":  sender_name or sender_addr,
        "sender_addr":  sender_addr,
        "recipients":   recipients,
        "body_plain":   body,
        "body_clean":   clean_email_body(body),
        "date":         parse_email_date(msg.get("Date", "")),
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
    raw_subject = m.subject or "(no subject)"
    return {
        "message_id":   mid,
        "in_reply_to":  irt,
        "references":   refs,
        "subject":      raw_subject,
        "base_subject": normalize_subject(raw_subject),
        "sender_name":  m.sender or "",
        "sender_addr":  m.sender or "",
        "recipients":   m.to or "",
        "body_plain":   body,
        "body_clean":   clean_email_body(body),
        "date":         parse_email_date(str(m.date) if m.date else ""),
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
            parsed_addr = getaddresses([from_header])
            if parsed_addr:
                sender_name, sender_addr = parsed_addr[0]
        to_header = msg.get("To", "")
        cc_header = msg.get("Cc", "")
        recipients = ", ".join(a for _, a in getaddresses([to_header, cc_header]) if a)
        body = extract_plain_text(msg)
        raw_subject = msg.get("Subject", "(no subject)")
        results.append({
            "message_id":   mid,
            "in_reply_to":  irt,
            "references":   refs,
            "subject":      raw_subject,
            "base_subject": normalize_subject(raw_subject),
            "sender_name":  sender_name or sender_addr,
            "sender_addr":  sender_addr,
            "recipients":   recipients,
            "body_plain":   body,
            "body_clean":   clean_email_body(body),
            "date":         parse_email_date(msg.get("Date", "")),
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
    try:
        y, m, d = iso_date.split("-")
        return f"{int(d):02d}-{MONTH_NAMES[int(m)-1]}-{y}"
    except Exception:
        return iso_date


# ── V3: Main Line Detection ────────────────────────────────────────────

def find_connected_components(email_list):
    """Partition emails into connected components based on In-Reply-To links."""
    id_set = {e["message_id"] for e in email_list}
    email_map = {e["message_id"]: e for e in email_list}

    # Build adjacency (undirected for component detection)
    neighbors = {mid: set() for mid in id_set}
    for e in email_list:
        parent = e.get("in_reply_to", "")
        if parent and parent in id_set:
            neighbors[e["message_id"]].add(parent)
            neighbors[parent].add(e["message_id"])

    visited = set()
    components = []

    for mid in id_set:
        if mid in visited:
            continue
        # BFS to find component
        stack = [mid]
        comp = []
        while stack:
            node = stack.pop()
            if node in visited:
                continue
            visited.add(node)
            comp.append(node)
            for nb in neighbors[node]:
                if nb not in visited:
                    stack.append(nb)
        components.append(comp)

    # Sort each component by date
    result = []
    for comp_ids in components:
        comp_emails = [email_map[mid] for mid in comp_ids]
        comp_emails.sort(key=lambda x: x.get("date", ""))
        result.append(comp_emails)
    # Sort components by size desc, then earliest date
    result.sort(key=lambda c: (-len(c), c[0].get("date", "")))
    return result


def compute_main_line(emails_in_component):
    """
    Given a connected component, find the longest reply chain as the main line.
    Returns (main_line_ids_ordered, side_branch_ids).
    """
    if len(emails_in_component) <= 1:
        return [e["message_id"] for e in emails_in_component], []

    id_set = {e["message_id"] for e in emails_in_component}
    email_map = {e["message_id"]: e for e in emails_in_component}

    # Build child lists
    children = {}
    roots = []
    for e in emails_in_component:
        parent = e.get("in_reply_to", "")
        if parent and parent in id_set:
            children.setdefault(parent, []).append(e["message_id"])
        else:
            roots.append(e["message_id"])

    if not roots:
        roots = [emails_in_component[0]["message_id"]]

    # Find longest path from any root (DFS)
    def longest_path(node_id, visited=None):
        if visited is None:
            visited = set()
        if node_id in visited:
            return []
        visited.add(node_id)
        best_tail = []
        for child_id in children.get(node_id, []):
            child_path = longest_path(child_id, set(visited))
            if len(child_path) > len(best_tail):
                best_tail = child_path
        return [node_id] + best_tail

    best_path = []
    for root in roots:
        path = longest_path(root)
        if len(path) > len(best_path):
            best_path = path

    main_set = set(best_path)
    side_ids = [mid for mid in id_set if mid not in main_set]

    # Sort side branches by their own reply chains
    return best_path, side_ids


def analyze_base_subject_group(emails):
    """
    Full analysis of one base_subject group.
    Returns structured data for the frontend.
    """
    components = find_connected_components(emails)

    all_main_line = []
    all_side = []
    component_results = []

    for comp in components:
        main_ids, side_ids = compute_main_line(comp)
        # Map IDs back to full email objects
        email_map = {e["message_id"]: e for e in comp}
        main_emails = [email_map[mid] for mid in main_ids]
        side_emails = [email_map[mid] for mid in side_ids]
        all_main_line.extend(main_emails)
        all_side.extend(side_emails)
        component_results.append({
            "main_line": main_emails,
            "side_branches": side_emails,
            "component_size": len(comp),
        })

    return {
        "components": component_results,
        "total_main": len(all_main_line),
        "total_side": len(all_side),
        "total": len(emails),
    }


# ── IMAP ──────────────────────────────────────────────────────────────
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
                      since_date=None, before_date=None):
    import socket
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

    criteria = []
    if since_date:
        criteria.append(f'SINCE "{to_imap_date(since_date)}"')
    else:
        criteria.append(f'SINCE "01-Jan-{datetime.now().year}"')
    if before_date:
        criteria.append(f'BEFORE "{to_imap_date(before_date)}"')

    search_criteria = " ".join(criteria)
    typ, msg_ids = conn.search(None, f'({search_criteria})')
    if typ != "OK":
        conn.logout()
        return 0, []

    id_list = msg_ids[0].split()
    if not id_list:
        conn.logout()
        return 0, []

    if limit and len(id_list) > limit:
        id_list = id_list[-limit:]

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


# ── Routes ─────────────────────────────────────────────────────────────
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
    conv_count = db.execute(
        "SELECT COUNT(DISTINCT base_subject) as c FROM emails WHERE base_subject IS NOT NULL"
    ).fetchone()["c"]
    return jsonify({
        "checked_today":      row is not None,
        "last_check_date":    row["check_date"] if row else None,
        "total_emails":       total,
        "total_threads":      thread_count,
        "total_conversations": conv_count,
        "default_date_from":  cfg.get("default_date_from", "2026-05-01"),
        "default_date_to":    cfg.get("default_date_to", "2026-05-31"),
        "last_fetch_date":    cfg.get("last_fetch_date", None),
        "imap_configured":    bool(cfg.get("email") and cfg.get("auth_code")),
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
                    (message_id, in_reply_to, refs, subject, base_subject,
                     sender_name, sender_addr, recipients,
                     body_plain, body_clean, date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                em["message_id"], em["in_reply_to"], em["references"],
                em["subject"], em["base_subject"],
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


# ── V3 Core: Conversations ────────────────────────────────────────────

@app.route("/api/conversations")
def api_conversations():
    """List all conversations grouped by base_subject (normalized subject)."""
    db = get_db()
    date_from = request.args.get("date_from", "")
    date_to = request.args.get("date_to", "")

    where = ["1=1"]
    params = []
    if date_from:
        where.append("date >= ?")
        params.append(date_from)
    if date_to:
        where.append("date <= ?")
        params.append(date_to + " 23:59:59")

    where_sql = " AND ".join(where)

    rows = db.execute(f"""
        SELECT base_subject,
               COUNT(*)        as total_count,
               MAX(date)       as latest_date,
               MIN(date)       as earliest_date,
               GROUP_CONCAT(DISTINCT sender_name) as participants,
               GROUP_CONCAT(DISTINCT thread_id)   as thread_ids
        FROM emails
        WHERE {where_sql} AND base_subject IS NOT NULL
        GROUP BY base_subject
        ORDER BY MAX(date) DESC
    """, params).fetchall()

    result = []
    for r in rows:
        result.append({
            "base_subject":  r["base_subject"],
            "total_count":   r["total_count"],
            "latest_date":   r["latest_date"] or "",
            "earliest_date": r["earliest_date"] or "",
            "participants":  r["participants"] or "",
            "thread_ids":    r["thread_ids"] or "",
        })
    return jsonify(result)


@app.route("/api/conversation/detail")
def api_conversation_detail():
    """Get full detail of one base_subject conversation with main line + side branches."""
    db = get_db()
    base_subject = request.args.get("base_subject", "").strip()
    if not base_subject:
        return jsonify({"error": "base_subject is required"}), 400

    date_from = request.args.get("date_from", "")
    date_to = request.args.get("date_to", "")

    where = ["base_subject = ?"]
    params = [base_subject]
    if date_from:
        where.append("date >= ?")
        params.append(date_from)
    if date_to:
        where.append("date <= ?")
        params.append(date_to + " 23:59:59")

    where_sql = " AND ".join(where)

    rows = db.execute(f"""
        SELECT id, message_id, in_reply_to, refs, subject, base_subject,
               sender_name, sender_addr, recipients, date, thread_id
        FROM emails
        WHERE {where_sql}
        ORDER BY date
    """, params).fetchall()

    if not rows:
        return jsonify({"error": "conversation not found"}), 404

    emails = [dict(r) for r in rows]
    analysis = analyze_base_subject_group(emails)

    # Serialize for frontend
    def serialize_emails(email_list):
        return [{
            "id":           e["id"],
            "message_id":   e["message_id"],
            "in_reply_to":  e.get("in_reply_to", "") or "",
            "refs":         e.get("refs", "") or "",
            "subject":      e.get("subject", "(no subject)"),
            "base_subject": e.get("base_subject", ""),
            "sender_name":  e.get("sender_name", ""),
            "sender_addr":  e.get("sender_addr", ""),
            "recipients":   e.get("recipients", ""),
            "date":         e.get("date", ""),
            "thread_id":    e.get("thread_id", ""),
        } for e in email_list]

    components_data = []
    for comp in analysis["components"]:
        components_data.append({
            "main_line":     serialize_emails(comp["main_line"]),
            "side_branches": serialize_emails(comp["side_branches"]),
            "component_size": comp["component_size"],
        })

    return jsonify({
        "base_subject": base_subject,
        "total_main":   analysis["total_main"],
        "total_side":   analysis["total_side"],
        "total":        analysis["total"],
        "components":   components_data,
    })


@app.route("/api/email/<int:email_id>")
def api_email_detail(email_id):
    db = get_db()
    m = db.execute("""
        SELECT id, message_id, in_reply_to, refs, subject, base_subject,
               sender_name, sender_addr, recipients,
               body_plain, body_clean, date
        FROM emails WHERE id=?
    """, (email_id,)).fetchone()
    if not m:
        return jsonify({"error": "邮件不存在"}), 404
    return jsonify({
        "id":           m["id"],
        "message_id":   m["message_id"],
        "in_reply_to":  m["in_reply_to"] or "",
        "refs":         m["refs"] or "",
        "subject":      m["subject"] or "(no subject)",
        "base_subject": m["base_subject"] or "",
        "sender_name":  m["sender_name"] or "",
        "sender_addr":  m["sender_addr"] or "",
        "recipients":   m["recipients"] or "",
        "body_plain":   m["body_plain"] or "",
        "body_clean":   m["body_clean"] or "",
        "date":         m["date"] or "",
    })


@app.route("/api/search")
def api_search():
    q = request.args.get("q", "").strip()
    if not q or len(q) < 1:
        return jsonify([])
    db = get_db()
    pattern = f"%{q}%"
    rows = db.execute("""
        SELECT id, message_id, subject, base_subject, sender_name, sender_addr, date, thread_id
        FROM emails
        WHERE subject LIKE ? OR sender_name LIKE ? OR sender_addr LIKE ? OR base_subject LIKE ?
        ORDER BY date DESC
        LIMIT 30
    """, (pattern, pattern, pattern, pattern)).fetchall()
    return jsonify([{
        "id": r["id"], "message_id": r["message_id"],
        "subject": r["subject"] or "(no subject)",
        "base_subject": r["base_subject"] or "",
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
        fetched, results = fetch_imap_emails(
            cfg["server"], int(cfg.get("port", 993)),
            cfg["email"], cfg["auth_code"], limit=5
        )
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    preview = []
    for em in results:
        preview.append({"subject": em["subject"], "from": em["sender_name"], "date": em["date"]})
    return jsonify({
        "status": "ok", "message": f"连接成功！今年共 {fetched} 封邮件（测试预览前5封）",
        "found": fetched, "preview": preview,
    })


@app.route("/api/imap-fetch", methods=["POST"])
def api_imap_fetch():
    db = get_db()
    cfg = load_config()
    if not cfg.get("email") or not cfg.get("auth_code"):
        return jsonify({"status": "error", "message": "请先配置邮箱和授权码"}), 400

    body_data = request.get_json(silent=True) or {}
    force = body_data.get("force", False)
    date_from = body_data.get("date_from", "")
    date_to = body_data.get("date_to", "")

    if date_from:
        since_date = date_from
    elif cfg.get("last_fetch_date"):
        since_date = cfg["last_fetch_date"]
    else:
        since_date = cfg.get("default_date_from", "2026-05-01")

    before_date = date_to if date_to else None

    if not force and not date_from and db.execute(
        "SELECT 1 FROM check_log WHERE check_date=?", (today_str(),)
    ).fetchone():
        return jsonify({"status": "cached", "message": "今天已从服务器获取过最新数据，无需重复检查"})

    try:
        fetched, results = fetch_imap_emails(
            cfg["server"], int(cfg.get("port", 993)),
            cfg["email"], cfg["auth_code"],
            since_date=since_date,
            before_date=before_date,
        )
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

    inserted = 0
    for em in results:
        try:
            cur = db.execute("""
                INSERT OR IGNORE INTO emails
                    (message_id, in_reply_to, refs, subject, base_subject,
                     sender_name, sender_addr, recipients,
                     body_plain, body_clean, date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                em["message_id"], em["in_reply_to"], em["references"],
                em["subject"], em["base_subject"],
                em["sender_name"], em["sender_addr"], em["recipients"],
                em["body_plain"], em["body_clean"], em["date"],
            ))
            if cur.rowcount:
                inserted += cur.rowcount
        except Exception:
            continue

    db.commit()
    build_threads()
    db.execute(
        "INSERT INTO check_log (check_date, checked_at) VALUES (?, ?)",
        (today_str(), f"IMAP {datetime.now().isoformat()}")
    )
    db.commit()

    cfg["last_fetch_date"] = today_str()
    if date_from:
        cfg["default_date_from"] = date_from
    if date_to:
        cfg["default_date_to"] = date_to
    save_config(cfg)

    return jsonify({
        "status": "updated", "message": f"从服务器获取 {fetched} 封邮件，新增入库 {inserted} 封",
        "fetched": fetched, "new_count": inserted,
        "since_date": since_date,
    })


@app.route("/api/import-sample", methods=["POST"])
def api_import_sample():
    db = get_db()
    samples = [
        {
            "message_id":  "<v3-001@demo.local>",
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
            "message_id":  "<v3-002@demo.local>",
            "in_reply_to": "<v3-001@demo.local>",
            "references":  "<v3-001@demo.local>",
            "subject":     "回复：关于Q3项目进度的讨论",
            "sender_name": "李四",
            "sender_addr": "lisi@example.com",
            "recipients":  "zhangsan@example.com, wangwu@example.com",
            "body_plain":  "张三你好，\n\n我这边前端模块已完成80%，预计本周五可以交付测试。\n\n李四",
            "body_clean":  "张三你好，\n\n我这边前端模块已完成80%，预计本周五可以交付测试。",
            "date":        "2025-08-10 10:30:00",
        },
        {
            "message_id":  "<v3-003@demo.local>",
            "in_reply_to": "<v3-002@demo.local>",
            "references":  "<v3-001@demo.local> <v3-002@demo.local>",
            "subject":     "Re: 关于Q3项目进度的讨论",
            "sender_name": "王五",
            "sender_addr": "wangwu@example.com",
            "recipients":  "zhangsan@example.com, lisi@example.com",
            "body_plain":  "后端API已全部完成，正在写单元测试。\n另外数据库迁移脚本还需要review一下。\n\n王五",
            "body_clean":  "后端API已全部完成，正在写单元测试。\n另外数据库迁移脚本还需要review一下。",
            "date":        "2025-08-10 14:15:00",
        },
        {
            "message_id":  "<v3-004@demo.local>",
            "in_reply_to": "<v3-003@demo.local>",
            "references":  "<v3-001@demo.local> <v3-002@demo.local> <v3-003@demo.local>",
            "subject":     "回复：Re: 关于Q3项目进度的讨论",
            "sender_name": "张三",
            "sender_addr": "zhangsan@example.com",
            "recipients":  "lisi@example.com, wangwu@example.com",
            "body_plain":  "好的，收到。\n\n大家辛苦了！\n张三",
            "body_clean":  "好的，收到。\n\n大家辛苦了！",
            "date":        "2025-08-10 16:00:00",
        },
        {
            "message_id":  "<v3-005@demo.local>",
            "in_reply_to": "<v3-001@demo.local>",
            "references":  "<v3-001@demo.local>",
            "subject":     "Re: 关于Q3项目进度的讨论",
            "sender_name": "赵六",
            "sender_addr": "zhaoliu@example.com",
            "recipients":  "zhangsan@example.com",
            "body_plain":  "张三，测试这边已经准备好了，随时可以开始。",
            "body_clean":  "张三，测试这边已经准备好了，随时可以开始。",
            "date":        "2025-08-10 11:00:00",
        },
        {
            "message_id":  "<v3-006@demo.local>",
            "in_reply_to": "",
            "references":  "",
            "subject":     "转发：关于Q3项目进度的讨论",
            "sender_name": "孙七",
            "sender_addr": "sunqi@example.com",
            "recipients":  "zhouba@example.com",
            "body_plain":  "周八，请关注这个项目的进展。\n\n---------- 转发邮件 ----------\n发件人: 张三\n...",
            "body_clean":  "周八，请关注这个项目的进展。",
            "date":        "2025-08-11 09:00:00",
        },
        {
            "message_id":  "<v3-007@demo.local>",
            "in_reply_to": "",
            "references":  "",
            "subject":     "FW：关于Q3项目进度的讨论",
            "sender_name": "周八",
            "sender_addr": "zhouba@example.com",
            "recipients":  "wujiu@example.com",
            "body_plain":  "吴九，请看一下这个项目进度，我们可能需要配合。",
            "body_clean":  "吴九，请看一下这个项目进度，我们可能需要配合。",
            "date":        "2025-08-11 10:00:00",
        },
    ]

    for s in samples:
        if not s.get("base_subject"):
            s["base_subject"] = normalize_subject(s["subject"])
        if not s["body_clean"]:
            s["body_clean"] = clean_email_body(s["body_plain"])

    inserted = 0
    for em in samples:
        try:
            cur = db.execute("""
                INSERT OR IGNORE INTO emails
                    (message_id, in_reply_to, refs, subject, base_subject,
                     sender_name, sender_addr, recipients,
                     body_plain, body_clean, date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                em["message_id"], em["in_reply_to"], em["references"],
                em["subject"], em["base_subject"],
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
    app.run(host="0.0.0.0", port=5003, debug=False)
