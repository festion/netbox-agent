#!/usr/bin/env python3
"""Simple HTTP health check server"""

import json
import asyncio
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.monitoring.health import HealthMonitor
from src.monitoring.metrics import SimpleMetrics

class HealthHandler(BaseHTTPRequestHandler):
    def __init__(self, health_monitor, metrics, *args, **kwargs):
        self.health_monitor = health_monitor
        self.metrics = metrics
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        if self.path == '/health':
            self.handle_health()
        elif self.path == '/metrics':
            self.handle_metrics()
        else:
            self.send_error(404)
    
    def handle_health(self):
        try:
            # Run health checks in async context
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            health_results = loop.run_until_complete(self.health_monitor.run_all_checks())
            loop.close()
            
            # Determine response code
            overall_status = self.health_monitor.system_status.value
            status_code = 200 if overall_status == 'healthy' else 503
            
            self.send_response(status_code)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            response = {
                "status": overall_status,
                "checks": {name: {
                    "status": check.status.value,
                    "message": check.message,
                    "response_time": check.response_time
                } for name, check in health_results.items()}
            }
            
            self.wfile.write(json.dumps(response, indent=2).encode())
            
        except Exception as e:
            self.send_error(500, str(e))
    
    def handle_metrics(self):
        try:
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            metrics_output = self.metrics.get_metrics()
            self.wfile.write(json.dumps(metrics_output, indent=2).encode())
            
        except Exception as e:
            self.send_error(500, str(e))

def run_health_server(port=8080):
    """Run simple health check server"""
    # Initialize monitoring
    config = {"netbox": {"url": "http://localhost"}}
    health_monitor = HealthMonitor(config)
    metrics = SimpleMetrics()
    
    # Create server
    handler = lambda *args, **kwargs: HealthHandler(health_monitor, metrics, *args, **kwargs)
    server = HTTPServer(('0.0.0.0', port), handler)
    
    print(f"Health server running on port {port}")
    print(f"Health endpoint: http://localhost:{port}/health")
    print(f"Metrics endpoint: http://localhost:{port}/metrics")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Shutting down health server")
        server.shutdown()

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    run_health_server(port)