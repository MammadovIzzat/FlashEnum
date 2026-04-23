# FlashEnum

**fastest way to enumerate**

A terminal-based penetration testing enumeration tool. Manage targets, discover subdomains, brute-force directories — all from one interface with persistent SQLite storage.

---

## Requirements

### Python
- Python 3.8+
- No pip packages required — stdlib only

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
> Requires Go. Install Go from https://go.dev/dl/

---

## Installation

```bash
git clone https://github.com/MammadovIzzat/FlashEnum.git
cd FlashEnum
chmod +x flash.sh
```

---

## Run

```bash
./flash.sh
# or
python3 main.py
```

---

## Features

### Target Management
- Add / delete targets (IP or domain) — auto-detected
- Persistent history in SQLite
- Arrow key selection across the tool
- Multi-select delete

### Dirsearch Integration
- Run dirsearch against any saved target
- You control all flags — no presets forced
- Ctrl+C stops the scan immediately, asks: restart / save partial / discard
- All results saved to database per scan

#### Query System
```
show 200          show only status 200
hide 403          exclude 403 from view
url /admin        filter URLs containing /admin
scan 3            filter to scan #3
all               reset all filters
delete 403        delete all 403 results (with confirm)
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

- `enumtool.db` is created automatically on first run — keep it safe, it holds all your scan data
- dirsearch and subfinder must be in your `PATH`
- Tested on Linux (Parrot OS / Kali)
