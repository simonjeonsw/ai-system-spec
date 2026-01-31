"""Supabase client initialization for YouTube Automation Factory.

Loads SUPABASE_URL and SUPABASE_KEY from root .env.
Uses supabase-py. See spec/TECH_SPEC.md.
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from supabase import create_client, Client

# Load .env from repository root (parent of lib/)
_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_ROOT / ".env")

_URL = os.getenv("SUPABASE_URL")
_KEY = os.getenv("SUPABASE_KEY")

if not _URL or not _KEY:
    raise ValueError(
        "SUPABASE_URL and SUPABASE_KEY must be set in .env at project root."
    )


def get_client() -> Client:
    """Return a configured Supabase client."""
    return create_client(_URL, _KEY)
