# FlashEnum

**fastest way to enumerate**

A terminal-based penetration testing enumeration tool. Manage targets, discover subdomains, brute-force directories — all from one interface with persistent SQLite storage.

---

## Requirements

### Build dependency
```bash
pip3 install pyinstaller
```

### External Tools

| Tool | Purpose | Install |
|------|---------|---------|
| [dirsearch](https://github.com/maurosoria/dirsearch) | Directory brute-force | see below |
| [subfinder](https://github.com/projectdiscovery/subfinder) | Subdomain discovery | see below |

#### Install dirsearch
```bash
git clone https://github.com/maurosoria/dirsearch.git
cd dirsearch
pip3 install -r requirements.txt
sudo ln -s $(pwd)/dirsearch.py /usr/local/bin/dirsearch
```

#### Install subfinder
```bash
go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest
sudo mv ~/go/bin/subfinder /usr/local/bin/
```
> Requires Go — https://go.dev/dl/

---

## Build

```bash
git clone https://github.com/MammadovIzzat/FlashEnum.git
cd FlashEnum
make build
```

Binary will be at `dist/flashenum`.

#### Install system-wide (optional)
```bash
sudo make install
# runs as: flashenum
```

#### Clean build artifacts
```bash
make clean
```

---

## Features

### Target Management
- Add / delete targets (IP or domain) — auto-detected
- Persistent history in SQLite
- Arrow key navigation across the entire tool
- Multi-select delete (Space to toggle, Enter to confirm)

### Dirsearch Integration
- Run dirsearch against any saved target
- You control all flags — nothing forced
- Ctrl+C kills the scan immediately, then asks: restart with new options / save partial / discard
- All results saved to database per scan

#### Query System
```
show 200          show only status 200
hide 403          exclude 403 from view
url /admin        filter URLs containing /admin
scan 3            filter to scan #3
show all          reset filters and show everything
delete 403        delete all 403 results (with confirm)
delete url /tmp   delete results matching URL (with confirm)
delete scan 3     delete entire scan #3 (with confirm)
delete all        wipe everything (with confirm)
list scans        show all saved scans
```

### Subfinder Integration
- Discovers subdomains for a domain target
- Probes each subdomain for a live web app (HTTPS:443, HTTP:80, HTTPS:8443, HTTP:8080)
- Subdomains with a web app are auto-added to targets
- Results stored with status code and scheme

---

## Notes

- All data is stored in `~/.flash/enumtool.db` — created automatically on first run
- `dirsearch` and `subfinder` must be in your `PATH`
- Tested on Linux (Parrot OS / Kali)
