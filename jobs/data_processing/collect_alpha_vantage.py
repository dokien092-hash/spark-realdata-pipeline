#!/usr/bin/env python3
"""
================================================================================
Alpha Vantage Stock Data Collector
================================================================================
PRIMARY data source for daily stock collection.

Features:
  - 25 API calls/day limit (free tier)
  - Each call returns 100 days of data
  - Most stable and reliable source
  - Stores in stocks_daily_alphavantage table

Usage:
  Daily: --days_back 1
  Backfill: --days_back 60 --batch 1
  
Priority in stocks_daily_all view: #1 (highest)
================================================================================
"""

import requests
import psycopg2
from datetime import datetime, timedelta
import logging
import time
import pandas as pd
import argparse
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get API key from environment
ALPHA_VANTAGE_KEY = os.getenv('ALPHA_VANTAGE_KEY', 'demo')

class AlphaVantageCollector:
    def __init__(self):
        self.postgres_config = {
            'host': 'postgres',
            'database': 'realdata_warehouse',
            'user': 'postgres',
            'password': 'postgres'
        }
        
        # Top 15 stocks - Fast daily collection (~4 minutes)
        # For larger backfills, use --batch parameter
        self.stock_symbols = [
            # Tech Giants (5)
            'AAPL', 'GOOGL', 'MSFT', 'AMZN', 'NVDA',
            # Major ETFs (3)
            'SPY', 'QQQ', 'VTI',
            # Finance (3)
            'JPM', 'BAC', 'V',
            # Healthcare (2)
            'JNJ', 'UNH',
            # Others (2)
            'WMT', 'XOM'
        ]
    
    def create_connection(self):
        """Create PostgreSQL connection"""
        try:
            conn = psycopg2.connect(**self.postgres_config)
            return conn
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            return None
    
    def fetch_daily_data(self, symbol, retry=1):
        """
        Fetch daily data from Alpha Vantage với retry mechanism
        retry: Số lần thử lại (chỉ 1 lần để không làm chậm)
        """
        max_retries = retry
        for attempt in range(max_retries + 1):
            try:
                url = 'https://www.alphavantage.co/query'
                params = {
                    'function': 'TIME_SERIES_DAILY',
                    'symbol': symbol,
                    'outputsize': 'compact',  # Last 100 days
                    'apikey': ALPHA_VANTAGE_KEY
                }
                
                response = requests.get(url, params=params, timeout=25)  # Giảm timeout xuống 25s
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Check for error messages
                    if 'Error Message' in data:
                        logger.error(f"Lỗi API cho {symbol}: {data['Error Message']}")
                        return None
                    
                    if 'Note' in data:
                        # Rate limit message
                        logger.warning(f"Đạt giới hạn API cho {symbol}: {data['Note']}")
                        if attempt < max_retries:
                            logger.info(f"Thử lại {symbol} sau 2 giây...")
                            time.sleep(2)
                            continue
                        return None
                    
                    if 'Time Series (Daily)' not in data:
                        # Log chi tiết để debug
                        response_keys = list(data.keys())
                        logger.warning(f"Không có 'Time Series (Daily)' cho {symbol}. Response keys: {response_keys}")
                        if 'Information' in data:
                            logger.warning(f"Information: {data['Information']}")
                        # Thử lại 1 lần nếu có retry
                        if attempt < max_retries:
                            logger.info(f"Thử lại {symbol} sau 2 giây...")
                            time.sleep(2)
                            continue
                        return None
                    
                    # Convert to DataFrame
                    time_series = data['Time Series (Daily)']
                    df_data = []
                    
                    for date_str, values in time_series.items():
                        df_data.append({
                            'date': datetime.strptime(date_str, '%Y-%m-%d').date(),
                            'open': float(values['1. open']),
                            'high': float(values['2. high']),
                            'low': float(values['3. low']),
                            'close': float(values['4. close']),
                            'volume': int(values['5. volume'])
                        })
                    
                    df = pd.DataFrame(df_data)
                    df = df.sort_values('date')
                    
                    logger.info(f"Lấy được {symbol}: {len(df)} ngày")
                    return df
                    
                else:
                    logger.error(f"Lỗi HTTP {response.status_code} cho {symbol}")
                    if attempt < max_retries:
                        logger.info(f"Thử lại {symbol} sau 2 giây...")
                        time.sleep(2)
                        continue
                    return None
                    
            except requests.Timeout:
                logger.error(f"Timeout khi lấy {symbol}")
                if attempt < max_retries:
                    logger.info(f"Thử lại {symbol} sau 2 giây...")
                    time.sleep(2)
                    continue
                return None
            except Exception as e:
                logger.error(f"Lỗi khi lấy {symbol}: {e}")
                if attempt < max_retries:
                    logger.info(f"Thử lại {symbol} sau 2 giây...")
                    time.sleep(2)
                    continue
                return None
        
        return None
    
    def collect_data(self, days_back=1, month=None):
        """
        Thu thập dữ liệu cổ phiếu.
        
        days_back: Số ngày lấy ngược (mặc định 1)
        month: Tháng cụ thể YYYY-MM (nếu có thì bỏ qua days_back)
        """
        # Xác định khoảng thời gian cần lấy
        if month:
            logger.info(f"Bắt đầu thu thập dữ liệu tháng: {month}")
            year, mon = map(int, month.split('-'))
            cutoff_date = datetime(year, mon, 1).date()
            logger.info(f"Lấy từ ngày: {cutoff_date}")
        else:
            logger.info(f"Bắt đầu thu thập {days_back} ngày gần nhất")
            cutoff_date = datetime.now().date() - timedelta(days=days_back)
        
        logger.info(f"Số stocks: {len(self.stock_symbols)}")
        logger.info(f"Thời gian ước tính: ~{len(self.stock_symbols) * 0.5:.0f} giây")
        
        conn = self.create_connection()
        if not conn:
            return False
        
        try:
            cursor = conn.cursor()
            total_count = 0
            success_count = 0
            
            # Lặp qua từng symbol để lấy dữ liệu
            for idx, symbol in enumerate(self.stock_symbols):
                logger.info(f"Đang xử lý {idx+1}/{len(self.stock_symbols)}: {symbol}")
                
                # Gọi API lấy data với retry 1 lần (để không làm chậm)
                df = self.fetch_daily_data(symbol, retry=1)
                
                if df is not None and not df.empty:
                    # Lọc chỉ lấy ngày >= cutoff_date
                    df = df[df['date'] >= cutoff_date]
                    
                    # Insert từng dòng vào database
                    for _, row in df.iterrows():
                        # Tính % thay đổi trong ngày
                        open_p = float(row['open'])
                        close_p = float(row['close'])
                        daily_ret = ((close_p - open_p) / open_p * 100.0) if open_p else 0.0
                        
                        # Insert hoặc update nếu đã tồn tại (ON CONFLICT)
                        cursor.execute("""
                            INSERT INTO stocks.stocks_daily_alphavantage (
                                symbol, date, open_price, high_price, low_price, 
                                close_price, volume, daily_return
                            ) VALUES (
                                %s, %s, %s, %s, %s, %s, %s, %s
                            ) ON CONFLICT (date, symbol) DO UPDATE SET
                                open_price = EXCLUDED.open_price,
                                high_price = EXCLUDED.high_price,
                                low_price = EXCLUDED.low_price,
                                close_price = EXCLUDED.close_price,
                                volume = EXCLUDED.volume,
                                daily_return = EXCLUDED.daily_return
                        """, (
                            symbol,
                            row['date'],
                            float(row['open']),
                            float(row['high']),
                            float(row['low']),
                            float(row['close']),
                            int(row['volume']),
                            daily_ret
                        ))
                        total_count += 1
                    
                    # Commit sau mỗi symbol
                    conn.commit()
                    success_count += 1
                    logger.info(f"Đã lưu {symbol}: {len(df)} bản ghi")
                else:
                    # Không có data (có thể bị delisted)
                    logger.warning(f"Không có dữ liệu cho {symbol}")
                
                # Delay nhỏ tránh spam API (Alpha limit theo ngày, không theo giây)
                # Giảm delay để tăng tốc độ (0.3s thay vì 0.5s)
                if idx < len(self.stock_symbols) - 1:
                    time.sleep(0.3)
            
            cursor.close()
            conn.close()
            
            # Tổng kết
            logger.info(f"Hoàn thành: {total_count} bản ghi từ {success_count}/{len(self.stock_symbols)} stocks")
            return True
            
        except Exception as e:
            logger.error(f"Lỗi thu thập dữ liệu: {e}")
            if conn:
                conn.rollback()
                conn.close()
            return False

