import requests
import pandas as pd
from datetime import datetime
import json

print("正在獲取近一周台幣兌美元匯率數據...")

# 使用 Yahoo Finance API
url = "https://query1.finance.yahoo.com/v8/finance/chart/TWDUSD=X?range=7d&interval=1d"
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

response = requests.get(url, headers=headers, timeout=10)
result = response.json()

print(f"HTTP 狀態碼：{response.status_code}")
print(f"JSON keys: {result.keys()}")

if 'chart' in result and result['chart']['result']:
    chart_data = result['chart']['result'][0]
    timestamps = chart_data['timestamp']
    quotes = chart_data['indicators']['quote'][0]
    meta = chart_data['meta']
    
    print(f"\n✅ Yahoo Finance API 獲取成功！")
    print(f"貨幣：{meta['currency']}")
    print(f"當前價格：{meta['regularMarketPrice']}")
    
    # 構建數據框
    df_list = []
    for i, ts in enumerate(timestamps):
        dt = datetime.fromtimestamp(ts)
        df_list.append({
            '日期': dt.strftime('%Y-%m-%d'),
            '開盤': round(quotes['open'][i], 6) if quotes['open'][i] else None,
            '最高': round(quotes['high'][i], 6) if quotes['high'][i] else None,
            '最低': round(quotes['low'][i], 6) if quotes['low'][i] else None,
            '收盤': round(quotes['close'][i], 6) if quotes['close'][i] else None,
        })
    
    data = pd.DataFrame(df_list)
    print("\n✅ 數據：")
    print(data.to_string(index=False))
    print(f"\n數據筆數：{len(data)}")
    
    # 保存數據供後續使用
    data.to_csv('twd_usd_data.csv', index=False)
    print("\n✅ 數據已保存至 twd_usd_data.csv")
else:
    print("❌ Yahoo Finance API 無數據")
    data = None

print("\n✅ 數據獲取完成！")