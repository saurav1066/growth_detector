#!/usr/bin/env python3
"""
Real-time Viral Keyword Monitoring Dashboard

Continuously monitors for viral keywords and provides real-time alerts.
"""

import time
import json
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Set
import threading
import signal

# Add paths
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from engines.viral_detection import ViralDetectionEngine
import configparser

class ViralMonitoringDashboard:
    """
    Real-time monitoring dashboard for viral keyword detection
    """
    
    def __init__(self, config_path: str = "config/settings.ini"):
        self.config = self._load_config(config_path)
        self.engine = ViralDetectionEngine(config_path)
        
        # Monitoring settings
        self.monitoring = True
        self.check_interval = 300  # 5 minutes
        self.alert_history: Set[str] = set()
        self.last_check = None
        
        # Database settings
        self.db_path = os.path.join(
            self.config['DATABASE']['db_path'],
            self.config['DATABASE']['db_name']
        )
        
        # Alert settings
        self.max_daily_alerts = int(self.config.get('VIRAL_DETECTION', 'max_daily_alerts', fallback='50'))
        self.confidence_threshold = float(self.config.get('VIRAL_DETECTION', 'confidence_threshold', fallback='0.7'))
        
    def _load_config(self, config_path: str) -> configparser.ConfigParser:
        """Load configuration from file"""
        config = configparser.ConfigParser()
        if os.path.exists(config_path):
            config.read(config_path)
        return config
    
    def start_monitoring(self):
        """Start the real-time monitoring loop"""
        print("🚀 Starting TikTok Viral Keyword Monitoring Dashboard")
        print("=" * 70)
        print(f"📊 Database: {self.db_path}")
        print(f"⏱️  Check Interval: {self.check_interval} seconds")
        print(f"🎯 Confidence Threshold: {self.confidence_threshold}")
        print(f"📢 Max Daily Alerts: {self.max_daily_alerts}")
        print("=" * 70)
        print("Press Ctrl+C to stop monitoring\n")
        
        # Setup signal handler for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        
        try:
            while self.monitoring:
                self._perform_check()
                time.sleep(self.check_interval)
        except KeyboardInterrupt:
            print("\n🛑 Monitoring stopped by user")
        except Exception as e:
            print(f"\n❌ Monitoring error: {e}")
        finally:
            self._cleanup()
    
    def _signal_handler(self, signum, frame):
        """Handle interrupt signal"""
        print("\n🛑 Received interrupt signal, stopping monitoring...")
        self.monitoring = False
    
    def _perform_check(self):
        """Perform a single viral detection check"""
        check_time = datetime.now()
        print(f"\n🔍 [{check_time.strftime('%H:%M:%S')}] Checking for viral keywords...")
        
        try:
            # Detect viral keywords
            results = self.engine.detect_viral_keywords(self.db_path, analysis_window_hours=6)
            
            # Filter by confidence threshold
            high_confidence_results = [
                r for r in results 
                if r['confidence'] >= self.confidence_threshold and r['viral_score'] > 0.3
            ]
            
            new_alerts = []
            for result in high_confidence_results:
                alert_key = f"{result['hashtag']}_{check_time.strftime('%Y%m%d')}"
                if alert_key not in self.alert_history:
                    self.alert_history.add(alert_key)
                    new_alerts.append(result)
            
            # Limit daily alerts
            if len(new_alerts) > self.max_daily_alerts:
                new_alerts = new_alerts[:self.max_daily_alerts]
            
            # Display results
            self._display_check_results(check_time, results, new_alerts)
            
            # Generate alerts for new high-confidence detections
            if new_alerts:
                self._generate_alerts(new_alerts)
            
            self.last_check = check_time
            
        except Exception as e:
            print(f"❌ Check failed: {e}")
    
    def _display_check_results(self, check_time: datetime, all_results: List[Dict], new_alerts: List[Dict]):
        """Display the results of a monitoring check"""
        total_detected = len(all_results)
        high_confidence = len([r for r in all_results if r['confidence'] >= self.confidence_threshold])
        new_count = len(new_alerts)
        
        print(f"   📈 Total detected: {total_detected}")
        print(f"   ⭐ High confidence: {high_confidence}")
        print(f"   🆕 New alerts: {new_count}")
        
        if all_results:
            # Show top 5 current viral keywords
            top_keywords = all_results[:5]
            print(f"   🔥 Top viral: " + ", ".join([f"#{k['hashtag']}" for k in top_keywords]))
            
            # Show viral scores
            if top_keywords:
                avg_score = sum(k['viral_score'] for k in top_keywords) / len(top_keywords)
                max_score = max(k['viral_score'] for k in top_keywords)
                print(f"   📊 Scores: avg={avg_score:.3f}, max={max_score:.3f}")
        else:
            print("   😴 No viral keywords detected")
        
        # Memory management - clean old alerts
        self._cleanup_old_alerts()
    
    def _generate_alerts(self, alerts: List[Dict]):
        """Generate alerts for newly detected viral keywords"""
        print(f"\n🚨 VIRAL KEYWORD ALERT - {len(alerts)} new detections!")
        print("=" * 50)
        
        for i, alert in enumerate(alerts, 1):
            urgency = self._calculate_urgency(alert)
            print(f"\n{i}. 🔥 #{alert['hashtag'].upper()} [{urgency}]")
            print(f"   Viral Score: {alert['viral_score']:.3f}")
            print(f"   Confidence: {alert['confidence']:.3f}")
            print(f"   Methods: {', '.join(alert['detection_methods'])}")
            
            # Show key metrics
            metrics = alert.get('growth_metrics', {})
            
            if 'exponential_growth' in metrics and metrics['exponential_growth'].get('detected'):
                exp = metrics['exponential_growth']
                print(f"   📈 Exponential growth detected (R²={exp.get('r_squared', 0):.3f})")
            
            if 'anomaly_score' in metrics and metrics['anomaly_score'].get('detected'):
                anomaly = metrics['anomaly_score']
                print(f"   🚨 Usage anomaly (Z-score={anomaly.get('z_score', 0):.2f})")
            
            if 'creator_velocity' in metrics:
                creator = metrics['creator_velocity']
                print(f"   👥 Creator growth: {creator.get('velocity', 0):.1f}/hour")
        
        # Save alerts to file
        self._save_alerts_to_file(alerts)
        
        print("=" * 50)
    
    def _calculate_urgency(self, alert: Dict) -> str:
        """Calculate alert urgency level"""
        score = alert['viral_score']
        confidence = alert['confidence']
        
        if score > 0.8 and confidence > 0.9:
            return "CRITICAL"
        elif score > 0.6 and confidence > 0.8:
            return "HIGH"
        elif score > 0.4 and confidence > 0.7:
            return "MEDIUM"
        else:
            return "LOW"
    
    def _save_alerts_to_file(self, alerts: List[Dict]):
        """Save alerts to a file for external processing"""
        alerts_dir = "alerts"
        os.makedirs(alerts_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = os.path.join(alerts_dir, f"viral_alerts_{timestamp}.json")
        
        alert_data = {
            'timestamp': datetime.now().isoformat(),
            'alert_count': len(alerts),
            'alerts': alerts
        }
        
        try:
            with open(filename, 'w') as f:
                json.dump(alert_data, f, indent=2, default=str)
            print(f"   💾 Alerts saved to: {filename}")
        except Exception as e:
            print(f"   ❌ Failed to save alerts: {e}")
    
    def _cleanup_old_alerts(self):
        """Remove old alerts from memory to prevent memory leaks"""
        if len(self.alert_history) > 10000:  # Keep only recent 10k alerts
            # Convert to list, sort, and keep most recent
            sorted_alerts = sorted(list(self.alert_history))
            self.alert_history = set(sorted_alerts[-5000:])  # Keep most recent 5k
    
    def _cleanup(self):
        """Cleanup resources"""
        print("🧹 Cleaning up resources...")
        
        # Save final statistics
        if self.last_check:
            duration = datetime.now() - self.last_check
            print(f"📊 Monitoring duration: {duration}")
            print(f"📢 Total alerts generated: {len(self.alert_history)}")

def run_single_check():
    """Run a single viral detection check (non-monitoring mode)"""
    dashboard = ViralMonitoringDashboard()
    
    print("🔍 Running single viral keyword check...")
    print("=" * 50)
    
    try:
        results = dashboard.engine.detect_viral_keywords(dashboard.db_path, analysis_window_hours=168)
        
        if results:
            print(f"📈 Detected {len(results)} viral keywords:")
            print()
            
            for i, result in enumerate(results[:10], 1):
                urgency = dashboard._calculate_urgency(result)
                print(f"{i:2}. #{result['hashtag']:<20} "
                      f"Score: {result['viral_score']:.3f}  "
                      f"Confidence: {result['confidence']:.3f}  "
                      f"[{urgency}]")
            
            if len(results) > 10:
                print(f"    ... and {len(results) - 10} more")
        else:
            print("😴 No viral keywords detected")
            print("💡 Try adjusting thresholds or increasing the analysis window")
    
    except Exception as e:
        print(f"❌ Check failed: {e}")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='TikTok Viral Keyword Monitoring Dashboard')
    parser.add_argument('--monitor', action='store_true',
                       help='Run continuous monitoring (default: single check)')
    parser.add_argument('--interval', type=int, default=300,
                       help='Monitoring interval in seconds (default: 300)')
    parser.add_argument('--threshold', type=float, default=0.7,
                       help='Confidence threshold for alerts (default: 0.7)')
    
    args = parser.parse_args()
    
    if args.monitor:
        # Continuous monitoring mode
        dashboard = ViralMonitoringDashboard()
        dashboard.check_interval = args.interval
        dashboard.confidence_threshold = args.threshold
        dashboard.start_monitoring()
    else:
        # Single check mode
        run_single_check()

if __name__ == "__main__":
    main()
