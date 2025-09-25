import pandas as pd
import sqlite3
import time
from datetime import datetime
import configparser
import logging
import os
import sys
import re

# Add utils to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from utils import database

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def get_config():
    """Loads configuration from settings.ini."""
    config = configparser.ConfigParser()
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'settings.ini')
    config.read(config_path)
    return config

def extract_hashtags_from_text(text):
    """
    Extracts hashtags from text using regex pattern.
    
    Args:
        text: Text content that may contain hashtags
        
    Returns:
        List of hashtag names (without # symbol)
    """
    if not text or pd.isna(text):
        return []
    
    # Find all hashtags in the text
    hashtag_pattern = r'#(\w+)'
    hashtags = re.findall(hashtag_pattern, str(text))
    
    return [hashtag.lower() for hashtag in hashtags]

def parse_csv_row(row):
    """
    Parses a CSV row and maps it to our database schema.
    
    Args:
        row: Pandas DataFrame row
        
    Returns:
        Dictionary with mapped video data
    """
    # Extract hashtags from text and dedicated hashtag columns
    hashtags = []
    
    # Get hashtags from text description
    text_hashtags = extract_hashtags_from_text(row.get('text', ''))
    hashtags.extend(text_hashtags)
    
    # Get hashtags from dedicated hashtag columns
    for i in range(10):  # Check for hashtag columns (hashtags/0/name, hashtags/1/name, etc.)
        hashtag_col = f'hashtags/{i}/name'
        if hashtag_col in row and pd.notna(row[hashtag_col]):
            hashtags.append(str(row[hashtag_col]).lower())
    
    # Remove duplicates
    hashtags = list(set(hashtags))
    
    # Parse create time
    create_time = 0
    if 'createTime' in row and pd.notna(row['createTime']):
        try:
            create_time = int(row['createTime'])
        except (ValueError, TypeError):
            create_time = int(time.time())
    
    # Parse counts safely
    def safe_int(value, default=0):
        try:
            return int(float(value)) if pd.notna(value) else default
        except (ValueError, TypeError):
            return default
    
    video_data = {
        'id': str(row.get('id', '')),
        'author_id': str(row.get('authorMeta/id', '')),
        'author_name': str(row.get('authorMeta/name', '')),
        'author_nickname': str(row.get('authorMeta/nickName', '')),
        'create_time': create_time,
        'video_description': str(row.get('text', '')),
        'hashtags': hashtags,
        'stats': {
            'play_count': safe_int(row.get('playCount')),
            'like_count': safe_int(row.get('diggCount')),
            'comment_count': safe_int(row.get('commentCount')),
            'share_count': safe_int(row.get('shareCount')),
        },
        'video_duration': safe_int(row.get('videoMeta/duration')),
        'video_height': safe_int(row.get('videoMeta/height')),
        'video_width': safe_int(row.get('videoMeta/width')),
        'music_name': str(row.get('musicMeta/musicName', '')),
        'music_author': str(row.get('musicMeta/musicAuthor', '')),
        'web_url': str(row.get('webVideoUrl', ''))
    }
    
    return video_data

