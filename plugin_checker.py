import requests
import json
import re
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import random
from tqdm import tqdm
import os
import logging
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def load_user_agents(filename='user_agents.txt'):
    """Load User-Agents from the specified file."""
    if not os.path.exists(filename):
        raise FileNotFoundError(f"{filename} not found in the script directory.")
    with open(filename, 'r', encoding='utf-8') as f:
        user_agents = [line.strip() for line in f if line.strip()]
    if not user_agents:
        raise ValueError(f"No valid User-Agents found in {filename}.")
    return user_agents

def get_user_agent(random_agent, user_agents_file='user_agents.txt'):
    """Get User-Agent: random from file if flag set, else fixed."""
    if random_agent:
        user_agents = load_user_agents(user_agents_file)
        return random.choice(user_agents)
    else:
        return 'Mozilla/5.0 (compatible; PluginChecker/1.0)'

def make_request(method, url, log_enabled, proxy=None, **kwargs):
    """Make a request and log if enabled."""
    if log_enabled:
        logging.info(f"Sending {method} request to {url}")
        if 'headers' in kwargs:
            logging.info(f"Headers: {kwargs['headers']}")
        if 'params' in kwargs:
            logging.info(f"Params: {kwargs['params']}")
        if proxy:
            logging.info(f"Using proxy for this request: {proxy}")
    
    proxies = {'http': proxy, 'https': proxy} if proxy else None
    resp = requests.request(method, url, proxies=proxies, verify=False, **kwargs)
    
    if log_enabled:
        logging.info(f"Response for {url}: Status {resp.status_code}, Content-Length: {len(resp.content) if resp.content else 0}")
        if resp.status_code != 200:
            logging.warning(f"Non-200 response for {url}: Status {resp.status_code}")
        logging.info(f"Response Headers: {dict(resp.headers)}")
    
    return resp

# Function to download the list of all plugins and their latest versions
def download_plugins_list(filename='plugins_latest.json', proxy=None, random_agent=False, log_enabled=False):
    """
    Download the list of all WordPress plugins from the API and save to JSON file.
    Format: {slug: version}
    """
    print("Starting download of plugins list...")
    plugins = {}
    per_page = 100  # You can increase, e.g., 400
    
    # Fetch first page to get total pages
    url = "https://api.wordpress.org/plugins/info/1.2/"
    params = {
        'action': 'query_plugins',
        'request[page]': 1,
        'request[per_page]': per_page
    }
    headers = {'User-Agent': get_user_agent(random_agent)}
    resp = make_request('GET', url, log_enabled, proxy, params=params, headers=headers)
    if resp.status_code != 200:
        print("Error downloading first page")
        return plugins
    
    data = resp.json()
    if 'info' not in data or 'plugins' not in data:
        print("Invalid response format")
        return plugins
    
    # Process first page
    for p in data['plugins']:
        if p['slug'] and p.get('version'):
            plugins[p['slug']] = p['version']
    
    total_pages = data['info'].get('pages', 1)
    print(f"Total pages: {total_pages}, Plugins so far: {len(plugins)}")
    
    # Download remaining pages with progress bar
    if total_pages > 1:
        for page in tqdm(range(2, total_pages + 1), desc="Downloading plugin pages"):
            params['request[page]'] = page
            headers = {'User-Agent': get_user_agent(random_agent)}
            resp = make_request('GET', url, log_enabled, proxy, params=params, headers=headers)
            if resp.status_code != 200:
                print(f"Error downloading page {page}")
                break
            data = resp.json()
            if not data.get('plugins'):
                break
            for p in data['plugins']:
                if p['slug'] and p.get('version'):
                    plugins[p['slug']] = p['version']
            time.sleep(0.5)  # Delay to avoid overloading the server
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(plugins, f, ensure_ascii=False, indent=2)
    print(f"Plugins list saved to {filename}. Count: {len(plugins)}")
    return plugins

