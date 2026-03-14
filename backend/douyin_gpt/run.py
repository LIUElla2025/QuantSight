"""启动脚本 — 从任意目录运行: python -m douyin_gpt"""
import subprocess
import sys
from pathlib import Path


def main():
    # 用 start_douyin_gpt.py 作为 Streamlit 入口，避免相对 import 问题
    entry = Path(__file__).resolve().parent.parent / "start_douyin_gpt.py"
    backend_dir = entry.parent

    subprocess.run(
        [
            sys.executable, "-m", "streamlit", "run",
            str(entry),
            "--server.headless", "true",
        ],
        cwd=str(backend_dir),
        check=True,
    )


if __name__ == "__main__":
    main()
