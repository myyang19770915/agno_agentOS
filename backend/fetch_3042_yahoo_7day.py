# -*- coding: utf-8 -*-
import os
import io
import sys
import traceback
from datetime import datetime, timedelta, timezone
import requests
import pandas as pd

try:
    # compute today in UTC+8
    now_utc = datetime.utcnow()
    now_utc8 = now_utc + timedelta(hours=8)
    today_utc8 = now_utc8.date()
    start_date = today_utc8 - timedelta(days=6)
    end_date = today_utc8

    # prepare Yahoo period1 and period2 in UTC (period1 = start 00:00 UTC of start_date, period2 = next day 00:00 UTC of end_date)
    # but start_date and end_date are in UTC+8; convert to UTC by subtracting 8 hours
    start_dt_utc = datetime(start_date.year, start_date.month, start_date.day, 0, 0, 0, tzinfo=timezone.utc) - timedelta(hours=8)
    end_dt_utc = datetime(end_date.year, end_date.month, end_date.day, 0, 0, 0, tzinfo=timezone.utc) - timedelta(hours=8) + timedelta(days=1)
    period1 = int(start_dt_utc.timestamp())
    period2 = int(end_dt_utc.timestamp())

    symbol = '3042.TW'
    url = f'https://query1.finance.yahoo.com/v7/finance/download/{symbol}?period1={period1}&period2={period2}&interval=1d&events=history&includeAdjustedClose=true'

    print('Fetching from URL:', url)
    resp = requests.get(url, timeout=20)
    df = None
    if resp.status_code == 200 and resp.text.strip():
        try:
            df = pd.read_csv(io.StringIO(resp.text), parse_dates=['Date'])
            print(f'Successfully downloaded CSV from Yahoo (rows={len(df)})')
        except Exception as e:
            print('Error parsing CSV from Yahoo:', e)
            traceback.print_exc()
            df = None
    else:
        print('Yahoo CSV download failed, status:', resp.status_code)

    if df is None or df.empty:
        # fallback to read HTML history page
        try:
            hist_url = f'https://finance.yahoo.com/quote/{symbol}/history?p={symbol}'
            print('Attempting HTML parse from:', hist_url)
            r2 = requests.get(hist_url, timeout=20)
            tables = pd.read_html(r2.text)
            print('Found', len(tables), 'tables in HTML')
            df = None
            for t in tables:
                if 'Date' in t.columns:
                    df = t.copy()
                    break
            if df is None:
                print('No table with Date column found in HTML')
            else:
                # rename Close* if present
                if 'Close*' in df.columns:
                    df = df.rename(columns={'Close*':'Close'})
                # drop rows where Close is NaN or contains 'Dividend'
                if 'Close' in df.columns:
                    df = df[df['Close'].notna()]
                # convert Date
                df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
                # numeric conversions
                for col in ['Open','High','Low','Close','Volume']:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col].astype(str).str.replace(',',''), errors='coerce')
                print('Parsed HTML table rows:', len(df))
        except Exception as e:
            print('HTML fallback failed:', e)
            traceback.print_exc()
            df = None

    # filter to start_date..end_date in UTC+8
    if df is None or df.empty:
        print('No data available from Yahoo for the specified range.')
    else:
        # Ensure Date column
        if 'Date' not in df.columns:
            print('No Date column in data; aborting.')
        else:
            # convert dates to date in UTC+8 context: treat Date as naive/local date and compare to start_date/end_date
            df['Date'] = pd.to_datetime(df['Date']).dt.tz_localize(None)
            df = df[(df['Date'].dt.date >= start_date) & (df['Date'].dt.date <= end_date)]
            # select columns
            cols = ['Date','Open','High','Low','Close','Volume']
            for c in cols:
                if c not in df.columns:
                    df[c] = pd.NA
            df = df[cols].sort_values('Date')

            # save CSV
            os.makedirs('downloads', exist_ok=True)
            out_csv = 'downloads/3042_yahoo_7day.csv'
            df.to_csv(out_csv, index=False, date_format='%Y-%m-%d')
            print('Saved CSV to', out_csv)

            # Print summary and rows in required format: Date, Open, High, Low, Close, Volume
            fetch_time_utc8 = (datetime.utcnow() + timedelta(hours=8)).strftime('%Y-%m-%d %H:%M:%S')
            print('\n--- SUMMARY ---')
            print('資料日期範圍:', start_date.isoformat(), '到', end_date.isoformat())
            print('抓取時間 (UTC+8):', fetch_time_utc8)
            print('資料來源: Yahoo Finance download URL / history page')
            print('\n--- DATA ROWS ---')
            # iterate rows
            for _, row in df.iterrows():
                d = row['Date'].date().isoformat() if pd.notna(row['Date']) else 'NA'
                def val(x):
                    if pd.isna(x):
                        return 'NA'
                    # for floats, format to 2 decimals except Volume
                    return (f"{int(x)}" if pd.api.types.is_integer_dtype(type(x)) or (isinstance(x, (int,)) ) else (f"{x:.2f}" if pd.notna(x) and isinstance(x, float) else str(x)))
                o = val(row['Open'])
                h = val(row['High'])
                l = val(row['Low'])
                c = val(row['Close'])
                v = val(row['Volume'])
                print(f"{d}, {o}, {h}, {l}, {c}, {v}")

            # final line with download link
            print('\nDOWNLOAD: http://localhost:7777/download/3042_yahoo_7day.csv')

except Exception as e:
    print('Unhandled error:', e)
    traceback.print_exc()

print('Done')