# Function to check installed plugins on the site
def check_wordpress_site(url, plugins_dict, max_workers=20, timeout=5, proxy=None, random_agent=False, log_enabled=False):
    """
    Check WordPress site for installed plugins and compare with latest version.
    By checking the existence of readme.txt in each plugin.
    """
    if not url.startswith('http'):
        url = 'https://' + url
    base_url = url.rstrip('/') + '/wp-content/plugins/'
    detected = {}
    
    def check_plugin(slug):
        headers = {'User-Agent': get_user_agent(random_agent)}
        try:
            readme_url = base_url + slug + '/readme.txt'
            resp = make_request('GET', readme_url, log_enabled, proxy, headers=headers, timeout=timeout)
            if resp.status_code == 200:
                content = resp.text
                # Extract version from Stable tag
                match = re.search(r'Stable tag:\s*([\d\.]+)', content, re.IGNORECASE)
                if match:
                    installed_version = match.group(1)
                    latest_version = plugins_dict.get(slug, 'unknown')
                    up_to_date = installed_version == latest_version
                    return {
                        'slug': slug,
                        'installed_version': installed_version,
                        'latest_version': latest_version,
                        'up_to_date': up_to_date
                    }
        except Exception:
            pass
        return None
    
    print(f"Starting check of site {url}...")
    
    total_checks = len(plugins_dict)
    with tqdm(total=total_checks, desc=f"Scanning plugins for {url}") as pbar:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(check_plugin, slug): slug for slug in plugins_dict}
            completed = 0
            for future in as_completed(futures):
                result = future.result()
                if result:
                    detected[result['slug']] = result
                completed += 1
                pbar.update(1)
    
    return detected

# Main script
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="WordPress Plugin Checker Tool")
    parser.add_argument('--download', action='store_true', help="Download plugins list (optional)")
    parser.add_argument('--site', type=str, help="Single WordPress site URL (e.g., example.com)")
    parser.add_argument('--sites_file', type=str, help="File with list of sites, one per line")
    parser.add_argument('--file', type=str, default='plugins_latest.json', help="Plugins list file")
    parser.add_argument('--workers', type=int, default=20, help="Number of threads for checking")
    parser.add_argument('--proxy', type=str, help="Proxy URL (e.g., http://127.0.0.1:8080)")
    parser.add_argument('--random-agent', action='store_true', help="Use random User-Agent from user_agents.txt (default: fixed)")
    parser.add_argument('--log', action='store_true', help="Enable logging of requests and responses to plugin_checker.log")
    parser.add_argument('--debug-proxy', action='store_true', help="Enable debug logging for proxy usage")
    
    args = parser.parse_args()
    
    # Setup logging if enabled
    if args.log:
        log_level = logging.DEBUG if args.debug_proxy else logging.INFO
        logging.basicConfig(
            filename='plugin_checker.log',
            level=log_level,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        print("Logging enabled to plugin_checker.log")
        if args.debug_proxy:
            print("Debug proxy mode enabled - more verbose logging")
            # Enable urllib3 debug for proxy/HTTP details (logs to console by default, but can be captured)
            import urllib3
            urllib3.disable_warnings()
            logging.getLogger("urllib3").setLevel(logging.DEBUG)
    
    # Handle sites input
    sites = []
    if args.sites_file:
        try:
            with open(args.sites_file, 'r') as f:
                sites = [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            print(f"Sites file {args.sites_file} not found.")
            exit(1)
    elif args.site:
        sites = [args.site]
    else:
        print("Provide --site for single site or --sites_file for multiple sites.")
        exit(1)
    
    if not sites:
        print("No sites to check.")
        exit(1)
    
    plugins = {}
    if args.download:
        plugins = download_plugins_list(args.file, args.proxy, args.random_agent, args.log)
    else:
        try:
            with open(args.file, 'r', encoding='utf-8') as f:
                plugins = json.load(f)
            print(f"Plugins list loaded from {args.file}. Count: {len(plugins)}")
        except FileNotFoundError:
            print(f"File {args.file} not found. Downloading automatically...")
            plugins = download_plugins_list(args.file, args.proxy, args.random_agent, args.log)
    
    # Check each site
    for site in sites:
        detected = check_wordpress_site(site, plugins, args.workers, proxy=args.proxy, random_agent=args.random_agent, log_enabled=args.log)
        
        # Save results to file named after the site
        netloc = re.sub(r'https?://', '', site).split('/')[0]
        netloc = re.sub(r'[^a-z0-9.-]', '_', netloc.lower())
        result_filename = f"{netloc}_results.json"
        with open(result_filename, 'w', encoding='utf-8') as f:
            json.dump(detected, f, ensure_ascii=False, indent=2)
        print(f"\nResults for {site} saved to {result_filename}")
        
        # Print summary
        print("Summary:")
        if detected:
            for slug, info in detected.items():
                status = "Up to date" if info['up_to_date'] else "Needs update"
                print(f"- {slug}: {info['installed_version']} (Latest: {info['latest_version']}) - {status}")
        else:
            print("No plugins found. Directory listing might be disabled or no specific plugins used.")
        print("\n" + "="*50 + "\n")
