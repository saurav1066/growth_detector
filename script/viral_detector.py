#!/usr/bin/env python3
"""
Viral Keyword Detection System

Main script for detecting rapidly growing keywords and viral trends in TikTok data.
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List

# Add paths
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from engines.viral_detection import ViralDetectionEngine
from utils.database import get_db_connection
import configparser

def load_config():
    """Load configuration settings"""
    config = configparser.ConfigParser()
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'settings.ini')
    config.read(config_path)
    return config

def format_viral_results(results: List[Dict]) -> None:
    """Format and display viral detection results"""
    if not results:
        print("🔍 No viral keywords detected in the current analysis window.")
        print("   Try increasing the analysis window or reducing thresholds.")
        return
    
    print("🚀 VIRAL KEYWORD DETECTION RESULTS")
    print("=" * 80)
    print(f"Analysis completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total viral keywords detected: {len(results)}")
    print()
    
    # Top viral keywords
    print("📈 TOP VIRAL KEYWORDS")
    print("-" * 80)
    print(f"{'Rank':<4} {'Keyword':<20} {'Score':<8} {'Methods':<25} {'Confidence':<12}")
    print("-" * 80)
    
    for i, result in enumerate(results[:20], 1):  # Top 20
        methods = ', '.join(result['detection_methods'][:2])  # First 2 methods
        if len(result['detection_methods']) > 2:
            methods += f" +{len(result['detection_methods']) - 2}"
        
        print(f"{i:<4} #{result['hashtag']:<19} {result['viral_score']:<8.3f} "
              f"{methods:<25} {result['confidence']:<12.3f}")
    
    if len(results) > 20:
        print(f"\n... and {len(results) - 20} more viral keywords")
    
    # Detailed analysis of top 5
    print(f"\n📊 DETAILED ANALYSIS - TOP 5 KEYWORDS")
    print("=" * 80)
    
    for i, result in enumerate(results[:5], 1):
        print(f"\n{i}. #{result['hashtag'].upper()}")
        print(f"   Viral Score: {result['viral_score']:.3f}")
        print(f"   Confidence: {result['confidence']:.3f}")
        print(f"   Detection Methods: {', '.join(result['detection_methods'])}")
        
        metrics = result['growth_metrics']
        
        # Exponential Growth
        if 'exponential_growth' in metrics:
            exp = metrics['exponential_growth']
            if exp.get('detected', False):
                print(f"   📈 Exponential Growth: R² = {exp.get('r_squared', 0):.3f}, "
                      f"Rate = {exp.get('growth_rate', 0):.3f}")
        
        # Anomaly Detection
        if 'anomaly_score' in metrics:
            anomaly = metrics['anomaly_score']
            if anomaly.get('detected', False):
                print(f"   🚨 Anomaly Detected: Z-score = {anomaly.get('z_score', 0):.2f}")
        
        # Acceleration
        if 'acceleration' in metrics:
            accel = metrics['acceleration']
            if accel.get('avg_acceleration', 0) > 0:
                print(f"   ⚡ Acceleration: {accel.get('avg_acceleration', 0):.2f}")
        
        # Creator Velocity
        if 'creator_velocity' in metrics:
            creator = metrics['creator_velocity']
            print(f"   👥 Creator Growth: {creator.get('velocity', 0):.2f}/hour, "
                  f"Rate: {creator.get('growth_rate', 0)*100:.1f}%")
        
        # Engagement Momentum
        if 'engagement_momentum' in metrics:
            engagement = metrics['engagement_momentum']
            print(f"   💝 Engagement: Trend = {engagement.get('engagement_trend', 'unknown')}, "
                  f"Quality = {engagement.get('quality_score', 0):.0f}")

def run_backtest(engine: ViralDetectionEngine, db_path: str, days: int) -> None:
    """Run backtesting analysis"""
    print(f"🔄 RUNNING BACKTEST ANALYSIS ({days} days)")
    print("=" * 60)
    
    results = engine.backtest_detection(db_path, days)
    
    if not results:
        print("❌ Backtest failed or no results available")
        return
    
    # Performance Summary
    summary = results.get('summary', {})
    print(f"\n📊 PERFORMANCE SUMMARY")
    print("-" * 40)
    print(f"Detection Accuracy: {summary.get('detection_accuracy', 'N/A')}")
    print(f"Coverage (Recall):  {summary.get('coverage', 'N/A')}")
    print(f"Overall Score (F1): {summary.get('overall_performance', 'N/A')}")
    print(f"Consistency:        {summary.get('consistency', 'N/A')}")
    print(f"Analysis Period:    {summary.get('total_analysis_days', 0)} days")
    
    # Daily Performance
    perf = results.get('performance_metrics', {})
    if perf:
        print(f"\n📈 DETAILED METRICS")
        print("-" * 40)
        print(f"Average Precision: {perf.get('avg_precision', 0)*100:.1f}% (±{perf.get('precision_std', 0)*100:.1f}%)")
        print(f"Average Recall:    {perf.get('avg_recall', 0)*100:.1f}% (±{perf.get('recall_std', 0)*100:.1f}%)")
        print(f"Average F1 Score:  {perf.get('avg_f1_score', 0)*100:.1f}%")
    
    # Recent Daily Results
    daily_results = results.get('daily_detections', [])
    if daily_results:
        print(f"\n📅 RECENT DAILY PERFORMANCE (Last 7 days)")
        print("-" * 60)
        print(f"{'Date':<12} {'Precision':<10} {'Recall':<10} {'F1-Score':<10} {'Detected':<10}")
        print("-" * 60)
        
        for day in daily_results[-7:]:  # Last 7 days
            print(f"{day['date']:<12} {day['precision']*100:<10.1f} "
                  f"{day['recall']*100:<10.1f} {day['f1_score']*100:<10.1f} "
                  f"{len(day.get('detected_viral', [])):<10}")

def export_results(results: List[Dict], filename: str) -> None:
    """Export results to JSON file"""
    output_data = {
        'timestamp': datetime.now().isoformat(),
        'total_detected': len(results),
        'results': results
    }
    
    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)
    
    print(f"📁 Results exported to: {filename}")

def main():
    parser = argparse.ArgumentParser(description='TikTok Viral Keyword Detection System')
    parser.add_argument('--window', '-w', type=int, default=24, 
                       help='Analysis window in hours (default: 24)')
    parser.add_argument('--backtest', type=int, metavar='DAYS',
                       help='Run backtest analysis for specified number of days')
    parser.add_argument('--export', type=str, metavar='FILENAME',
                       help='Export results to JSON file')
    parser.add_argument('--min-score', type=float, default=0.0,
                       help='Minimum viral score threshold (default: 0.0)')
    parser.add_argument('--top', type=int, default=50,
                       help='Maximum number of results to show (default: 50)')
    parser.add_argument('--config', type=str, 
                       default='config/settings.ini',
                       help='Configuration file path')
    
    args = parser.parse_args()
    
    # Load configuration
    config = load_config()
    db_name = config['DATABASE']['db_name']
    db_path = config['DATABASE']['db_path']
    full_db_path = os.path.join(db_path, db_name)
    
    # Check if database exists
    if not os.path.exists(full_db_path):
        print("❌ Database not found!")
        print(f"   Expected location: {full_db_path}")
        print("   Run 'python script/csv_injestor.py' first to create the database.")
        return
    
    # Initialize viral detection engine
    engine = ViralDetectionEngine(args.config)
    
    print("🎵 TikTok Viral Keyword Detection System")
    print("=" * 60)
    
    if args.backtest:
        # Run backtest analysis
        run_backtest(engine, full_db_path, args.backtest)
    else:
        # Run viral detection
        print(f"🔍 Analyzing viral keywords (window: {args.window}h)")
        print(f"📊 Database: {full_db_path}")
        print(f"⚡ Min Score: {args.min_score}")
        print()
        
        # Detect viral keywords
        results = engine.detect_viral_keywords(full_db_path, args.window)
        
        # Filter by minimum score
        if args.min_score > 0:
            results = [r for r in results if r['viral_score'] >= args.min_score]
        
        # Limit results
        results = results[:args.top]
        
        # Display results
        format_viral_results(results)
        
        # Export if requested
        if args.export:
            export_results(results, args.export)
        
        # Summary statistics
        if results:
            avg_score = sum(r['viral_score'] for r in results) / len(results)
            max_score = max(r['viral_score'] for r in results)
            
            print(f"\n📊 SUMMARY STATISTICS")
            print("-" * 40)
            print(f"Average Viral Score: {avg_score:.3f}")
            print(f"Maximum Viral Score: {max_score:.3f}")
            print(f"Keywords above 0.5:  {len([r for r in results if r['viral_score'] > 0.5])}")
            print(f"Keywords above 0.7:  {len([r for r in results if r['viral_score'] > 0.7])}")
            
            # Detection method distribution
            all_methods = []
            for r in results:
                all_methods.extend(r['detection_methods'])
            
            if all_methods:
                method_counts = {}
                for method in all_methods:
                    method_counts[method] = method_counts.get(method, 0) + 1
                
                print(f"\nDetection Method Usage:")
                for method, count in sorted(method_counts.items(), key=lambda x: x[1], reverse=True):
                    print(f"  {method}: {count} keywords")
    
    print(f"\n✅ Analysis complete!")

if __name__ == "__main__":
    main()
