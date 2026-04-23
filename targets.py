from datetime import date
from db import get_connection
from ui import single_select


def _detect_type(host):
    parts = host.split(".")
    try:
        if len(parts) == 4:
            list(map(int, parts))
            return "ip"
    except ValueError:
        pass
    return "domain"


def add_target(host):
    host = host.strip().lower()
    target_type = _detect_type(host)
    today = str(date.today())

    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO targets (host, type, added_at) VALUES (?, ?, ?)",
            (host, target_type, today),
        )
        conn.commit()
        print(f"  [+] Added: {host} ({target_type})")
    except Exception:
        print(f"  [!] Target already exists: {host}")
    finally:
        conn.close()


def delete_target(target_id):
    conn = get_connection()
    cursor = conn.execute("DELETE FROM targets WHERE id = ?", (target_id,))
    conn.commit()
    conn.close()
    if cursor.rowcount:
        print(f"  [+] Target #{target_id} deleted.")
    else:
        print(f"  [!] No target with id {target_id}.")


def list_targets():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM targets ORDER BY id").fetchall()
    conn.close()
    return rows


def get_target(target_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM targets WHERE id = ?", (target_id,)).fetchone()
    conn.close()
    return row


def add_subdomain(target_id, host):
    host = host.strip().lower()
    today = str(date.today())
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO subdomains (target_id, host, discovered_at) VALUES (?, ?, ?)",
            (target_id, host, today),
        )
        conn.commit()
    except Exception:
        pass
    finally:
        conn.close()


def list_subdomains(target_id):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM subdomains WHERE target_id = ? ORDER BY id", (target_id,)
    ).fetchall()
    conn.close()
    return rows


def select_target():
    targets = list_targets()
    if not targets:
        print("  [!] No targets saved. Add one first.")
        return None

    return single_select(
        list(targets),
        label_fn=lambda t: f"{t['host']}  ({t['type']})  added {t['added_at']}",
        title="Select Target",
    )
