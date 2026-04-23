import subprocess
import signal
import json
import os
import sys
import tempfile
import threading
import time
from datetime import datetime
from db import get_connection
from targets import select_target, list_targets, get_target
import jobs as jobmgr


def _stream_log(log_path, stop_ev):
    with open(log_path, "r") as f:
        while not stop_ev.is_set():
            line = f.readline()
            if line:
                sys.stdout.write(line)
                sys.stdout.flush()
            else:
                time.sleep(0.05)


def run_scan():
    target = select_target()
    if not target:
        return

    scheme = input("  http or https? [http]: ").strip().lower() or "http"
    url = f"{scheme}://{target['host']}"

    while True:
        extra = input("  Extra dirsearch flags (leave empty to skip): ").strip()

        tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        tmp.close()

        log_path = jobmgr.new_log_path()
        log_fh   = open(log_path, "w", buffering=1)

        cmd = f"dirsearch -u {url} --format json -o {tmp.name}"
        if extra:
            cmd += f" {extra}"

        print(f"\n  Running: {cmd}\n")

        proc = subprocess.Popen(
            cmd, shell=True, preexec_fn=os.setsid,
            stdout=log_fh, stderr=subprocess.STDOUT,
        )

        stop_ev   = threading.Event()
        stream_t  = threading.Thread(target=_stream_log, args=(log_path, stop_ev), daemon=True)
        stream_t.start()

        interrupted = False
        try:
            proc.wait()
            stop_ev.set()
        except KeyboardInterrupt:
            interrupted = True
            stop_ev.set()
            print("\n\n  [!] Scan interrupted.\n")

        if interrupted:
            print("  [1] Send to background")
            print("  [2] Restart with different options")
            print("  [3] Save partial results and stop")
            print("  [4] Discard everything and stop\n")
            choice = input("  > ").strip()

            if choice == "1":
                job = jobmgr.add_job(f"dirsearch  {target['host']}", proc, log_path)

                def bg_save(j=job, tid=target["id"], u=url, c=cmd, t=tmp.name, fh=log_fh):
                    j.proc.wait()
                    fh.close()
                    j.status = "done"
                    if os.path.exists(t) and os.path.getsize(t) > 0:
                        _save_results(tid, u, c, t, silent=True)
                    if os.path.exists(t):
                        os.unlink(t)

                threading.Thread(target=bg_save, daemon=True).start()
                print(f"  [+] Job #{job.id} running in background  (Main Menu → Jobs)\n")
                return

            elif choice == "2":
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                proc.wait()
                log_fh.close()
                if os.path.exists(log_path):
                    os.unlink(log_path)
                if os.path.exists(tmp.name):
                    os.unlink(tmp.name)
                print()
                continue

            elif choice == "3":
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                proc.wait()
                log_fh.close()
                if os.path.exists(tmp.name) and os.path.getsize(tmp.name) > 0:
                    _save_results(target["id"], url, cmd, tmp.name)
                else:
                    print("  [!] No partial results to save.")
                if os.path.exists(log_path):
                    os.unlink(log_path)
                break

            else:
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                proc.wait()
                log_fh.close()
                if os.path.exists(log_path):
                    os.unlink(log_path)
                if os.path.exists(tmp.name):
                    os.unlink(tmp.name)
                print("  Discarded.\n")
                break

        else:
            log_fh.close()
            if os.path.exists(log_path):
                os.unlink(log_path)
            if os.path.exists(tmp.name) and os.path.getsize(tmp.name) > 0:
                _save_results(target["id"], url, cmd, tmp.name)
            else:
                print("  [!] No output file found. Scan may have failed.")
            break


