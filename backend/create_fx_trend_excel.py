import os
import traceback
from datetime import datetime

try:
    # ===== 近一周 USD/TWD 每日匯率數據 =====
    fx_data = [
        {"date": datetime(2026, 6, 1), "day": "週一", "usd_twd": 31.379, "twd_usd": 0.031874},
        {"date": datetime(2026, 6, 2), "day": "週二", "usd_twd": 31.514, "twd_usd": 0.031737},
        {"date": datetime(2026, 6, 3), "day": "週三", "usd_twd": 31.365, "twd_usd": 0.031888},
        {"date": datetime(2026, 6, 4), "day": "週四", "usd_twd": 31.378, "twd_usd": 0.031875},
        {"date": datetime(2026, 6, 5), "day": "週五", "usd_twd": 31.439, "twd_usd": 0.031813},
    ]

    # ===== 計算統計數據 =====
    usd_twd_values = [d["usd_twd"] for d in fx_data]
    twd_usd_values = [d["twd_usd"] for d in fx_data]
    usd_twd_high = max(usd_twd_values)
    usd_twd_low = min(usd_twd_values)
    usd_twd_avg = sum(usd_twd_values) / len(usd_twd_values)
    usd_twd_change = usd_twd_values[-1] - usd_twd_values[0]
    usd_twd_pct_change = (usd_twd_change / usd_twd_values[0]) * 100

    # ===== 安裝 xlsxwriter =====
    import subprocess
    subprocess.check_call(['pip', 'install', 'xlsxwriter'])
    import xlsxwriter

    # ===== 建立 Excel 檔案 =====
    os.makedirs('downloads', exist_ok=True)
    output_path = 'downloads/USD_TWD_Trend_20260605.xlsx'
    workbook = xlsxwriter.Workbook(output_path)

    # 定義樣式
    header_format = workbook.add_format({
        'bold': True,
        'font_color': 'white',
        'bg_color': '#1F4E79',
        'border': 1,
        'align': 'center',
        'valign': 'vcenter',
        'font_size': 11,
    })

    title_format = workbook.add_format({
        'bold': True,
        'font_color': '#1F4E79',
        'font_size': 14,
        'align': 'left',
    })

    data_format = workbook.add_format({
        'border': 1,
        'align': 'center',
        'valign': 'vcenter',
        'font_size': 10,
    })

    format_header = workbook.add_format({
        'bold': True,
        'bg_color': '#D6E4F0',
        'border': 1,
        'align': 'center',
        'valign': 'vcenter',
        'font_color': '#1F4E79',
        'font_size': 10,
    })

    # ========================================
    # Sheet 1: 趨勢圖表
    # ========================================
    ws1 = workbook.add_worksheet('USD/TWD 趨勢圖')
    ws1.set_column('A:A', 8)
    ws1.set_column('B:B', 15)
    ws1.set_column('C:C', 15)

    # 標題
    ws1.merge_range('A1:C1', '台幣 (TWD) 兌美元 (USD) 近一周匯率趨勢 (2026/06/01 - 2026/06/05)')
    ws1['A1'] = title_format

    # 資料列
    ws1.write('A3', '日期')
    ws1.write('B3', 'USD/TWD')
    ws1.write('C3', 'TWD/USD')
    for fmt in [ws1['A3'], ws1['B3'], ws1['C3']]:
        fmt.apply(header_format)

    for i, d in enumerate(fx_data, 4):
        ws1.write(i, 0, d["date"].strftime('%Y/%m/%d'), data_format)
        ws1.write(i, 1, d["usd_twd"], workbook.add_format({'border': 1, 'num_format': '0.000', 'align': 'center'}))
        ws1.write(i, 2, d["twd_usd"], workbook.add_format({'border': 1, 'num_format': '0.0000', 'align': 'center'}))

    # 建立折線圖 (USD/TWD)
    chart = workbook.add_chart({'type': 'line'})
    chart.set_title({'name': 'USD/TWD 近一周匯率走勢', 'name_font': {'size': 12, 'bold': True}})
    chart.set_x_axis({'name': '日期', 'name_font': {'size': 10}})
    chart.set_y_axis({'name': 'USD/TWD', 'name_font': {'size': 10}})
    chart.set_style(1)
    chart.add_series({
        'name': 'USD/TWD',
        'categories': f"='USD/TWD 趨勢圖'!$A$4:$A$8",
        'values': f"='USD/TWD 趨勢圖'!$B$4:$B$8",
        'line': {'color': '#1F4E79', 'width': 2},
        'marker': {'type': 'circle', 'size': 6, 'fill': {'color': '#1F4E79'}},
        'data_label': {'value': True, 'num_format': '0.000'},
    })

    chart.set_legend({'position': 'bottom'})
    chart.set_size({'width': 700, 'height': 350})

    ws1.insert_chart('A11', chart, {'x_scale': 1.5, 'y_scale': 1.5})

    # ========================================
    # Sheet 2: 匯率趨勢表
    # ========================================
    ws2 = workbook.add_worksheet('匯率趨勢表')
    ws2.set_column('A:A', 25)
    ws2.set_column('B:B', 18)
    ws2.set_column('C:C', 18)
    ws2.set_column('D:D', 15)
    ws2.set_column('E:E', 18)

    ws2.merge_range('A1:E1', '近一周 USD/TWD 匯率趨勢表 (2026/06/01 - 2026/06/05)')
    ws2['A1'] = title_format

    ws2.write('A3', '指標')
    ws2.write('B3', '數值')
    ws2.write('C3', '說明')
    ws2.write('D3', '')
    ws2.write('E3', '')

    for fmt in [ws2['A3'], ws2['B3'], ws2['C3']]:
        fmt.apply(header_format)

    stats = [
        ["📅 數據期間", "2026/06/01 ~ 2026/06/05", "近 5 個交易日"],
        ["", "", ""],
        ["最高匯率 (USD/TWD)", usd_twd_high, "出現在 06/02 (週二)"],
        ["最低匯率 (USD/TWD)", usd_twd_low, "出現在 06/03 (週三)"],
        ["平均匯率 (USD/TWD)", round(usd_twd_avg, 3), "近一周平均水平"],
        ["匯率變化", f"{usd_twd_change:+.3f}", f"{usd_twd_pct_change:+.2f}%"],
        ["", "", ""],
        ["📊 每日明細", "", ""],
    ]

    for i, row in enumerate(stats):
        for j, val in enumerate(row):
            cell = ws2.cell(row=4 + i, column=j + 1, value=val)
            if i == 0:
                cell.apply(format_header)
            elif i in [5, 9]:
                cell.apply(header_format)
            else:
                cell.apply(data_format)

    # 寫每日明細
    for i, d in enumerate(fx_data):
        row_num = 14 + i
        ws2.cell(row=row_num, column=1, value=d["date"].strftime('%Y/%m/%d')).apply(data_format)
        ws2.cell(row=row_num, column=2, value=d["day"]).apply(data_format)
        ws2.cell(row=row_num, column=3, value=d["usd_twd"]).apply(data_format)
        ws2.cell(row=row_num, column=4, value=d["twd_usd"]).apply(data_format)
        # 計算每日變化
        if i == 0:
            ws2.cell(row=row_num, column=5, value="-").apply(data_format)
        else:
            change = d["usd_twd"] - fx_data[i-1]["usd_twd"]
            pct = (change / fx_data[i-1]["usd_twd"]) * 100
            ws2.cell(row=row_num, column=5, value=f"{change:+.3f} ({pct:+.2f}%)").apply(data_format)

    # ========================================
    # Sheet 3: TWD/USD 趨勢圖
    # ========================================
    ws3 = workbook.add_worksheet('TWD/USD 趨勢圖')
    ws3.set_column('A:A', 8)
    ws3.set_column('B:B', 15)
    ws3.set_column('C:C', 15)

    ws3.merge_range('A1:C1', 'TWD/USD 近一周匯率趨勢 (2026/06/01 - 2026/06/05)')
    ws3['A1'] = title_format

    ws3.write('A3', '日期')
    ws3.write('B3', 'USD/TWD')
    ws3.write('C3', 'TWD/USD')
    for fmt in [ws3['A3'], ws3['B3'], ws3['C3']]:
        fmt.apply(header_format)

    for i, d in enumerate(fx_data, 4):
        ws3.write(i, 0, d["date"].strftime('%Y/%m/%d'), data_format)
        ws3.write(i, 1, d["usd_twd"], workbook.add_format({'border': 1, 'num_format': '0.000', 'align': 'center'}))
        ws3.write(i, 2, d["twd_usd"], workbook.add_format({'border': 1, 'num_format': '0.0000', 'align': 'center'}))

    # 建立折線圖 (TWD/USD)
    chart2 = workbook.add_chart({'type': 'line'})
    chart2.set_title({'name': 'TWD/USD 近一周匯率走勢', 'name_font': {'size': 12, 'bold': True}})
    chart2.set_x_axis({'name': '日期', 'name_font': {'size': 10}})
    chart2.set_y_axis({'name': 'TWD/USD', 'name_font': {'size': 10}})
    chart2.set_style(2)
    chart2.add_series({
        'name': 'TWD/USD',
        'categories': f"='TWD/USD 趨勢圖'!$A$4:$A$8",
        'values': f"='TWD/USD 趨勢圖'!$C$4:$C$8",
        'line': {'color': 'E74C3C', 'width': 2},
        'marker': {'type': 'diamond', 'size': 6, 'fill': {'color': 'E74C3C'}},
        'data_label': {'value': True, 'num_format': '0.0000'},
    })
    chart2.set_legend({'position': 'bottom'})
    chart2.set_size({'width': 700, 'height': 350})
    ws3.insert_chart('A11', chart2, {'x_scale': 1.5, 'y_scale': 1.5})

    # ===== 儲存檔案 =====
    workbook.close()

    # 驗證檔案
    exists = os.path.exists(output_path)
    fsize = os.path.getsize(output_path) if exists else 0

    print("=" * 60)
    print("✅ Excel 檔案產生成功！")
    print("=" * 60)
    print(f"📁 路徑       : {output_path}")
    print(f"📊 檔案大小   : {fsize:,} bytes ({fsize/1024:.1f} KB)")
    print(f"✅ 檔案存在   : {exists}")
    print(f"📋 工作表數量 : {3}")
    print(f"📋 工作表列表 : 趨勢圖 | 匯率趨勢表 | TWD/USD 趨勢圖")
    print()
    print("📊 近一周 USD/TWD 匯率摘要:")
    print(f"   最高 : {usd_twd_high:.3f} (06/02 週二)")
    print(f"   最低 : {usd_twd_low:.3f} (06/03 週三)")
    print(f"   平均 : {usd_twd_avg:.3f}")
    print(f"   變化 : {usd_twd_change:+.3f} ({usd_twd_pct_change:+.2f}%)")
    print()
    print("📅 每日明細:")
    for d in fx_data:
        print(f"   {d['date'].strftime('%Y/%m/%d')} ({d['day']}): USD/TWD = {d['usd_twd']:.3f}, TWD/USD = {d['twd_usd']:.4f}")
    print("=" * 60)
    print("🎉 下載連結已準備就緒！")

    result = "SUCCESS"

except Exception as e:
    print(f"❌ 錯誤: {e}")
    print(traceback.format_exc())
    result = "FAILED"