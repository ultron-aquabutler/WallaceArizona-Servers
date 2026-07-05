#!/usr/bin/env python3
"""
NetBox MCP Server for WallaceArizona Homelab.

Provides read-only access to NetBox infrastructure data via MCP tools.
Uses pynetbox for the NetBox API and FastMCP for the MCP transport layer.
"""

import os
import logging
from typing import Optional

import pynetbox
from mcp.server.fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

NETBOX_URL = os.getenv("NETBOX_URL", "https://netbox.loc.wallacearizona.us")
NETBOX_API_TOKEN = os.getenv("NETBOX_API_TOKEN")
if not NETBOX_API_TOKEN:
    raise ValueError("NETBOX_API_TOKEN environment variable is required")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# NetBox API client (pynetbox)
# ---------------------------------------------------------------------------

nb = pynetbox.api(NETBOX_URL, token=NETBOX_API_TOKEN)
nb.http_session.verify = True  # default; keep explicit for clarity

# ---------------------------------------------------------------------------
# MCP server (FastMCP — Streamable HTTP on port 8000)
# ---------------------------------------------------------------------------

mcp = FastMCP("NetBox MCP Server", port=8000)


# ---------------------------------------------------------------------------
# Helper: safe attribute access
# ---------------------------------------------------------------------------

def _val(obj, *attrs, default=None):
    """Safely drill into nested dict-like objects."""
    for a in attrs:
        try:
            obj = getattr(obj, a, None) or obj.get(a, None)
        except (AttributeError, TypeError):
            return default
        if obj is None:
            return default
    return obj


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@mcp.tool()
def get_device(name: str) -> dict:
    """
    Get device details, interfaces, and IP addresses by device name.

    Args:
        name: Device name (e.g. "ws3", "truenas", "uxg-pro")
    """
    logger.info("get_device(name=%s)", name)
    try:
        dev = nb.dcim.devices.get(name=name)
    except Exception as exc:
        return {"error": f"NetBox API error: {exc}"}

    if not dev:
        return {"error": f"Device '{name}' not found"}

    # Collect interfaces
    interfaces = []
    try:
        for iface in nb.dcim.interfaces.filter(device_id=dev.id):
            ip_list = []
            try:
                for ip in nb.ipam.ip_addresses.filter(assigned_object_id=iface.id,
                                                      assigned_object_type="dcim.interface"):
                    ip_list.append({
                        "address": str(ip.address),
                        "dns_name": ip.dns_name or "",
                        "description": ip.description or "",
                        "family": str(ip.family) if hasattr(ip, "family") else "",
                    })
            except Exception:
                pass

            interfaces.append({
                "id": iface.id,
                "name": iface.name,
                "type": _val(iface, "type", "label", default=""),
                "enabled": iface.enabled,
                "mac_address": getattr(iface, "mac_address", "") or "",
                "description": iface.description or "",
                "mtu": getattr(iface, "mtu", None),
                "ip_addresses": ip_list,
            })
    except Exception as exc:
        logger.warning("Could not fetch interfaces for device %s: %s", name, exc)

    # Collect all IPs assigned directly to the device
    ip_addresses = []
    try:
        for ip in nb.ipam.ip_addresses.filter(assigned_object_id=dev.id,
                                              assigned_object_type="dcim.device"):
            ip_addresses.append({
                "address": str(ip.address),
                "dns_name": ip.dns_name or "",
                "description": ip.description or "",
                "family": str(ip.family) if hasattr(ip, "family") else "",
            })
    except Exception:
        pass

    # Also collect IPs from the interfaces we just fetched
    for iface in interfaces:
        for ip in iface["ip_addresses"]:
            tagged = {"interface": iface["name"]}
            tagged.update(ip)
            if tagged not in ip_addresses:
                ip_addresses.append(tagged)

    return {
        "device": {
            "id": dev.id,
            "name": dev.name,
            "status": _val(dev, "status", "label", default="unknown"),
            "role": _val(dev, "device_role", "name", default=""),
            "device_type": _val(dev, "device_type", "model", default=""),
            "manufacturer": _val(dev, "device_type", "manufacturer", "name", default=""),
            "site": _val(dev, "site", "name", default=""),
            "rack": _val(dev, "rack", "name", default=""),
            "serial": getattr(dev, "serial", "") or "",
            "asset_tag": getattr(dev, "asset_tag", "") or "",
            "comments": getattr(dev, "comments", "") or "",
        },
        "interfaces": interfaces,
        "ip_addresses": ip_addresses,
    }


