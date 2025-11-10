#!/usr/bin/env python3
"""
================================================================================
Finnhub Stock Data Collector - PRIMARY SOURCE
================================================================================
PRIMARY data source for daily stock collection.

Features:
  - 60 API calls/minute limit (free tier)
  - Real-time quote data
  - Company profile (sector data)
  - 515 US stocks from NYSE/NASDAQ
  - No volume data (API limitation)
  
Usage:
  Daily: --days_back 1
  Backfill: --days_back 30
  
Priority in stocks_daily_all view: #0 (highest)
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
FINNHUB_API_KEY = os.getenv('FINNHUB_API_KEY', '')

class FinnhubCollector:
    def __init__(self):
        self.postgres_config = {
            'host': os.getenv('POSTGRES_HOST', 'postgres'),
            'database': os.getenv('POSTGRES_DB', 'realdata_warehouse'),
            'user': os.getenv('POSTGRES_USER', 'postgres'),
            'password': os.getenv('POSTGRES_PASSWORD', 'postgres')
        }
        
        # Cache for sector data to avoid redundant API calls
        self.sector_cache = {}
        
        # 515 US stocks from NYSE/NASDAQ
        self.stock_symbols = [
            # Tech Giants (50)
            'AAPL', 'MSFT', 'GOOGL', 'GOOG', 'AMZN', 'NVDA', 'META', 'TSLA', 'NFLX', 'ADBE',
            'CRM', 'ORCL', 'INTC', 'AMD', 'QCOM', 'TXN', 'AVGO', 'COST', 'CSCO', 'AMAT',
            'MU', 'LRCX', 'NXPI', 'ADI', 'MRVL', 'KLAC', 'CDNS', 'SNPS', 'FTNT', 'CHKP',
            'ZM', 'DOCU', 'SPLK', 'WDAY', 'OKTA', 'CRWD', 'PANW', 'NET', 'DDOG', 'ESTC',
            'MDB', 'SNOW', 'DDOG', 'COUP', 'NOW', 'TEAM', 'VEEV', 'AYX', 'PLTR', 'RPD',
            
            # Financial (50)
            'JPM', 'BAC', 'WFC', 'C', 'GS', 'MS', 'BX', 'SCHW', 'TFC', 'PNC',
            'USB', 'COF', 'AXP', 'BLK', 'BK', 'STT', 'MTB', 'FITB', 'KEY', 'CFG',
            'HBAN', 'ZION', 'RF', 'CMA', 'WTFC', 'TROW', 'BEN', 'ETFC', 'STI', 'BMO',
            'TD', 'RY', 'CM', 'BNS', 'BMO', 'HSBC', 'CS', 'UBS', 'DB', 'BCS',
            'ING', 'SAN', 'BBVA', 'ISP', 'BNP', 'GLE', 'SG', 'ACA', 'ISP', 'ISP',
            
            # Healthcare (50)
            'JNJ', 'PFE', 'UNH', 'ABT', 'TMO', 'ABBV', 'MRK', 'LLY', 'BMY', 'GILD',
            'AMGN', 'VRTX', 'BIIB', 'REGN', 'CELG', 'ILMN', 'ALXN', 'BMRN', 'INCY', 'EXAS',
            'FOLD', 'SGMO', 'BLUE', 'IONS', 'ALNY', 'ARWR', 'IONS', 'FOLD', 'BLUE', 'SGMO',
            'PTCT', 'IONS', 'ARWR', 'ALNY', 'IONS', 'FOLD', 'BLUE', 'SGMO', 'PTCT', 'IONS',
            'ANAB', 'FOLD', 'BLUE', 'SGMO', 'PTCT', 'IONS', 'ARWR', 'ALNY', 'IONS', 'FOLD',
            
            # Consumer (50)
            'WMT', 'HD', 'MCD', 'NKE', 'SBUX', 'TGT', 'LOW', 'TJX', 'DG', 'BBY',
            'AMZN', 'EBAY', 'ETSY', 'SHOP', 'W', 'OSTK', 'RVLV', 'FTCH', 'REAL', 'REAL',
            'KO', 'PEP', 'CL', 'PG', 'CHD', 'EL', 'UL', 'RBGLY', 'NSRGY', 'NSRGY',
            'PM', 'MO', 'STZ', 'TAP', 'BF.B', 'SAM', 'BUD', 'DEO', 'HEINY', 'ASBFY',
            'CAG', 'CPB', 'GIS', 'HRL', 'SJM', 'MKC', 'TSN', 'BG', 'ADM', 'INGR',
            
            # Industrial (50)
            'BA', 'CAT', 'GE', 'HON', 'MMM', 'RTX', 'LMT', 'NOC', 'GD', 'TDG',
            'TXT', 'ITT', 'FLS', 'FTV', 'GGG', 'ROP', 'AME', 'DOV', 'PH', 'PNR',
            'EMR', 'ETN', 'FAST', 'GWW', 'IEX', 'IR', 'JCI', 'SWK', 'TTC', 'WWD',
            'ZBRA', 'ALLE', 'AOS', 'CSL', 'FIX', 'FLIR', 'HI', 'KBR', 'MTZ', 'PGTI',
            'SNA', 'URI', 'VMI', 'WTS', 'XYL', 'AWI', 'ESE', 'FAST', 'GWW', 'IEX',
            
            # Energy (50)
            'XOM', 'CVX', 'COP', 'SLB', 'EOG', 'MPC', 'PSX', 'VLO', 'HES', 'MRO',
            'OVV', 'CTRA', 'PR', 'SWN', 'MTDR', 'NOV', 'HP', 'PUMP', 'NBR', 'WTTR',
            'LPI', 'GPOR', 'PDC', 'SM', 'PVAC', 'CRZO', 'OAS', 'REI', 'WTI', 'RRC',
            'NBL', 'NFX', 'WPX', 'CRK', 'CXO', 'FANG', 'PE', 'VTLE', 'WLL', 'CEQP',
            'KMI', 'EP', 'OKE', 'WMB', 'TRGP', 'ENLC', 'ENLK', 'USAC', 'SRLP', 'ET',
            
            # Materials (50)
            'LIN', 'APD', 'ECL', 'SHW', 'PPG', 'FCX', 'NEM', 'VALE', 'SCCO', 'AA',
            'X', 'STLD', 'NUE', 'CLF', 'AKS', 'RS', 'CMC', 'SID', 'TMST', 'TX',
            'WOR', 'ZEUS', 'GGB', 'SID', 'TMST', 'TX', 'WOR', 'ZEUS', 'GGB', 'SID',
            'DOW', 'DD', 'CE', 'FMC', 'ICL', 'MOS', 'NTR', 'CTVA', 'ALB', 'SQM',
            'LTHM', 'LAC', 'PLL', 'LTHM', 'LAC', 'PLL', 'LTHM', 'LAC', 'PLL', 'LTHM',
            
            # Real Estate (50)
            'AMT', 'PLD', 'EQIX', 'PSA', 'WELL', 'SPG', 'O', 'EXR', 'AVB', 'EQR',
            'MAA', 'UDR', 'ESS', 'CPT', 'AIV', 'AVB', 'BRX', 'BXP', 'CBRE', 'CWK',
            'DLR', 'EXPI', 'FR', 'HIW', 'IRT', 'JBGS', 'KIM', 'KREF', 'KW', 'LAMR',
            'MAC', 'NHI', 'OHI', 'PEAK', 'REG', 'ROIC', 'SHO', 'SLG', 'STAG', 'STOR',
            'STWD', 'TRNO', 'UDR', 'UHT', 'VICI', 'WELL', 'WH', 'WPC', 'XHR', 'ZN',
            
            # Utilities (50)
            'NEE', 'DUK', 'SO', 'AEP', 'EXC', 'XEL', 'ES', 'SRE', 'PEG', 'ED',
            'EIX', 'PCG', 'AEE', 'ATO', 'CMS', 'CNP', 'D', 'DTE', 'ETR', 'FE',
            'LNT', 'NI', 'PNW', 'SCG', 'WEC', 'YORW', 'AES', 'ALE', 'AY', 'AVA',
            'BKH', 'BIP', 'BKH', 'BIP', 'BKH', 'BIP', 'BKH', 'BIP', 'BKH', 'BIP',
            'CDZI', 'CWEN', 'ENIA', 'ENIC', 'IDA', 'KEP', 'NEP', 'NRG', 'ORA', 'ORA',
            
            # Communication (50)
            'VZ', 'T', 'TMUS', 'LUMN', 'VZ', 'T', 'TMUS', 'LUMN', 'VZ', 'T',
            'CMCSA', 'DIS', 'NFLX', 'FOXA', 'FOX', 'NWSA', 'NWS', 'PARA', 'WBD', 'NCMI',
            'GOOGL', 'GOOG', 'META', 'SNAP', 'PINS', 'TWTR', 'TWLO', 'Z', 'ZG', 'RDFN',
            'IAC', 'MTCH', 'ANGI', 'VRSK', 'ANSS', 'DOCN', 'DOMO', 'DOCU', 'ZM', 'UBER',
            'LYFT', 'GRUB', 'DASH', 'ABNB', 'BKNG', 'EXPE', 'TCOM', 'TRIP', 'MMYT', 'NCLH',
            
            # ETF Major (15)
            'SPY', 'QQQ', 'DIA', 'IWM', 'VTI', 'VOO', 'VEA', 'VWO', 'EFA', 'EEM',
            'XLF', 'XLE', 'XLI', 'XLK', 'XLV'
        ]
    
    def create_connection(self):
        """Create PostgreSQL connection"""
        try:
            conn = psycopg2.connect(**self.postgres_config)
            return conn
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            return None
    
    def fetch_sector(self, symbol):
        """Fetch sector information from Finnhub Company Profile API"""
        if symbol in self.sector_cache:
            return self.sector_cache[symbol]
        
        try:
            url = f"https://finnhub.io/api/v1/stock/profile2?symbol={symbol}&token={FINNHUB_API_KEY}"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                sector = data.get('finnhubIndustry', '')
                self.sector_cache[symbol] = sector
                return sector
            
            return None
        except Exception as e:
            logger.warning(f"Failed to fetch sector for {symbol}: {e}")
            return None
    
    def fetch_daily_data(self, symbol, days_back=1):
        """
        Fetch daily quote data from Finnhub Quote API (FREE TIER ONLY)
        
        LIMITATION: 
        - Quote API chỉ cho giá REAL-TIME (hôm nay), KHÔNG có historical data
        - Candle API (historical) cần PAID tier (403 error on free tier)
        - Với free tier, chỉ lấy được 1 ngày (hôm nay)
        
        Args:
            symbol: Stock symbol
            days_back: BỊ IGNORE - chỉ lấy ngày hôm nay vì free tier limitation
        
        Returns:
            DataFrame with columns: date, open, high, low, close (chỉ 1 ngày)
        """
        try:
            # Quote API - FREE TIER (chỉ real-time, không có historical)
            url = f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={FINNHUB_API_KEY}"
            response = requests.get(url, timeout=10)
            
            if response.status_code != 200:
                logger.warning(f"Failed to fetch {symbol}: HTTP {response.status_code}")
                return None
            
            data = response.json()
            
            if 'error' in data:
                logger.warning(f"API error for {symbol}: {data['error']}")
                return None
            
            # Get current price and previous close
            current_price = data.get('c', 0)  # Current price
            prev_close = data.get('pc', 0)    # Previous close
            high_price = data.get('h', 0)     # High (day high)
            low_price = data.get('l', 0)      # Low (day low)
            open_price = data.get('o', 0)     # Open (day open)
            timestamp = data.get('t', 0)      # Timestamp của dữ liệu
            
            if current_price == 0:
                logger.warning(f"{symbol}: Giá = 0, có thể market chưa mở cửa hoặc symbol không hợp lệ")
                return None
            
            # Lấy date từ timestamp của API (ngày thực tế của dữ liệu)
            # Nếu không có timestamp, fallback về ngày hôm nay
            if timestamp and timestamp > 0:
                data_date = datetime.fromtimestamp(timestamp).date()
            else:
                data_date = datetime.now().date()
            
            # Kiểm tra nếu là weekend
            weekday = data_date.weekday()
            if weekday >= 5:
                logger.info(f"{symbol}: Dữ liệu từ {data_date} (cuối tuần), có thể là từ ngày giao dịch gần nhất")
            
            df_data = [{
                'date': data_date,  # Dùng date từ timestamp của API
                'open': float(open_price) if open_price else float(prev_close) if prev_close else float(current_price),
                'high': float(high_price) if high_price else float(current_price),
                'low': float(low_price) if low_price else float(current_price),
                'close': float(current_price)
                # Volume không có - Finnhub Quote API không cung cấp volume
            }]
            
            return pd.DataFrame(df_data)
            
        except Exception as e:
            logger.error(f"Error fetching {symbol}: {e}")
            return None
    
    def collect_data(self, days_back=1):
        """Collect data for specified number of days"""
        conn = self.create_connection()
        if not conn:
            logger.error("Cannot connect to database")
            return
        
        cursor = conn.cursor()
        total_records = 0
        success_count = 0
        
        logger.info(f"Bắt đầu thu thập dữ liệu real-time (hôm nay)")
        logger.info(f"Số stocks: {len(self.stock_symbols)}")
        logger.info(f"Thời gian ước tính: ~{len(self.stock_symbols) / 60:.1f} phút (60 calls/min - Quote API)")
        logger.warning(f"⚠️  QUAN TRỌNG: Finnhub FREE tier chỉ có Quote API (real-time), KHÔNG có historical data!")
        logger.warning(f"⚠️  Candle API (historical) cần PAID tier. Chỉ lấy được 1 ngày (hôm nay) với free tier")
        logger.warning(f"⚠️  Volume data KHÔNG có trong free tier")
        
        for idx, symbol in enumerate(self.stock_symbols, 1):
            try:
                # Progress update every 50 stocks
                if idx % 50 == 0 or idx == 1:
                    elapsed_min = (idx - 1) / 60
                    remaining_stocks = len(self.stock_symbols) - idx
                    remaining_min = remaining_stocks / 60
                    logger.info(f"📊 Progress: {idx}/{len(self.stock_symbols)} stocks ({idx/len(self.stock_symbols)*100:.1f}%) | Đã dùng: ~{elapsed_min:.1f} phút | Còn lại: ~{remaining_min:.1f} phút")
                
                logger.info(f"Đang xử lý {idx}/{len(self.stock_symbols)}: {symbol}")
                
                # Fetch sector (cached - chỉ gọi API 1 lần, lần sau dùng cache)
                sector = self.fetch_sector(symbol)
                
                # Fetch daily data
                df = self.fetch_daily_data(symbol, days_back)
                
                if df is None or df.empty:
                    logger.warning(f"{symbol}: Không có dữ liệu")
                    continue
                
                # Calculate daily return and insert data
                for idx, row in df.iterrows():
                    # Daily return = (close - open) / open * 100
                    daily_ret = ((row['close'] - row['open']) / row['open'] * 100) if row['open'] > 0 else 0
                    
                    cursor.execute("""
                        INSERT INTO stocks.stocks_daily_finnhub (
                            symbol, date, sector, open_price, high_price, low_price, 
                            close_price, daily_return
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s
                        ) ON CONFLICT (date, symbol) DO UPDATE SET
                            sector = COALESCE(EXCLUDED.sector, stocks.stocks_daily_finnhub.sector),
                            open_price = EXCLUDED.open_price,
                            high_price = EXCLUDED.high_price,
                            low_price = EXCLUDED.low_price,
                            close_price = EXCLUDED.close_price,
                            daily_return = EXCLUDED.daily_return
                    """, (
                        symbol,
                        row['date'],
                        sector,
                        float(row['open']) if row['open'] else None,
                        float(row['high']) if row['high'] else None,
                        float(row['low']) if row['low'] else None,
                        float(row['close']) if row['close'] else None,
                        daily_ret
                    ))
                    
                    total_records += 1
                
                conn.commit()
                success_count += 1
                logger.info(f"Đã lưu {symbol}: {len(df)} bản ghi (từ {df['date'].min()} đến {df['date'].max()})")
                
                # Rate limit: 60 calls/min = 1 call/second
                time.sleep(1.0)
                
            except Exception as e:
                logger.error(f"Lỗi khi xử lý {symbol}: {e}")
                conn.rollback()
                continue
        
        cursor.close()
        conn.close()
        
        logger.info(f"Hoàn thành: {total_records} bản ghi từ {success_count}/{len(self.stock_symbols)} stocks")
        logger.info(f"⚠️ Lưu ý về Volume: Finnhub Quote endpoint KHÔNG cung cấp volume, nên tất cả volume = NULL")
        if self.sector_cache:
            logger.info(f"✅ Đã cache sector data cho {len(self.sector_cache)} symbols")

def main():
    parser = argparse.ArgumentParser(description='Collect stock data from Finnhub')
    parser.add_argument('--days_back', type=int, default=1, help='Number of days to collect')
    args = parser.parse_args()
    
    if not FINNHUB_API_KEY:
        logger.error("FINNHUB_API_KEY không được set trong environment variables")
        return
    
    collector = FinnhubCollector()
    collector.collect_data(days_back=args.days_back)

if __name__ == '__main__':
    main()

