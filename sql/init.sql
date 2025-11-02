-- Financial Data Pipeline Database Schema
-- Multi-source data with intelligent deduplication

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Tạo schema riêng cho stock data (tách khỏi Airflow metadata)
CREATE SCHEMA IF NOT EXISTS stocks;

-- ============================================
-- PRIMARY TABLES (Data Sources)
-- ============================================

-- Stocks Daily Data Table (Polygon.io source)
CREATE TABLE IF NOT EXISTS stocks.stocks_daily_polygon (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    symbol VARCHAR(20) NOT NULL,
    date DATE NOT NULL,
    sector VARCHAR(100),
    open_price NUMERIC(12,4),
    high_price NUMERIC(12,4),
    low_price NUMERIC(12,4),
    close_price NUMERIC(12,4),
    volume BIGINT,
    market_cap BIGINT,
    avg_pe_ratio NUMERIC(8,2),
    daily_return NUMERIC(8,4),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(date, symbol)
);

-- Alpha Vantage Data Table (Most reliable source)
CREATE TABLE IF NOT EXISTS stocks.stocks_daily_alphavantage (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    symbol VARCHAR(20) NOT NULL,
    date DATE NOT NULL,
    sector VARCHAR(100),
    open_price NUMERIC(12,4),
    high_price NUMERIC(12,4),
    low_price NUMERIC(12,4),
    close_price NUMERIC(12,4),
    volume BIGINT,
    market_cap BIGINT,
    avg_pe_ratio NUMERIC(8,2),
    daily_return NUMERIC(8,4),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(date, symbol)
);

-- Yahoo Finance Data Table (Backup source)
CREATE TABLE IF NOT EXISTS stocks.stocks_daily_yahoo (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    symbol VARCHAR(20) NOT NULL,
    date DATE NOT NULL,
    sector VARCHAR(100),
    open_price NUMERIC(12,4),
    high_price NUMERIC(12,4),
    low_price NUMERIC(12,4),
    close_price NUMERIC(12,4),
    volume BIGINT,
    market_cap BIGINT,
    avg_pe_ratio NUMERIC(8,2),
    daily_return NUMERIC(8,4),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(date, symbol)
);

-- ============================================
-- UNIFIED VIEW (Smart Deduplication)
-- ============================================
-- Priority: Alpha Vantage > Polygon > Yahoo
CREATE OR REPLACE VIEW stocks.stocks_daily_all AS
WITH ranked_data AS (
    SELECT 
        id, symbol, date, sector, open_price, high_price, low_price,
        close_price, volume, market_cap, avg_pe_ratio, daily_return,
        created_at,
        'alphavantage' as source,
        1 as priority
    FROM stocks.stocks_daily_alphavantage
    
    UNION ALL
    
    SELECT 
        id, symbol, date, sector, open_price, high_price, low_price,
        close_price, volume, market_cap, avg_pe_ratio, daily_return,
        created_at,
        CASE 
            WHEN created_at >= '2025-10-15' THEN 'polygon'
            ELSE 'yahoo'
        END as source,
        2 as priority
    FROM stocks.stocks_daily_polygon
    
    UNION ALL
    
    SELECT 
        id, symbol, date, sector, open_price, high_price, low_price,
        close_price, volume, market_cap, avg_pe_ratio, daily_return,
        created_at,
        'yahoo' as source,
        3 as priority
    FROM stocks.stocks_daily_yahoo
),
deduplicated AS (
    SELECT 
        *,
        ROW_NUMBER() OVER (PARTITION BY symbol, date ORDER BY priority ASC, created_at DESC) as rn
    FROM ranked_data
)
SELECT 
    id, symbol, date, sector, open_price, high_price, low_price,
    close_price, volume, market_cap, avg_pe_ratio, daily_return,
    created_at, source
FROM deduplicated
WHERE rn = 1;

-- ============================================
-- INDEXES (Performance Optimization)
-- ============================================
-- Polygon table indexes
CREATE INDEX IF NOT EXISTS idx_polygon_date_symbol ON stocks.stocks_daily_polygon(date, symbol);
CREATE INDEX IF NOT EXISTS idx_polygon_date ON stocks.stocks_daily_polygon(date);
CREATE INDEX IF NOT EXISTS idx_polygon_symbol ON stocks.stocks_daily_polygon(symbol);

-- Alpha Vantage table indexes
CREATE INDEX IF NOT EXISTS idx_alpha_date_symbol ON stocks.stocks_daily_alphavantage(date, symbol);
CREATE INDEX IF NOT EXISTS idx_alpha_date ON stocks.stocks_daily_alphavantage(date);
CREATE INDEX IF NOT EXISTS idx_alpha_symbol ON stocks.stocks_daily_alphavantage(symbol);

-- Yahoo table indexes
CREATE INDEX IF NOT EXISTS idx_yahoo_date_symbol ON stocks.stocks_daily_yahoo(date, symbol);
CREATE INDEX IF NOT EXISTS idx_yahoo_date ON stocks.stocks_daily_yahoo(date);
CREATE INDEX IF NOT EXISTS idx_yahoo_symbol ON stocks.stocks_daily_yahoo(symbol);

-- ============================================
-- ANALYSIS VIEWS (Common Queries)
-- ============================================
CREATE OR REPLACE VIEW daily_market_summary AS
SELECT 
    date,
    COUNT(DISTINCT symbol) as total_stocks,
    AVG(close_price) as avg_price,
    AVG(daily_return) as avg_return,
    SUM(volume) as total_volume,
    SUM(market_cap) as total_market_cap
FROM stocks.stocks_daily_all 
GROUP BY date
ORDER BY date DESC;

CREATE OR REPLACE VIEW top_performers AS
SELECT 
    symbol,
    date,
    close_price,
    daily_return,
    sector,
    volume,
    market_cap
FROM stocks.stocks_daily_all 
WHERE daily_return > 0
ORDER BY daily_return DESC
LIMIT 10;

CREATE OR REPLACE VIEW sector_performance AS
SELECT 
    sector,
    date,
    COUNT(*) as stock_count,
    AVG(daily_return) as avg_return,
    SUM(market_cap) as total_market_cap
FROM stocks.stocks_daily_all 
WHERE sector IS NOT NULL
GROUP BY sector, date
ORDER BY avg_return DESC;

CREATE OR REPLACE VIEW monthly_performance AS
SELECT 
    symbol,
    COUNT(*) as trading_days,
    AVG(daily_return) as avg_daily_return,
    MIN(close_price) as min_price,
    MAX(close_price) as max_price,
    SUM(daily_return) as total_return,
    AVG(volume) as avg_volume,
    AVG(market_cap) as avg_market_cap
FROM stocks.stocks_daily_all 
GROUP BY symbol
ORDER BY avg_daily_return DESC;

CREATE OR REPLACE VIEW volatility_analysis AS
SELECT 
    symbol,
    COUNT(*) as days,
    AVG(daily_return) as avg_return,
    STDDEV(daily_return) as volatility,
    MIN(daily_return) as worst_day,
    MAX(daily_return) as best_day
FROM stocks.stocks_daily_all 
GROUP BY symbol
HAVING COUNT(*) >= 5
ORDER BY volatility DESC;




