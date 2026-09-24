from __future__ import annotations

import argparse
import os

from .app import serve


def main():
    parser = argparse.ArgumentParser(description="LLMTier 0.3 OpenAI-compatible gateway")
    parser.add_argument("--host", default=os.environ.get("LLMTIER_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("LLMTIER_PORT", "8180")))
    parser.add_argument("--database", default=os.environ.get("LLMTIER_DATABASE", "var/llmtier-v03.sqlite3"))
    parser.add_argument("--settings", default=os.environ.get("LLMTIER_SETTINGS"), help="Required only when bootstrapping an empty database")
    args = parser.parse_args(); serve(args.host, args.port, args.database, args.settings)


if __name__ == "__main__": main()
