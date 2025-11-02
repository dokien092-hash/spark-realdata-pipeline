import yfinance as yf
import psycopg2
from datetime import datetime, timedelta
import logging
import time
import pandas as pd
import argparse
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# PostgreSQL configuration
POSTGRES_CONFIG = {
    'host': os.getenv('POSTGRES_HOST', 'postgres'),
    'database': os.getenv('POSTGRES_DB', 'realdata_warehouse'),
    'user': os.getenv('POSTGRES_USER', 'postgres'),
    'password': os.getenv('POSTGRES_PASSWORD', 'postgres')
}

class USStockCollector:
    def __init__(self):
        self.postgres_config = POSTGRES_CONFIG
        self.connection = None
        
        # Danh sách cổ phiếu US từ S&P 500 (25 stocks cho Alpha Vantage limit)
        self.us_stocks = [
            # Tech Giants
            'AAPL',  # Apple
            'MSFT',  # Microsoft
            'GOOGL', # Alphabet
            'AMZN',  # Amazon
            'TSLA',  # Tesla
            'META',  # Meta
            'NVDA',  # NVIDIA
            'NFLX',  # Netflix
            'ADBE',  # Adobe
            'CRM',   # Salesforce
            
            # Financial
            'JPM',   # JPMorgan Chase
            'BAC',   # Bank of America
            'WFC',   # Wells Fargo
            'GS',    # Goldman Sachs
            'MS',    # Morgan Stanley
            
            # Healthcare
            'JNJ',   # Johnson & Johnson
            'PFE',   # Pfizer
            'UNH',   # UnitedHealth
            'ABT',   # Abbott
            'TMO',   # Thermo Fisher
            
            # Consumer
            'PG',    # Procter & Gamble
            'KO',    # Coca-Cola
            'PEP',   # PepsiCo
            'WMT',   # Walmart
            'HD',    # Home Depot
        ]
    
    def create_connection(self):
        """Tạo kết nối PostgreSQL"""
        try:
            self.connection = psycopg2.connect(**self.postgres_config)
            logger.info("Kết nối PostgreSQL thành công")
        except Exception as e:
            logger.error(f"Lỗi kết nối PostgreSQL: {e}")
            self.connection = None
    
    def close_connection(self):
        """Đóng kết nối PostgreSQL"""
        if self.connection:
            self.connection.close()
            logger.info("Đã đóng kết nối PostgreSQL")

    def get_exchange_and_currency(self, symbol):
        """Xác định sàn giao dịch và tiền tệ cho US stocks"""
        return 'NYSE', 'USD'  # Mặc định cho US stocks

    def save_data_to_postgres(self, df, symbol, exchange, currency, source):
        """Lưu DataFrame vào PostgreSQL"""
        if self.connection is None:
            logger.error("Không có kết nối PostgreSQL để lưu dữ liệu.")
            return
        
        cursor = self.connection.cursor()
        insert_count = 0
        
        for index, row in df.iterrows():
            try:
                # Tính daily_return
                daily_return = None
                if index > 0:
                    prev_close = df.iloc[index-1]['Close']
                    if prev_close is not None and prev_close != 0:
                        daily_return = ((row['Close'] - prev_close) / prev_close) * 100
                
                cursor.execute(
                    """
                    INSERT INTO stocks.stocks_daily_yahoo (
                        symbol, date, exchange, currency, open_price, high_price, low_price, 
                        close_price, volume, daily_return, source
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (date, symbol) DO UPDATE SET
                        exchange = EXCLUDED.exchange,
                        currency = EXCLUDED.currency,
                        open_price = EXCLUDED.open_price,
                        high_price = EXCLUDED.high_price,
                        low_price = EXCLUDED.low_price,
                        close_price = EXCLUDED.close_price,
                        volume = EXCLUDED.volume,
                        daily_return = EXCLUDED.daily_return,
                        source = EXCLUDED.source,
                        created_at = CURRENT_TIMESTAMP;
                    """,
                    (
                        symbol,
                        row['Date'].date(),
                        exchange,
                        currency,
                        row['Open'],
                        row['High'],
                        row['Low'],
                        row['Close'],
                        row['Volume'],
                        daily_return,
                        source
                    )
                )
                insert_count += 1
            except Exception as e:
                logger.error(f"Lỗi khi lưu dữ liệu {symbol} ngày {row['Date'].date()}: {e}")
                self.connection.rollback()
                raise
        
        self.connection.commit()
        logger.info(f"Đã lưu {insert_count} records cho {symbol}")

    def collect_data(self, days_back=1, symbols=None):
        """
        Thu thập dữ liệu cổ phiếu US từ yfinance.
        """
        if symbols is None:
            symbols_to_collect = self.us_stocks
        else:
            symbols_to_collect = [s.upper() for s in symbols]

        logger.info(f"Bắt đầu thu thập dữ liệu US market ({len(symbols_to_collect)} stocks)")
        self.create_connection()
        if not self.connection:
            return False

        success_count = 0
        total_symbols = len(symbols_to_collect)

        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back + 5)  # Lấy thêm vài ngày để tính daily_return

        for idx, symbol in enumerate(symbols_to_collect):
            logger.info(f"Xử lý {idx+1}/{total_symbols}: {symbol}")
            logger.info(f"Đang lấy dữ liệu {symbol}...")
            try:
                # Retry logic cho yfinance
                max_retries = 3
                for retry in range(max_retries):
                    try:
                        # yfinance's 'end' is exclusive; add 1 day to include the end_date
                        df = yf.download(symbol, start=start_date, end=end_date + timedelta(days=1), interval="1d", progress=False)
                        
                        if df.empty:
                            logger.warning(f"Không có dữ liệu từ yfinance cho {symbol}")
                            break
                        else:
                            break  # Success, exit retry loop
                            
                    except Exception as retry_error:
                        if retry < max_retries - 1:
                            wait_time = (retry + 1) * 10  # 10s, 20s, 30s
                            logger.warning(f"Retry {retry + 1}/{max_retries} cho {symbol}, chờ {wait_time}s: {retry_error}")
                            time.sleep(wait_time)
                        else:
                            raise retry_error
                
                if df.empty:
                    logger.warning(f"Không có dữ liệu từ yfinance cho {symbol} sau {max_retries} lần thử")
                    continue
                
                df = df.reset_index()
                df['Date'] = pd.to_datetime(df['Date']).dt.tz_localize(None)  # Remove timezone info
                
                exchange, currency = self.get_exchange_and_currency(symbol)
                source = 'yfinance'

                self.save_data_to_postgres(df, symbol, exchange, currency, source)
                logger.info(f"✅ {symbol}: Thành công")
                success_count += 1
                time.sleep(5)  # Delay 5 giây giữa các requests để tránh rate limit
            except Exception as e:
                logger.error(f"Lỗi khi thu thập dữ liệu {symbol}: {e}")
                logger.error(f"❌ {symbol}: Lỗi lưu database")
                self.connection.rollback()
                
        self.close_connection()
        if success_count == total_symbols:
            logger.info(f"Hoàn thành: {success_count}/{total_symbols} stocks thành công")
            logger.info("🎉 Thu thập dữ liệu US market thành công!")
            return True
        else:
            logger.error(f"❌ Lỗi thu thập dữ liệu cổ phiếu US")
            logger.info(f"Hoàn thành: {success_count}/{total_symbols} stocks thành công")
            logger.error("❌ Thu thập dữ liệu US market thất bại!")
            return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Collect daily stock data for US market from yfinance.")
    parser.add_argument('--days_back', type=int, default=3,
                        help='Number of days back to collect data.')
    parser.add_argument('--symbols', nargs='*', type=str,
                        help='Specific stock symbols to collect (e.g., AAPL MSFT GOOGL).')
    args = parser.parse_args()

    collector = USStockCollector()
    collector.collect_data(days_back=args.days_back, symbols=args.symbols)
