#!/usr/bin/env python3
"""
將所有現有的 Plotly 圖表 HTML 從 inline bundle 模式轉換為 CDN 模式

問題背景：
  - 預設 fig.write_html() 會將整個 Plotly.js (~4.7MB) 內嵌進每個 HTML
  - 每次載入圖表 iframe 都需要下載 4.7MB
  - 改用 CDN 模式後，HTML 降至 ~60KB，Plotly.js 由瀏覽器快取

做法：
  - 偵測 HTML 中是否包含內嵌的 Plotly bundle（特徵字串）
  - 替換為 CDN <script> 標籤

腳本使用方式：
  cd /root/agno_agentOS/backend
  python convert_charts_to_cdn.py
"""

import os
import sys

CHARTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "charts")

# Plotly CDN 腳本標籤 (使用 esm.sh 的公共 CDN，或可換成 unpkg/cdnjs)
CDN_SCRIPT = '<script src="https://cdn.plot.ly/plotly-3.3.1.min.js" charset="utf-8"></script>'

PLOTLY_CONFIG_MARKER = '<script type="text/javascript">window.PlotlyConfig'
SCRIPT_OPEN = '<script type="text/javascript">'
SCRIPT_CLOSE = '</script>'

def convert_file(html_path: str) -> bool:
    """
    將單一 HTML 檔案從 inline bundle 轉為 CDN 模式。
    策略：用字串搜尋定位 PlotlyConfig script 和緊接的 bundle script，
    整塊替換為 CDN <script> 標籤。
    返回 True 表示已轉換，False 表示跳過。
    """
    with open(html_path, "r", encoding="utf-8") as f:
        content = f.read()

    orig_size = len(content)

    # 已是 CDN 模式（<script src="...cdn..."> 標籤存在），跳過
    if '<script src="https://cdn.plot.ly/' in content or '<script src="https://unpkg.com/plotly' in content:
        return False

    # 定位 PlotlyConfig script 起始位置
    cfg_start = content.find(PLOTLY_CONFIG_MARKER)
    if cfg_start == -1:
        return False  # 沒有 PlotlyConfig，格式不符

    # PlotlyConfig script 結束位置
    cfg_end = content.find(SCRIPT_CLOSE, cfg_start)
    if cfg_end == -1:
        return False
    cfg_end += len(SCRIPT_CLOSE)

    # 緊接著是 Plotly bundle script 的起始位置（允許中間有空白）
    bundle_start = content.find(SCRIPT_OPEN, cfg_end)
    if bundle_start == -1:
        return False

    # 驗證這個 script 確實是 Plotly bundle（包含 "plotly.js v"）
    bundle_check_end = min(bundle_start + 200, len(content))
    if "plotly.js v" not in content[bundle_start:bundle_check_end]:
        return False

    # 找 bundle script 的結束 </script>
    bundle_end = content.find(SCRIPT_CLOSE, bundle_start)
    if bundle_end == -1:
        return False
    bundle_end += len(SCRIPT_CLOSE)

    # 驗證刪除區間夠大（bundle 至少 4MB）
    removed_size = bundle_end - cfg_start
    if removed_size < 4_000_000:
        return False

    # 組合新內容：刪除 cfg_start ~ bundle_end，插入 CDN script
    new_content = content[:cfg_start] + CDN_SCRIPT + content[bundle_end:]
    new_size = len(new_content)
    saved = orig_size - new_size

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"  ✅ 已轉換: {orig_size/1024/1024:.2f} MB → {new_size/1024:.0f} KB  (節省 {saved/1024/1024:.2f} MB)")
    return True


def main():
    if not os.path.isdir(CHARTS_DIR):
        print(f"❌ charts 目錄不存在: {CHARTS_DIR}")
        sys.exit(1)

    html_files = [f for f in os.listdir(CHARTS_DIR) if f.endswith(".html")]
    if not html_files:
        print("⚠️  charts/ 目錄中沒有 HTML 檔案")
        return

    print(f"📂 掃描目錄: {CHARTS_DIR}")
    print(f"📊 找到 {len(html_files)} 個 HTML 圖表\n")

    converted = 0
    skipped = 0

    for fname in sorted(html_files):
        fpath = os.path.join(CHARTS_DIR, fname)
        size_mb = os.path.getsize(fpath) / 1024 / 1024
        print(f"  処理: {fname} ({size_mb:.2f} MB)")
        if convert_file(fpath):
            converted += 1
        else:
            print(f"  ⏭️ 跳過（已是 CDN 模式或格式不符）")
            skipped += 1

    print(f"\n✨ 完成！已轉換: {converted} 個，跳過: {skipped} 個")
    print(f"💡 後續新生成的圖表會直接使用 CDN，無需再次執行此腳本")


if __name__ == "__main__":
    main()
