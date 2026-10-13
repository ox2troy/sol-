#!/usr/bin/env python3
"""
Solana Funding Tracer Bot
-------------------------
Traces the origin ("mother wallet") of funds for given Solana addresses
by following incoming transactions backwards and saves results to CSV.
"""

import os
import time
import requests
import pandas as pd
from collections import deque
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ================== CONFIG ==================
HELIUS_API_KEY = os.getenv("3d5044bb-6951-4ccc-90ce-826548e1f461", "")
MAX_HOPS = int(os.getenv("MAX_HOPS", 20))
MIN_SOL_AMOUNT = float(os.getenv("MIN_SOL_AMOUNT", 0.1))
OUTPUT_CSV = os.getenv("OUTPUT_CSV", "solana_funding_trace.csv")
# ============================================

BASE_URL = "https://api.helius.xyz/v0"


def get_transfers(address: str, limit: int = 100) -> list:
    """Fetch recent transfers for a Solana address using Helius Enhanced Transactions API."""
    if not HELIUS_API_KEY:
        raise ValueError("HELIUS_API_KEY is missing. Please set it in .env file.")

    url = f"{BASE_URL}/addresses/{address}/transactions"
    params = {
        "api-key": HELIUS_API_KEY,
        "limit": limit,
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"[ERROR] {response.status_code} for {address}: {response.text[:200]}")
            return []
    except Exception as e:
        print(f"[ERROR] Request failed for {address}: {e}")
        return []


def extract_incoming_funders(address: str, transactions: list) -> list:
    """Extract wallets that sent SOL (or tokens) to the given address."""
    funders = []

    for tx in transactions:
        # Native SOL transfers
        for transfer in tx.get("nativeTransfers", []):
            to_account = transfer.get("toUserAccount")
            amount = transfer.get("amount", 0) / 1e9  # lamports → SOL

            if to_account == address and amount >= MIN_SOL_AMOUNT:
                funders.append({
                    "from": transfer.get("fromUserAccount"),
                    "amount_sol": round(amount, 6),
                    "signature": tx.get("signature"),
                    "timestamp": tx.get("timestamp"),
                    "type": "SOL"
                })

        # Token transfers (optional but useful)
        for transfer in tx.get("tokenTransfers", []):
            to_account = transfer.get("toUserAccount")
            if to_account == address:
                funders.append({
                    "from": transfer.get("fromUserAccount"),
                    "amount_sol": 0,
                    "signature": tx.get("signature"),
                    "timestamp": tx.get("timestamp"),
                    "type": "TOKEN",
                    "mint": transfer.get("mint")
                })

    return funders


def trace_wallet(start_address: str, max_hops: int = MAX_HOPS) -> list:
    """
    Perform BFS backwards tracing to find funding sources.
    Returns a list of records ready for CSV.
    """
    start_address = start_address.strip()
    visited = set()
    queue = deque([(start_address, 0, [start_address])])
    results = []

    print(f"\n→ Starting trace for: {start_address}")

    while queue:
        current, hop, path = queue.popleft()

        if current in visited or hop >= max_hops:
            continue
        visited.add(current)

        print(f"  Hop {hop}: checking {current[:8]}...{current[-6:]}")

        transactions = get_transfers(current)
        time.sleep(0.4)  # Be nice to the API

        funders = extract_incoming_funders(current, transactions)

        for f in funders:
            funder = f.get("from")
            if not funder or funder in visited:
                continue

            new_path = path + [funder]

            record = {
                "target_wallet": start_address,
                "hop": hop + 1,
                "current_wallet": current,
                "funder_wallet": funder,
                "amount_sol": f.get("amount_sol", 0),
                "type": f.get("type", ""),
                "signature": f.get("signature", ""),
                "timestamp": f.get("timestamp", ""),
                "full_path": " → ".join(new_path),
                "scanned_at": datetime.utcnow().isoformat()
            }
            results.append(record)

            queue.append((funder, hop + 1, new_path))

    print(f"  Found {len(results)} funding links for {start_address}")
    return results


def save_to_csv(all_results: list, filename: str = OUTPUT_CSV):
    """Save results to a clean CSV file."""
    if not all_results:
        print("No data to save.")
        return

    df = pd.DataFrame(all_results)

    preferred_order = [
        "target_wallet", "hop", "current_wallet", "funder_wallet",
        "amount_sol", "type", "signature", "timestamp",
        "full_path", "scanned_at"
    ]
    cols = [c for c in preferred_order if c in df.columns]
    df = df[cols]

    df.to_csv(filename, index=False)
    print(f"\n✅ Results saved to: {filename}")
    print(f"   Total records: {len(df)}")


def main():
    print("=" * 55)
    print("   Solana Funding Tracer Bot")
    print("   Traces mother wallets / origin funders")
    print("=" * 55)

    if not HELIUS_API_KEY or HELIUS_API_KEY == "your_helius_api_key_here":
        print("\n❌ ERROR: Please set your HELIUS_API_KEY in the .env file")
        print("   1. Copy .env.example to .env")
        print("   2. Get a free key at https://helius.dev")
        print("   3. Paste the key into .env")
        return

    # ============================================================
    #  PASTE THE WALLET ADDRESSES YOU WANT TO TRACE HERE
    #  The bot will run them ONE AFTER THE OTHER
    # ============================================================
    wallets_to_check = [
        # "WalletAddress1Here",
        # "WalletAddress2Here",
        # "WalletAddress3Here",
        # Add as many as you want — they will be processed sequentially
    ]
    # ============================================================

    # Also load any addresses from wallets.txt (optional)
    if os.path.exists("wallets.txt"):
        with open("wallets.txt", "r") as f:
            file_wallets = [line.strip() for line in f if line.strip() and not line.startswith("#")]
            wallets_to_check.extend(file_wallets)

    # Remove duplicates while keeping order
    seen = set()
    wallets_to_check = [w for w in wallets_to_check if not (w in seen or seen.add(w))]

    if not wallets_to_check:
        print("\n⚠️  No wallets provided.")
        print("   → Add addresses in the 'wallets_to_check' list inside tracer.py")
        print("   → or put them in wallets.txt (one address per line)")
        return

    print(f"\n📋 Total wallets to process: {len(wallets_to_check)}")
    for i, w in enumerate(wallets_to_check, 1):
        print(f"   {i}. {w}")

    all_data = []

    for idx, wallet in enumerate(wallets_to_check, 1):
        print(f"\n[{idx}/{len(wallets_to_check)}] Processing next wallet...")
        results = trace_wallet(wallet)
        all_data.extend(results)

        # Small pause between wallets to be gentle on the API
        if idx < len(wallets_to_check):
            time.sleep(1.5)

    save_to_csv(all_data)
    print("\n✅ All wallets finished.")


if __name__ == "__main__":
    main()
