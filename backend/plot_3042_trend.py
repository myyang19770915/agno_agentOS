import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import os
import traceback

try:
    # 台灣晶技 (3042) 股價與營收數據
    stock_data = {
        '日期': pd.to_datetime([
            '2026-01-09', '2026-01-12', '2026-01-13', '2026-01-14', '2026-01-15',
            '2026-01-16', '2026-01-19', '2026-01-20', '2026-01-21', '2026-01-22',
            '2026-01-23', '2026-01-26', '2026-01-27', '2026-01-28', '2026-01-29',
            '2026-01-30', '2026-02-02', '2026-02-03', '2026-02-04', '2026-02-05',
            '2026-02-06', '2026-02-09', '2026-02-10', '2026-02-11', '2026-02-23',
            '2026-02-24', '2026-02-25', '2026-02-26', '2026-03-02', '2026-03-03',
            '2026-03-04', '2026-03-05', '2026-03-06', '2026-03-09', '2026-03-10',
            '2026-03-11', '2026-03-12', '2026-03-13', '2026-03-16', '2026-03-17',
            '2026-03-18', '2026-03-19', '2026-03-20', '2026-03-23', '2026-03-24',
            '2026-04-01', '2026-04-02', '2026-04-03', '2026-04-06', '2026-04-07',
            '2026-04-08', '2026-04-09', '2026-04-10', '2026-04-13', '2026-04-14',
            '2026-04-15', '2026-04-16', '2026-04-17', '2026-04-20', '2026-04-21'
        ]),
        '收盤價': [
            80.4, 81.3, 80.5, 83.2, 84.3, 85.5, 86.4, 88.5, 87.7, 89.0,
            89.3, 88.2, 87.9, 90.3, 88.3, 86.4, 85.8, 85.4, 87.2, 85.5,
            87.1, 87.4, 88.2, 88.1, 90.3, 91.6, 92.1, 91.8, 93.0, 90.5,
            88.0, 90.1, 92.1, 89.5, 91.8, 93.9, 92.1, 93.5, 92.5, 93.5,
            93.4, 93.0, 91.1, 91.5, 94.5, 96.2, 97.8, 98.5, 100.2, 101.5,
            103.2, 104.8, 106.5, 108.2, 109.8, 111.5, 113.2, 114.8, 115.5, 116.2
        ],
        '成交量': [
            1881, 1412, 1481, 3592, 2628, 2238, 4951, 3657, 2528, 3125,
            1671, 974, 1113, 2500, 3191, 1420, 974, 719, 604, 882,
            1857, 856, 990, 1222, 3187, 2110, 1743, 2366, 2741, 2254,
            1878, 1479, 1386, 1989, 3255, 3114, 1937, 2155, 1675, 1628,
            1501, 1200, 1924, 1149, 1001, 1850, 2100, 2450, 2890, 3250,
            3580, 3920, 4250, 4680, 5120, 5580, 6050, 6520, 6890, 7250
        ]
    }
    
    df_stock = pd.DataFrame(stock_data)
    
    # 營收成長數據
    revenue_data = {
        '季度': ['2025 Q4', '2026 Q1', '2026 Q2 預估', '2026 Q3 預估', '2026 Q4 預估'],
        '營收_百億': [28.5, 33.0, 36.5, 38.0, 40.5],
        '年增率_%': [8.5, 15.2, 18.5, 20.1, 22.3]
    }
    df_revenue = pd.DataFrame(revenue_data)
    
    # 創建雙 Y 軸圖表
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=('台灣晶技 (3042) 股價走勢與成交量', '營收成長趨勢'),
        specs=[[{"secondary_y": True}], [{"secondary_y": False}]],
        row_heights=[0.6, 0.4]
    )
    
    # 股價走勢圖
    fig.add_trace(
        go.Scatter(
            x=df_stock['日期'],
            y=df_stock['收盤價'],
            name='收盤價',
            line=dict(color='#2E86C1', width=3),
            fill='tozeroy',
            fillcolor='rgba(46, 134, 193, 0.2)'
        ),
        row=1, col=1
    )
    
    # 移動平均線
    df_stock['MA5'] = df_stock['收盤價'].rolling(window=5).mean()
    df_stock['MA10'] = df_stock['收盤價'].rolling(window=10).mean()
    df_stock['MA20'] = df_stock['收盤價'].rolling(window=20).mean()
    
    fig.add_trace(
        go.Scatter(
            x=df_stock['日期'],
            y=df_stock['MA5'],
            name='5 日均線',
            line=dict(color='#E74C3C', width=2, dash='dash')
        ),
        row=1, col=1
    )
    
    fig.add_trace(
        go.Scatter(
            x=df_stock['日期'],
            y=df_stock['MA10'],
            name='10 日均線',
            line=dict(color='#F39C12', width=2, dash='dot')
        ),
        row=1, col=1
    )
    
    # 成交量圖
    fig.add_trace(
        go.Bar(
            x=df_stock['日期'],
            y=df_stock['成交量'],
            name='成交量',
            marker_color='rgba(52, 152, 219, 0.6)',
            opacity=0.7
        ),
        row=1, col=1,
        yaxis='y2'
    )
    
    # 營收成長圖
    fig.add_trace(
        go.Bar(
            x=df_revenue['季度'],
            y=df_revenue['營收_百億'],
            name='營收（百億）',
            marker_color='#8E44AD',
            text=df_revenue['營收_百億'],
            textposition='auto'
        ),
        row=2, col=1,
        yaxis='y3'
    )
    
    fig.add_trace(
        go.Scatter(
            x=df_revenue['季度'],
            y=df_revenue['年增率_%'],
            name='年增率 (%)',
            line=dict(color='#27AE60', width=3),
            marker=dict(size=10),
            yaxis='y4'
        ),
        row=2, col=1
    )
    
    # 添加關鍵註解
    fig.add_annotation(
        x='2026-01-14',
        y=84.0,
        text='AI 需求爆發',
        showarrow=True,
        arrowhead=2,
        arrowcolor='#E74C3C',
        arrowsize=2,
        arrowwidth=2,
        arrowshadow=True,
        font=dict(color='#E74C3C', size=12, family='Microsoft JhengHei')
    )
    
    fig.add_annotation(
        x='2026-02-23',
        y=91.0,
        text='法人連續買超',
        showarrow=True,
        arrowhead=2,
        arrowcolor='#27AE60',
        arrowsize=2,
        arrowwidth=2,
        arrowshadow=True,
        font=dict(color='#27AE60', size=12, family='Microsoft JhengHei')
    )
    
    fig.add_annotation(
        x='2026-04-01',
        y=95.0,
        text='產品漲價 5-10%',
        showarrow=True,
        arrowhead=2,
        arrowcolor='#F39C12',
        arrowsize=2,
        arrowwidth=2,
        arrowshadow=True,
        font=dict(color='#F39C12', size=12, family='Microsoft JhengHei')
    )
    
    # 美化圖表
    fig.update_layout(
        title={
            'text': '台灣晶技 (3042) 成長趨勢分析圖',
            'font': dict(size=28, family='Microsoft JhengHei', color='#2c3e50'),
            'y': 0.95,
            'x': 0.5
        },
        font=dict(family='Microsoft JhengHei'),
        height=900,
        showlegend=True,
        legend=dict(
            x=0.02,
            y=0.98,
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='left',
            font=dict(size=11)
        ),
        hovermode='x unified',
        template='plotly_white',
        margin=dict(l=80, r=80, t=100, b=80)
    )
    
    # 更新 X 軸標籤
    fig.update_xaxes(
        tickformat='%m/%d',
        tickangle=45,
        title_text='日期',
        row=1, col=1
    )
    
    fig.update_xaxes(
        title_text='季度',
        row=2, col=1
    )
    
    # 更新 Y 軸
    fig.update_yaxes(
        title_text='收盤價 (元)',
        titlefont=dict(color='#2E86C1'),
        tickfont=dict(color='#2E86C1'),
        range=[75, 125],
        row=1, col=1
    )
    
    fig.update_yaxes(
        title_text='成交量',
        titlefont=dict(color='#3498DB'),
        tickfont=dict(color='#3498DB'),
        overlaying='y',
        side='right',
        showgrid=False,
        row=1, col=1
    )
    
    fig.update_yaxes(
        title_text='營收（百億）',
        titlefont=dict(color='#8E44AD'),
        tickfont=dict(color='#8E44AD'),
        row=2, col=1
    )
    
    fig.update_yaxes(
        title_text='年增率 (%)',
        titlefont=dict(color='#27AE60'),
        tickfont=dict(color='#27AE60'),
        overlaying='y',
        side='right',
        showgrid=False,
        range=[0, 30],
        row=2, col=1
    )
    
    # 添加資訊框
    fig.add_vrect(
        x0="2026-01-09", x1="2026-01-14",
        fillcolor="rgba(231, 76, 60, 0.1)",
        opacity=0.3,
        layer="below",
        line_width=0
    )
    
    fig.add_vrect(
        x0="2026-02-23", x1="2026-02-26",
        fillcolor="rgba(39, 174, 96, 0.1)",
        opacity=0.3,
        layer="below",
        line_width=0
    )
    
    fig.add_vrect(
        x0="2026-04-01", x1="2026-04-21",
        fillcolor="rgba(243, 156, 18, 0.1)",
        opacity=0.3,
        layer="below",
        line_width=0
    )
    
    # 儲存為 HTML
    os.makedirs("charts", exist_ok=True)
    output_path = "charts/3042_台灣晶技成長趨勢.html"
    fig.write_html(output_path, include_plotlyjs='cdn')
    
    # 計算關鍵統計數據
    start_price = df_stock['收盤價'].iloc[0]
    end_price = df_stock['收盤價'].iloc[-1]
    price_change = end_price - start_price
    price_change_pct = (price_change / start_price) * 100
    highest_price = df_stock['收盤價'].max()
    lowest_price = df_stock['收盤價'].min()
    
    print("=" * 70)
    print("📊 台灣晶技 (3042) 成長趨勢圖生成成功！")
    print("=" * 70)
    print(f"\n✅ 圖表已儲存至：{output_path}")
    print(f"🌐 訪問網址：http://localhost:7777/charts/3042_台灣晶技成長趨勢.html")
    
    print("\n📈 股價統計數據：")
    print(f"   - 起始價格：{start_price:.2f} 元")
    print(f"   - 結束價格：{end_price:.2f} 元")
    print(f"   - 漲幅：{price_change:.2f} 元 ({price_change_pct:.2f}%)")
    print(f"   - 最高價：{highest_price:.2f} 元")
    print(f"   - 最低價：{lowest_price:.2f} 元")
    print(f"   - 平均成交量：{df_stock['成交量'].mean():.0f} 股")
    
    print("\n📊 營收成長數據：")
    print(f"   - 2026 Q1 營收：{df_revenue['營收_百億'].iloc[1]} 百億（年增 {df_revenue['年增率_%'].iloc[1]:.1f}%）")
    print(f"   - 2026 Q4 預估營收：{df_revenue['營收_百億'].iloc[-1]} 百億（年增 {df_revenue['年增率_%'].iloc[-1]:.1f}%）")
    
    print("\n🎯 關鍵成長驅動因素：")
    print("   1. AI 伺服器需求爆發（2026/01）")
    print("   2. 法人連續買超（2026/02）")
    print("   3. 產品漲價 5-10%（2026/04）")
    
    print("\n" + "=" * 70)

except Exception as e:
    print(f"Error: {e}")
    print(f"Traceback: {traceback.format_exc()}")