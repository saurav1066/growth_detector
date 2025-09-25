"""
Viral Keyword Detection Engine

This module implements advanced algorithms to detect rapidly growing keywords
and predict viral content trends in TikTok data.
"""

import numpy as np
import pandas as pd
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
from scipy import stats
from scipy.optimize import curve_fit
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import IsolationForest
import configparser
import sys
import os

# Add utils to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from utils import database

class ViralDetectionEngine:
    """
    Core engine for detecting viral keywords using multiple algorithms
    """
    
    def __init__(self, config_path: str = "config/settings.ini"):
        """
        Initialize the viral detection engine
        
        Args:
            config_path: Path to configuration file
        """
        self.config = self._load_config(config_path)
        self.logger = self._setup_logging()
        
        # Detection parameters
        self.min_usage_threshold = int(self.config.get('VIRAL_DETECTION', 'min_usage_threshold', fallback='10'))
        self.growth_threshold = float(self.config.get('VIRAL_DETECTION', 'growth_threshold', fallback='2.0'))
        self.anomaly_threshold = float(self.config.get('VIRAL_DETECTION', 'anomaly_threshold', fallback='3.0'))
        self.time_windows = [1, 6, 24, 168]  # hours: 1h, 6h, 24h, 7d
        
        self.logger.info("Viral Detection Engine initialized")
    
    def _load_config(self, config_path: str) -> configparser.ConfigParser:
        """Load configuration from file"""
        config = configparser.ConfigParser()
        if os.path.exists(config_path):
            config.read(config_path)
        return config
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for the engine"""
        logger = logging.getLogger('ViralDetection')
        logger.setLevel(logging.INFO)
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        return logger
    
    def detect_viral_keywords(self, db_path: str, analysis_window_hours: int = 24) -> List[Dict]:
        """
        Main method to detect viral keywords
        
        Args:
            db_path: Path to SQLite database
            analysis_window_hours: Time window for analysis
            
        Returns:
            List of viral keyword detection results
        """
        self.logger.info(f"Starting viral keyword detection with {analysis_window_hours}h window")
        
        conn = sqlite3.connect(db_path)
        
        # Get time-series data for all hashtags
        hashtag_timeseries = self._get_hashtag_timeseries(conn, analysis_window_hours)
        
        if not hashtag_timeseries:
            self.logger.warning("No hashtag data found for analysis")
            return []
        
        viral_keywords = []
        
        for hashtag, timeseries_data in hashtag_timeseries.items():
            # Skip hashtags with insufficient data
            if len(timeseries_data) < 3 or timeseries_data['total_usage'].sum() < self.min_usage_threshold:
                continue
            
            detection_results = self._analyze_hashtag_virality(hashtag, timeseries_data)
            
            if detection_results['is_viral']:
                viral_keywords.append(detection_results)
        
        # Sort by viral score (descending)
        viral_keywords.sort(key=lambda x: x['viral_score'], reverse=True)
        
        conn.close()
        self.logger.info(f"Detected {len(viral_keywords)} viral keywords")
        
        return viral_keywords
    
    def _get_hashtag_timeseries(self, conn: sqlite3.Connection, window_hours: int) -> Dict:
        """
        Extract time-series data for hashtags
        
        Args:
            conn: Database connection
            window_hours: Analysis time window in hours
            
        Returns:
            Dictionary of hashtag time-series data
        """
        # Calculate time window
        end_time = datetime.now().timestamp()
        start_time = end_time - (window_hours * 3600)
        
        query = """
        SELECT 
            h.name as hashtag,
            v.collection_timestamp,
            COUNT(*) as usage_count,
            COUNT(DISTINCT v.author_id) as unique_creators,
            AVG(v.like_count) as avg_likes,
            AVG(v.comment_count) as avg_comments,
            AVG(v.share_count) as avg_shares,
            AVG(v.play_count) as avg_views
        FROM hashtags h
        JOIN video_hashtags vh ON h.id = vh.hashtag_id
        JOIN videos v ON vh.video_id = v.id
        WHERE v.collection_timestamp BETWEEN ? AND ?
        GROUP BY h.name, 
                 CAST(v.collection_timestamp / 3600 AS INTEGER)  -- Group by hour
        ORDER BY h.name, v.collection_timestamp
        """
        
        cursor = conn.cursor()
        cursor.execute(query, (start_time, end_time))
        results = cursor.fetchall()
        
        # Organize data by hashtag
        hashtag_data = {}
        for row in results:
            hashtag, timestamp, usage, creators, avg_likes, avg_comments, avg_shares, avg_views = row
            
            if hashtag not in hashtag_data:
                hashtag_data[hashtag] = {
                    'timestamps': [],
                    'usage_counts': [],
                    'unique_creators': [],
                    'avg_engagement': []
                }
            
            hashtag_data[hashtag]['timestamps'].append(timestamp)
            hashtag_data[hashtag]['usage_counts'].append(usage)
            hashtag_data[hashtag]['unique_creators'].append(creators)
            
            # Calculate engagement score
            engagement = (avg_likes or 0) + (avg_comments or 0) + (avg_shares or 0)
            hashtag_data[hashtag]['avg_engagement'].append(engagement)
        
        # Convert to DataFrame for easier analysis
        processed_data = {}
        for hashtag, data in hashtag_data.items():
            df = pd.DataFrame(data)
            if len(df) > 0:
                df['total_usage'] = df['usage_counts']
                df['hour'] = pd.to_datetime(df['timestamps'], unit='s')
                processed_data[hashtag] = df
        
        return processed_data
    
    def _analyze_hashtag_virality(self, hashtag: str, timeseries_data: pd.DataFrame) -> Dict:
        """
        Analyze a single hashtag for viral characteristics
        
        Args:
            hashtag: Hashtag name
            timeseries_data: Time-series DataFrame
            
        Returns:
            Dictionary with viral analysis results
        """
        results = {
            'hashtag': hashtag,
            'is_viral': False,
            'viral_score': 0.0,
            'growth_metrics': {},
            'detection_methods': [],
            'confidence': 0.0,
            'analysis_timestamp': datetime.now().isoformat()
        }
        
        # Method 1: Exponential Growth Detection
        exp_growth = self._detect_exponential_growth(timeseries_data)
        results['growth_metrics']['exponential_growth'] = exp_growth
        
        # Method 2: Anomaly Detection
        anomaly_score = self._detect_usage_anomalies(timeseries_data)
        results['growth_metrics']['anomaly_score'] = anomaly_score
        
        # Method 3: Acceleration Analysis
        acceleration = self._calculate_acceleration(timeseries_data)
        results['growth_metrics']['acceleration'] = acceleration
        
        # Method 4: Creator Velocity Analysis
        creator_velocity = self._analyze_creator_velocity(timeseries_data)
        results['growth_metrics']['creator_velocity'] = creator_velocity
        
        # Method 5: Engagement Momentum
        engagement_momentum = self._calculate_engagement_momentum(timeseries_data)
        results['growth_metrics']['engagement_momentum'] = engagement_momentum
        
        # Combine metrics to calculate viral score
        viral_score = self._calculate_viral_score(results['growth_metrics'])
        results['viral_score'] = viral_score
        
        # Determine if viral based on composite score and individual thresholds
        is_viral, detection_methods, confidence = self._determine_virality(results['growth_metrics'])
        results['is_viral'] = is_viral
        results['detection_methods'] = detection_methods
        results['confidence'] = confidence
        
        return results
    
    def _detect_exponential_growth(self, data: pd.DataFrame) -> Dict:
        """
        Detect exponential growth patterns using curve fitting
        """
        if len(data) < 4:
            return {'detected': False, 'r_squared': 0.0, 'growth_rate': 0.0}
        
        try:
            # Prepare data
            x = np.arange(len(data))
            y = data['total_usage'].cumsum().values
            
            # Avoid log(0) issues
            y = np.maximum(y, 1)
            
            # Fit exponential curve: y = a * exp(b * x)
            def exp_func(x, a, b):
                return a * np.exp(b * x)
            
            # Initial guess
            popt, _ = curve_fit(exp_func, x, y, p0=[1, 0.1], maxfev=1000)
            
            # Calculate R-squared
            y_pred = exp_func(x, *popt)
            ss_res = np.sum((y - y_pred) ** 2)
            ss_tot = np.sum((y - np.mean(y)) ** 2)
            r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
            
            growth_rate = popt[1]  # Exponential growth parameter
            
            return {
                'detected': r_squared > 0.8 and growth_rate > 0.1,
                'r_squared': r_squared,
                'growth_rate': growth_rate,
                'exponential_params': popt.tolist()
            }
            
        except Exception as e:
            self.logger.debug(f"Exponential fitting failed for {data}: {e}")
            return {'detected': False, 'r_squared': 0.0, 'growth_rate': 0.0}
    
    def _detect_usage_anomalies(self, data: pd.DataFrame) -> Dict:
        """
        Detect anomalous usage spikes using statistical methods
        """
        usage = data['total_usage'].values
        
        if len(usage) < 3:
            return {'detected': False, 'z_score': 0.0, 'isolation_score': 0.0}
        
        # Z-score based anomaly detection
        mean_usage = np.mean(usage)
        std_usage = np.std(usage)
        
        if std_usage == 0:
            z_scores = np.zeros_like(usage)
        else:
            z_scores = np.abs((usage - mean_usage) / std_usage)
        
        max_z_score = np.max(z_scores)
        
        # Isolation Forest for multivariate anomaly detection
        try:
            features = data[['total_usage', 'unique_creators', 'avg_engagement']].fillna(0)
            if len(features) >= 3:
                iso_forest = IsolationForest(contamination=0.1, random_state=42)
                anomaly_scores = iso_forest.fit_predict(features)
                isolation_score = np.mean(anomaly_scores == -1)  # Proportion of anomalies
            else:
                isolation_score = 0.0
        except Exception:
            isolation_score = 0.0
        
        return {
            'detected': max_z_score > self.anomaly_threshold,
            'z_score': float(max_z_score),
            'isolation_score': float(isolation_score),
            'anomaly_threshold': self.anomaly_threshold
        }
    
    def _calculate_acceleration(self, data: pd.DataFrame) -> Dict:
        """
        Calculate growth acceleration (second derivative)
        """
        usage = data['total_usage'].values
        
        if len(usage) < 3:
            return {'acceleration': 0.0, 'avg_acceleration': 0.0}
        
        # Calculate first and second derivatives
        velocity = np.diff(usage)
        acceleration = np.diff(velocity)
        
        avg_acceleration = np.mean(acceleration) if len(acceleration) > 0 else 0.0
        max_acceleration = np.max(acceleration) if len(acceleration) > 0 else 0.0
        
        return {
            'acceleration': float(max_acceleration),
            'avg_acceleration': float(avg_acceleration),
            'positive_acceleration_ratio': float(np.mean(acceleration > 0)) if len(acceleration) > 0 else 0.0
        }
    
    def _analyze_creator_velocity(self, data: pd.DataFrame) -> Dict:
        """
        Analyze how quickly new creators are adopting the hashtag
        """
        creators = data['unique_creators'].values
        
        if len(creators) < 2:
            return {'velocity': 0.0, 'growth_rate': 0.0}
        
        # Calculate creator growth rate
        creator_diff = np.diff(creators)
        avg_creator_growth = np.mean(creator_diff) if len(creator_diff) > 0 else 0.0
        
        # Calculate creator diversity (how distributed the usage is among creators)
        total_usage = data['total_usage'].sum()
        total_creators = creators.sum()
        
        diversity_ratio = total_creators / total_usage if total_usage > 0 else 0.0
        
        return {
            'velocity': float(avg_creator_growth),
            'growth_rate': float(avg_creator_growth / np.mean(creators)) if np.mean(creators) > 0 else 0.0,
            'diversity_ratio': float(diversity_ratio),
            'total_creators': int(total_creators)
        }
    
    def _calculate_engagement_momentum(self, data: pd.DataFrame) -> Dict:
        """
        Calculate engagement momentum and quality
        """
        engagement = data['avg_engagement'].fillna(0).values
        usage = data['total_usage'].values
        
        if len(engagement) < 2:
            return {'momentum': 0.0, 'quality_score': 0.0}
        
        # Calculate engagement growth
        engagement_growth = np.diff(engagement)
        avg_engagement_growth = np.mean(engagement_growth) if len(engagement_growth) > 0 else 0.0
        
        # Calculate engagement quality (engagement per usage)
        quality_scores = []
        for i in range(len(engagement)):
            if usage[i] > 0:
                quality_scores.append(engagement[i] / usage[i])
            else:
                quality_scores.append(0)
        
        avg_quality = np.mean(quality_scores) if quality_scores else 0.0
        
        return {
            'momentum': float(avg_engagement_growth),
            'quality_score': float(avg_quality),
            'engagement_trend': 'increasing' if avg_engagement_growth > 0 else 'decreasing'
        }
    
    def _calculate_viral_score(self, metrics: Dict) -> float:
        """
        Calculate composite viral score from all metrics
        """
        score = 0.0
        
        # Exponential growth (30% weight)
        exp_growth = metrics.get('exponential_growth', {})
        if exp_growth.get('detected', False):
            score += 0.3 * exp_growth.get('r_squared', 0.0)
        
        # Anomaly detection (25% weight)
        anomaly = metrics.get('anomaly_score', {})
        if anomaly.get('detected', False):
            score += 0.25 * min(anomaly.get('z_score', 0.0) / 5.0, 1.0)  # Normalize z-score
        
        # Acceleration (20% weight)
        acceleration = metrics.get('acceleration', {})
        if acceleration.get('avg_acceleration', 0.0) > 0:
            score += 0.2 * min(acceleration.get('avg_acceleration', 0.0) / 10.0, 1.0)
        
        # Creator velocity (15% weight)
        creator_vel = metrics.get('creator_velocity', {})
        if creator_vel.get('velocity', 0.0) > 0:
            score += 0.15 * min(creator_vel.get('growth_rate', 0.0), 1.0)
        
        # Engagement momentum (10% weight)
        engagement = metrics.get('engagement_momentum', {})
        if engagement.get('momentum', 0.0) > 0:
            score += 0.1 * min(engagement.get('momentum', 0.0) / 1000.0, 1.0)  # Normalize
        
        return min(score, 1.0)  # Cap at 1.0
    
    def _determine_virality(self, metrics: Dict) -> Tuple[bool, List[str], float]:
        """
        Determine if hashtag is viral based on multiple criteria
        """
        detection_methods = []
        confidence_scores = []
        
        # Check exponential growth
        exp_growth = metrics.get('exponential_growth', {})
        if exp_growth.get('detected', False):
            detection_methods.append('exponential_growth')
            confidence_scores.append(exp_growth.get('r_squared', 0.0))
        
        # Check anomaly detection
        anomaly = metrics.get('anomaly_score', {})
        if anomaly.get('detected', False):
            detection_methods.append('anomaly_detection')
            confidence_scores.append(min(anomaly.get('z_score', 0.0) / 5.0, 1.0))
        
        # Check acceleration
        acceleration = metrics.get('acceleration', {})
        if acceleration.get('avg_acceleration', 0.0) > 5.0:  # Threshold for significant acceleration
            detection_methods.append('acceleration')
            confidence_scores.append(min(acceleration.get('avg_acceleration', 0.0) / 20.0, 1.0))
        
        # Check creator velocity
        creator_vel = metrics.get('creator_velocity', {})
        if creator_vel.get('growth_rate', 0.0) > 0.5:  # 50% creator growth rate threshold
            detection_methods.append('creator_velocity')
            confidence_scores.append(min(creator_vel.get('growth_rate', 0.0), 1.0))
        
        # Determine if viral (need at least 2 detection methods or very high confidence in one)
        is_viral = len(detection_methods) >= 2 or (len(confidence_scores) > 0 and max(confidence_scores) > 0.9)
        
        avg_confidence = np.mean(confidence_scores) if confidence_scores else 0.0
        
        return is_viral, detection_methods, float(avg_confidence)
    
    def backtest_detection(self, db_path: str, backtest_days: int = 30) -> Dict:
        """
        Backtest the viral detection system on historical data
        
        Args:
            db_path: Path to database
            backtest_days: Number of days to backtest
            
        Returns:
            Backtesting results and performance metrics
        """
        self.logger.info(f"Starting backtest for {backtest_days} days")
        
        conn = sqlite3.connect(db_path)
        
        # Get historical data
        end_time = datetime.now().timestamp()
        start_time = end_time - (backtest_days * 24 * 3600)
        
        # Simulate day-by-day detection
        results = {
            'daily_detections': [],
            'performance_metrics': {},
            'summary': {}
        }
        
        for day in range(backtest_days):
            day_start = start_time + (day * 24 * 3600)
            day_end = day_start + (24 * 3600)
            
            # Get known viral hashtags for this day (top 5% by growth)
            known_viral = self._get_known_viral_hashtags(conn, day_start, day_end)
            
            # Run detection as if we were at that point in time
            detected_viral = self._simulate_detection_at_time(conn, day_end)
            
            # Calculate daily metrics
            daily_metrics = self._calculate_daily_metrics(known_viral, detected_viral)
            daily_metrics['date'] = datetime.fromtimestamp(day_start).strftime('%Y-%m-%d')
            
            results['daily_detections'].append(daily_metrics)
        
        # Calculate overall performance metrics
        results['performance_metrics'] = self._calculate_overall_performance(results['daily_detections'])
        results['summary'] = self._generate_backtest_summary(results)
        
        conn.close()
        
        self.logger.info("Backtest completed")
        return results
    
    def _get_known_viral_hashtags(self, conn: sqlite3.Connection, start_time: float, end_time: float) -> List[str]:
        """Get hashtags that were actually viral during a specific time period"""
        query = """
        SELECT 
            h.name,
            COUNT(*) as usage_count,
            COUNT(*) * 1.0 / (? - ?) as usage_rate
        FROM hashtags h
        JOIN video_hashtags vh ON h.id = vh.hashtag_id  
        JOIN videos v ON vh.video_id = v.id
        WHERE v.collection_timestamp BETWEEN ? AND ?
        GROUP BY h.name
        HAVING usage_count >= ?
        ORDER BY usage_rate DESC
        LIMIT ?
        """
        
        cursor = conn.cursor()
        time_window_hours = (end_time - start_time) / 3600
        cursor.execute(query, (end_time, start_time, start_time, end_time, self.min_usage_threshold, 10))
        
        results = cursor.fetchall()
        return [row[0] for row in results[:5]]  # Top 5% as "known viral"
    
    def _simulate_detection_at_time(self, conn: sqlite3.Connection, timestamp: float) -> List[str]:
        """Simulate running detection at a specific historical timestamp"""
        # This would use only data available up to that timestamp
        # For simplicity, we'll return empty list for now (backtesting needs historical simulation)
        # In a full implementation, this would create a temporary database with data up to timestamp
        return []
    
    def _calculate_daily_metrics(self, known_viral: List[str], detected_viral: List[str]) -> Dict:
        """Calculate precision, recall, F1 for a single day"""
        true_positives = len(set(known_viral) & set(detected_viral))
        false_positives = len(set(detected_viral) - set(known_viral))
        false_negatives = len(set(known_viral) - set(detected_viral))
        
        precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
        recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
        f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        
        return {
            'known_viral': known_viral,
            'detected_viral': detected_viral,
            'true_positives': true_positives,
            'false_positives': false_positives,
            'false_negatives': false_negatives,
            'precision': precision,
            'recall': recall,
            'f1_score': f1_score
        }
    
    def _calculate_overall_performance(self, daily_results: List[Dict]) -> Dict:
        """Calculate overall performance metrics across all days"""
        if not daily_results:
            return {}
        
        precisions = [day['precision'] for day in daily_results if day['precision'] is not None]
        recalls = [day['recall'] for day in daily_results if day['recall'] is not None]
        f1_scores = [day['f1_score'] for day in daily_results if day['f1_score'] is not None]
        
        return {
            'avg_precision': np.mean(precisions) if precisions else 0,
            'avg_recall': np.mean(recalls) if recalls else 0,
            'avg_f1_score': np.mean(f1_scores) if f1_scores else 0,
            'precision_std': np.std(precisions) if precisions else 0,
            'recall_std': np.std(recalls) if recalls else 0,
            'total_days_analyzed': len(daily_results)
        }
    
    def _generate_backtest_summary(self, results: Dict) -> Dict:
        """Generate human-readable backtest summary"""
        perf = results['performance_metrics']
        
        return {
            'detection_accuracy': f"{perf.get('avg_precision', 0)*100:.1f}%",
            'coverage': f"{perf.get('avg_recall', 0)*100:.1f}%",
            'overall_performance': f"{perf.get('avg_f1_score', 0)*100:.1f}%",
            'consistency': 'High' if perf.get('precision_std', 1) < 0.2 else 'Medium' if perf.get('precision_std', 1) < 0.4 else 'Low',
            'total_analysis_days': perf.get('total_days_analyzed', 0)
        }
