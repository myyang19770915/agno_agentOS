"""
tests/conftest.py — Pytest 共用 fixture 與設定
"""
import sys
from pathlib import Path

# 確保可 import app 套件
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
