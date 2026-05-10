"""
Attack engine module for ghost0 - builds attack chains, fetches CVEs, and tracks attack state.
"""
import re
import json
import time
import requests
import subprocess
import shlex
from collections import defaultdict
from typing import Dict, List, Optional
import os
from dotenv import load_dotenv

from logger_config import get_logger

load_dotenv()

logger = get_logger(__name__)

NVD_API = "https://services.nvd.nist.gov/rest/json/cves/2.0"
CACHE_FILE = "cve_cache.json"
CACHE_TTL = 86400  # 24 hours

# Configuration
NVD_API_KEY = os.getenv('NVD_API_KEY', '')
MAX_CVE_RESULTS = 3
MAX_EXPLOIT_RESULTS = 3

ATTACK_STAGES = [
    "recon",
    "enumeration",
    "initial_access",
    "privilege_escalation",
    "lateral_movement",
    "persistence"
]

attack_state: Dict = defaultdict(lambda: {
    "stage": "recon",
    "services": {},
    "findings": []
})


# -----------------------
# Cache
# -----------------------
def load_cache() -> Dict:
    """Load CVE cache from JSON file."""
    try:
        with open(CACHE_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse cache: {e}")
        return {}


def save_cache(cache: Dict) -> None:
    """Save CVE cache to JSON file."""
    try:
        with open(CACHE_FILE, 'w') as f:
            json.dump(cache, f, indent=2)
        logger.debug(f"Cached {len(cache)} entries")
    except IOError as e:
        logger.error(f"Failed to save cache: {e}")


# -----------------------
# Parse Nmap
# -----------------------
def parse_nmap(text: str) -> List[Dict]:
    """
    Parse nmap output to extract open services.
    
    Args:
        text: nmap output text
    
    Returns:
        List of service dictionaries
    """
    services = []
    
    for line in text.split("\n"):
        if "/tcp" not in line or "open" not in line:
            continue
        
        try:
            parts = line.split()
            if len(parts) < 3:
                continue
            
            port = parts[0]
            service = parts[2]
            version = " ".join(parts[3:]) if len(parts) > 3 else "unknown"
            
            services.append({
                "port": port,
                "service": service.lower(),
                "version": version.lower()
            })
        
        except (IndexError, ValueError) as e:
            logger.debug(f"Failed to parse line: {line} - {e}")
            continue
    
    logger.info(f"Parsed {len(services)} open services from nmap")
    return services


# -----------------------
# Fetch CVEs
# -----------------------
def fetch_cves(service: str, version: str) -> List[str]:
    """
    Fetch CVEs for a service and version from NVD.
    
    Args:
        service: Service name
        version: Service version
    
    Returns:
        List of CVE descriptions
    """
    cache = load_cache()
    key = f"{service}:{version}"
    
    # Check cache
    if key in cache:
        entry = cache[key]
        if time.time() - entry["time"] < CACHE_TTL:
            logger.debug(f"Using cached CVEs for {key}")
            return entry["data"]
    
    query = f"{service} {version}"
    
    try:
        logger.debug(f"Fetching CVEs for: {query}")
        
        params = {"keywordSearch": query}
        if NVD_API_KEY:
            params["apiKey"] = NVD_API_KEY
        
        r = requests.get(
            NVD_API,
            params=params,
            timeout=15
        )
        r.raise_for_status()
        
        data = r.json()
        out = []
        
        for item in data.get("vulnerabilities", [])[:MAX_CVE_RESULTS]:
            try:
                cve_id = item["cve"]["id"]
                desc = item["cve"]["descriptions"][0]["value"][:100]
                out.append(f"{cve_id} - {desc}")
            except (KeyError, IndexError) as e:
                logger.debug(f"Failed to parse CVE entry: {e}")
                continue
        
        # Cache the result
        cache[key] = {
            "time": time.time(),
            "data": out
        }
        save_cache(cache)
        
        logger.info(f"Found {len(out)} CVEs for {service}")
        return out
    
    except requests.RequestException as e:
        logger.error(f"Failed to fetch CVEs: {e}")
        return []
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON from NVD API: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error fetching CVEs: {e}")
        return []


# -----------------------
# Searchsploit Mapping
# -----------------------
def searchsploit_lookup(version: str) -> List[str]:
    """
    Look up exploits using searchsploit.
    
    Args:
        version: Service version
    
    Returns:
        List of exploit descriptions
    """
    if not version or len(version) < 2:
        logger.warning("Invalid version string for searchsploit")
        return []
    
    try:
        # Sanitize version string - only allow alphanumeric, dots, and dashes
        sanitized = re.sub(r'[^a-zA-Z0-9.\-_]', '', version)
        if not sanitized:
            logger.warning(f"Version string invalid after sanitization: {version}")
            return []
        
        logger.debug(f"Searching exploits for: {sanitized}")
        
        # Use shlex to safely split arguments
        cmd = ["searchsploit", "--json", sanitized]
        
        r = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if r.returncode != 0:
            logger.debug(f"searchsploit failed: {r.stderr}")
            return []
        
        data = json.loads(r.stdout)
        results = []
        
        for e in data.get("RESULTS_EXPLOIT", [])[:MAX_EXPLOIT_RESULTS]:
            try:
                title = e.get('Title', 'Unknown')
                path = e.get('Path', 'N/A')
                results.append(f"{title} -> {path}")
            except (KeyError, TypeError) as e:
                logger.debug(f"Failed to parse exploit: {e}")
                continue
        
        logger.info(f"Found {len(results)} exploits")
        return results
    
    except subprocess.TimeoutExpired:
        logger.error("searchsploit timed out")
        return []
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON from searchsploit: {e}")
        return []
    except FileNotFoundError:
        logger.warning("searchsploit not found. Install with: apt-get install exploitdb")
        return []
    except Exception as e:
        logger.error(f"Unexpected error in searchsploit: {e}")
        return []


# -----------------------
# Smart Payloads
# -----------------------
def smart_payloads(service: str) -> List[str]:
    """
    Generate smart payloads based on service type.
    
    Args:
        service: Service name
    
    Returns:
        List of suggested payloads
    """
    payloads = []
    
    service_lower = service.lower()
    
    if "http" in service_lower or "web" in service_lower:
        payloads += [
            "../../etc/passwd",
            "<script>alert(1)</script>",
            "' OR 1=1--"
        ]
    
    elif "ftp" in service_lower:
        payloads += [
            "anonymous login",
            "put shell.php"
        ]
    
    elif "smb" in service_lower or "samba" in service_lower:
        payloads += [
            "enum4linux",
            "smbclient -L",
            "upload .so"
        ]
    
    elif "ssh" in service_lower:
        payloads += [
            "hydra brute",
            "credential reuse"
        ]
    
    return payloads


# -----------------------
# State Tracking
# -----------------------
def update_state(
    target: str,
    service: str,
    stage: str
) -> None:
    """
    Update attack state for a service.
    
    Args:
        target: Target hostname/IP
        service: Service name
        stage: Current attack stage
    """
    if stage not in ATTACK_STAGES:
        logger.warning(f"Invalid stage: {stage}")
        return
    
    attack_state[target]["stage"] = stage
    attack_state[target]["services"][service] = {
        "stage": stage,
        "updated": time.time()
    }
    logger.debug(f"Updated state for {target}:{service} -> {stage}")


# -----------------------
# Decision Engine
# -----------------------
def response_analyzer(text: str) -> List[str]:
    """
    Analyze response text for exploitation findings.
    
    Args:
        text: Response text to analyze
    
    Returns:
        List of findings
    """
    t = text.lower()
    findings = []
    
    patterns = [
        ("403", "Try header bypass"),
        ("root:x:", "LFI confirmed"),
        ("uid=", "RCE confirmed"),
        ("sql syntax", "Possible SQLi"),
        ("permission denied", "Auth bypass opportunity"),
        ("admin", "Admin panel found"),
    ]
    
    for pattern, finding in patterns:
        if pattern in t:
            findings.append(finding)
    
    return list(set(findings))  # Deduplicate


# -----------------------
# Build Chain
# -----------------------
def build_attack_chain(
    nmap_output: str,
    target: str = "target"
) -> str:
    """
    Build a complete attack chain from nmap output.
    
    Args:
        nmap_output: nmap command output
        target: Target hostname/IP
    
    Returns:
        Formatted attack chain string
    """
    services = parse_nmap(nmap_output)
    
    if not services:
        logger.warning("No services parsed from nmap output")
        return ""
    
    out = []
    
    for s in services:
        service = s["service"]
        version = s["version"]
        port = s["port"]
        
        out.append(f"\n[{port}] {service}")
        
        # CVEs
        cves = fetch_cves(service, version)
        if cves:
            out.append(" CVEs:")
            for c in cves:
                out.append(f"  - {c}")
        
        # Exploits
        exploits = searchsploit_lookup(version)
        if exploits:
            out.append(" Exploits:")
            for e in exploits:
                out.append(f"  - {e}")
        
        # Payloads
        payloads = smart_payloads(service)
        if payloads:
            out.append(" Suggested Payloads:")
            for p in payloads:
                out.append(f"  - {p}")
        
        # Update state
        update_state(target, service, "enumeration")
        
    logger.info(f"Built attack chain for {len(services)} services")
    return "\n".join(out)


# -----------------------
# Get Current Attack State
# -----------------------
def get_state(target: str = "target") -> Dict:
    """
    Get current attack state for a target.
    
    Args:
        target: Target hostname/IP
    
    Returns:
        Attack state dictionary
    """
    return attack_state.get(target, {})

