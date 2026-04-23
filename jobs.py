import os
import sys
import time
import tty
import termios
import select
import signal
import threading
from datetime import datetime
from db import FLASH_DIR

JOBS_DIR = os.path.join(FLASH_DIR, "jobs")
os.makedirs(JOBS_DIR, exist_ok=True)

_jobs  = {}
_lock  = threading.Lock()
_count = 0


def new_log_path():
    global _count
    with _lock:
        _count += 1
        return os.path.join(JOBS_DIR, f"job_{_count}.log")


class Job:
    def __init__(self, job_id, label, proc, log_path):
        self.id       = job_id
        self.label    = label
        self.proc     = proc
        self.log_path = log_path
        self.started  = datetime.now().strftime("%H:%M:%S")
        self.status   = "running"

    def refresh(self):
        if self.status == "running" and self.proc.poll() is not None:
            self.status = "done"
        return self.status


def add_job(label, proc, log_path):
    with _lock:
        job_id = len(_jobs) + 1
        j = Job(job_id, label, proc, log_path)
        _jobs[job_id] = j
    return j


def get_job(job_id):
    return _jobs.get(job_id)


def list_jobs():
    for j in _jobs.values():
        j.refresh()
    return list(_jobs.values())


def remove_job(job_id):
    _jobs.pop(job_id, None)


def kill_job(job):
    try:
        os.killpg(os.getpgid(job.proc.pid), signal.SIGTERM)
        job.proc.wait()
    except Exception:
        pass
    job.status = "killed"


def _read_key():
    fd  = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        return sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def attach(job):
    job.refresh()
    print(f"\n  Job #{job.id}: {job.label}  [{job.status}]")
    print(f"  Started: {job.started}")

    if job.log_path is None:
        if job.status == "running":
            print("  Running in background — results save to DB when done.")
            print("  Press 'k' to kill or any other key to go back.\n")
            ch = _read_key()
            if ch == "k":
                kill_job(job)
                print(f"\n  [job #{job.id} killed]\n")
            else:
                print()
        else:
            print("  Finished — check results in the query / subdomains menu.\n")
        return

    print("  'b' detach   'k' kill\n")
    print("  " + "-" * 60)

    detach_ev = threading.Event()
    kill_ev   = threading.Event()

    def key_listener():
        fd  = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            while not detach_ev.is_set():
                r, _, _ = select.select([sys.stdin], [], [], 0.1)
                if r:
                    ch = sys.stdin.read(1)
                    if ch in ("b", "\x1a"):
                        detach_ev.set()
                    elif ch == "k":
                        kill_ev.set()
                        detach_ev.set()
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)

    threading.Thread(target=key_listener, daemon=True).start()

    try:
        with open(job.log_path, "r") as f:
            while not detach_ev.is_set():
                line = f.readline()
                if line:
                    sys.stdout.write(line)
                    sys.stdout.flush()
                else:
                    job.refresh()
                    if job.status != "running":
                        for line in f:
                            sys.stdout.write(line)
                        sys.stdout.flush()
                        detach_ev.set()
                    else:
                        time.sleep(0.05)
    except Exception:
        pass

    detach_ev.set()

    if kill_ev.is_set():
        kill_job(job)
        print(f"\n\n  [job #{job.id} killed]\n")
    elif job.status in ("done", "killed"):
        print(f"\n\n  [job #{job.id} finished]\n")
    else:
        print(f"\n\n  [detached — job #{job.id} still running]\n")
