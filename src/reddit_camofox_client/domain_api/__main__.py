"""CLI entry point: run `python -m reddit_camofox_client.domain_api`."""
from __future__ import annotations
import argparse
import logging
import sys


def main() -> None:
    parser = argparse.ArgumentParser(description="Reddit Camofox Client API server")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8001)
    parser.add_argument("--log-level", default="info", choices=["debug", "info", "warning", "error"])
    args = parser.parse_args()
    logging.basicConfig(level=getattr(logging, args.log_level.upper()),
                        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s", stream=sys.stderr)
    import uvicorn
    uvicorn.run("reddit_camofox_client.domain_api.server:app", host=args.host, port=args.port, log_level=args.log_level)


if __name__ == "__main__":
    main()
