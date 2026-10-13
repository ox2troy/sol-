# Solana Funding Tracer Bot

A simple Python bot that traces the origin of funds ("mother wallet" / end-point funder) for Solana addresses by following incoming transactions backwards. All results are saved to a CSV file.

## Features

- Traces funding sources up to a configurable number of hops
- Supports multiple wallets at once
- Saves clean CSV output with full path of the funding chain
- Uses Helius Enhanced Transactions API (free tier available)
- Easy configuration via `.env` file

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Get a free Helius API key

1. Go to [https://helius.dev](https://helius.dev)
2. Create an account and generate an API key
3. Copy `.env.example` to `.env`
4. Paste your key:

```bash
cp .env.example .env
# then edit .env and put your key
```

### 3. Add wallets to investigate

**Option A** – Edit `wallets.txt` (recommended)  
Put one Solana address per line.

**Option B** – Edit the list inside `tracer.py`

### 4. Run the bot

```bash
python tracer.py
```

Results will be saved to `solana_funding_trace.csv`

## CSV Columns

| Column          | Description                              |
|-----------------|------------------------------------------|
| target_wallet   | The original address you asked about     |
| hop             | How many steps back from the target      |
| current_wallet  | The address currently being examined     |
| funder_wallet   | Who sent funds to the current wallet     |
| amount_sol      | Amount transferred (in SOL)              |
| type            | SOL or TOKEN                             |
| signature       | Transaction signature                    |
| timestamp       | Unix timestamp of the transfer           |
| full_path       | Complete chain of wallets                |
| scanned_at      | When this record was created             |

## Configuration (`.env`)

```
HELIUS_API_KEY=your_key_here
MAX_HOPS=6
MIN_SOL_AMOUNT=0.001
OUTPUT_CSV=solana_funding_trace.csv
```

## Notes

- This tool only uses **public** blockchain data.
- Rate limits apply on the free Helius plan — the script already includes delays.
- Very active wallets may return limited history (API limit). Increase depth carefully.
- For production use, consider a paid Helius plan or combining with Solscan Pro API.

## Disclaimer

This tool is for educational, research, and legitimate investigation purposes only. Use responsibly and in accordance with applicable laws.