def ingest_from_csv(csv_path, db_name, db_path="data/", batch_size=1000):
    """
    Ingests data from a CSV file into the SQLite database.
    
    This function processes TikTok data and assigns timestamps for analysis.
    
    Args:
        csv_path: Path to the CSV file
        db_name: Name of the database file
        db_path: Path where the database should be stored
        batch_size: Number of records to process in each batch
    """
    logging.info(f"Starting data ingestion from CSV: {csv_path}")
    
    # Check if file exists
    if not os.path.exists(csv_path):
        logging.error(f"File not found: {csv_path}")
        return False
    
    try:
        # Read CSV file
        logging.info("Reading CSV file...")
        df = pd.read_csv(csv_path)
        logging.info(f"Loaded {len(df)} records from CSV")
        
        # Display column information
        logging.info(f"CSV columns: {list(df.columns)}")
        
    except Exception as e:
        logging.error(f"Error reading CSV file: {e}")
        return False

    # Connect to database
    conn = database.get_db_connection(db_name, db_path)
    if not conn:
        logging.error("Failed to connect to database")
        return False
    
    # Create tables
    database.create_tables(conn)
    logging.info("Database tables created/verified")

    # Process data in batches
    total_records = len(df)
    processed = 0
    failed = 0
    
    # Base timestamp for simulating time series (start from 30 days ago)
    base_timestamp = int(time.time()) - 30 * 24 * 3600
    
    for i in range(0, total_records, batch_size):
        batch_end = min(i + batch_size, total_records)
        batch_df = df.iloc[i:batch_end]
        
        logging.info(f"Processing batch {i//batch_size + 1}: records {i+1} to {batch_end}")
        
        videos_to_insert = []
        
        for idx, row in batch_df.iterrows():
            try:
                # Parse the row
                video_data = parse_csv_row(row)
                
                # Assign collection timestamp (simulate data collection over time)
                video_data['collection_timestamp'] = base_timestamp + processed * 1800  # 30 minute intervals
                
                videos_to_insert.append(video_data)
                processed += 1
                
            except Exception as e:
                logging.warning(f"Failed to process row {idx}: {e}")
                failed += 1
                continue
        
        # Insert batch into database
        try:
            database.insert_videos(conn, videos_to_insert)
            logging.info(f"Successfully inserted batch of {len(videos_to_insert)} videos")
        except Exception as e:
            logging.error(f"Failed to insert batch: {e}")
            failed += len(videos_to_insert)
    
    conn.close()
    
    logging.info("="*50)
    logging.info("CSV INGESTION COMPLETE")
    logging.info(f"Total records processed: {processed}")
    logging.info(f"Total records failed: {failed}")
    logging.info(f"Success rate: {(processed/(processed+failed)*100):.2f}%")
    logging.info("="*50)
    
    return True

def show_database_stats(db_name, db_path="data/"):
    """
    Shows statistics about the ingested data.
    
    Args:
        db_name: Name of the database file
        db_path: Path where the database is stored
    """
    conn = database.get_db_connection(db_name, db_path)
    if not conn:
        return
    
    cursor = conn.cursor()
    
    # Get basic stats
    cursor.execute("SELECT COUNT(*) FROM videos")
    video_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM hashtags")
    hashtag_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM video_hashtags")
    video_hashtag_count = cursor.fetchone()[0]
    
    # Get top hashtags
    cursor.execute("""
        SELECT name, total_usage_count 
        FROM hashtags 
        ORDER BY total_usage_count DESC 
        LIMIT 10
    """)
    top_hashtags = cursor.fetchall()
    
    print("\n" + "="*50)
    print("DATABASE STATISTICS")
    print("="*50)
    print(f"Total Videos: {video_count:,}")
    print(f"Total Unique Hashtags: {hashtag_count:,}")
    print(f"Total Video-Hashtag Relations: {video_hashtag_count:,}")
    
    print(f"\nTop 10 Hashtags:")
    for hashtag, count in top_hashtags:
        print(f"  #{hashtag}: {count:,} uses")
    
    conn.close()

if __name__ == "__main__":
    # Load configuration
    config = get_config()
    db_name = config['DATABASE']['db_name']
    db_path = config['DATABASE']['db_path']
    batch_size = int(config['INGESTION']['batch_size'])
    
    # Set logging level from config
    log_level = config['INGESTION']['log_level']
    logging.getLogger().setLevel(getattr(logging, log_level))
    
    # CSV file path
    csv_file_path = 'data/dataset_free-tiktok-scraper_2022-07-27_21-44-20-266 - Data.csv'
    
    print("TikTok Data Ingestion System")
    print("="*50)
    
    # Ingest data from CSV to SQLite database
    success = ingest_from_csv(csv_file_path, db_name, db_path, batch_size)
    
    if success:
        # Show statistics
        show_database_stats(db_name, db_path)
        
        print(f"\nDatabase created: {os.path.join(db_path, db_name)}")
        print("You can now perform hashtag trend analysis!")
    else:
        print("Ingestion failed. Check the logs for details.")
