#!/usr/bin/env python3
"""Configuration validation script"""

import json
import sys
import os
from pathlib import Path

def validate_config():
    """Validate NetBox Agent configuration"""
    config_path = Path("config/netbox-agent.json")
    
    if not config_path.exists():
        print("❌ Configuration file not found: config/netbox-agent.json")
        return False
    
    try:
        with open(config_path) as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in configuration file: {e}")
        return False
    
    # Check required sections
    required_sections = ["netbox", "logging"]
    for section in required_sections:
        if section not in config:
            print(f"❌ Missing required section: {section}")
            return False
    
    # Check NetBox configuration
    netbox_config = config.get("netbox", {})
    if not netbox_config.get("url"):
        print("❌ NetBox URL not configured")
        return False
    
    if not netbox_config.get("token"):
        print("❌ NetBox API token not configured")
        return False
    
    # Check environment file
    env_path = Path(".env")
    if not env_path.exists():
        print("⚠️  Environment file (.env) not found - using defaults")
    
    print("✅ Configuration validation passed")
    return True

if __name__ == "__main__":
    if validate_config():
        sys.exit(0)
    else:
        sys.exit(1)