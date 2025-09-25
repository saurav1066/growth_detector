import sqlite3
import logging
import os
from typing import List, Dict, Any, Optional

def get_db_connection(db_name: str, db_path: str = "data/") -> Optional[sqlite3.Connection]:
    """
    Establishes a connection to the SQLite database.
    
    Args:
        db_name: Name of the database file
        db_path: Path where the database should be stored
        
    Returns:
        SQLite connection object or None if failed
    """
    try:
        # Ensure the database directory exists
        os.makedirs(db_path, exist_ok=True)
        
        db_full_path = os.path.join(db_path, db_name)
        conn = sqlite3.connect(db_full_path)
        conn.execute("PRAGMA foreign_keys = ON")
        logging.info(f"Connected to database: {db_full_path}")
        return conn
    except Exception as e:
        logging.error(f"Failed to connect to database: {e}")
        return None

def create_tables(conn: sqlite3.Connection) -> None:
    """
    Creates the necessary tables for TikTok data analysis.
    
    Args:
        conn: SQLite database connection
    """
    cursor = conn.cursor()
    
    # Create videos table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS videos (
            id TEXT PRIMARY KEY,
            author_id TEXT,
            author_name TEXT,
            author_nickname TEXT,
            create_time INTEGER,
            collection_timestamp INTEGER,
            video_description TEXT,
            play_count INTEGER DEFAULT 0,
            like_count INTEGER DEFAULT 0,
            comment_count INTEGER DEFAULT 0,
            share_count INTEGER DEFAULT 0,
            video_duration INTEGER,
            video_height INTEGER,
            video_width INTEGER,
            music_name TEXT,
            music_author TEXT,
            web_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create hashtags table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS hashtags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            total_usage_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create video_hashtags junction table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS video_hashtags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id TEXT,
            hashtag_id INTEGER,
            FOREIGN KEY (video_id) REFERENCES videos(id),
            FOREIGN KEY (hashtag_id) REFERENCES hashtags(id),
            UNIQUE(video_id, hashtag_id)
        )
    ''')
    
    # Create indexes for better performance
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_videos_create_time ON videos(create_time)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_videos_collection_timestamp ON videos(collection_timestamp)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_videos_author ON videos(author_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_hashtags_name ON hashtags(name)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_video_hashtags_video ON video_hashtags(video_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_video_hashtags_hashtag ON video_hashtags(hashtag_id)')
    
    conn.commit()
    logging.info("Database tables created successfully")

def insert_hashtag(conn: sqlite3.Connection, hashtag_name: str) -> int:
    """
    Inserts a hashtag or returns existing hashtag ID.
    
    Args:
        conn: SQLite database connection
        hashtag_name: Name of the hashtag (without #)
        
    Returns:
        Hashtag ID
    """
    cursor = conn.cursor()
    
    # Clean hashtag name
    hashtag_name = hashtag_name.strip().lower().replace('#', '')
    
    if not hashtag_name:
        return None
    
    try:
        # Try to insert new hashtag
        cursor.execute(
            'INSERT INTO hashtags (name, total_usage_count) VALUES (?, 1)',
            (hashtag_name,)
        )
        hashtag_id = cursor.lastrowid
        logging.debug(f"Created new hashtag: {hashtag_name} with ID: {hashtag_id}")
    except sqlite3.IntegrityError:
        # Hashtag already exists, get its ID and increment usage count
        cursor.execute('SELECT id FROM hashtags WHERE name = ?', (hashtag_name,))
        hashtag_id = cursor.fetchone()[0]
        cursor.execute(
            'UPDATE hashtags SET total_usage_count = total_usage_count + 1 WHERE id = ?',
            (hashtag_id,)
        )
        logging.debug(f"Updated existing hashtag: {hashtag_name} with ID: {hashtag_id}")
    
    return hashtag_id

def insert_videos(conn: sqlite3.Connection, videos_data: List[Dict[str, Any]]) -> None:
    """
    Inserts video data into the database.
    
    Args:
        conn: SQLite database connection
        videos_data: List of video data dictionaries
    """
    cursor = conn.cursor()
    
    for video_data in videos_data:
        try:
            # Extract video information
            video_id = str(video_data.get('id', ''))
            author_id = str(video_data.get('author_id', ''))
            author_name = video_data.get('author_name', '')
            author_nickname = video_data.get('author_nickname', '')
            create_time = video_data.get('create_time', 0)
            collection_timestamp = video_data.get('collection_timestamp', 0)
            video_description = video_data.get('video_description', '')
            
            # Extract stats
            stats = video_data.get('stats', {})
            play_count = stats.get('play_count', 0) or 0
            like_count = stats.get('like_count', 0) or 0
            comment_count = stats.get('comment_count', 0) or 0
            share_count = stats.get('share_count', 0) or 0
            
            # Extract video metadata
            video_duration = video_data.get('video_duration', 0)
            video_height = video_data.get('video_height', 0)
            video_width = video_data.get('video_width', 0)
            music_name = video_data.get('music_name', '')
            music_author = video_data.get('music_author', '')
            web_url = video_data.get('web_url', '')
            
            # Insert video
            cursor.execute('''
                INSERT OR REPLACE INTO videos (
                    id, author_id, author_name, author_nickname, create_time, collection_timestamp,
                    video_description, play_count, like_count, comment_count, share_count,
                    video_duration, video_height, video_width, music_name, music_author, web_url
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                video_id, author_id, author_name, author_nickname, create_time, collection_timestamp,
                video_description, play_count, like_count, comment_count, share_count,
                video_duration, video_height, video_width, music_name, music_author, web_url
            ))
            
            # Process hashtags
            hashtags = video_data.get('hashtags', [])
            for hashtag in hashtags:
                if isinstance(hashtag, dict):
                    hashtag_name = hashtag.get('name', '')
                else:
                    hashtag_name = str(hashtag)
                
                if hashtag_name:
                    hashtag_id = insert_hashtag(conn, hashtag_name)
                    if hashtag_id:
                        # Link video to hashtag
                        try:
                            cursor.execute(
                                'INSERT OR IGNORE INTO video_hashtags (video_id, hashtag_id) VALUES (?, ?)',
                                (video_id, hashtag_id)
                            )
                        except Exception as e:
                            logging.warning(f"Failed to link video {video_id} to hashtag {hashtag_name}: {e}")
            
            logging.debug(f"Inserted video: {video_id}")
            
        except Exception as e:
            logging.error(f"Failed to insert video {video_data.get('id', 'unknown')}: {e}")
            continue
    
    conn.commit()
    logging.info(f"Inserted {len(videos_data)} videos")

