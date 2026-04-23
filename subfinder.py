import subprocess
import signal
import os
import sys
import tempfile
import threading
import time
import urllib.request
import urllib.error
from datetime import datetime
from db import get_connection
from targets import select_target, list_targets, get_target
import jobs as jobmgr


_CHECKS = [
    ("https", 443),
    ("http",  80),
    ("https", 8443),
    ("http",  8080),
]


def _check_webapp(host):
    for scheme, port in _CHECKS:
        url = f"{scheme}://{host}" if port in (80, 443) else f"{scheme}://{host}:{port}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "EnumTool/0.1"})
            resp = urllib.request.urlopen(req, timeout=5)
            return scheme, resp.status
        except urllib.error.HTTPError as e:
            return scheme, e.code
        except Exception:
            continue
    return None, None


def _save_subdomains(target_id, hosts, out=None):
    if out is None:
        out = sys.stdout

    def emit(msg, end="\n"):
        out.write(msg + end)
        out.flush()

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    today = now[:10]
    conn = get_connection()

    saved = 0
    webapps = 0

    for host in hosts:
        emit(f"  Checking {host} ...", end=" ")
        scheme, status = _check_webapp(host)

        has_webapp    = 1 if scheme else 0
        webapp_scheme = scheme or ""
        webapp_status = status or 0

        if has_webapp:
            emit(f"[{webapp_status}] {webapp_scheme.upper()}")
            webapps += 1
        else:
            emit("no response")

        try:
            conn.execute(
                """INSERT INTO subdomains
                   (target_id, host, discovered_at, has_webapp, webapp_scheme, webapp_status)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(host) DO UPDATE SET
                       has_webapp=excluded.has_webapp,
                       webapp_scheme=excluded.webapp_scheme,
                       webapp_status=excluded.webapp_status""",
                (target_id, host, now, has_webapp, webapp_scheme, webapp_status),
            )
            saved += 1
        except Exception:
            pass

        if has_webapp:
            try:
                conn.execute(
                    "INSERT OR IGNORE INTO targets (host, type, added_at) VALUES (?, ?, ?)",
                    (host, "domain", today),
                )
            except Exception:
                pass

    conn.commit()
    conn.close()
    emit(f"\n  [+] {saved} subdomains saved, {webapps} have web apps and were added to targets.\n")


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

    if target["type"] != "domain":
        print("  [!] Subfinder works with domains only.\n")
        return

    extra = input("  Extra subfinder flags (leave empty to skip): ").strip()

    tmp = tempfile.NamedTemporaryFile(suffix=".txt", delete=False)
    tmp.close()

    log_path = jobmgr.new_log_path()
    log_fh   = open(log_path, "w", buffering=1)

    cmd = f"subfinder -d {target['host']} -o {tmp.name}"
    if extra:
        cmd += f" {extra}"

    print(f"\n  Running: {cmd}\n")

    proc = subprocess.Popen(
        cmd, shell=True, preexec_fn=os.setsid,
        stdout=log_fh, stderr=subprocess.STDOUT,
    )

    stop_ev  = threading.Event()
    stream_t = threading.Thread(target=_stream_log, args=(log_path, stop_ev), daemon=True)
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
        print("  [2] Discard and stop\n")
        choice = input("  > ").strip()

        if choice == "1":
            job = jobmgr.add_job(f"subfinder  {target['host']}", proc, log_path)

            def bg_probe(j=job, tid=target["id"], t=tmp.name, fh=log_fh):
                j.proc.wait()
                if os.path.exists(t) and os.path.getsize(t) > 0:
                    with open(t) as f:
                        hosts = [l.strip() for l in f if l.strip()]
                    os.unlink(t)
                    fh.write(f"\n  [+] Found {len(hosts)} subdomains. Probing...\n\n")
                    fh.flush()
                    _save_subdomains(tid, hosts, out=fh)
                else:
                    fh.write("  [!] No subdomains found.\n")
                fh.close()
                j.status = "done"

            threading.Thread(target=bg_probe, daemon=True).start()
            print(f"  [+] Job #{job.id} running in background  (Main Menu → Jobs)\n")
            return

        else:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            proc.wait()
            log_fh.close()
            if os.path.exists(log_path):
                os.unlink(log_path)
            if os.path.exists(tmp.name):
                os.unlink(tmp.name)
            print("  Discarded.\n")
            return

    # Normal finish
    log_fh.close()
    if os.path.exists(log_path):
        os.unlink(log_path)

    if not os.path.exists(tmp.name) or os.path.getsize(tmp.name) == 0:
        print("  [!] No subdomains found or subfinder failed.\n")
        if os.path.exists(tmp.name):
            os.unlink(tmp.name)
        return

    with open(tmp.name) as f:
        hosts = [line.strip() for line in f if line.strip()]
    os.unlink(tmp.name)

    if not hosts:
        print("  [!] No subdomains found.\n")
        return

    print(f"\n  [+] Found {len(hosts)} subdomains. Probing for web apps...\n")
    _save_subdomains(target["id"], hosts)


def list_subdomains(target_id):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM subdomains WHERE target_id = ? ORDER BY has_webapp DESC, host",
        (target_id,),
    ).fetchall()
    conn.close()

    if not rows:
        print("  [!] No subdomains discovered yet.\n")
        return

    print(f"\n  {'Host':<45} {'WebApp':<8} {'Scheme':<8} {'Status'}")
    print("  " + "-" * 72)
    for r in rows:
        webapp = "YES" if r["has_webapp"] else "no"
        status = str(r["webapp_status"]) if r["webapp_status"] else "-"
        print(f"  {r['host']:<45} {webapp:<8} {r['webapp_scheme']:<8} {status}")
    print(f"\n  {len(rows)} subdomain(s)\n")
