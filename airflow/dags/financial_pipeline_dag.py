

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.operators.postgres import PostgresOperator
import logging

# Default arguments
default_args = {
    'owner': 'financial-pipeline',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=10),
}

# DAG definition
dag = DAG(
    'financial_pipeline_dag',
    default_args=default_args,
    description='Daily stock data collection pipeline',
    schedule_interval='0 22 * * 1-5',  # Chạy lúc 22:00 UTC (5:00 sáng VN) từ T2-T6
    catchup=False,
    max_active_runs=3,  # Tăng từ 1 lên 3 để tránh blocking
    tags=['stocks', 'daily-collection']
)

# Task: Thu thập dữ liệu US stocks với fallback thông minh
def trigger_daily_stock_collection():
    """
    Thu thập dữ liệu cổ phiếu US với fallback thông minh:
    1. Kiểm tra ngày chứng khoán đóng cửa
    2. Thử Alpha Vantage (ưu tiên - 25 calls/day)
    3. Nếu thất bại → Fallback Polygon (5 calls/minute)
    """
    import subprocess
    import os
    from datetime import datetime, timedelta
    
    # Kiểm tra ngày chứng khoán đóng cửa
    today = datetime.now()
    weekday = today.weekday()  # 0=Monday, 6=Sunday
    
    # Kiểm tra weekend (Saturday=5, Sunday=6)
    if weekday >= 5:
        logging.info(f"US Market: Đóng cửa vào cuối tuần (weekday={weekday})")
        logging.info("US Market: Bỏ qua thu thập dữ liệu")
        return True
    
    # Kiểm tra ngày lễ US (có thể mở rộng thêm)
    # TODO: Thêm logic kiểm tra ngày lễ US (New Year, Independence Day, Thanksgiving, Christmas)
    
    # Bước 1: Thử Alpha Vantage (primary) - với timeout
    logging.info("Đang thử Alpha Vantage (primary)...")
    try:
        result = subprocess.run([
            'python', '/opt/airflow/jobs/data_processing/collect_alpha_vantage.py', '--days_back', '1'
        ], capture_output=True, text=True, env=os.environ.copy(), timeout=300)  # 5 phút timeout
        
        logging.info(f"Alpha output: {result.stdout}")
        logging.info(f"Alpha error: {result.stderr}")
        
        # Kiểm tra xem có lấy được data không
        alpha_success = (
            result.returncode == 0 and 
            ("Hoàn thành" in result.stdout or "Collected" in result.stdout) and 
            "0 bản ghi" not in result.stdout and
            "0 records" not in result.stdout and
            "bản ghi từ" in result.stdout  # Có dữ liệu được thu thập
        )
    except subprocess.TimeoutExpired:
        logging.error("Alpha Vantage: Timeout sau 5 phút")
        alpha_success = False
    
    if alpha_success:
        logging.info("Alpha Vantage: Thành công, đã lấy được dữ liệu US")
        return True
    else:
        logging.warning("Alpha Vantage: Thất bại, chuyển sang Polygon...")
        
        # Bước 2: Fallback sang Polygon - với timeout
        logging.info("Fallback: Đang thử Polygon...")
        try:
            result = subprocess.run([
                'python', '/opt/airflow/jobs/data_processing/collect_polygon.py', '--days_back', '1'
            ], capture_output=True, text=True, env=os.environ.copy(), timeout=600)  # 10 phút timeout
            
            logging.info(f"Polygon output: {result.stdout}")
            
            if result.returncode == 0:
                logging.info("Polygon: Fallback thành công")
                return True
            else:
                logging.error("Cả 2 nguồn đều thất bại (Alpha + Polygon)")
                logging.error(f"Polygon error: {result.stderr}")
                return False
        except subprocess.TimeoutExpired:
            logging.error("Polygon: Timeout sau 10 phút")
            logging.error("Cả 2 nguồn đều thất bại (Alpha timeout + Polygon timeout)")
            return False

# Task: Thu thập dữ liệu VN stocks (TẠM DỪNG)
def trigger_vn_stock_collection():
    """
    Thu thập dữ liệu cổ phiếu Việt Nam từ yfinance
    TẠM DỪNG để tránh rate limiting
    """
    import subprocess
    import os
    from datetime import datetime
    
    # Kiểm tra ngày chứng khoán đóng cửa VN
    today = datetime.now()
    weekday = today.weekday()  # 0=Monday, 6=Sunday
    
    # Kiểm tra weekend (Saturday=5, Sunday=6)
    if weekday >= 5:
        logging.info(f"VN Market: Đóng cửa vào cuối tuần (weekday={weekday})")
        logging.info("VN Market: Bỏ qua thu thập dữ liệu")
        return True
    
    # Kiểm tra ngày lễ VN (có thể mở rộng thêm)
    # TODO: Thêm logic kiểm tra ngày lễ VN
    
    logging.info("VN Market: TẠM DỪNG để tránh rate limiting")
    logging.info("VN Market: Sẽ được kích hoạt lại sau khi fix yfinance")
    return True  # Return success để không block pipeline

# US Market Collection Task
us_stock_collection_task = PythonOperator(
    task_id='us_stock_collection',
    python_callable=trigger_daily_stock_collection,
    dag=dag
)

# VN Market Collection Task  
vn_stock_collection_task = PythonOperator(
    task_id='vn_stock_collection',
    python_callable=trigger_vn_stock_collection,
    dag=dag
)

# Task: Bảo trì database hàng ngày
db_maintenance_task = PostgresOperator(
    task_id='database_maintenance',
    postgres_conn_id='postgres_default',
    sql="""
    -- Xóa dữ liệu cũ hơn 90 ngày (giữ 3 tháng)
    DELETE FROM stocks.stocks_daily_polygon WHERE date < CURRENT_DATE - INTERVAL '90 days';
    DELETE FROM stocks.stocks_daily_alphavantage WHERE date < CURRENT_DATE - INTERVAL '90 days';
    DELETE FROM stocks.stocks_daily_yahoo WHERE date < CURRENT_DATE - INTERVAL '90 days';
    
    -- Cập nhật thống kê database
    ANALYZE stocks.stocks_daily_polygon;
    ANALYZE stocks.stocks_daily_alphavantage;
    ANALYZE stocks.stocks_daily_yahoo;
    
    -- Log tổng kết từ view tổng hợp
    SELECT 
        'Maintenance completed' as status,
        COUNT(*) as total_records,
        COUNT(DISTINCT symbol) as unique_symbols,
        COUNT(DISTINCT source) as data_sources,
        MIN(date) as earliest_date,
        MAX(date) as latest_date
    FROM stocks.stocks_daily_all;
    """,
    dag=dag
)

# Luồng chạy: Thu thập US + VN data song song → Bảo trì database
[us_stock_collection_task, vn_stock_collection_task] >> db_maintenance_task

