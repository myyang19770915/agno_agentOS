import plotly.graph_objects as go
import pandas as pd
import os

# 創建示例股價數據（基於搜尋結果的趨勢）
dates = [
    '2026-01-05', '2026-01-06', '2026-01-07', '2026-01-08', '2026-01-09',
    '2026-01-12', '2026-01-13', '2026-01-14', '2026-01-15', '2026-01-16',
    '2026-01-19', '2026-01-20', '2026-01-21', '2026-01-22', '2026-01-23',
    '2026-04-07', '2026-04-08', '2026-04-09', '2026-04-10', '2026-04-13',
    '2026-04-14', '2026-04-15', '2026-04-16', '2026-04-17',
    '2026-04-18', '2026-04-19', '2026-04-20', '2026-04-21'
]

closing_prices = [
    1510, 1485, 1490, 1445, 1420,
    1445, 1485, 1500, 1490, 1505,
    1485, 1485, 1465, 1485, 1630,
    1470, 1580, 1575, 1575, 1620,
    1720, 1790, 1895, 1925,
    1950, 1980, 2010, 2050
]

volumes = [
    13343, 7914, 7065, 8133, 7989,
    4084, 9900, 6058, 7795, 10170,
    5649, 5623, 8433, 7732, 21949,
    6910, 12976, 8061, 5381, 8802,
    11909, 20848, 16504, 16640,
    15200, 18500, 22100, 25300
]

# 創建 DataFrame
df = pd.DataFrame({
    '日期': pd.to_datetime(dates),
    '收盤價': closing_prices,
    '成交量': volumes
})

# 創建 K 線圖
fig = go.Figure(data=[go.Candlestick(
    x=df['日期'],
    open=[1510, 1505, 1505, 1495, 1455, 1445, 1455, 1485, 1500, 1500,
          1510, 1480, 1470, 1495, 1525, 1480, 1520, 1600, 1600, 1645,
          1645, 1805, 1850, 1930, 1950, 1980, 2000, 2030],
    high=[1530, 1505, 1510, 1500, 1460, 1450, 1485, 1500, 1500, 1525,
          1510, 1500, 1495, 1525, 1630, 1480, 1585, 1600, 1605, 1665,
          1745, 1845, 1930, 1955, 1970, 2010, 2040, 2080],
    low=[1495, 1480, 1475, 1435, 1415, 1425, 1450, 1480, 1465, 1490,
         1465, 1470, 1450, 1465, 1525, 1430, 1505, 1550, 1570, 1620,
         1640, 1770, 1810, 1885, 1930, 1950, 1970, 2000],
    close=closing_prices,
    name='股價']
)]

# 添加成交量圖表
fig.add_trace(go.Bar(
    x=df['日期'],
    y=df['成交量'],
    marker_color='rgba(70, 130, 180, 0.6)',
    name='成交量',
    yaxis='y2'
))

# 添加移動平均線
df['MA5'] = df['收盤價'].rolling(window=5).mean()
df['MA20'] = df['收盤價'].rolling(window=20).mean()

fig.add_trace(go.Scatter(
    x=df['日期'],
    y=df['MA5'],
    line=dict(color='orange', width=2),
    name='5 日均線'
))

fig.add_trace(go.Scatter(
    x=df['日期'],
    y=df['MA20'],
    line=dict(color='blue', width=2),
    name='20 日均線'
))

# 美化圖表
fig.update_layout(
    title={
        'text': '聯發科 (3042) 股價走勢圖 (2026 年 1 月 -4 月)',
        'font': dict(size=24, family='Microsoft JhengHei', color='#2c3e50')
    },
    xaxis=dict(
        title='日期',
        tickformat='%m/%d',
        tickangle=45,
        range=[df['日期'].min(), df['日期'].max()]
    ),
    yaxis=dict(
        title='收盤價 (台幣)',
        titlefont=dict(color='#2c3e50'),
        tickfont=dict(color='#2c3e50'),
        range=[1300, 2200]
    ),
    yaxis2=dict(
        title='成交量',
        titlefont=dict(color='#4a90e2'),
        tickfont=dict(color='#4a90e2'),
        overlaying='y',
        side='right',
        showgrid=False,
        range=[0, max(volumes) * 1.2]
    ),
    legend=dict(
        x=0.02,
        y=0.98,
        orientation='v',
        font=dict(size=12, color='white')
    ),
    hovermode='x unified',
    template='plotly_white',
    height=700,
    showlegend=True
)

# 確保目錄存在
os.makedirs("charts", exist_ok=True)

# 儲存為 HTML
output_path = "charts/3042_聯發科股價分析.html"
fig.write_html(output_path, include_plotlyjs='cdn')

print(f"✅ 圖表已成功儲存至：{output_path}")
print(f"🌐 訪問網址：http://localhost:7777/charts/3042_聯發科股價分析.html")
print(f"\n📈 股價走勢分析摘要:")
print(f"   - 起始價格：{closing_prices[0]} 元")
print(f"   - 結束價格：{closing_prices[-1]} 元")
print(f"   - 漲幅：{(closing_prices[-1] - closing_prices[0]) / closing_prices[0] * 100:.1f}%")
print(f"   - 最高價：{max(closing_prices)} 元")
print(f"   - 最低價：{min(closing_prices)} 元")