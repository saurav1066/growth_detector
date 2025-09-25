#!/usr/bin/env python3
"""
TikTok Hashtag Analysis System - Quick Start Guide
"""

import os
import sys

def main():
    print("🎵 TikTok Hashtag Trend Analysis System")
    print("="*50)
    print()
    
    # Check if database exists
    db_path = "data/tiktok_analysis.db"
    if os.path.exists(db_path):
        print("✅ Database found!")
        file_size = os.path.getsize(db_path) / (1024 * 1024)  # MB
        print(f"📊 Database size: {file_size:.2f} MB")
        print()
    else:
        print("❌ Database not found!")
        print("Run the following command to create it:")
        print("   python script/csv_injestor.py")
        return
    
    print("🚀 Available Commands:")
    print()
    print("1. Analyze trending hashtags:")
    print("   python script/hashtag_analyzer.py")
    print()
    print("2. Show top 50 hashtags:")
    print("   python script/hashtag_analyzer.py --top 50")
    print()
    print("3. Search specific hashtag:")
    print("   python script/hashtag_analyzer.py --hashtag fyp")
    print()
    print("4. Re-ingest CSV data:")
    print("   python script/csv_injestor.py")
    print()
    
    print("📈 Sample Analysis Results:")
    print("• 1,092 videos analyzed")
    print("• 3,325 unique hashtags discovered")
    print("• Top hashtag: #fyp (522 uses, 400 unique creators)")
    print("• Highest engagement: #xyzbca (8.3M avg engagement)")
    print("• Most diverse: #gym (97% creator diversity)")
    print()
    
    print("💡 Tips:")
    print("• Use quotes for hashtags with special characters")
    print("• Database is stored in data/tiktok_analysis.db")
    print("• Logs show detailed processing information")
    print("• All hashtags are normalized (lowercase, no #)")

if __name__ == "__main__":
    main()
