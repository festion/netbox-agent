from collections import defaultdict, deque
import time
import json
from typing import Dict

class SimpleMetrics:
    """Simple metrics collection without external dependencies"""
    
    def __init__(self):
        self.counters = defaultdict(int)
        self.histograms = defaultdict(lambda: deque(maxlen=100))
        self.gauges = {}
        self.start_time = time.time()
    
    def increment_counter(self, name: str, value: int = 1, labels: Dict = None):
        """Increment a counter metric"""
        key = f"{name}:{json.dumps(labels or {}, sort_keys=True)}"
        self.counters[key] += value
    
    def record_histogram(self, name: str, value: float, labels: Dict = None):
        """Record a histogram value"""
        key = f"{name}:{json.dumps(labels or {}, sort_keys=True)}"
        self.histograms[key].append(value)
    
    def set_gauge(self, name: str, value: float, labels: Dict = None):
        """Set a gauge value"""
        key = f"{name}:{json.dumps(labels or {}, sort_keys=True)}"
        self.gauges[key] = value
    
    def get_metrics(self) -> Dict:
        """Get all metrics as dictionary"""
        metrics = {
            "uptime_seconds": time.time() - self.start_time,
            "counters": dict(self.counters),
            "gauges": dict(self.gauges),
            "histograms": {}
        }
        
        # Calculate histogram statistics
        for key, values in self.histograms.items():
            if values:
                metrics["histograms"][key] = {
                    "count": len(values),
                    "avg": sum(values) / len(values),
                    "min": min(values),
                    "max": max(values)
                }
        
        return metrics