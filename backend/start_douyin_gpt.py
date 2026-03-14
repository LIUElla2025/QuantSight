"""Streamlit 启动入口 — 解决相对 import 问题

用法: cd backend && streamlit run start_douyin_gpt.py
或者: cd backend && python -m douyin_gpt
"""
import sys
from pathlib import Path

# 将 backend 目录加入 Python 路径，使 douyin_gpt 包可被 import
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# 现在可以用绝对 import 了
from douyin_gpt.app import main

main()
