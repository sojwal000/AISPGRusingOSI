"""
Time Series Forecasting for Risk Prediction.
Uses Prophet and statistical methods to forecast future risk levels.
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import logging
import numpy as np

# Setup logger
try:
    from app.core.logging import setup_logger
    logger = setup_logger(__name__)
except ImportError:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)


class RiskForecaster:
    """
    Time series forecasting for geopolitical risk scores.
    Uses Prophet for trend and seasonality analysis.
    """
    
    # Forecast configuration
    DEFAULT_FORECAST_DAYS = 14
    MIN_DATA_POINTS = 14  # Minimum historical points needed
    
    # Seasonality patterns (weekly patterns in geopolitical events)
    WEEKLY_SEASONALITY = True
    YEARLY_SEASONALITY = True
    
    def __init__(self):
        """Initialize risk forecaster."""
        self.model = None
        self._prophet_available = None
        logger.info("RiskForecaster initialized")
    
    def _check_prophet(self) -> bool:
        """Check if Prophet is available."""
        if self._prophet_available is not None:
            return self._prophet_available
        
        try:
            from prophet import Prophet
            self._prophet_available = True
            logger.info("Prophet is available")
        except ImportError:
            self._prophet_available = False
            logger.warning("Prophet not installed - using statistical fallback")
        
        return self._prophet_available
    
    def prepare_data(self, risk_scores: List[Dict]) -> Optional[object]:
        """
        Prepare data for Prophet forecasting.
        
        Args:
            risk_scores: List of dicts with 'timestamp' and 'overall_score'
        
        Returns:
            DataFrame for Prophet or None if insufficient data
        """
        if len(risk_scores) < self.MIN_DATA_POINTS:
            logger.warning(f"Insufficient data points: {len(risk_scores)} < {self.MIN_DATA_POINTS}")
            return None
        
        try:
            import pandas as pd
            
            # Convert to DataFrame
            df = pd.DataFrame(risk_scores)
            
            # Ensure correct column names for Prophet
            if 'timestamp' in df.columns:
                df['ds'] = pd.to_datetime(df['timestamp'])
            elif 'date' in df.columns:
                df['ds'] = pd.to_datetime(df['date'])
            else:
                logger.error("No timestamp column found in data")
                return None
            
            # Use overall_score as target
            if 'overall_score' in df.columns:
                df['y'] = df['overall_score']
            elif 'score' in df.columns:
                df['y'] = df['score']
            else:
                logger.error("No score column found in data")
                return None
            
            # Sort by date and handle duplicates
            df = df.groupby('ds')['y'].mean().reset_index()
            df = df.sort_values('ds')
            
            logger.info(f"Prepared {len(df)} data points for forecasting")
            return df[['ds', 'y']]
            
        except Exception as e:
            logger.error(f"Error preparing data: {e}")
            return None
    
    def forecast_prophet(self, df, periods: int = 14) -> Dict:
        """
        Forecast using Prophet.
        
        Args:
            df: Prepared DataFrame with 'ds' and 'y' columns
            periods: Number of days to forecast
        
        Returns:
            Forecast results dictionary
        """
        try:
            from prophet import Prophet
            import pandas as pd
            
            # Initialize Prophet with geopolitical-relevant settings
            model = Prophet(
                daily_seasonality=False,
                weekly_seasonality=self.WEEKLY_SEASONALITY,
                yearly_seasonality=self.YEARLY_SEASONALITY,
                changepoint_prior_scale=0.1,  # More sensitive to changes
                interval_width=0.95
            )
            
            # Fit model
            model.fit(df)
            
            # Create future dates
            future = model.make_future_dataframe(periods=periods)
            
            # Generate forecast
            forecast = model.predict(future)
            
            # Extract relevant columns
            result_df = forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].tail(periods)
            
            # Build result
            forecasts = []
            for _, row in result_df.iterrows():
                forecasts.append({
                    "date": row['ds'].strftime('%Y-%m-%d'),
                    "predicted_score": round(max(0, min(100, row['yhat'])), 2),
                    "lower_bound": round(max(0, min(100, row['yhat_lower'])), 2),
                    "upper_bound": round(max(0, min(100, row['yhat_upper'])), 2)
                })
            
            # Calculate trend direction
            last_actual = df['y'].iloc[-1]
            last_forecast = forecasts[-1]['predicted_score'] if forecasts else last_actual
            trend = "increasing" if last_forecast > last_actual + 5 else (
                "decreasing" if last_forecast < last_actual - 5 else "stable"
            )
            
            # Get trend components
            trend_components = {
                "trend": "up" if trend == "increasing" else ("down" if trend == "decreasing" else "flat"),
                "change_rate": round((last_forecast - last_actual) / max(last_actual, 1) * 100, 2)
            }
            
            return {
                "method": "prophet",
                "forecast_days": periods,
                "forecasts": forecasts,
                "trend": trend,
                "trend_components": trend_components,
                "current_score": round(last_actual, 2),
                "predicted_end_score": last_forecast,
                "confidence_interval": 0.95
            }
            
        except Exception as e:
            logger.error(f"Prophet forecasting failed: {e}")
            return {"error": str(e), "method": "prophet_failed"}
    
    def forecast_statistical(self, risk_scores: List[Dict], periods: int = 14) -> Dict:
        """
        Statistical fallback forecasting using moving averages and linear regression.
        
        Args:
            risk_scores: Historical risk scores
            periods: Number of days to forecast
        
        Returns:
            Forecast results dictionary
        """
        try:
            from datetime import datetime, timedelta
            
            # Extract scores and dates
            scores = []
            dates = []
            for r in risk_scores:
                score = r.get('overall_score') or r.get('score', 50)
                scores.append(score)
                
                ts = r.get('timestamp') or r.get('date')
                if isinstance(ts, str):
                    ts = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                dates.append(ts)
            
            if len(scores) < 3:
                return {"error": "Insufficient data", "method": "statistical"}
            
            scores = np.array(scores)
            
            # Calculate statistics
            mean_score = np.mean(scores)
            std_score = np.std(scores)
            
            # Simple linear regression for trend
            x = np.arange(len(scores))
            slope, intercept = np.polyfit(x, scores, 1)
            
            # Moving average (7-day)
            ma_window = min(7, len(scores))
            ma = np.convolve(scores, np.ones(ma_window)/ma_window, mode='valid')
            recent_ma = ma[-1] if len(ma) > 0 else mean_score
            
            # Generate forecasts
            forecasts = []
            last_date = dates[-1] if dates else datetime.utcnow()
            
            for i in range(1, periods + 1):
                # Trend-based prediction with mean reversion
                trend_pred = intercept + slope * (len(scores) + i)
                
                # Weight recent MA more heavily
                predicted = 0.6 * recent_ma + 0.3 * trend_pred + 0.1 * mean_score
                predicted = max(0, min(100, predicted))
                
                # Confidence bounds widen over time
                uncertainty = std_score * (1 + i * 0.1)
                
                forecast_date = last_date + timedelta(days=i)
                forecasts.append({
                    "date": forecast_date.strftime('%Y-%m-%d'),
                    "predicted_score": round(predicted, 2),
                    "lower_bound": round(max(0, predicted - uncertainty), 2),
                    "upper_bound": round(min(100, predicted + uncertainty), 2)
                })
            
            # Determine trend
            trend = "increasing" if slope > 1 else ("decreasing" if slope < -1 else "stable")
            
            return {
                "method": "statistical",
                "forecast_days": periods,
                "forecasts": forecasts,
                "trend": trend,
                "trend_components": {
                    "slope": round(slope, 4),
                    "mean": round(mean_score, 2),
                    "std": round(std_score, 2),
                    "recent_ma": round(recent_ma, 2)
                },
                "current_score": round(scores[-1], 2),
                "predicted_end_score": forecasts[-1]['predicted_score'] if forecasts else mean_score,
                "confidence_interval": 0.68  # ~1 std dev
            }
            
        except Exception as e:
            logger.error(f"Statistical forecasting failed: {e}")
            return {"error": str(e), "method": "statistical_failed"}
    
    def forecast(self, risk_scores: List[Dict], periods: int = None) -> Dict:
        """
        Main forecasting method - uses Prophet if available, else statistical fallback.
        
        Args:
            risk_scores: List of historical risk scores
            periods: Number of days to forecast
        
        Returns:
            Forecast results
        """
        periods = periods or self.DEFAULT_FORECAST_DAYS
        
        if not risk_scores:
            return {"error": "No data provided", "method": "none"}
        
        # Try Prophet first
        if self._check_prophet():
            df = self.prepare_data(risk_scores)
            if df is not None and len(df) >= self.MIN_DATA_POINTS:
                result = self.forecast_prophet(df, periods)
                if "error" not in result:
                    return result
        
        # Fallback to statistical method
        return self.forecast_statistical(risk_scores, periods)
    
    def detect_trend_change(self, risk_scores: List[Dict], threshold: float = 15.0) -> Dict:
        """
        Detect significant trend changes in risk scores.
        
        Args:
            risk_scores: Historical risk scores
            threshold: Percentage change threshold for significance
        
        Returns:
            Trend change analysis
        """
        if len(risk_scores) < 7:
            return {"change_detected": False, "reason": "insufficient_data"}
        
        scores = [r.get('overall_score') or r.get('score', 50) for r in risk_scores]
        
        # Compare recent week to previous period
        recent = np.mean(scores[-7:])
        previous = np.mean(scores[-14:-7]) if len(scores) >= 14 else np.mean(scores[:-7])
        
        change_pct = (recent - previous) / max(previous, 1) * 100
        
        if abs(change_pct) > threshold:
            direction = "increasing" if change_pct > 0 else "decreasing"
            severity = "significant" if abs(change_pct) > threshold * 2 else "moderate"
            
            return {
                "change_detected": True,
                "direction": direction,
                "change_percentage": round(change_pct, 2),
                "severity": severity,
                "recent_average": round(recent, 2),
                "previous_average": round(previous, 2)
            }
        
        return {
            "change_detected": False,
            "change_percentage": round(change_pct, 2),
            "recent_average": round(recent, 2),
            "previous_average": round(previous, 2)
        }
    
    def get_risk_outlook(self, forecast_result: Dict) -> Dict:
        """
        Generate human-readable risk outlook from forecast.
        
        Args:
            forecast_result: Output from forecast() method
        
        Returns:
            Risk outlook summary
        """
        if "error" in forecast_result:
            return {
                "outlook": "unknown",
                "confidence": "low",
                "summary": "Insufficient data for outlook"
            }
        
        current = forecast_result.get('current_score', 50)
        predicted = forecast_result.get('predicted_end_score', current)
        trend = forecast_result.get('trend', 'stable')
        
        # Determine outlook
        if predicted > 75:
            outlook = "critical"
            summary = f"Risk expected to reach critical levels ({predicted:.0f})"
        elif predicted > 60:
            outlook = "elevated"
            summary = f"Risk expected to be elevated ({predicted:.0f})"
        elif predicted > 40:
            outlook = "moderate"
            summary = f"Risk expected to remain moderate ({predicted:.0f})"
        else:
            outlook = "low"
            summary = f"Risk expected to remain low ({predicted:.0f})"
        
        # Add trend context
        if trend == "increasing":
            summary += " with upward trend"
        elif trend == "decreasing":
            summary += " with improving conditions"
        
        # Determine confidence
        method = forecast_result.get('method', 'unknown')
        ci = forecast_result.get('confidence_interval', 0.68)
        confidence = "high" if method == "prophet" and ci >= 0.9 else (
            "medium" if ci >= 0.8 else "low"
        )
        
        return {
            "outlook": outlook,
            "confidence": confidence,
            "summary": summary,
            "trend": trend,
            "current_score": round(current, 2),
            "predicted_score": round(predicted, 2),
            "forecast_days": forecast_result.get('forecast_days', 14)
        }


# Singleton instance
_forecaster = None


def get_risk_forecaster() -> RiskForecaster:
    """Get or create singleton forecaster instance."""
    global _forecaster
    if _forecaster is None:
        _forecaster = RiskForecaster()
    return _forecaster


if __name__ == "__main__":
    # Test forecasting
    from datetime import datetime, timedelta
    
    # Generate sample data
    base_date = datetime.utcnow() - timedelta(days=30)
    sample_data = []
    
    for i in range(30):
        date = base_date + timedelta(days=i)
        # Simulate trending risk with some noise
        score = 45 + i * 0.5 + np.random.normal(0, 3)
        score = max(0, min(100, score))
        
        sample_data.append({
            "timestamp": date,
            "overall_score": score
        })
    
    print("Testing Risk Forecasting:")
    print("=" * 80)
    
    forecaster = RiskForecaster()
    result = forecaster.forecast(sample_data, periods=7)
    
    print(f"Method: {result.get('method')}")
    print(f"Current score: {result.get('current_score')}")
    print(f"Trend: {result.get('trend')}")
    print(f"Forecasts:")
    
    for f in result.get('forecasts', [])[:5]:
        print(f"  {f['date']}: {f['predicted_score']} [{f['lower_bound']}-{f['upper_bound']}]")
    
    print()
    outlook = forecaster.get_risk_outlook(result)
    print(f"Outlook: {outlook['outlook']} (confidence: {outlook['confidence']})")
    print(f"Summary: {outlook['summary']}")
