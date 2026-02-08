# lib/supabase_client.py
"""Supabase client initialization for YouTube Automation Factory.

Loads SUPABASE_URL and SUPABASE_KEY from root .env.
Uses supabase-py. See spec/TECH_SPEC.md.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client

# 1. Load .env from project root
_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_ROOT / ".env")

_URL = os.getenv("SUPABASE_URL")
_KEY = os.getenv("SUPABASE_KEY")  # Match the .env key name if needed.

if not _URL or not _KEY:
    raise ValueError(
        "SUPABASE_URL and SUPABASE_KEY must be set in .env at project root."
    )

# 2. Initialize the client (outside the function).
supabase: Client = create_client(_URL, _KEY)

def get_client() -> Client:
    """Optional: Return the pre-configured client."""
    return supabase
