
# 🔌 WordPress Plugin Checker

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
![Status](https://img.shields.io/badge/status-beta-yellow)

**Plugin Checker** is a Python tool to enumerate WordPress plugins on target sites by checking for plugin `readme.txt` files and comparing detected versions with the latest versions from the WordPress Plugins API.

---

## 🔒 IMPORTANT (Use Responsibly)

This tool is intended for **authorized security assessments only**. Do **not** scan or probe websites you do not have explicit permission to test. Unauthorized scanning may be illegal and unethical.

By using this repository you confirm you have permission to scan the target site(s).

---

## 🚀 Features

- Downloads latest plugin version list from WordPress API (optional).
- Checks a single site or multiple sites for installed plugins via `wp-content/plugins/*/readme.txt`.
- Extracts installed plugin version (from `Stable tag`) and compares with latest known version.
- Multithreaded checks with progress bars (uses `tqdm`).
- Optional request/response logging and proxy support.
- Optionally uses a random User-Agent list for requests.

---

## 🧰 Prerequisites

- **Python 3.8+**
- Python packages (see `requirements.txt` below)
- Optional: Proxy server for debugging requests

Create a `user_agents.txt` file in the same directory if you plan to use `--random-agent`. Put one User-Agent string per line.

---

## 📦 Installation (GitHub-style quick start)

```bash
git clone https://github.com/<your-username>/plugin-checker.git
cd plugin-checker

# create a virtualenv (recommended)
python3 -m venv venv
source venv/bin/activate

# install dependencies
pip install -r requirements.txt
```

---

## 📄 `requirements.txt`

```txt
requests
tqdm
```

*(These are external packages; the rest of the script uses standard library modules.)*

---

## ⚙️ Usage

```bash
python3 plugin_checker.py --site example.com
```

Or scan multiple sites (one per line):

```bash
python3 plugin_checker.py --sites_file sites.txt
```

### Common options

```
--download            Download latest plugins list from WordPress API and save to plugins_latest.json
--site SITE           Single WordPress site URL (e.g., example.com or https://example.com)
--sites_file FILE     File with list of sites (one per line)
--file FILE           Plugins list file (default: plugins_latest.json)
--workers N           Number of threads to use (default: 20)
--proxy URL           Proxy URL (e.g., http://127.0.0.1:8080)
--random-agent        Use random User-Agent strings from user_agents.txt
--log                 Enable logging to plugin_checker.log
--debug-proxy         Enable verbose urllib3 logging for proxy debugging
```

---

## 🧩 Example Workflows

### 1) Load existing plugin file and check a site
```bash
python3 plugin_checker.py --site example.com --file plugins_latest.json
```

### 2) Download the latest plugins list, then check multiple sites
```bash
python3 plugin_checker.py --download --file plugins_latest.json
python3 plugin_checker.py --sites_file sites.txt --file plugins_latest.json
```

### 3) Use proxy and random User-Agent
```bash
python3 plugin_checker.py --site example.com --proxy http://127.0.0.1:8080 --random-agent --log
```

---

## 🗂 Output

For each scanned site, a JSON results file is created:  
`<normalized_site>_results.json` (e.g., `example_com_results.json`)

Each entry structure:
```json
{
  "plugin-slug": {
    "slug": "plugin-slug",
    "installed_version": "1.2.3",
    "latest_version": "1.3.0",
    "up_to_date": false
  }
}
```

A console summary is printed with "Up to date" / "Needs update" statuses.

---

## 🔧 Internals & Tuning

- **How detection works**: The script requests `/wp-content/plugins/<slug>/readme.txt` for each plugin slug from the `plugins_latest.json` list and searches for the `Stable tag:` line to extract the installed version.
- **Threading**: Controlled by `--workers` (default 20). Increase for faster checks, but be mindful of target load and rate limits.
- **Rate-limiting / politeness**: The script includes a small delay when downloading plugin pages; you can increase delays if concerned about load.
- **User-Agents**: Use `--random-agent` and provide `user_agents.txt` if you need rotating UA strings.

---

## ✅ Testing & Troubleshooting

- If plugin list download fails: check network connectivity and WordPress API availability.
- If detection returns no plugins: the target may have directory listing blocked or not expose `readme.txt`.
- If many false negatives: consider that some sites remove plugin readme files or block automated requests.
- If `requests` raises SSL errors: script disables warnings and uses `verify=False` for requests to plugin readme paths (intended for broad compatibility). If you require strict TLS, modify `make_request` to set `verify=True`.

---

## 🛠️ CI Example (GitHub Actions)

> **Do not** run network scans on shared CI runners unless you control targets.

`.github/workflows/ci.yml`:

```yaml
name: CI

on: [push, pull_request]

jobs:
  lint_and_smoke:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.10"
      - name: Install deps
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
      - name: Run lightweight smoke test
        run: |
          python -c "import requests, json, re; print('imports ok')"
```

---

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repo
2. Create a branch `git checkout -b feature/my-change`
3. Commit and push
4. Open a Pull Request

Include tests or reproduction steps for major changes.

---

## 🐞 Reporting Security Issues

If you discover a security vulnerability (e.g., the tool exposes secrets or causes unintended harm), do **not** open a public issue. Contact the repository owner privately with reproduction steps and impact.

---

## 📜 License

Licensed under the **MIT License**. See `LICENSE` for details.

---

## ✨ Acknowledgements

- WordPress Plugins API
- `requests` library
- `tqdm` for progress bars

---

## 📫 Author

Developed by **Alireza Bolbolabadi** ([github.com/bolbolabadi](https://github.com/bolbolabadi))

If you find this useful, please ⭐ the repository!

