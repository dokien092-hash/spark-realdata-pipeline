#!/usr/bin/env python3


import yfinance as yf
import psycopg2
from datetime import datetime, timedelta
import logging
import time
import pandas as pd
import argparse
import random
import pickle
import os
from pathlib import Path

# Configure yfinance session with custom headers to avoid rate limiting
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

# Cache directory
CACHE_DIR = Path("/tmp/stock_data_cache")
CACHE_DIR.mkdir(exist_ok=True)

def get_cache_key(symbol, date):
    """Generate cache key for symbol and date"""
    return f"{symbol}_{date.strftime('%Y%m%d')}"

def load_from_cache(symbol, date):
    """Load data from cache if available and fresh (< 24 hours)"""
    cache_file = CACHE_DIR / f"{get_cache_key(symbol, date)}.pkl"
    if cache_file.exists():
        # Check if cache is fresh (< 24 hours old)
        cache_age = time.time() - cache_file.stat().st_mtime
        if cache_age < 86400:  # 24 hours
            try:
                with open(cache_file, 'rb') as f:
                    return pickle.load(f)
            except:
                pass
    return None

def save_to_cache(symbol, date, data):
    """Save data to cache"""
    cache_file = CACHE_DIR / f"{get_cache_key(symbol, date)}.pkl"
    try:
        with open(cache_file, 'wb') as f:
            pickle.dump(data, f)
    except:
        pass