def main():
    parser = argparse.ArgumentParser(description='Alpha Vantage collector')
    parser.add_argument('--days_back', type=int, default=None, help='Days back to collect')
    parser.add_argument('--month', type=str, default=None, help='Month to collect (YYYY-MM format, e.g. 2025-10)')
    parser.add_argument('--batch', type=int, default=None, help='Batch number for large collections (1-based)')
    args = parser.parse_args()
    
    if not ALPHA_VANTAGE_KEY or ALPHA_VANTAGE_KEY == 'demo':
        logger.error("ALPHA_VANTAGE_KEY chưa được set! Lấy key miễn phí tại: https://www.alphavantage.co/support/#api-key")
        logger.info("Using 'demo' key (limited to 1 symbol)")
    
    collector = AlphaVantageCollector()
    
    # If batch specified, use subset of symbols (25 calls/day limit)
    if args.batch:
        batch_size = 20
        start_idx = (args.batch - 1) * batch_size
        end_idx = start_idx + batch_size
        collector.stock_symbols = collector.stock_symbols[start_idx:end_idx]
        logger.info(f"📦 Batch {args.batch}: symbols {start_idx+1} to {end_idx}")
    
    if args.month:
        collector.collect_data(month=args.month)
    else:
        days_back = args.days_back if args.days_back else 1
        collector.collect_data(days_back=days_back)

if __name__ == "__main__":
    main()

