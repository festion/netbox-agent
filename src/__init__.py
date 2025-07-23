"""
NetBox Agent - Automated NetBox population from various sources

This package provides automated discovery and population of NetBox infrastructure
data from multiple sources including Home Assistant, network scans, and file systems.
"""

__version__ = "1.0.0"
__author__ = "dev"
__email__ = "dev@example.com"

from .netbox_agent import NetBoxAgent

__all__ = ["NetBoxAgent"]