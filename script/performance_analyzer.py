#!/usr/bin/env python3
"""
Performance Metrics and Backtesting Analysis

Comprehensive evaluation of the viral detection system performance.
"""

import os
import sys
import json
import numpy as np
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt

# Add paths
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from engines.viral_detection import ViralDetectionEngine
from utils.database import get_db_connection
import configparser

class PerformanceAnalyzer:
    """
    Analyzes and reports on viral detection system performance
    """
    
    def __init__(self, config_path: str = "config/settings.ini"):
        self.config = self._load_config(config_path)
        self.engine = ViralDetectionEngine(config_path)
        
        # Database settings
        self.db_path = os.path.join(
            self.config['DATABASE']['db_path'],
            self.config['DATABASE']['db_name']
        )
    
    def _load_config(self, config_path: str) -> configparser.ConfigParser:
        """Load configuration from file"""
        config = configparser.ConfigParser()
        if os.path.exists(config_path):
            config.read(config_path)
        return config
    
    def comprehensive_backtest(self, days: int = 30) -> Dict:
        """
        Run comprehensive backtesting analysis
        
        Args:
            days: Number of days to backtest
            
        Returns:
            Comprehensive performance report
        """
        print(f"🔄 Running comprehensive backtest analysis ({days} days)")
        print("=" * 70)
        
        # Run basic backtest
        basic_results = self.engine.backtest_detection(self.db_path, days)
        
        # Additional performance analysis
        detailed_metrics = self._calculate_detailed_metrics()
        threshold_analysis = self._analyze_threshold_sensitivity()
        timing_analysis = self._analyze_detection_timing()
        
        # Combine all results
        comprehensive_results = {
            'basic_backtest': basic_results,
            'detailed_metrics': detailed_metrics,
            'threshold_analysis': threshold_analysis,
            'timing_analysis': timing_analysis,
            'recommendations': self._generate_recommendations(basic_results)
        }
        
        return comprehensive_results
    
    def _calculate_detailed_metrics(self) -> Dict:
        """Calculate detailed performance metrics beyond basic precision/recall"""
        print("📊 Calculating detailed metrics...")
        
        conn = sqlite3.connect(self.db_path)
        
        # Get current viral detection results
        current_results = self.engine.detect_viral_keywords(self.db_path, 168)
        
        # Calculate various metrics
        metrics = {
            'detection_distribution': self._analyze_detection_distribution(current_results),
            'confidence_analysis': self._analyze_confidence_scores(current_results),
            'method_effectiveness': self._analyze_method_effectiveness(current_results),
            'score_distribution': self._analyze_score_distribution(current_results),
            'hashtag_characteristics': self._analyze_hashtag_characteristics(conn, current_results)
        }
        
        conn.close()
        return metrics
    
    def _analyze_detection_distribution(self, results: List[Dict]) -> Dict:
        """Analyze the distribution of viral detections"""
        if not results:
            return {'total': 0, 'by_score_range': {}}
        
        score_ranges = {
            'very_high': len([r for r in results if r['viral_score'] >= 0.8]),
            'high': len([r for r in results if 0.6 <= r['viral_score'] < 0.8]),
            'medium': len([r for r in results if 0.4 <= r['viral_score'] < 0.6]),
            'low': len([r for r in results if r['viral_score'] < 0.4])
        }
        
        return {
            'total': len(results),
            'by_score_range': score_ranges,
            'avg_score': np.mean([r['viral_score'] for r in results]),
            'score_std': np.std([r['viral_score'] for r in results])
        }
    
    def _analyze_confidence_scores(self, results: List[Dict]) -> Dict:
        """Analyze confidence score distribution and reliability"""
        if not results:
            return {}
        
        confidences = [r['confidence'] for r in results]
        
        return {
            'mean_confidence': np.mean(confidences),
            'median_confidence': np.median(confidences),
            'confidence_std': np.std(confidences),
            'high_confidence_ratio': len([c for c in confidences if c >= 0.8]) / len(confidences),
            'low_confidence_ratio': len([c for c in confidences if c < 0.5]) / len(confidences)
        }
    
    def _analyze_method_effectiveness(self, results: List[Dict]) -> Dict:
        """Analyze which detection methods are most effective"""
        method_counts = {}
        method_scores = {}
        
        for result in results:
            for method in result['detection_methods']:
                if method not in method_counts:
                    method_counts[method] = 0
                    method_scores[method] = []
                
                method_counts[method] += 1
                method_scores[method].append(result['viral_score'])
        
        method_analysis = {}
        for method in method_counts:
            method_analysis[method] = {
                'count': method_counts[method],
                'avg_score': np.mean(method_scores[method]),
                'usage_percentage': (method_counts[method] / len(results)) * 100
            }
        
        return method_analysis
    
    def _analyze_score_distribution(self, results: List[Dict]) -> Dict:
        """Analyze viral score distribution patterns"""
        if not results:
            return {}
        
        scores = [r['viral_score'] for r in results]
        
        return {
            'min_score': min(scores),
            'max_score': max(scores),
            'mean_score': np.mean(scores),
            'median_score': np.median(scores),
            'score_range': max(scores) - min(scores),
            'quartiles': {
                'q1': np.percentile(scores, 25),
                'q2': np.percentile(scores, 50),
                'q3': np.percentile(scores, 75)
            }
        }
    
    def _analyze_hashtag_characteristics(self, conn: sqlite3.Connection, results: List[Dict]) -> Dict:
        """Analyze characteristics of detected viral hashtags"""
        if not results:
            return {}
        
        hashtags = [r['hashtag'] for r in results]
        
        # Get hashtag statistics from database
        cursor = conn.cursor()
        
        characteristics = {
            'avg_length': np.mean([len(h) for h in hashtags]),
            'length_distribution': {},
            'common_patterns': self._find_common_patterns(hashtags),
            'usage_statistics': {}
        }
        
        # Length distribution
        for hashtag in hashtags:
            length_range = f"{(len(hashtag)//5)*5}-{(len(hashtag)//5)*5+4}"
            characteristics['length_distribution'][length_range] = \
                characteristics['length_distribution'].get(length_range, 0) + 1
        
        # Get usage statistics for detected hashtags
        for hashtag in hashtags[:10]:  # Limit to top 10 for performance
            cursor.execute("""
                SELECT 
                    h.total_usage_count,
                    COUNT(DISTINCT v.author_id) as unique_creators,
                    AVG(v.like_count) as avg_likes
                FROM hashtags h
                JOIN video_hashtags vh ON h.id = vh.hashtag_id
                JOIN videos v ON vh.video_id = v.id
                WHERE h.name = ?
                GROUP BY h.id
            """, (hashtag,))
            
            result = cursor.fetchone()
            if result:
                characteristics['usage_statistics'][hashtag] = {
                    'total_usage': result[0],
                    'unique_creators': result[1],
                    'avg_likes': result[2] or 0
                }
        
        return characteristics
    
    def _find_common_patterns(self, hashtags: List[str]) -> Dict:
        """Find common patterns in viral hashtags"""
        patterns = {
            'starts_with_fyp': len([h for h in hashtags if h.startswith('fyp')]),
            'contains_for': len([h for h in hashtags if 'for' in h]),
            'contains_you': len([h for h in hashtags if 'you' in h]),
            'contains_viral': len([h for h in hashtags if 'viral' in h]),
            'contains_challenge': len([h for h in hashtags if 'challenge' in h]),
            'all_caps': len([h for h in hashtags if h.isupper()]),
            'contains_numbers': len([h for h in hashtags if any(c.isdigit() for c in h)])
        }
        
        return patterns
    
    def _analyze_threshold_sensitivity(self) -> Dict:
        """Analyze how different thresholds affect detection performance"""
        print("🎯 Analyzing threshold sensitivity...")
        
        # Test different viral score thresholds
        thresholds = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
        threshold_results = {}
        
        # Get base results
        base_results = self.engine.detect_viral_keywords(self.db_path, 24)
        
        for threshold in thresholds:
            filtered_results = [r for r in base_results if r['viral_score'] >= threshold]
            
            threshold_results[threshold] = {
                'count': len(filtered_results),
                'avg_score': np.mean([r['viral_score'] for r in filtered_results]) if filtered_results else 0,
                'avg_confidence': np.mean([r['confidence'] for r in filtered_results]) if filtered_results else 0
            }
        
        # Find optimal threshold (balance between quantity and quality)
        optimal_threshold = self._find_optimal_threshold(threshold_results)
        
        return {
            'threshold_analysis': threshold_results,
            'optimal_threshold': optimal_threshold,
            'recommendation': f"Use threshold {optimal_threshold} for balanced performance"
        }
    
    def _find_optimal_threshold(self, threshold_results: Dict) -> float:
        """Find the optimal threshold balancing quantity and quality"""
        scores = []
        
        for threshold, results in threshold_results.items():
            count = results['count']
            avg_score = results['avg_score']
            avg_confidence = results['avg_confidence']
            
            # Balance formula: prioritize moderate count with high quality
            if count > 0:
                balance_score = (count / 50) * avg_score * avg_confidence  # Normalize count to ~1
                scores.append((threshold, balance_score))
        
        if scores:
            optimal = max(scores, key=lambda x: x[1])
            return optimal[0]
        
        return 0.5  # Default
    
    def _analyze_detection_timing(self) -> Dict:
        """Analyze how quickly keywords are detected after they start growing"""
        print("⏱️  Analyzing detection timing...")
        
        # This would require more sophisticated time-series analysis
        # For now, provide basic timing metrics
        
        return {
            'avg_detection_window': '6 hours',  # Based on current analysis window
            'detection_lag_estimate': '2-4 hours',  # Estimated lag time
            'recommendation': 'Consider reducing analysis window to 3-4 hours for faster detection'
        }
    
    def _generate_recommendations(self, backtest_results: Dict) -> List[str]:
        """Generate actionable recommendations based on performance analysis"""
        recommendations = []
        
        if not backtest_results:
            return ["Run backtest analysis first to generate recommendations"]
        
        performance = backtest_results.get('performance_metrics', {})
        
        # Precision recommendations
        precision = performance.get('avg_precision', 0)
        if precision < 0.7:
            recommendations.append("Consider increasing viral score threshold to reduce false positives")
        elif precision > 0.9:
            recommendations.append("Precision is very high - consider lowering thresholds to catch more keywords")
        
        # Recall recommendations  
        recall = performance.get('avg_recall', 0)
        if recall < 0.6:
            recommendations.append("Consider lowering detection thresholds to improve coverage")
        elif recall > 0.9:
            recommendations.append("Excellent coverage - maintain current sensitivity settings")
        
        # F1 Score recommendations
        f1 = performance.get('avg_f1_score', 0)
        if f1 < 0.7:
            recommendations.append("Overall performance needs improvement - review algorithm parameters")
        elif f1 > 0.8:
            recommendations.append("Strong overall performance - consider production deployment")
        
        # Consistency recommendations
        precision_std = performance.get('precision_std', 0)
        if precision_std > 0.2:
            recommendations.append("High performance variance - consider ensemble methods for stability")
        
        return recommendations
    
    def generate_performance_report(self, analysis_results: Dict, output_file: str = None) -> str:
        """Generate a comprehensive performance report"""
        report_lines = []
        
        # Header
        report_lines.append("🚀 TIKTOK VIRAL DETECTION SYSTEM - PERFORMANCE REPORT")
        report_lines.append("=" * 80)
        report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("")
        
        # Executive Summary
        basic_results = analysis_results.get('basic_backtest', {})
        if basic_results:
            summary = basic_results.get('summary', {})
            report_lines.append("📊 EXECUTIVE SUMMARY")
            report_lines.append("-" * 40)
            report_lines.append(f"Detection Accuracy: {summary.get('detection_accuracy', 'N/A')}")
            report_lines.append(f"Coverage Rate:      {summary.get('coverage', 'N/A')}")
            report_lines.append(f"Overall Score:      {summary.get('overall_performance', 'N/A')}")
            report_lines.append(f"System Consistency: {summary.get('consistency', 'N/A')}")
            report_lines.append("")
        
        # Detailed Metrics
        detailed = analysis_results.get('detailed_metrics', {})
        if detailed:
            dist = detailed.get('detection_distribution', {})
            report_lines.append("📈 DETECTION ANALYSIS")
            report_lines.append("-" * 40)
            report_lines.append(f"Total Keywords Analyzed: {dist.get('total', 0)}")
            report_lines.append(f"Average Viral Score:     {dist.get('avg_score', 0):.3f}")
            
            score_ranges = dist.get('by_score_range', {})
            for range_name, count in score_ranges.items():
                report_lines.append(f"  {range_name.title():15}: {count:3d} keywords")
            report_lines.append("")
        
        # Method Effectiveness
        methods = detailed.get('method_effectiveness', {})
        if methods:
            report_lines.append("🔍 DETECTION METHOD EFFECTIVENESS")
            report_lines.append("-" * 40)
            for method, stats in methods.items():
                report_lines.append(f"{method:20}: {stats['count']:3d} uses "
                                  f"({stats['usage_percentage']:5.1f}%) "
                                  f"Avg Score: {stats['avg_score']:.3f}")
            report_lines.append("")
        
        # Threshold Analysis
        threshold_analysis = analysis_results.get('threshold_analysis', {})
        if threshold_analysis:
            report_lines.append("🎯 THRESHOLD OPTIMIZATION")
            report_lines.append("-" * 40)
            report_lines.append(f"Recommended Threshold: {threshold_analysis.get('optimal_threshold', 'N/A')}")
            report_lines.append(f"Reasoning: {threshold_analysis.get('recommendation', 'N/A')}")
            report_lines.append("")
        
        # Recommendations
        recommendations = analysis_results.get('recommendations', [])
        if recommendations:
            report_lines.append("💡 RECOMMENDATIONS")
            report_lines.append("-" * 40)
            for i, rec in enumerate(recommendations, 1):
                report_lines.append(f"{i}. {rec}")
            report_lines.append("")
        
        # Footer
        report_lines.append("=" * 80)
        report_lines.append("Report generated by TikTok Viral Detection Performance Analyzer")
        
        report_text = "\n".join(report_lines)
        
        # Save to file if specified
        if output_file:
            with open(output_file, 'w') as f:
                f.write(report_text)
            print(f"📁 Performance report saved to: {output_file}")
        
        return report_text

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='TikTok Viral Detection Performance Analysis')
    parser.add_argument('--backtest-days', type=int, default=15,
                       help='Number of days for backtesting (default: 15)')
    parser.add_argument('--output', type=str,
                       help='Output file for performance report')
    parser.add_argument('--quick', action='store_true',
                       help='Run quick analysis (skip detailed metrics)')
    
    args = parser.parse_args()
    
    analyzer = PerformanceAnalyzer()
    
    print("🔬 TikTok Viral Detection Performance Analyzer")
    print("=" * 60)
    
    if not os.path.exists(analyzer.db_path):
        print("❌ Database not found!")
        print(f"   Expected: {analyzer.db_path}")
        return
    
    if args.quick:
        # Quick analysis - basic backtest only
        print("⚡ Running quick performance analysis...")
        results = analyzer.engine.backtest_detection(analyzer.db_path, args.backtest_days)
        analysis_results = {'basic_backtest': results}
    else:
        # Comprehensive analysis
        print("🔍 Running comprehensive performance analysis...")
        analysis_results = analyzer.comprehensive_backtest(args.backtest_days)
    
    # Generate and display report
    report = analyzer.generate_performance_report(analysis_results, args.output)
    print(report)

if __name__ == "__main__":
    main()
