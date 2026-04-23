import sys
import tty
import termios


def _get_key():
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
        if ch == "\x1b":
            ch2 = sys.stdin.read(1)
            ch3 = sys.stdin.read(1)
            return ch + ch2 + ch3
        return ch
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def single_select(items, label_fn, title="Select item"):
    """
    Navigate with arrow keys, Enter to confirm selection, q/Ctrl+C to cancel.
    Returns selected item or None if cancelled.
    """
    if not items:
        return None

    cursor = 0
    first_draw = True

    def draw():
        nonlocal first_draw
        lines = []
        lines.append(f"  {title}")
        lines.append("  ↑↓ navigate   Enter select   q cancel")
        lines.append("")
        for i, item in enumerate(items):
            arrow = ">" if i == cursor else " "
            lines.append(f"  {arrow} {label_fn(item)}")
        lines.append("")

        if not first_draw:
            print(f"\033[{len(lines)}A", end="")
        first_draw = False

        for line in lines:
            print(f"\033[2K{line}")

    while True:
        draw()
        key = _get_key()

        if key == "\x1b[A":  # up
            cursor = max(0, cursor - 1)
        elif key == "\x1b[B":  # down
            cursor = min(len(items) - 1, cursor + 1)
        elif key in ("\r", "\n"):  # enter
            print()
            return items[cursor]
        elif key in ("q", "\x03"):  # q or ctrl+c
            print()
            return None


def multi_select(items, label_fn, title="Select items"):
    """
    Navigate with arrow keys, Space to toggle, Enter to confirm, q/Ctrl+C to cancel.
    Returns list of selected items, empty list if cancelled.
    """
    if not items:
        return []

    selected = set()
    cursor = 0
    first_draw = True

    def draw():
        nonlocal first_draw
        lines = []
        lines.append(f"  {title}")
        lines.append("  ↑↓ navigate   Space select   Enter confirm   q cancel")
        lines.append("")
        for i, item in enumerate(items):
            marker = "[X]" if i in selected else "[ ]"
            arrow = ">" if i == cursor else " "
            lines.append(f"  {arrow} {marker} {label_fn(item)}")
        lines.append("")
        lines.append(f"  Selected: {len(selected)}")

        if not first_draw:
            print(f"\033[{len(lines)}A", end="")
        first_draw = False

        for line in lines:
            print(f"\033[2K{line}")

    while True:
        draw()
        key = _get_key()

        if key == "\x1b[A":  # up
            cursor = max(0, cursor - 1)
        elif key == "\x1b[B":  # down
            cursor = min(len(items) - 1, cursor + 1)
        elif key == " ":  # space
            if cursor in selected:
                selected.discard(cursor)
            else:
                selected.add(cursor)
        elif key in ("\r", "\n"):  # enter
            print()
            return [items[i] for i in sorted(selected)]
        elif key in ("q", "\x03"):  # q or ctrl+c
            print()
            return []