def setup_yfinance_session():
    """Setup yfinance with custom session to reduce rate limiting"""
    session = requests.Session()
    
    # Retry strategy - more conservative
    retry = Retry(
        total=3,
        backoff_factor=3,
        status_forcelist=[429, 500, 502, 503, 504],
        respect_retry_after_header=True
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    
    # Rotate User-Agent to appear as different browsers
    user_agents = [
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
    ]
    session.headers['User-Agent'] = random.choice(user_agents)
    
    return session

# Apply custom session to yfinance
yf.set_tz_cache_location("/tmp/yfinance_cache")

# Polygon.io configuration
POLYGON_API_KEY = os.getenv('POLYGON_API_KEY', '')  # Set via environment variable

def fetch_from_polygon(symbol, start_date, end_date):
    """
    Lấy dữ liệu từ Polygon.io API.
    
    Limit: 5 calls/phút (free tier), data delay 15 phút
    """
    if not POLYGON_API_KEY:
        logger.warning("POLYGON_API_KEY not set, skipping Polygon.io")
        return None
    
    try:
        # Polygon uses different date format
        from_date = start_date.strftime('%Y-%m-%d')
        to_date = end_date.strftime('%Y-%m-%d')
        
        url = f'https://api.polygon.io/v2/aggs/ticker/{symbol}/range/1/day/{from_date}/{to_date}'
        params = {
            'adjusted': 'true',
            'sort': 'asc',
            'apiKey': POLYGON_API_KEY
        }
        
        response = requests.get(url, params=params, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'OK' and data.get('results'):
                # Convert Polygon format to DataFrame
                results = data['results']
                df = pd.DataFrame(results)
                
                # Rename columns to match yfinance format
                df['Date'] = pd.to_datetime(df['t'], unit='ms')
                df['Open'] = df['o']
                df['High'] = df['h']
                df['Low'] = df['l']
                df['Close'] = df['c']
                df['Volume'] = df['v']
                
                df = df.set_index('Date')[['Open', 'High', 'Low', 'Close', 'Volume']]
                logger.info(f"Polygon.io: Fetched {symbol} ({len(df)} days)")
                return df
            else:
                logger.warning(f"Polygon.io: No data available for {symbol}")
                return None
        elif response.status_code == 429:
            logger.warning(f"Polygon.io rate limit hit for {symbol}")
            return None
        else:
            logger.error(f"Polygon.io HTTP {response.status_code} error for {symbol}")
            return None
            
    except Exception as e:
        logger.error(f"Polygon.io fetch error for {symbol}: {e}")
        return None

class RateLimiter:
    """Simple rate limiter for Polygon.io: 5 calls/minute"""
    def __init__(self):
        self.request_times = []
        
    def wait(self):
        """Wait to respect 5 calls/minute limit"""
        now = time.time()
        
        # Remove timestamps older than 60 seconds
        self.request_times = [t for t in self.request_times if now - t < 60]
        
        # If we've made 5 calls in the last minute, wait for the oldest to expire
        if len(self.request_times) >= 5:
            oldest = self.request_times[0]
            wait_time = 61 - (now - oldest)  # 61s to be safe
            if wait_time > 0:
                logger.info(f"Đạt giới hạn API: chờ {wait_time:.0f}s (Polygon giới hạn 5 calls/phút)")
                time.sleep(wait_time)
                # Clean up after wait
                now = time.time()
                self.request_times = [t for t in self.request_times if now - t < 60]
        
        self.request_times.append(time.time())
        
    def record_success(self):
        """Not needed for simple limiter"""
        pass
            
    def record_failure(self):
        """Not needed for simple limiter"""
        pass
        
    def should_pause(self):
        """Not needed for simple limiter"""
        return False

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MonthlyDataCollector:
    def __init__(self):
        self.postgres_config = {
            'host': 'postgres',
            'database': 'realdata_warehouse',
            'user': 'postgres',
            'password': 'postgres'
        }
        
        # Top 30 most popular stocks (optimized for Polygon free tier: 5 calls/min)
        # Collection time: ~6-7 minutes for 30 symbols
        # Top 15 stocks - Fast daily collection (~3 minutes)
        self.stock_symbols = [
            # FAANG + Tech Giants (most traded)
            'AAPL', 'GOOGL', 'MSFT', 'AMZN', 'NVDA', 'TSLA',
            # Major Market ETFs (essential indicators)
            'SPY', 'QQQ', 'VTI',
            # Finance (Dow components)
            'JPM', 'BAC', 'V',
            # Healthcare & Consumer
            'JNJ', 'PG'
        ]
        
        # Extended list (55 symbols - uncomment for comprehensive coverage, ~11 minutes)
        # self.stock_symbols = [
        #     'AAPL', 'GOOGL', 'MSFT', 'AMZN', 'META', 'NVDA', 'NFLX', 'TSLA',
        #     'SPY', 'QQQ', 'VTI', 'IWM', 'EFA', 'VEA', 'VWO',
        #     'JPM', 'BAC', 'WFC', 'GS', 'MS', 'C', 'AXP',
        #     'JNJ', 'PFE', 'UNH', 'ABBV', 'MRK', 'TMO', 'ABT',
        #     'PG', 'KO', 'PEP', 'WMT', 'HD', 'MCD', 'NKE',
        #     'BA', 'CAT', 'GE', 'MMM', 'HON', 'UPS', 'FDX',
        #     'XOM', 'CVX', 'COP', 'EOG', 'SLB', 'KMI',
        #     'NEE', 'SO', 'DUK', 'AEP', 'EXC', 'XEL'
        # ]
    
    def create_connection(self):
        """Create PostgreSQL connection"""
        try:
            conn = psycopg2.connect(**self.postgres_config)
            return conn
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            return None
    
    def collect_stock_data_for_period(self, start_date, end_date):
        """
        Thu thập dữ liệu cổ phiếu từ Polygon.io.
        
        - Dùng cache local tránh lấy lại
        - Tự động chờ khi đạt 5 calls/phút
        - Lưu vào bảng stocks_daily_polygon
        """
        logger.info(f"Thu thập dữ liệu cổ phiếu từ {start_date} đến {end_date}")
        
        conn = self.create_connection()
        if not conn:
            return False
        
        try:
            cursor = conn.cursor()
            total_count = 0
            rate_limiter = RateLimiter()

            # Lặp qua từng symbol với rate limiting
            for idx, symbol in enumerate(self.stock_symbols):
                logger.info(f"Đang xử lý {idx+1}/{len(self.stock_symbols)}: {symbol}")
                
                # Simple rate limit check (no adaptive logic needed)
                
                # Check cache first
                cached_data = load_from_cache(symbol, start_date)
                if cached_data is not None:
                    logger.info(f"Dùng dữ liệu cache cho {symbol}")
                    df = cached_data
                    # No API call needed, skip rate limit
                else:
                    # Use Polygon.io only (no Yahoo fallback)
                    df = None
                    
                    if not POLYGON_API_KEY:
                        logger.error(f"POLYGON_API_KEY chưa set. Bỏ qua {symbol}")
                        continue
                    
                    # Wait before request (respects rate limit: 5 calls/minute for free tier)
                    rate_limiter.wait()
                    
                    # Fetch from Polygon with retry
                    max_retries = 3
                    for retry in range(max_retries):
                        df = fetch_from_polygon(symbol, start_date, end_date)
                        
                        if df is not None and not df.empty:
                            # Success - save to cache
                            save_to_cache(symbol, start_date, df)
                            break
                        else:
                            # Retry with simple delay
                            if retry < max_retries - 1:
                                logger.warning(f"Thử lại {retry+1}/{max_retries} cho {symbol}, chờ 5s")
                                time.sleep(5)
                            else:
                                logger.error(f"{symbol} thất bại sau {max_retries} lần thử")
                                df = None
                
                # Process data if available
                if df is not None and not df.empty:
                    try:
                        for dt_idx, row in df.iterrows():
                            if pd.isna(row.get('Open')) or pd.isna(row.get('Close')):
                                continue
                            open_p = float(row['Open'])
                            close_p = float(row['Close'])
                            high_p = float(row.get('High', open_p))
                            low_p = float(row.get('Low', open_p))
                            volume_v = int(row.get('Volume', 0)) if not pd.isna(row.get('Volume', 0)) else 0
                            daily_ret = ((close_p - open_p) / open_p * 100.0) if open_p else 0.0

                            cursor.execute("""
                                INSERT INTO stocks.stocks_daily_polygon (
                                    symbol, date, sector, open_price, high_price, low_price, 
                                    close_price, volume, market_cap, avg_pe_ratio, daily_return
                                ) VALUES (
                                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                                ) ON CONFLICT (date, symbol) DO UPDATE SET
                                    sector = EXCLUDED.sector,
                                    open_price = EXCLUDED.open_price,
                                    high_price = EXCLUDED.high_price,
                                    low_price = EXCLUDED.low_price,
                                    close_price = EXCLUDED.close_price,
                                    volume = EXCLUDED.volume,
                                    market_cap = EXCLUDED.market_cap,
                                    avg_pe_ratio = EXCLUDED.avg_pe_ratio,
                                    daily_return = EXCLUDED.daily_return
                            """, (
                                symbol,
                                dt_idx.date(),
                                'Unknown',
                                open_p,
                                high_p,
                                low_p,
                                close_p,
                                volume_v,
                                0,
                                0,
                                daily_ret
                            ))
                            total_count += 1
                    except Exception as e:
                        logger.error(f"Error processing {symbol} data: {e}")
                        continue
            
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info(f"Đã thu thập {total_count} bản ghi cổ phiếu")
            return True
            
        except Exception as e:
            logger.error(f"Error in collect_stock_data_for_period: {e}")
            if conn:
                conn.rollback()
                conn.close()
            return False
    
    
    def collect_monthly_data(self, days_back=30):
        """Thu thập dữ liệu N ngày gần nhất (mặc định 30 ngày)"""
        logger.info(f"Bắt đầu thu thập {days_back} ngày gần nhất")
        
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days_back)
        
        logger.info(f"Thu thập từ {start_date} đến {end_date}")
        
        # Collect stock data only
        self.collect_stock_data_for_period(start_date, end_date)
        
        logger.info("Thu thập dữ liệu hoàn tất")
    
    def get_data_summary(self):
        """Get summary of collected data"""
        try:
            conn = self.create_connection()
            if conn:
                cursor = conn.cursor()
                
                # Stocks summary
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_records,
                        COUNT(DISTINCT symbol) as unique_symbols,
                        COUNT(DISTINCT date) as unique_dates,
                        MIN(date) as earliest_date,
                        MAX(date) as latest_date,
                        AVG(daily_return) as avg_return
                    FROM stocks_daily
                """)
                stocks_summary = cursor.fetchone()
                
                cursor.close()
                conn.close()
                
                logger.info("Data Summary:")
                logger.info(f"  Stocks: {stocks_summary[0]} records, {stocks_summary[1]} symbols, {stocks_summary[2]} dates")
                logger.info(f"  Period: {stocks_summary[3]} to {stocks_summary[4]}")
                logger.info(f"  Avg Return: {stocks_summary[5]:.2f}%")
                
        except Exception as e:
            logger.error(f"Error getting data summary: {e}")

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Collect stock data over a time window')
    parser.add_argument('--days_back', type=int, default=None, help='Number of days back to collect')
    parser.add_argument('--start_date', type=str, default=None, help='Start date (YYYY-MM-DD), inclusive')
    parser.add_argument('--end_date', type=str, default=None, help='End date (YYYY-MM-DD), inclusive')
    args = parser.parse_args()

    collector = MonthlyDataCollector()

    # Priority: explicit range if provided; otherwise days_back (default to 30 if neither provided)
    if args.start_date and args.end_date:
        try:
            start_date = datetime.strptime(args.start_date, '%Y-%m-%d').date()
            end_date_inclusive = datetime.strptime(args.end_date, '%Y-%m-%d').date()
        except ValueError:
            logger.error("Invalid date format. Use YYYY-MM-DD for --start_date/--end_date")
            return

        if end_date_inclusive < start_date:
            logger.error("end_date must be on or after start_date")
            return

        # yfinance's 'end' is exclusive; add 1 day to include the end_date provided by the user
        end_date_exclusive = end_date_inclusive + timedelta(days=1)
        logger.info(f"Thu thập khoảng thời gian: {start_date} đến {end_date_inclusive}")
        collector.collect_stock_data_for_period(start_date, end_date_exclusive)

    else:
        days_back = args.days_back if args.days_back is not None else 30
        collector.collect_monthly_data(days_back=days_back)

    # Get summary
    collector.get_data_summary()

if __name__ == "__main__":
    main()
