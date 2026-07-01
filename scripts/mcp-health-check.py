#!/usr/bin/env python3
"""Enhanced MCP Endpoint Health Check Script - Simplified Version"""

import subprocess
import json
import sys
import time
from datetime import datetime

# Service endpoint configurations with more specific checks
ENDPOINTS = [
    # docker-mcp: GET /mcp/ endpoint
    ("wamcp", "https://wamcp.loc.wallacearizona.us/mcp/", "GET"),
    
    # unifi-mcp: Should accept POST to /mcp 
    ("wamcp-unifi", "https://wamcp-unifi.loc.wallacearizona.us/mcp", "POST", "{}"),
    
    # truenas-mcp: GET /health endpoint
    ("wamcp-truenas", "https://wamcp-truenas.loc.wallacearizona.us/health", "GET"),
    
    # proxmox-mcp-plus: POST /get_cluster_status
    ("wamcp-proxmox-plus", "https://wamcp-proxmox-plus.loc.wallacearizona.us/get_cluster_status", "POST", "{}"),
    
    # pihole-mcp: GET /sse endpoint
    ("wamcp-pihole", "https://wamcp-pihole.loc.wallacearizona.us/sse", "GET"),
]

def check_endpoint(name, url, method="GET", data=None, timeout=10):
    """Check endpoint reachability via curl with enhanced error handling"""
    try:
        # Basic curl command for simple execution
        cmd = [
            "curl", 
            "-s",           # Silent mode
            "-o", "/dev/null", # Output to /dev/null
            "-w", "%{http_code}", # Return HTTP status only
            "--connect-timeout", str(timeout),
            "--max-time", str(timeout + 5),
            "-X", method,
        ]
        
        # Add headers for POST requests
        if method == "POST":
            cmd.extend(["-H", "Content-Type: application/json"])
            if data:
                cmd.extend(["-d", data])
                
        cmd.append(url)
        
        # Execute the curl command
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 10)
        output = result.stdout.strip()
        
        # Try to extract status code properly
        if not output:
            return {
                "status": "unreachable",
                "code": 0,
                "success": False,
                "error": "Empty response"
            }
        
        # Handle numeric responses 
        if output.isdigit() and int(output) > 0:
            code = int(output)
            return {
                "status": "reachable",
                "code": code,
                "success": True,
                "error": ""
            }
        else:
            return {
                "status": "error",
                "code": 0,
                "success": False,
                "error": f"Unexpected response: {output}"
            }
            
    except subprocess.TimeoutExpired:
        return {
            "status": "timeout", 
            "code": -1,
            "success": False,
            "error": f"Timeout after {timeout}s"
        }
    except Exception as e:
        return {
            "status": "error",
            "code": -1,
            "success": False,
            "error": f"Error: {str(e)}"
        }

def main():
    results = {}
    failures = []
    
    print("Starting MCP health check at {}".format(datetime.now().isoformat()))
    
    # Define endpoints with their specific methods and data
    for endpoint_config in ENDPOINTS:
        name = endpoint_config[0]
        url = endpoint_config[1]
        method = endpoint_config[2] if len(endpoint_config) > 2 else "GET"
        data = endpoint_config[3] if len(endpoint_config) > 3 else None
        
        start_time = time.time()
        result = check_endpoint(name, url, method, data)
        end_time = time.time()
        
        # Add processing time to timing info
        result["processing_time"] = end_time - start_time
        
        results[f"endpoint_{name}"] = result
        
        # Track failures
        if result["status"] != "reachable" or not result.get("success", False):
            failures.append({
                "service": name,
                "status": result["status"],
                "error": result.get("error", "Unknown error"),
                "code": result.get("code", -1)
            })
    
    # Add metadata
    results["timestamp"] = datetime.now().isoformat()
    results["failures"] = failures
    
    # Output to stdout for human consumption
    print(json.dumps(results, indent=2))
    
    # Also write to file for cron job consumption
    try:
        with open("/tmp/mcp-check-results.json", "w") as f:
            json.dump(results, f, indent=2)
    except Exception as e:
        print(f"Warning: Could not write results to file: {e}")
    
    # Return exit code based on failures
    failure_count = len(failures)
    if failure_count > 0:
        print(f"\nFound {failure_count} service issue(s)")
        for fail in failures:
            print(f"  - {fail['service']}: {fail['status']} ({fail['error']})")
    
    # Exit with 0 for success, 1 for any failures
    return 0 if failure_count == 0 else 1

if __name__ == "__main__":
    sys.exit(main())