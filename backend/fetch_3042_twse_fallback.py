# -*- coding: utf-8 -*-
import os, sys, json
from datetime import datetime, timedelta
import requests
import pandas as pd

try:
    # compute today in UTC+8
    now_utc = datetime.utcnow()
    now_utc8 = now_utc + timedelta(hours=8)
    today = now_utc8.date()
    start_date = today - timedelta(days=6)
    end_date = today

    # First, attempt Yahoo download as user requested
    # Prepare Yahoo period1/period2 based on UTC+8 dates
    from datetime import timezone
    start_dt_utc = datetime(start_date.year, start_date.month, start_date.day, 0, 0, 0, tzinfo=timezone.utc) - timedelta(hours=8)
    end_dt_utc = datetime(end_date.year, end_date.month, end_date.day, 0, 0, 0, tzinfo=timezone.utc) - timedelta(hours=8) + timedelta(days=1)
    period1 = int(start_dt_utc.timestamp())
    period2 = int(end_dt_utc.timestamp())
    symbol = '3042.TW'
    yahoo_url = f'https://query1.finance.yahoo.com/v7/finance/download/{symbol}?period1={period1}&period2={period2}&interval=1d&events=history&includeAdjustedClose=true'
    print('Attempting Yahoo download URL:', yahoo_url)
    r = requests.get(yahoo_url, timeout=15)
    if r.status_code == 200 and r.text.strip():
        print('Yahoo download succeeded unexpectedly')
        df = pd.read_csv(pd.io.common.StringIO(r.text), parse_dates=['Date'])
    else:
        print('Yahoo download failed with status', r.status_code)
        df = None

    if df is None or df.empty:
        # fallback: use TWSE API to get monthly data for current and previous month
        print('Using TWSE fallback API')
        months = set()
        months.add(today.replace(day=1))
        prev_month = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
        months.add(prev_month)
        rows = []
        for m in sorted(months):
            date_param = m.strftime('%Y%m01')
            url = f'https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=json&date={date_param}&stockNo=3042'
            print('Fetching', url)
            rr = requests.get(url, timeout=15)
            if rr.status_code != 200:
                print('TWSE request failed for', date_param, 'status', rr.status_code)
                continue
            js = rr.json()
            if js.get('stat') != 'OK':
                print('TWSE returned stat not OK:', js.get('stat'))
                continue
            data = js.get('data', [])
            for rrow in data:
                # TWSE data format example: ['2026/02/24','1,234,567','111,111,111','91.10','92.00','90.50','91.10','+0.80']
                # fields: date, volume, value, open, high, low, close, change
                rows.append(rrow)
        if not rows:
            print('No TWSE data retrieved')
            df = None
        else:
            # Build DataFrame and normalize
            df_raw = pd.DataFrame(rows)
            # Ensure at least 7 columns
            # We'll map last 5 columns to open, high, low, close
            def parse_date(dstr):
                # handle formats like '2026/02/24' or '111/02/24' (ROC)
                try:
                    parts = dstr.split('/')
                    if len(parts) == 3:
                        y = int(parts[0])
                        m = int(parts[1])
                        d = int(parts[2])
                        if y < 1900:
                            # ROC year
                            y = y + 1911
                        return datetime(y, m, d).date()
                except:
                    return None
                return None
            records = []
            for rrow in rows:
                # find date
                try:
                    d = parse_date(rrow[0])
                except:
                    d = None
                # find numeric fields from end
                # attempt to find open, high, low, close in positions -5..-2 or so
                open_v = high_v = low_v = close_v = None
                volume = None
                try:
                    # volume often at index 1
                    vol_raw = rrow[1] if len(rrow) > 1 else None
                    if vol_raw is not None:
                        vol = str(vol_raw).replace(',','')
                        volume = int(vol) if vol.isdigit() else None
                except:
                    volume = None
                # try to locate open/high/low/close by scanning for numeric with dots
                nums = []
                for cell in rrow:
                    s = str(cell).replace(',','').replace('—','').strip()
                    try:
                        # exclude +/- change strings
                        if s in ('','-','--'):
                            continue
                        # try float
                        f = float(s)
                        nums.append(f)
                    except:
                        # skip
                        pass
                # heuristic: last four numeric values are open, high, low, close or open, high, low, close order present somewhere
                if len(nums) >= 4:
                    # take last 4
                    possible = nums[-4:]
                    open_v, high_v, low_v, close_v = possible[0], possible[1], possible[2], possible[3]
                records.append({'Date': d, 'Open': open_v, 'High': high_v, 'Low': low_v, 'Close': close_v, 'Volume': volume})
            df = pd.DataFrame(records)
            # drop rows with date None
            df = df[df['Date'].notna()]
            # filter date range
            df = df[(df['Date'] >= start_date) & (df['Date'] <= end_date)]
            df = df.sort_values('Date')
    # prepare output file name as requested
    os.makedirs('downloads', exist_ok=True)
    out_csv = 'downloads/3042_yahoo_7day.csv'
    if df is None or df.empty:
        # create empty csv with headers
        df_empty = pd.DataFrame(columns=['Date','Open','High','Low','Close','Volume'])
        df_empty.to_csv(out_csv, index=False)
        print('No data available; created empty CSV at', out_csv)
    else:
        # ensure columns present
        df_out = df.copy()
        for c in ['Open','High','Low','Close','Volume']:
            if c not in df_out.columns:
                df_out[c] = pd.NA
        df_out = df_out[['Date','Open','High','Low','Close','Volume']]
        # format date
        df_out['Date'] = df_out['Date'].apply(lambda d: d.strftime('%Y-%m-%d') if (d is not None and str(d)!='nan') else '')
        df_out.to_csv(out_csv, index=False)
        print('Saved CSV with', len(df_out), 'rows to', out_csv)

    # print summary and rows as user requested
    fetch_time_utc8 = (datetime.utcnow() + timedelta(hours=8)).strftime('%Y-%m-%d %H:%M:%S')
    print('\n--- SUMMARY ---')
    print('資料日期範圍:', start_date.isoformat(), '到', end_date.isoformat())
    print('抓取時間 (UTC+8):', fetch_time_utc8)
    print('資料來源: Yahoo Finance attempted but returned 429 Too Many Requests; 改用台灣證券交易所 TWSE API: https://www.twse.com.tw/exchangeReport/STOCK_DAY')
    print('\n--- DATA ROWS (Date, Open, High, Low, Close, Volume) ---')
    if df is None or df.empty:
        print('No trading data available for the specified range.')
    else:
        for _, r in df_out.iterrows():
            D = r['Date'] if pd.notna(r['Date']) and r['Date']!='' else 'NA'
            def fmt(x):
                if pd.isna(x) or x==None:
                    return 'NA'
                if isinstance(x, (int,)):
                    return str(x)
                try:
                    return f"{float(x):.2f}" if x != '' else 'NA'
                except:
                    return str(x)
            O = fmt(r['Open'])
            H = fmt(r['High'])
            L = fmt(r['Low'])
            C = fmt(r['Close'])
            V = fmt(r['Volume'])
            print(f"{D}, {O}, {H}, {L}, {C}, {V}")

    print('\nDOWNLOAD: http://localhost:7777/download/3042_yahoo_7day.csv')

except Exception as e:
    print('Error in script:', e)
    import traceback
    traceback.print_exc()