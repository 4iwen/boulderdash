import subprocess
import sys


def test_pylint_runs_clean():
    disabled = [
        "all",
        "C0301", # long lines
        "C0103", # short names
    ]

    enabled = [
        "trailing-whitespace",
        "wrong-import-order",
        "multiple-imports",
        "ungrouped-imports",
    ]

    cmd = [
        sys.executable,
        "-m",
        "pylint",
        "-sn",
        f"--disable={','.join(disabled)}",
        f"--enable={','.join(enabled)}",
        "game",
        "main.py",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)

    if result.returncode != 0:
        output = (result.stdout + "\n" + result.stderr).strip()
        raise AssertionError(output)
