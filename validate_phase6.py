#!/usr/bin/env python3
"""
Phase 6 Production Readiness Validation Script
Validates all production readiness features and deployments
"""

import sys
import os
import json
import subprocess
import importlib.util
from pathlib import Path

class Phase6Validator:
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.passed_checks = []
        
    def log_error(self, message):
        self.errors.append(message)
        print(f"❌ {message}")
    
    def log_warning(self, message):
        self.warnings.append(message)
        print(f"⚠️  {message}")
    
    def log_success(self, message):
        self.passed_checks.append(message)
        print(f"✅ {message}")
    
    def check_error_handling_system(self):
        """Validate error handling implementation"""
        print("\n🔍 Checking Error Handling System...")
        
        error_handling_file = Path("src/utils/error_handling.py")
        if not error_handling_file.exists():
            self.log_error("Error handling module not found")
            return
        
        # Check for required classes and functions
        try:
            spec = importlib.util.spec_from_file_location("error_handling", error_handling_file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            required_classes = ["ErrorSeverity", "ErrorCategory", "ErrorEvent", "ErrorHandler"]
            for cls_name in required_classes:
                if not hasattr(module, cls_name):
                    self.log_error(f"Missing class: {cls_name}")
                else:
                    self.log_success(f"Found class: {cls_name}")
            
            # Check retry decorator
            if hasattr(module, "retry_with_backoff"):
                self.log_success("Retry decorator available")
            else:
                self.log_error("Missing retry_with_backoff decorator")
                
        except Exception as e:
            self.log_error(f"Error importing error handling module: {e}")
    
    def check_health_monitoring(self):
        """Validate health monitoring system"""
        print("\n🔍 Checking Health Monitoring System...")
        
        health_file = Path("src/monitoring/health.py")
        if not health_file.exists():
            self.log_error("Health monitoring module not found")
            return
        
        try:
            spec = importlib.util.spec_from_file_location("health", health_file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            required_classes = ["HealthStatus", "HealthCheck", "HealthMonitor"]
            for cls_name in required_classes:
                if not hasattr(module, cls_name):
                    self.log_error(f"Missing class: {cls_name}")
                else:
                    self.log_success(f"Found class: {cls_name}")
                    
        except Exception as e:
            self.log_error(f"Error importing health module: {e}")
    
    def check_performance_optimization(self):
        """Validate performance optimization features"""
        print("\n🔍 Checking Performance Optimization...")
        
        # Check caching system
        cache_file = Path("src/utils/caching.py")
        if not cache_file.exists():
            self.log_error("Caching module not found")
        else:
            self.log_success("Caching module found")
        
        # Check connection pooling
        pool_file = Path("src/utils/connection_pool.py")
        if not pool_file.exists():
            self.log_error("Connection pooling module not found")
        else:
            self.log_success("Connection pooling module found")
    
    def check_metrics_system(self):
        """Validate metrics collection system"""
        print("\n🔍 Checking Metrics Collection...")
        
        metrics_file = Path("src/monitoring/metrics.py")
        if not metrics_file.exists():
            self.log_error("Metrics module not found")
            return
        
        try:
            spec = importlib.util.spec_from_file_location("metrics", metrics_file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            if hasattr(module, "SimpleMetrics"):
                self.log_success("SimpleMetrics class found")
            else:
                self.log_error("SimpleMetrics class not found")
                
        except Exception as e:
            self.log_error(f"Error importing metrics module: {e}")
    
    def check_deployment_configurations(self):
        """Validate deployment configurations"""
        print("\n🔍 Checking Deployment Configurations...")
        
        # Check systemd service
        service_file = Path("scripts/netbox-agent.service")
        if service_file.exists():
            self.log_success("Systemd service file found")
        else:
            self.log_error("Systemd service file not found")
        
        # Check Docker configurations
        dockerfile = Path("Dockerfile")
        docker_compose = Path("docker-compose.yml")
        
        if dockerfile.exists():
            self.log_success("Dockerfile found")
        else:
            self.log_error("Dockerfile not found")
        
        if docker_compose.exists():
            self.log_success("Docker Compose file found")
        else:
            self.log_error("Docker Compose file not found")
    
    def check_installation_scripts(self):
        """Validate installation and setup scripts"""
        print("\n🔍 Checking Installation Scripts...")
        
        scripts = [
            "scripts/install.sh",
            "scripts/quick-start.sh",
            "scripts/validate-config.py",
            "scripts/health_check.py",
            "scripts/health_server.py"
        ]
        
        for script in scripts:
            script_path = Path(script)
            if script_path.exists():
                # Check if executable
                if os.access(script_path, os.X_OK):
                    self.log_success(f"Script found and executable: {script}")
                else:
                    self.log_warning(f"Script found but not executable: {script}")
            else:
                self.log_error(f"Script not found: {script}")
    
    def check_requirements(self):
        """Validate requirements and dependencies"""
        print("\n🔍 Checking Requirements...")
        
        req_file = Path("requirements.txt")
        if not req_file.exists():
            self.log_error("requirements.txt not found")
            return
        
        # Check for production-ready dependencies
        with open(req_file) as f:
            requirements = f.read().lower()
        
        required_deps = ["psutil", "aiohttp"]
        for dep in required_deps:
            if dep in requirements:
                self.log_success(f"Required dependency found: {dep}")
            else:
                self.log_error(f"Missing required dependency: {dep}")
    
    def validate_file_structure(self):
        """Validate the overall file structure"""
        print("\n🔍 Checking File Structure...")
        
        required_dirs = [
            "src/utils",
            "src/monitoring", 
            "scripts",
            "config"
        ]
        
        for dir_path in required_dirs:
            if Path(dir_path).exists():
                self.log_success(f"Directory found: {dir_path}")
            else:
                self.log_error(f"Directory not found: {dir_path}")
    
    def run_validation(self):
        """Run all validation checks"""
        print("🚀 Starting Phase 6 Production Readiness Validation")
        print("=" * 60)
        
        self.validate_file_structure()
        self.check_error_handling_system()
        self.check_health_monitoring()
        self.check_performance_optimization()
        self.check_metrics_system()
        self.check_deployment_configurations()
        self.check_installation_scripts()
        self.check_requirements()
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 VALIDATION SUMMARY")
        print("=" * 60)
        
        print(f"✅ Passed checks: {len(self.passed_checks)}")
        print(f"⚠️  Warnings: {len(self.warnings)}")
        print(f"❌ Errors: {len(self.errors)}")
        
        if self.errors:
            print("\n❌ ERRORS FOUND:")
            for error in self.errors:
                print(f"   • {error}")
        
        if self.warnings:
            print("\n⚠️  WARNINGS:")
            for warning in self.warnings:
                print(f"   • {warning}")
        
        if not self.errors:
            print("\n🎉 Phase 6 Production Readiness validation PASSED!")
            print("The NetBox Agent is ready for production deployment!")
            return True
        else:
            print(f"\n💥 Phase 6 validation FAILED with {len(self.errors)} error(s)")
            print("Please fix the errors above before proceeding to production.")
            return False

def main():
    validator = Phase6Validator()
    success = validator.run_validation()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()