def _save_results(target_id, url, command, json_file, silent=False):
    try:
        with open(json_file) as f:
            data = json.load(f)
    except Exception:
        print("  [!] Could not parse dirsearch JSON output.")
        return

    results = data.get("results", [])
    if not results:
        print("  [!] Scan finished but no results to save.")
        return

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_connection()

    cursor = conn.execute(
        "INSERT INTO dirsearch_scans (target_id, url, command, scanned_at) VALUES (?, ?, ?, ?)",
        (target_id, url, command, now),
    )
    scan_id = cursor.lastrowid

    for r in results:
        conn.execute(
            """INSERT INTO dirsearch_results
               (scan_id, target_id, url, status_code, content_length, redirect, scanned_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                scan_id,
                target_id,
                r.get("url", ""),
                r.get("status", 0),
                r.get("length", 0),
                r.get("redirect", "") or "",
                now,
            ),
        )

    conn.commit()
    conn.close()
    if not silent:
        print(f"\n  [+] Saved {len(results)} results from scan #{scan_id}\n")


# ---------------------------------------------------------------------------
# Query engine
# ---------------------------------------------------------------------------

def _build_where(filters):
    clauses = ["1=1"]
    params = []

    if "target_id" in filters:
        clauses.append("r.target_id = ?")
        params.append(filters["target_id"])
    if "scan_id" in filters:
        clauses.append("r.scan_id = ?")
        params.append(filters["scan_id"])
    if "status_include" in filters:
        clauses.append("r.status_code = ?")
        params.append(filters["status_include"])
    if "status_exclude" in filters:
        clauses.append("r.status_code != ?")
        params.append(filters["status_exclude"])
    if "url_contains" in filters:
        clauses.append("r.url LIKE ?")
        params.append(f"%{filters['url_contains']}%")

    return " AND ".join(clauses), params


def _show_results(filters):
    conn = get_connection()
    where, params = _build_where(filters)
    rows = conn.execute(
        f"SELECT r.* FROM dirsearch_results r WHERE {where} ORDER BY r.status_code, r.url",
        params,
    ).fetchall()
    conn.close()

    if not rows:
        print("  [!] No results match.\n")
        return

    print(f"\n  {'#':<5} {'Status':<8} {'Length':<10} {'URL'}")
    print("  " + "-" * 75)
    for r in rows:
        redirect = f"  → {r['redirect']}" if r["redirect"] else ""
        print(f"  {r['id']:<5} {r['status_code']:<8} {r['content_length']:<10} {r['url']}{redirect}")
    active = {k: v for k, v in filters.items() if k != "target_id"}
    print(f"\n  {len(rows)} result(s)  |  filters: {active or 'none'}\n")


def _delete_with_filters(filters):
    conn = get_connection()
    where, params = _build_where(filters)
    count = conn.execute(
        f"SELECT COUNT(*) FROM dirsearch_results r WHERE {where}", params
    ).fetchone()[0]

    if not count:
        print("  [!] No results match — nothing deleted.\n")
        conn.close()
        return

    confirm = input(f"  [!] About to delete {count} result(s). Confirm? [y/N]: ").strip().lower()
    if confirm != "y":
        print("  Cancelled.\n")
        conn.close()
        return

    conn.execute(
        f"DELETE FROM dirsearch_results WHERE id IN "
        f"(SELECT r.id FROM dirsearch_results r WHERE {where})",
        params,
    )
    conn.commit()
    conn.close()
    print(f"  [+] Deleted {count} result(s).\n")


def _delete_all(target_id=None):
    conn = get_connection()
    if target_id:
        count = conn.execute(
            "SELECT COUNT(*) FROM dirsearch_results WHERE target_id = ?", (target_id,)
        ).fetchone()[0]
    else:
        count = conn.execute("SELECT COUNT(*) FROM dirsearch_results").fetchone()[0]

    if not count:
        print("  [!] Nothing to delete.\n")
        conn.close()
        return

    scope = f"target #{target_id}" if target_id else "ALL targets"
    confirm = input(f"  [!] Delete ALL {count} results for {scope}? [y/N]: ").strip().lower()
    if confirm != "y":
        print("  Cancelled.\n")
        conn.close()
        return

    if target_id:
        conn.execute("DELETE FROM dirsearch_scans WHERE target_id = ?", (target_id,))
    else:
        conn.execute("DELETE FROM dirsearch_scans")

    conn.commit()
    conn.close()
    print(f"  [+] Deleted all results and scans for {scope}.\n")


def _delete_scan(scan_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM dirsearch_scans WHERE id = ?", (scan_id,)).fetchone()
    if not row:
        print(f"  [!] Scan #{scan_id} not found.\n")
        conn.close()
        return
    confirm = input(f"  [!] Delete entire scan #{scan_id} ({row['url']})? [y/N]: ").strip().lower()
    if confirm != "y":
        print("  Cancelled.\n")
        conn.close()
        return
    conn.execute("DELETE FROM dirsearch_scans WHERE id = ?", (scan_id,))
    conn.commit()
    conn.close()
    print(f"  [+] Scan #{scan_id} and all its results deleted.\n")


def _list_scans(target_id=None):
    conn = get_connection()
    if target_id:
        rows = conn.execute(
            "SELECT s.*, COUNT(r.id) as total FROM dirsearch_scans s "
            "LEFT JOIN dirsearch_results r ON r.scan_id = s.id "
            "WHERE s.target_id = ? GROUP BY s.id ORDER BY s.id",
            (target_id,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT s.*, COUNT(r.id) as total FROM dirsearch_scans s "
            "LEFT JOIN dirsearch_results r ON r.scan_id = s.id "
            "GROUP BY s.id ORDER BY s.id"
        ).fetchall()
    conn.close()

    if not rows:
        print("  [!] No scans found.\n")
        return

    print(f"\n  {'ID':<5} {'Results':<9} {'URL':<40} {'Date'}")
    print("  " + "-" * 75)
    for r in rows:
        print(f"  {r['id']:<5} {r['total']:<9} {r['url']:<40} {r['scanned_at']}")
    print()


def _print_help():
    print("""
  Query commands:
    show 200          show only status 200
    show /admin       show URLs containing /admin
    hide 403          exclude status 403
    url /login        show URLs containing /login
    target example    show URLs containing 'example'
    scan 3            filter to scan #3
    all / show all    reset filters and show everything

    delete all        delete everything (all results + scans)
    delete 403        delete all results with status 403
    delete url /tmp   delete results where URL contains /tmp
    delete scan 3     delete entire scan #3 and its results
    delete target x   delete results where URL contains 'x'

    list scans        show all scans
    results           show current results with active filters
    help              show this help
    back              exit query mode
""")


def query_menu(target_id=None):
    filters = {}
    if target_id:
        filters["target_id"] = target_id

    _print_help()
    _show_results(filters)

    while True:
        try:
            raw = input("  query> ").strip()
        except (KeyboardInterrupt, EOFError):
            break

        if not raw:
            continue

        cmd = raw.lower()

        if cmd == "back":
            break

        elif cmd == "help":
            _print_help()

        elif cmd in ("all", "show all"):
            filters = {"target_id": target_id} if target_id else {}
            _show_results(filters)

        elif cmd == "results":
            _show_results(filters)

        elif cmd == "list scans":
            _list_scans(target_id)

        # --- SHOW ---
        elif cmd.startswith("show "):
            val = cmd[5:].strip()
            if val.isdigit():
                filters["status_include"] = int(val)
                filters.pop("status_exclude", None)
            else:
                filters["url_contains"] = val
            _show_results(filters)

        # --- HIDE ---
        elif cmd.startswith("hide "):
            val = cmd[5:].strip()
            if val.isdigit():
                filters["status_exclude"] = int(val)
                filters.pop("status_include", None)
            _show_results(filters)

        # --- URL ---
        elif cmd.startswith("url "):
            filters["url_contains"] = cmd[4:].strip()
            _show_results(filters)

        # --- TARGET ---
        elif cmd.startswith("target "):
            filters["url_contains"] = cmd[7:].strip()
            _show_results(filters)

        # --- SCAN filter ---
        elif cmd.startswith("scan ") and not cmd.startswith("scan #"):
            val = cmd[5:].strip()
            if val.isdigit():
                filters["scan_id"] = int(val)
            _show_results(filters)

        # --- DELETE ---
        elif cmd.startswith("delete "):
            rest = cmd[7:].strip()

            if rest == "all":
                _delete_all(target_id)

            elif rest.isdigit():
                # delete 403
                f = dict(filters)
                f["status_include"] = int(rest)
                f.pop("status_exclude", None)
                _delete_with_filters(f)

            elif rest.startswith("url "):
                f = dict(filters)
                f["url_contains"] = rest[4:].strip()
                _delete_with_filters(f)

            elif rest.startswith("target "):
                f = dict(filters)
                f["url_contains"] = rest[7:].strip()
                _delete_with_filters(f)

            elif rest.startswith("scan "):
                val = rest[5:].strip()
                if val.isdigit():
                    _delete_scan(int(val))

            else:
                print("  [!] Unknown delete syntax. Type 'help'.\n")

        else:
            print("  [!] Unknown command. Type 'help'.\n")