def get_hashtag_trends(conn: sqlite3.Connection, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Gets trending hashtags based on usage count.
    
    Args:
        conn: SQLite database connection
        limit: Maximum number of hashtags to return
        
    Returns:
        List of hashtag trend data
    """
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            h.name,
            h.total_usage_count,
            COUNT(DISTINCT v.author_id) as unique_creators,
            AVG(v.like_count) as avg_likes,
            AVG(v.play_count) as avg_views,
            AVG(v.comment_count) as avg_comments,
            AVG(v.share_count) as avg_shares
        FROM hashtags h
        JOIN video_hashtags vh ON h.id = vh.hashtag_id
        JOIN videos v ON vh.video_id = v.id
        WHERE h.total_usage_count >= 10
        GROUP BY h.id, h.name, h.total_usage_count
        ORDER BY h.total_usage_count DESC
        LIMIT ?
    ''', (limit,))
    
    results = cursor.fetchall()
    
    trends = []
    for row in results:
        trends.append({
            'hashtag': row[0],
            'usage_count': row[1],
            'unique_creators': row[2],
            'avg_likes': round(row[3] or 0, 2),
            'avg_views': round(row[4] or 0, 2),
            'avg_comments': round(row[5] or 0, 2),
            'avg_shares': round(row[6] or 0, 2)
        })
    
    return trends
