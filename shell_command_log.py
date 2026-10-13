"""Print subprocess argv as PowerShell-style continuations before it runs."""
import subprocess


def _is_option_token(s):
    if not s:
        return False
    if s.startswith("--"):
        return True
    if s.startswith("-") and len(s) >= 2:
        return True
    if len(s) >= 2 and s.startswith("/") and s[1].isalpha():
        return True
    return False


def _argv_to_segments(argv):
    """Split argv into display segments (option+value paired when applicable)."""
    if not argv:
        return []
    segments = [argv[0]]
    i = 1
    while i < len(argv):
        a = argv[i]
        if (
            i + 1 < len(argv)
            and _is_option_token(a)
            and not _is_option_token(argv[i + 1])
        ):
            segments.append([a, argv[i + 1]])
            i += 2
        else:
            segments.append(a)
            i += 1
    return segments


def log_next_shell_command(argv):
    """Log the command as multiline PowerShell (` backtick continuation), like connect-cache docstrings.

    Options that take a value are kept on one line with their value; other args get one line each.
    Quoting follows Windows rules via list2cmdline per segment.
    """
    print("\n  ▶ Next command:")
    if not argv:
        print("  (empty)\n")
        return

    cont = " `"
    segments = _argv_to_segments(argv)
    indent_cont = "      "

    for j, seg in enumerate(segments):
        if isinstance(seg, list):
            line = subprocess.list2cmdline(seg)
        else:
            line = subprocess.list2cmdline([seg])
        is_last = j == len(segments) - 1
        if j == 0:
            prefix = "  "
        else:
            prefix = indent_cont
        if is_last:
            print(f"{prefix}{line}")
        else:
            print(f"{prefix}{line}{cont}")
    print()
