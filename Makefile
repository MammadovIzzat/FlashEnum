NAME    = flashenum
ENTRY   = main.py
DIST    = dist/$(NAME)

.PHONY: build clean install uninstall

build:
	@command -v pyinstaller >/dev/null 2>&1 || { echo "[!] pyinstaller not found. Run: pip3 install pyinstaller"; exit 1; }
	pyinstaller --onefile --name $(NAME) $(ENTRY)
	@echo ""
	@echo "[+] Binary ready: $(DIST)"

clean:
	rm -rf build dist __pycache__ *.spec

install: build
	@cp $(DIST) /usr/local/bin/$(NAME)
	@echo "[+] Installed: /usr/local/bin/$(NAME)"

uninstall:
	@rm -f /usr/local/bin/$(NAME)
	@echo "[+] Uninstalled."
