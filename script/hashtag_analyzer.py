import os
import sys
import configparser
import sqlite3
from datetime import datetime, timedelta
import logging

# Add utils to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from utils import database

def get_config():
    """Loads configuration from settings.ini."""
    config = configparser.ConfigParser()
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'settings.ini')
    config.read(config_path)
    return config

def analyze_hashtag_trends(db_name, db_path="data/", top_n=20):
    """
    Analyzes hashtag trends from the database.
    
    Args:
        db_name: Name of the database file
        db_path: Path where the database is stored
        top_n: Number of top hashtags to analyze
    """
    conn = database.get_db_connection(db_name, db_path)
    if not conn:
        print("Failed to connect to database")
        return
    
    print("TIKTOK HASHTAG TREND ANALYSIS")
    print("="*60)
    
    # Get trending hashtags
    trends = database.get_hashtag_trends(conn, limit=top_n)
    
    if not trends:
        print("No trending hashtags found. Make sure data has been ingested.")
        conn.close()
        return
    
    print(f"\nTop {len(trends)} Trending Hashtags:")
    print("-" * 60)
    print(f"{'Rank':<4} {'Hashtag':<20} {'Uses':<8} {'Creators':<10} {'Avg Likes':<12}")
    print("-" * 60)
    
    for i, trend in enumerate(trends, 1):
        print(f"{i:<4} #{trend['hashtag']:<19} {trend['usage_count']:<8} "
              f"{trend['unique_creators']:<10} {trend['avg_likes']:<12}")
    
    # Additional analysis
    cursor = conn.cursor()
    
    # Get engagement metrics
    print(f"\n\nENGAGEMENT ANALYSIS")
    print("="*60)
    
    cursor.execute("""
        SELECT 
            h.name,
            AVG(v.like_count) as avg_likes,
            AVG(v.comment_count) as avg_comments,
            AVG(v.share_count) as avg_shares,
            AVG(v.play_count) as avg_views,
            (AVG(v.like_count) + AVG(v.comment_count) + AVG(v.share_count)) as engagement_score
        FROM hashtags h
        JOIN video_hashtags vh ON h.id = vh.hashtag_id
        JOIN videos v ON vh.video_id = v.id
        WHERE h.total_usage_count >= 50
        GROUP BY h.id, h.name
        ORDER BY engagement_score DESC
        LIMIT 10
    """)
    
    engagement_results = cursor.fetchall()
    
    print(f"\nTop 10 Hashtags by Engagement:")
    print("-" * 60)
    print(f"{'Hashtag':<20} {'Avg Likes':<12} {'Avg Comments':<14} {'Avg Shares':<12} {'Engagement':<12}")
    print("-" * 60)
    
    for row in engagement_results:
        hashtag, avg_likes, avg_comments, avg_shares, avg_views, engagement = row
        print(f"#{hashtag:<19} {avg_likes:<12.0f} {avg_comments:<14.0f} {avg_shares:<12.0f} {engagement:<12.0f}")
    
    # Creator analysis
    print(f"\n\nCREATOR DIVERSITY ANALYSIS")
    print("="*60)
    
    cursor.execute("""
        SELECT 
            h.name,
            COUNT(DISTINCT v.author_id) as unique_creators,
            h.total_usage_count,
            ROUND(CAST(COUNT(DISTINCT v.author_id) AS FLOAT) / h.total_usage_count * 100, 2) as diversity_ratio
        FROM hashtags h
        JOIN video_hashtags vh ON h.id = vh.hashtag_id
        JOIN videos v ON vh.video_id = v.id
        WHERE h.total_usage_count >= 20
        GROUP BY h.id, h.name, h.total_usage_count
        ORDER BY diversity_ratio DESC
        LIMIT 10
    """)
    
    diversity_results = cursor.fetchall()
    
    print(f"\nHashtags with Highest Creator Diversity:")
    print("-" * 60)
    print(f"{'Hashtag':<20} {'Creators':<10} {'Total Uses':<12} {'Diversity %':<12}")
    print("-" * 60)
    
    for row in diversity_results:
        hashtag, creators, total_uses, diversity = row
        print(f"#{hashtag:<19} {creators:<10} {total_uses:<12} {diversity:<12}%")
    
    conn.close()
    
    print(f"\nAnalysis complete! Database: {os.path.join(db_path, db_name)}")