@mcp.tool()
def search_ip(addr: str) -> dict:
    """
    Search for an IP address and return what it's assigned to.

    Args:
        addr: IP address to search (e.g. "10.0.10.1" or "10.0.10.0/24")
    """
    logger.info("search_ip(addr=%s)", addr)
    try:
        results = nb.ipam.ip_addresses.filter(address=addr)
    except Exception as exc:
        return {"error": f"NetBox API error: {exc}"}

    ips = []
    for ip in results:
        entry = {
            "id": ip.id,
            "address": str(ip.address),
            "status": _val(ip, "status", "label", default=""),
            "role": getattr(ip, "role", None) or "",
            "dns_name": ip.dns_name or "",
            "description": ip.description or "",
            "tenant": _val(ip, "tenant", "name", default=""),
        }

        # Resolve assigned object
        if ip.assigned_object:
            obj_type = getattr(ip.assigned_object, "assigned_object_type", None)
            if obj_type == "dcim.interface":
                try:
                    iface = nb.dcim.interfaces.get(ip.assigned_object.id)
                    if iface:
                        entry["assigned_to"] = {
                            "type": "interface",
                            "interface": iface.name,
                            "device": _val(iface, "device", "name", default=""),
                        }
                except Exception:
                    entry["assigned_to"] = {
                        "type": "interface",
                        "id": ip.assigned_object.id,
                    }
            elif obj_type == "dcim.device":
                try:
                    dev = nb.dcim.devices.get(ip.assigned_object.id)
                    if dev:
                        entry["assigned_to"] = {
                            "type": "device",
                            "device": dev.name,
                        }
                except Exception:
                    entry["assigned_to"] = {
                        "type": "device",
                        "id": ip.assigned_object.id,
                    }
            elif obj_type == "virtualization.vminterface":
                try:
                    vm_iface = nb.virtualization.interfaces.get(ip.assigned_object.id)
                    if vm_iface:
                        entry["assigned_to"] = {
                            "type": "vm_interface",
                            "interface": vm_iface.name,
                            "virtual_machine": _val(vm_iface, "virtual_machine", "name", default=""),
                        }
                except Exception:
                    entry["assigned_to"] = {
                        "type": "vm_interface",
                        "id": ip.assigned_object.id,
                    }
            else:
                entry["assigned_to"] = {
                    "type": str(obj_type or "unknown"),
                    "id": ip.assigned_object.id if hasattr(ip.assigned_object, "id") else None,
                }

        ips.append(entry)

    if not ips:
        return {"error": f"IP address '{addr}' not found in NetBox"}

    return {"ip_addresses": ips}


@mcp.tool()
def list_devices(role: Optional[str] = None,
                 site: Optional[str] = None,
                 status: Optional[str] = None) -> dict:
    """
    List devices in NetBox with optional filters.

    Args:
        role: Filter by device role name (e.g. "server", "switch")
        site: Filter by site name (e.g. "Home")
        status: Filter by status label (e.g. "active", "offline", "staged")
    """
    logger.info("list_devices(role=%s, site=%s, status=%s)", role, site, status)

    kwargs = {}
    if role:
        kwargs["role"] = role
    if site:
        kwargs["site"] = site
    if status:
        kwargs["status"] = status

    try:
        devices = nb.dcim.devices.filter(**kwargs)
    except Exception as exc:
        return {"error": f"NetBox API error: {exc}"}

    results = []
    for dev in devices:
        results.append({
            "id": dev.id,
            "name": dev.name,
            "status": _val(dev, "status", "label", default=""),
            "role": _val(dev, "device_role", "name", default=""),
            "device_type": _val(dev, "device_type", "model", default=""),
            "manufacturer": _val(dev, "device_type", "manufacturer", "name", default=""),
            "site": _val(dev, "site", "name", default=""),
            "rack": _val(dev, "rack", "name", default=""),
        })

    return {
        "total": len(results),
        "devices": results,
    }


