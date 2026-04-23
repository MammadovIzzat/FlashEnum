from db import init_db
from targets import add_target, delete_target, list_targets
from dirsearch import run_scan as dirsearch_scan, query_menu, _list_scans
from subfinder import run_scan as subfinder_scan, list_subdomains
from ui import multi_select, single_select


def print_banner():
    print("""
  ███████╗██╗      █████╗ ███████╗██╗  ██╗
  ██╔════╝██║     ██╔══██╗██╔════╝██║  ██║
  █████╗  ██║     ███████║███████╗███████║
  ██╔══╝  ██║     ██╔══██║╚════██║██╔══██║
  ██║     ███████╗██║  ██║███████║██║  ██║
  ╚═╝     ╚══════╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝
  ███████╗███╗   ██╗██╗   ██╗███╗   ███╗
  ██╔════╝████╗  ██║██║   ██║████╗ ████║
  █████╗  ██╔██╗ ██║██║   ██║██╔████╔██║
  ██╔══╝  ██║╚██╗██║██║   ██║██║╚██╔╝██║
  ███████╗██║ ╚████║╚██████╔╝██║ ╚═╝ ██║
  ╚══════╝╚═╝  ╚═══╝ ╚═════╝ ╚═╝     ╚═╝
        fastest way to enumerate  v0.1
    """)


def target_menu():
    while True:
        print("""
  --- Target Manager ---
  [1] Add target
  [2] Delete target
  [3] List targets
  [4] Show subdomains of a target
  [0] Back
""")
        choice = input("  > ").strip()

        if choice == "1":
            host = input("  Enter host (IP or domain): ").strip()
            if host:
                add_target(host)

        elif choice == "2":
            targets = list_targets()
            if not targets:
                print("  [!] No targets to delete.")
                continue
            to_delete = multi_select(
                list(targets),
                label_fn=lambda t: f"{t['host']}  ({t['type']})",
                title="Delete Targets",
            )
            if not to_delete:
                print("  Cancelled.")
                continue
            print("  About to delete:")
            for t in to_delete:
                print(f"    - {t['host']}")
            confirm = input("\n  Confirm? [y/N]: ").strip().lower()
            if confirm == "y":
                for t in to_delete:
                    delete_target(t["id"])

        elif choice == "3":
            targets = list_targets()
            if not targets:
                print("  [!] No targets saved.")
            else:
                print("\n  Saved targets:")
                for t in targets:
                    print(f"    [{t['id']}] {t['host']}  type={t['type']}  added={t['added_at']}")

        elif choice == "4":
            targets = list_targets()
            if not targets:
                print("  [!] No targets saved.")
                continue
            t = single_select(list(targets), lambda t: t["host"], title="Show Subdomains")
            if t:
                list_subdomains(t["id"])

        elif choice == "0":
            break


def dirsearch_menu():
    while True:
        print("""
  --- Dirsearch ---
  [1] Run scan
  [2] Query results (all targets)
  [3] Query results (pick target)
  [4] List all scans
  [0] Back
""")
        choice = input("  > ").strip()

        if choice == "1":
            dirsearch_scan()

        elif choice == "2":
            query_menu()

        elif choice == "3":
            targets = list_targets()
            if not targets:
                print("  [!] No targets saved.")
                continue
            t = single_select(list(targets), lambda t: t["host"], title="Query Results For")
            if t:
                query_menu(target_id=t["id"])

        elif choice == "4":
            _list_scans()

        elif choice == "0":
            break


def subfinder_menu():
    while True:
        print("""
  --- Subfinder ---
  [1] Run scan
  [2] Show subdomains of a target
  [0] Back
""")
        choice = input("  > ").strip()

        if choice == "1":
            subfinder_scan()

        elif choice == "2":
            targets = list_targets()
            if not targets:
                print("  [!] No targets saved.")
                continue
            t = single_select(list(targets), lambda t: t["host"], title="Show Subdomains")
            if t:
                list_subdomains(t["id"])

        elif choice == "0":
            break


def main_menu():
    print_banner()
    while True:
        print("""
  --- Main Menu ---
  [1] Targets
  [2] Dirsearch
  [3] Subfinder
  [0] Exit
""")
        choice = input("  > ").strip()

        if choice == "1":
            target_menu()
        elif choice == "2":
            dirsearch_menu()
        elif choice == "3":
            subfinder_menu()
        elif choice == "0":
            print("\n  Bye.\n")
            break


if __name__ == "__main__":
    init_db()
    main_menu()