def search_hashtag(db_name, hashtag_name, db_path="data/"):
    """
    Searches for specific hashtag information.
    
    Args:
        db_name: Name of the database file
        hashtag_name: Name of hashtag to search (without #)
        db_path: Path where the database is stored
    """
    conn = database.get_db_connection(db_name, db_path)
    if not conn:
        return
    
    cursor = conn.cursor()
    
    # Clean hashtag name
    hashtag_name = hashtag_name.strip().lower().replace('#', '')
    
    # Get hashtag info
    cursor.execute("""
        SELECT 
            h.name,
            h.total_usage_count,
            COUNT(DISTINCT v.author_id) as unique_creators,
            AVG(v.like_count) as avg_likes,
            AVG(v.comment_count) as avg_comments,
            AVG(v.share_count) as avg_shares,
            AVG(v.play_count) as avg_views,
            MIN(v.create_time) as first_seen,
            MAX(v.create_time) as last_seen
        FROM hashtags h
        JOIN video_hashtags vh ON h.id = vh.hashtag_id
        JOIN videos v ON vh.video_id = v.id
        WHERE h.name = ?
        GROUP BY h.id, h.name, h.total_usage_count
    """, (hashtag_name,))
    
    result = cursor.fetchone()
    
    if not result:
        print(f"Hashtag '#{hashtag_name}' not found in database.")
        conn.close()
        return
    
    name, usage_count, unique_creators, avg_likes, avg_comments, avg_shares, avg_views, first_seen, last_seen = result
    
    print(f"\nHASHTAG ANALYSIS: #{name}")
    print("="*50)
    print(f"Total Usage: {usage_count:,}")
    print(f"Unique Creators: {unique_creators:,}")
    print(f"Average Likes: {avg_likes:,.0f}")
    print(f"Average Comments: {avg_comments:,.0f}")
    print(f"Average Shares: {avg_shares:,.0f}")
    print(f"Average Views: {avg_views:,.0f}")
    
    if first_seen:
        first_date = datetime.fromtimestamp(first_seen).strftime('%Y-%m-%d')
        last_date = datetime.fromtimestamp(last_seen).strftime('%Y-%m-%d')
        print(f"First Seen: {first_date}")
        print(f"Last Seen: {last_date}")
    
    # Get top videos for this hashtag
    cursor.execute("""
        SELECT 
            v.id,
            v.author_name,
            v.like_count,
            v.comment_count,
            v.play_count,
            v.video_description
        FROM videos v
        JOIN video_hashtags vh ON v.id = vh.video_id
        JOIN hashtags h ON vh.hashtag_id = h.id
        WHERE h.name = ?
        ORDER BY v.like_count DESC
        LIMIT 5
    """, (hashtag_name,))
    
    top_videos = cursor.fetchall()
    
    if top_videos:
        print(f"\nTop 5 Videos with #{name}:")
        print("-" * 50)
        for i, video in enumerate(top_videos, 1):
            video_id, author, likes, comments, views, description = video
            print(f"{i}. @{author} - {likes:,} likes, {views:,} views")
            print(f"   {description[:100]}...")
            print()
    
    conn.close()

if __name__ == "__main__":
    # Load configuration
    config = get_config()
    db_name = config['DATABASE']['db_name']
    db_path = config['DATABASE']['db_path']
    
    import argparse
    
    parser = argparse.ArgumentParser(description='Analyze TikTok hashtag trends')
    parser.add_argument('--hashtag', type=str, help='Search for specific hashtag')
    parser.add_argument('--top', '-t', type=int, default=20, help='Number of top hashtags to show')
    
    args = parser.parse_args()
    
    if args.hashtag:
        search_hashtag(db_name, args.hashtag, db_path)
    else:
        analyze_hashtag_trends(db_name, db_path, args.top)
