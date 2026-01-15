"""
Anomaly Detection for Geopolitical Risk Signals.
Detects unusual patterns in risk scores, events, and news volume.
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import logging
import numpy as np
from collections import defaultdict

# Setup logger
try:
    from app.core.logging import setup_logger
    logger = setup_logger(__name__)
except ImportError:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)


class AnomalyDetector:
    """
    Multi-method anomaly detection for risk signals.
    Uses Isolation Forest, statistical methods, and domain-specific rules.
    """
    
    # Configuration
    CONTAMINATION = 0.1  # Expected proportion of anomalies
    Z_SCORE_THRESHOLD = 2.5  # Standard deviations for statistical anomaly
    IQR_MULTIPLIER = 1.5  # Interquartile range multiplier
    
    # Domain-specific thresholds
    RISK_SPIKE_THRESHOLD = 20.0  # Points increase in 24h
    NEWS_VOLUME_SPIKE = 3.0  # Multiple of average
    EVENT_CLUSTER_THRESHOLD = 5  # Events in short window
    
    def __init__(self):
        """Initialize anomaly detector."""
        self._sklearn_available = None
        self._isolation_forest = None
        logger.info("AnomalyDetector initialized")
    
    def _check_sklearn(self) -> bool:
        """Check if sklearn is available."""
        if self._sklearn_available is not None:
            return self._sklearn_available
        
        try:
            from sklearn.ensemble import IsolationForest
            self._sklearn_available = True
        except ImportError:
            self._sklearn_available = False
            logger.warning("sklearn not available - using statistical methods only")
        
        return self._sklearn_available
    
    def detect_zscore_anomalies(self, values: List[float], 
                                threshold: float = None) -> List[Dict]:
        """
        Detect anomalies using Z-score method.
        
        Args:
            values: List of numeric values
            threshold: Z-score threshold (default: Z_SCORE_THRESHOLD)
        
        Returns:
            List of anomaly detections
        """
        threshold = threshold or self.Z_SCORE_THRESHOLD
        
        if len(values) < 3:
            return []
        
        arr = np.array(values)
        mean = np.mean(arr)
        std = np.std(arr)
        
        if std == 0:
            return []
        
        anomalies = []
        for i, val in enumerate(values):
            z_score = (val - mean) / std
            
            if abs(z_score) > threshold:
                anomalies.append({
                    "index": i,
                    "value": val,
                    "z_score": round(z_score, 4),
                    "type": "high" if z_score > 0 else "low",
                    "severity": "critical" if abs(z_score) > threshold * 1.5 else "warning"
                })
        
        return anomalies
    
    def detect_iqr_anomalies(self, values: List[float], 
                            multiplier: float = None) -> List[Dict]:
        """
        Detect anomalies using Interquartile Range method.
        More robust to outliers than Z-score.
        
        Args:
            values: List of numeric values
            multiplier: IQR multiplier (default: IQR_MULTIPLIER)
        
        Returns:
            List of anomaly detections
        """
        multiplier = multiplier or self.IQR_MULTIPLIER
        
        if len(values) < 4:
            return []
        
        arr = np.array(values)
        q1 = np.percentile(arr, 25)
        q3 = np.percentile(arr, 75)
        iqr = q3 - q1
        
        lower_bound = q1 - multiplier * iqr
        upper_bound = q3 + multiplier * iqr
        
        anomalies = []
        for i, val in enumerate(values):
            if val < lower_bound or val > upper_bound:
                deviation = (val - upper_bound) if val > upper_bound else (lower_bound - val)
                
                anomalies.append({
                    "index": i,
                    "value": val,
                    "deviation": round(deviation, 4),
                    "type": "high" if val > upper_bound else "low",
                    "bounds": {"lower": round(lower_bound, 2), "upper": round(upper_bound, 2)}
                })
        
        return anomalies
    
    def detect_isolation_forest(self, data: List[List[float]], 
                               contamination: float = None) -> List[int]:
        """
        Detect anomalies using Isolation Forest algorithm.
        Good for multivariate anomaly detection.
        
        Args:
            data: 2D array of features
            contamination: Expected proportion of anomalies
        
        Returns:
            List of anomaly indices
        """
        if not self._check_sklearn():
            return []
        
        contamination = contamination or self.CONTAMINATION
        
        if len(data) < 10:
            logger.warning("Insufficient data for Isolation Forest")
            return []
        
        try:
            from sklearn.ensemble import IsolationForest
            
            model = IsolationForest(
                contamination=contamination,
                random_state=42,
                n_estimators=100
            )
            
            predictions = model.fit_predict(data)
            
            # -1 indicates anomaly
            anomaly_indices = [i for i, p in enumerate(predictions) if p == -1]
            
            logger.info(f"Isolation Forest detected {len(anomaly_indices)} anomalies")
            return anomaly_indices
            
        except Exception as e:
            logger.error(f"Isolation Forest failed: {e}")
            return []
    
    def detect_risk_spikes(self, risk_scores: List[Dict], 
                          threshold: float = None) -> List[Dict]:
        """
        Detect sudden spikes in risk scores.
        
        Args:
            risk_scores: List of dicts with 'timestamp' and 'overall_score'
            threshold: Point change threshold
        
        Returns:
            List of spike detections
        """
        threshold = threshold or self.RISK_SPIKE_THRESHOLD
        
        if len(risk_scores) < 2:
            return []
        
        # Sort by timestamp
        sorted_scores = sorted(risk_scores, 
                              key=lambda x: x.get('timestamp') or x.get('date'))
        
        spikes = []
        for i in range(1, len(sorted_scores)):
            current = sorted_scores[i].get('overall_score') or sorted_scores[i].get('score', 0)
            previous = sorted_scores[i-1].get('overall_score') or sorted_scores[i-1].get('score', 0)
            
            change = current - previous
            
            if abs(change) >= threshold:
                ts = sorted_scores[i].get('timestamp') or sorted_scores[i].get('date')
                
                spikes.append({
                    "timestamp": ts.isoformat() if hasattr(ts, 'isoformat') else str(ts),
                    "previous_score": round(previous, 2),
                    "current_score": round(current, 2),
                    "change": round(change, 2),
                    "direction": "spike" if change > 0 else "drop",
                    "severity": "critical" if abs(change) >= threshold * 1.5 else "warning"
                })
        
        return spikes
    
    def detect_news_volume_anomaly(self, article_counts: List[Dict]) -> List[Dict]:
        """
        Detect unusual news volume (could indicate developing situation).
        
        Args:
            article_counts: List of dicts with 'date' and 'count'
        
        Returns:
            List of volume anomalies
        """
        if len(article_counts) < 7:
            return []
        
        counts = [a.get('count', 0) for a in article_counts]
        mean_count = np.mean(counts)
        
        anomalies = []
        for i, ac in enumerate(article_counts):
            count = ac.get('count', 0)
            
            if mean_count > 0 and count >= mean_count * self.NEWS_VOLUME_SPIKE:
                anomalies.append({
                    "date": ac.get('date'),
                    "count": count,
                    "average": round(mean_count, 2),
                    "multiple": round(count / mean_count, 2),
                    "type": "volume_spike",
                    "significance": "high" if count >= mean_count * 5 else "medium"
                })
        
        return anomalies
    
    def detect_event_cluster(self, events: List[Dict], 
                            window_hours: int = 24) -> List[Dict]:
        """
        Detect clusters of events (multiple incidents in short time).
        
        Args:
            events: List of events with 'timestamp'
            window_hours: Time window for clustering
        
        Returns:
            List of event clusters
        """
        if len(events) < self.EVENT_CLUSTER_THRESHOLD:
            return []
        
        # Sort events by timestamp
        sorted_events = sorted(events, 
                              key=lambda x: x.get('timestamp') or x.get('event_date'))
        
        clusters = []
        window = timedelta(hours=window_hours)
        
        i = 0
        while i < len(sorted_events):
            # Find all events within window
            start_time = sorted_events[i].get('timestamp') or sorted_events[i].get('event_date')
            if isinstance(start_time, str):
                start_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            
            cluster_events = [sorted_events[i]]
            j = i + 1
            
            while j < len(sorted_events):
                event_time = sorted_events[j].get('timestamp') or sorted_events[j].get('event_date')
                if isinstance(event_time, str):
                    event_time = datetime.fromisoformat(event_time.replace('Z', '+00:00'))
                
                if event_time - start_time <= window:
                    cluster_events.append(sorted_events[j])
                    j += 1
                else:
                    break
            
            # Check if cluster is significant
            if len(cluster_events) >= self.EVENT_CLUSTER_THRESHOLD:
                total_fatalities = sum(e.get('fatalities', 0) for e in cluster_events)
                
                clusters.append({
                    "start_time": start_time.isoformat() if hasattr(start_time, 'isoformat') else str(start_time),
                    "event_count": len(cluster_events),
                    "total_fatalities": total_fatalities,
                    "window_hours": window_hours,
                    "severity": "critical" if total_fatalities > 50 or len(cluster_events) > 10 else "high"
                })
                
                i = j  # Skip past this cluster
            else:
                i += 1
        
        return clusters
    
    def analyze_multivariate(self, risk_scores: List[Dict]) -> Dict:
        """
        Perform multivariate anomaly detection on risk signals.
        
        Args:
            risk_scores: List of risk scores with component signals
        
        Returns:
            Comprehensive anomaly analysis
        """
        if len(risk_scores) < 10:
            return {"error": "Insufficient data", "anomalies": []}
        
        # Extract features
        features = []
        for rs in risk_scores:
            feature_vector = [
                rs.get('overall_score', 50),
                rs.get('conflict_signal', {}).get('score', 0) if isinstance(rs.get('conflict_signal'), dict) else 0,
                rs.get('news_signal', {}).get('score', 0) if isinstance(rs.get('news_signal'), dict) else 0,
                rs.get('economic_signal', {}).get('score', 0) if isinstance(rs.get('economic_signal'), dict) else 0,
            ]
            features.append(feature_vector)
        
        # Run isolation forest
        if_anomalies = self.detect_isolation_forest(features)
        
        # Run statistical detection on overall scores
        overall_scores = [rs.get('overall_score', 50) for rs in risk_scores]
        zscore_anomalies = self.detect_zscore_anomalies(overall_scores)
        iqr_anomalies = self.detect_iqr_anomalies(overall_scores)
        
        # Detect spikes
        spikes = self.detect_risk_spikes(risk_scores)
        
        # Combine all anomalies
        all_anomaly_indices = set(if_anomalies)
        all_anomaly_indices.update(a['index'] for a in zscore_anomalies)
        all_anomaly_indices.update(a['index'] for a in iqr_anomalies)
        
        # Build detailed anomaly list
        anomalies = []
        for idx in sorted(all_anomaly_indices):
            rs = risk_scores[idx]
            
            methods_detected = []
            if idx in if_anomalies:
                methods_detected.append("isolation_forest")
            
            zscore_match = next((z for z in zscore_anomalies if z['index'] == idx), None)
            if zscore_match:
                methods_detected.append("z_score")
            
            iqr_match = next((i for i in iqr_anomalies if i['index'] == idx), None)
            if iqr_match:
                methods_detected.append("iqr")
            
            anomalies.append({
                "index": idx,
                "timestamp": rs.get('timestamp'),
                "overall_score": rs.get('overall_score'),
                "detection_methods": methods_detected,
                "confidence": len(methods_detected) / 3.0  # Higher if detected by multiple methods
            })
        
        return {
            "total_points": len(risk_scores),
            "anomaly_count": len(anomalies),
            "anomaly_rate": round(len(anomalies) / len(risk_scores), 4),
            "anomalies": anomalies,
            "spikes": spikes,
            "methods_used": ["isolation_forest", "z_score", "iqr"] if self._check_sklearn() else ["z_score", "iqr"]
        }
    
    def generate_alerts(self, analysis: Dict, country_code: str = None) -> List[Dict]:
        """
        Generate actionable alerts from anomaly analysis.
        
        Args:
            analysis: Output from analyze_multivariate()
            country_code: Country code for context
        
        Returns:
            List of alert objects
        """
        alerts = []
        
        # High confidence anomalies
        for anomaly in analysis.get('anomalies', []):
            if anomaly.get('confidence', 0) >= 0.66:  # Detected by 2+ methods
                alerts.append({
                    "type": "anomaly_detected",
                    "severity": "high",
                    "country": country_code,
                    "timestamp": anomaly.get('timestamp'),
                    "score": anomaly.get('overall_score'),
                    "message": f"Anomalous risk score detected: {anomaly.get('overall_score'):.1f}",
                    "detection_confidence": anomaly.get('confidence')
                })
        
        # Risk spikes
        for spike in analysis.get('spikes', []):
            if spike.get('severity') == 'critical':
                alerts.append({
                    "type": "risk_spike",
                    "severity": "critical",
                    "country": country_code,
                    "timestamp": spike.get('timestamp'),
                    "message": f"Risk spike detected: {spike.get('previous_score'):.1f} → {spike.get('current_score'):.1f} ({spike.get('direction')})",
                    "change": spike.get('change')
                })
        
        # High anomaly rate
        if analysis.get('anomaly_rate', 0) > 0.2:
            alerts.append({
                "type": "high_volatility",
                "severity": "warning",
                "country": country_code,
                "message": f"High risk volatility detected: {analysis.get('anomaly_rate')*100:.1f}% anomalous readings",
                "anomaly_rate": analysis.get('anomaly_rate')
            })
        
        return alerts


# Singleton instance
_detector = None


def get_anomaly_detector() -> AnomalyDetector:
    """Get or create singleton detector instance."""
    global _detector
    if _detector is None:
        _detector = AnomalyDetector()
    return _detector


if __name__ == "__main__":
    # Test anomaly detection
    from datetime import datetime, timedelta
    
    # Generate sample data with anomalies
    base_date = datetime.utcnow() - timedelta(days=30)
    sample_data = []
    
    for i in range(30):
        date = base_date + timedelta(days=i)
        
        # Normal score around 45-55
        score = 50 + np.random.normal(0, 5)
        
        # Inject anomalies on specific days
        if i == 10:  # Spike
            score = 85
        elif i == 20:  # Drop
            score = 15
        elif i == 25:  # Another spike
            score = 78
        
        score = max(0, min(100, score))
        
        sample_data.append({
            "timestamp": date,
            "overall_score": score
        })
    
    print("Testing Anomaly Detection:")
    print("=" * 80)
    
    detector = AnomalyDetector()
    
    # Test spike detection
    spikes = detector.detect_risk_spikes(sample_data)
    print(f"Spikes detected: {len(spikes)}")
    for s in spikes:
        print(f"  {s['timestamp']}: {s['previous_score']:.1f} → {s['current_score']:.1f} ({s['direction']})")
    
    # Test multivariate analysis
    print("\nMultivariate Analysis:")
    analysis = detector.analyze_multivariate(sample_data)
    print(f"Total anomalies: {analysis['anomaly_count']}")
    print(f"Anomaly rate: {analysis['anomaly_rate']*100:.1f}%")
    
    # Generate alerts
    print("\nGenerated Alerts:")
    alerts = detector.generate_alerts(analysis, "IND")
    for alert in alerts:
        print(f"  [{alert['severity'].upper()}] {alert['message']}")
