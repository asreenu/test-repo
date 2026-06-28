# Mac Studio Finder

Daily search for **high-memory Mac Studio** listings (128 GB+) across reputable and acceptable sellers. Built to run on your local Mac and schedule via `launchd`.

## Quick start (local Mac)

```bash
cd mac-studio-finder
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Optional: copy and edit config
cp config.example.yaml config.yaml

# Run once manually
python run_search.py
```

Results are written to `~/.mac-studio-finder/latest_results.json`. macOS notifications fire when new matches appear.

## Schedule daily run

```bash
chmod +x install_schedule.sh
./install_schedule.sh
```

Default: every day at **8:00 AM** local time. Override:

```bash
RUN_AT_HOUR=7 RUN_AT_MINUTE=30 ./install_schedule.sh
```

Uninstall:

```bash
launchctl bootout gui/$(id -u)/com.macstudio.finder
rm ~/Library/LaunchAgents/com.macstudio.finder.plist
```

## Configuration

Edit `config.yaml`:

| Setting | Default | Purpose |
|---------|---------|---------|
| `search.min_memory_gb` | 128 | Minimum unified memory |
| `search.max_price_usd` | 5500 | Price cap (rough FX for GBP/EUR) |
| `search.chip_keywords` | M2/M3 Ultra, M4 Max | Used when RAM not in title |
| `sources.*.enabled` | varies | Toggle each seller |

Environment overrides:

- `MIN_MEMORY_GB`
- `MAX_PRICE_USD`
- `NOTIFY_ONLY_NEW=true|false`
- `EBAY_APP_ID` — enables eBay Finding API (recommended; HTML scraping is often blocked)

## Sources (reputable → acceptable)

| Source | Tier | Method |
|--------|------|--------|
| Apple Certified Refurbished | Reputable | `REFURB_GRID_BOOTSTRAP` JSON |
| Refurb.me | Reputable | HTML / Nuxt fallback |
| Techable | Reputable | Shopify `products.json` |
| iPowerResale | Reputable | Shopify `products.json` |
| Hoxton Macs (UK) | Reputable | Shopify (disabled by default) |
| Mac of All Trades | Reputable | HTML search |
| Back Market | Acceptable | HTML category page |
| Swappa | Acceptable | HTML listings |
| Adorama Used | Acceptable | HTML search |
| eBay | Acceptable | Finding API or search link fallback |

## Notes

- **RAM is soldered** — the script filters aggressively on memory in title/variants.
- Some sites block datacenter IPs; running from your home Mac (as intended) works better.
- When a source fails, the run continues and warnings are logged (never silent failure).
- First run marks all current matches as "seen"; notifications apply to **new** listings after that.

## Example output

```
Matched listings: 3
New listings: 3
[reputable ] apple_refurb     128GB    $3,979  Refurbished Mac Studio Apple M2 Ultra...
[reputable ] techable         128GB    $2,449  Mac Studio (2022) M1 Ultra 128 GB / 2 TB
[acceptable] swappa           128GB    $4,450  Mac Studio M2 Ultra | 128GB RAM
```

## Project layout

```
mac-studio-finder/
  run_search.py          # CLI entrypoint
  config.yaml            # Your search criteria
  install_schedule.sh    # launchd installer
  mac_studio_finder/
    sources/vendors.py   # Seller adapters
    runner.py            # Orchestration
    storage.py           # Seen-listing state
    notifier.py          # macOS alerts
```

Move this folder anywhere on your Mac and point `install_schedule.sh` / `config.yaml` at it.
