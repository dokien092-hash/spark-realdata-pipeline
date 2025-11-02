#!/usr/bin/env python3
"""
Vietnam Stock Market Data Collector using yfinance
Thu thập dữ liệu cổ phiếu Việt Nam từ yfinance
"""

import yfinance as yf
import psycopg2
from datetime import datetime, timedelta
import logging
import time
import pandas as pd
import argparse
import os
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Database configuration
POSTGRES_CONFIG = {
    'host': os.getenv('POSTGRES_HOST', 'postgres'),
    'database': os.getenv('POSTGRES_DB', 'realdata_warehouse'),
    'user': os.getenv('POSTGRES_USER', 'postgres'),
    'password': os.getenv('POSTGRES_PASSWORD', 'postgres'),
    'port': os.getenv('POSTGRES_PORT', '5432')
}

class VNStockCollector:
    def __init__(self):
        self.postgres_config = POSTGRES_CONFIG
        self.connection = None
        self.fail_count = 0  # Đếm số lần fail liên tiếp
        self.max_fails = 7   # Dừng sau 7 lần fail liên tiếp
        
        # Danh sách cổ phiếu VN thực tế và đã kiểm tra (52 stocks thành công)
        self.vn_stocks = [
            # Blue chips - VN30 (Top stocks)
            'VNM',  # Vinamilk
            'VIC',  # Vingroup
            'VHM',  # Vinhomes
            'VCB',  # Vietcombank
            'HPG',  # Hoa Phat Group
            'MSN',  # Masan Group
            'GAS',  # PetroVietnam Gas
            'VRE',  # Vincom Retail
            'PLX',  # Petrolimex
            'POW',  # PetroVietnam Power
            'VJC',  # VietJet Air
            'VGC',  # Viglacera
            'SAB',  # Sabeco
            'VSH',  # Vietnam Shipbuilding Industry
            'VPI',  # Vietnam Petroleum Institute
            
            # Banking & Finance (Major banks)
            'BID',  # BIDV
            'CTG',  # VietinBank
            'ACB',  # Asia Commercial Bank
            'TCB',  # Techcombank
            'MBB',  # Military Bank
            'STB',  # Saigon Thuong Tin Bank
            'TPB',  # Tien Phong Bank
            'EIB',  # Eximbank
            'HDB',  # HDBank
            'LPB',  # Lien Viet Post Bank
            'VIB',  # Vietnam International Bank
            'SSI',  # SSI Securities
            'VCI',  # Viet Capital Securities
            'VND',  # VNDirect Securities
            
            # Technology & Telecom
            'FPT',  # FPT Corporation
            'CMG',  # CMC Corporation
            'ELC',  # Electronic Components
            'ITD',  # ITD Group
            'VTO',  # Viettel Post
            
            # Real Estate & Construction
            'KDH',  # Khang Dien House
            'NVL',  # Novaland
            'PDR',  # Phat Dat Real Estate
            'DXG',  # Dat Xanh Group
            'HDG',  # Ha Do Group
            'CII',  # Ho Chi Minh City Infrastructure Investment
            'CTD',  # Construction Corporation No.1
            'VCG',  # Viettel Construction
            
            # Consumer & Retail
            'MWG',  # Mobile World
            'PNJ',  # Phu Nhuan Jewelry
            'FRT',  # FPT Retail
            'DGW',  # Digiworld
            
            # Energy & Utilities
            'DPM',  # Petrovietnam Fertilizer
            'DQC',  # Dien Quang Lamp
            'DRC',  # Danang Rubber
            'DTA',  # Da Nang Tourism
            'DVP',  # Dinh Vu Port
            'DXS',  # Dong Xanh Port
        ]
    
    def create_connection(self):
        """Tạo kết nối PostgreSQL"""
        try:
            self.connection = psycopg2.connect(**self.postgres_config)
            logger.info("Kết nối PostgreSQL thành công")
            return True
        except Exception as e:
            logger.error(f"Lỗi kết nối PostgreSQL: {e}")
            return False
    
    def fetch_vn_stock_data(self, symbol, days_back=3):
        """Lấy dữ liệu cổ phiếu VN từ yfinance"""
        try:
            logger.info(f"Đang lấy dữ liệu {symbol}...")
            
            # Tạo ticker object
            ticker = yf.Ticker(symbol)
            
            # Lấy dữ liệu historical
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            # Lấy data với period để đảm bảo có data
            data = ticker.history(
                start=start_date,
                end=end_date,
                interval='1d'
            )
            
            if data.empty:
                logger.warning(f"Không có dữ liệu cho {symbol}")
                return None
            
            # Chuyển đổi index thành column
            data = data.reset_index()
            
            # Rename columns để phù hợp với database
            data.columns = data.columns.str.lower()
            data = data.rename(columns={
                'date': 'date',
                'open': 'open_price',
                'high': 'high_price', 
                'low': 'low_price',
                'close': 'close_price',
                'volume': 'volume'
            })
            
            # Thêm thông tin bổ sung
            data['symbol'] = symbol  # Giữ nguyên symbol (đã bỏ .VN từ đầu)
            data['exchange'] = 'HOSE'  # Mặc định HOSE, có thể cải thiện sau
            data['currency'] = 'VND'
            data['source'] = 'yfinance'
            
            # Tính daily return
            data['daily_return'] = data['close_price'].pct_change() * 100
            
            # Làm sạch data
            data = data.dropna(subset=['open_price', 'close_price'])
            
            logger.info(f"Lấy được {symbol}: {len(data)} ngày")
            return data
            
        except Exception as e:
            logger.error(f"Lỗi khi lấy dữ liệu {symbol}: {e}")
            return None
    
    def save_to_database(self, df, symbol):
        """Lưu dữ liệu vào database"""
        if df is None or df.empty:
            return False
        
        try:
            cursor = self.connection.cursor()
            
            # Tạo bảng nếu chưa có
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS stocks.stocks_daily_yahoo (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                symbol VARCHAR(20) NOT NULL,
                date DATE NOT NULL,
                exchange VARCHAR(10),
                open_price NUMERIC(15,2),
                high_price NUMERIC(15,2),
                low_price NUMERIC(15,2),
                close_price NUMERIC(15,2),
                volume BIGINT,
                daily_return NUMERIC(8,4),
                currency VARCHAR(3),
                source VARCHAR(20),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(date, symbol)
            );
            """
            cursor.execute(create_table_sql)
            
            # Insert data với ON CONFLICT
            for _, row in df.iterrows():
                insert_sql = """
                INSERT INTO stocks.stocks_daily_yahoo 
                (symbol, date, exchange, open_price, high_price, low_price, 
                 close_price, volume, daily_return, currency, source)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (date, symbol) 
                DO UPDATE SET
                    open_price = EXCLUDED.open_price,
                    high_price = EXCLUDED.high_price,
                    low_price = EXCLUDED.low_price,
                    close_price = EXCLUDED.close_price,
                    volume = EXCLUDED.volume,
                    daily_return = EXCLUDED.daily_return,
                    source = EXCLUDED.source,
                    created_at = CURRENT_TIMESTAMP;
                """
                
                cursor.execute(insert_sql, (
                    row['symbol'],
                    row['date'].date(),
                    row['exchange'],
                    row['open_price'],
                    row['high_price'],
                    row['low_price'],
                    row['close_price'],
                    int(row['volume']) if pd.notna(row['volume']) else 0,
                    row['daily_return'] if pd.notna(row['daily_return']) else 0,
                    row['currency'],
                    row['source']
                ))
            
            self.connection.commit()
            cursor.close()
            
            logger.info(f"Đã lưu {len(df)} records cho {symbol}")
            return True
            
        except Exception as e:
            logger.error(f"Lỗi khi lưu dữ liệu {symbol}: {e}")
            return False
    
    def collect_vn_market_data(self, days_back=3):
        """Thu thập dữ liệu toàn bộ thị trường VN"""
        logger.info(f"Bắt đầu thu thập dữ liệu VN market ({len(self.vn_stocks)} stocks)")
        
        if not self.create_connection():
            return False
        
        success_count = 0
        total_count = len(self.vn_stocks)
        
        for idx, symbol in enumerate(self.vn_stocks):
            try:
                logger.info(f"Xử lý {idx+1}/{total_count}: {symbol}")
                
                # Kiểm tra fail counter
                if self.fail_count >= self.max_fails:
                    logger.error(f"🛑 DỪNG: Đã fail {self.fail_count} lần liên tiếp (max: {self.max_fails})")
                    logger.error("🛑 Tạm dừng luồng để tránh rate limiting từ Yahoo Finance")
                    break
                
                # Lấy dữ liệu
                df = self.fetch_vn_stock_data(symbol, days_back)
                
                if df is not None and not df.empty:
                    # Lưu vào database
                    if self.save_to_database(df, symbol):
                        success_count += 1
                        self.fail_count = 0  # Reset fail counter khi thành công
                        logger.info(f"✅ {symbol}: Thành công")
                    else:
                        self.fail_count += 1
                        logger.error(f"❌ {symbol}: Lỗi lưu database (fail: {self.fail_count})")
                else:
                    self.fail_count += 1
                    logger.warning(f"⚠️ {symbol}: Không có dữ liệu (fail: {self.fail_count})")
                
                # Delay để tránh rate limiting
                if idx < total_count - 1:
                    time.sleep(5)  # 5 giây delay để tránh rate limit
                    
            except Exception as e:
                self.fail_count += 1
                logger.error(f"❌ {symbol}: Lỗi - {e} (fail: {self.fail_count})")
                continue
        
        # Đóng kết nối
        if self.connection:
            self.connection.close()
        
        logger.info(f"Hoàn thành: {success_count}/{total_count} stocks thành công")
        return success_count > 0

def main():
    parser = argparse.ArgumentParser(description='Vietnam Stock Market Data Collector')
    parser.add_argument('--days_back', type=int, default=3, help='Số ngày lấy dữ liệu (default: 3)')
    parser.add_argument('--symbols', nargs='+', help='Danh sách symbols cụ thể (optional)')
    
    args = parser.parse_args()
    
    # Khởi tạo collector
    collector = VNStockCollector()
    
    # Override symbols nếu được chỉ định
    if args.symbols:
        collector.vn_stocks = [s + '.VN' if not s.endswith('.VN') else s for s in args.symbols]
        logger.info(f"Sử dụng symbols: {collector.vn_stocks}")
    
    # Thu thập dữ liệu
    success = collector.collect_vn_market_data(args.days_back)
    
    if success:
        logger.info("🎉 Thu thập dữ liệu VN market thành công!")
        print("✅ Hoàn thành thu thập dữ liệu cổ phiếu Việt Nam")
    else:
        logger.error("❌ Thu thập dữ liệu VN market thất bại!")
        print("❌ Lỗi thu thập dữ liệu cổ phiếu Việt Nam")
        exit(1)

if __name__ == "__main__":
    main()