@mcp.tool()
def get_site(name: str) -> dict:
    """
    Get site details including devices, racks, and prefixes.

    Args:
        name: Site name (e.g. "Home")
    """
    logger.info("get_site(name=%s)", name)
    try:
        site = nb.dcim.sites.get(name=name)
    except Exception as exc:
        return {"error": f"NetBox API error: {exc}"}

    if not site:
        return {"error": f"Site '{name}' not found"}

    # Collect devices at this site
    devices = []
    try:
        for dev in nb.dcim.devices.filter(site_id=site.id):
            devices.append({
                "id": dev.id,
                "name": dev.name,
                "status": _val(dev, "status", "label", default=""),
                "role": _val(dev, "device_role", "name", default=""),
                "device_type": _val(dev, "device_type", "model", default=""),
            })
    except Exception as exc:
        logger.warning("Could not fetch devices for site %s: %s", name, exc)

    # Collect racks at this site
    racks = []
    try:
        for rack in nb.dcim.racks.filter(site_id=site.id):
            racks.append({
                "id": rack.id,
                "name": rack.name,
                "status": _val(rack, "status", "label", default=""),
                "role": _val(rack, "role", "name", default=""),
                "facility_id": getattr(rack, "facility_id", "") or "",
                "u_height": getattr(rack, "u_height", 0),
            })
    except Exception as exc:
        logger.warning("Could not fetch racks for site %s: %s", name, exc)

    # Collect prefixes at this site
    prefixes = []
    try:
        for pfx in nb.ipam.prefixes.filter(site_id=site.id):
            prefixes.append({
                "prefix": str(pfx.prefix),
                "status": _val(pfx, "status", "label", default=""),
                "vlan": _val(pfx, "vlan", "vid", default=None),
                "description": pfx.description or "",
            })
    except Exception:
        pass

    return {
        "site": {
            "id": site.id,
            "name": site.name,
            "slug": site.slug,
            "description": site.description or "",
            "status": _val(site, "status", "label", default=""),
            "facility": getattr(site, "facility", "") or "",
            "time_zone": getattr(site, "time_zone", "") or "",
        },
        "devices": devices,
        "racks": racks,
        "prefixes": prefixes,
    }


@mcp.tool()
def list_prefixes() -> dict:
    """
    Get a summary of IP prefix usage across all sites.
    """
    logger.info("list_prefixes()")
    try:
        prefixes = nb.ipam.prefixes.all()
    except Exception as exc:
        return {"error": f"NetBox API error: {exc}"}

    results = []
    status_counts = {}
    for pfx in prefixes:
        entry = {
            "prefix": str(pfx.prefix),
            "status": _val(pfx, "status", "label", default=""),
            "vlan_vid": _val(pfx, "vlan", "vid", default=None),
            "vlan_name": _val(pfx, "vlan", "name", default=""),
            "site": _val(pfx, "site", "name", default=""),
            "role": _val(pfx, "role", "name", default=""),
            "description": pfx.description or "",
            "family": str(pfx.family) if hasattr(pfx, "family") else "",
        }
        results.append(entry)

        label = _val(pfx, "status", "label", default="unknown")
        status_counts[label] = status_counts.get(label, 0) + 1

    return {
        "total_prefixes": len(results),
        "status_distribution": status_counts,
        "prefixes": results,
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logger.info("Starting NetBox MCP server on port 8000")
    logger.info("NetBox URL: %s", NETBOX_URL)
    mcp.run(transport="streamable-http")