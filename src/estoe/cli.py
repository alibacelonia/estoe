"""CLI scaffold. Secret retrieval is intentionally pending design approval."""

from __future__ import annotations

import argparse
import sys
from importlib.metadata import version


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="estoe", description="Secret to Env — cloud secrets to local .env files."
    )
    parser.add_argument("--version", action="version", version=f"estoe {version('estoe')}")
    commands = parser.add_subparsers(dest="command", required=True)
    pull = commands.add_parser(
        "pull",
        help="Generate a dotenv file from one JSON secret (planned; not implemented yet).",
        description=(
            "Expand one JSON secret into environment variables. "
            "Scaffold only: this version performs no cloud reads or file writes."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples (planned workflow):\n"
            "  estoe pull --provider aws --secret example/dev/app --profile sandbox\n"
            "  estoe pull --provider aws --secret example/dev/app --region us-east-1\n"
            "  estoe pull --provider aws --secret example/dev/app --output .env.local\n"
            "  estoe pull --provider aws --secret example/dev/app --preview\n\n"
            "AWS credentials must already be configured, including SSO login when needed.\n"
            "Preview will retrieve the secret and may incur AWS charges; it shows keys only.\n"
            "Generated files contain plaintext secrets: keep them out of version control.\n"
            "Do not execute or shell-source generated dotenv content."
        ),
    )
    pull.add_argument(
        "--provider", required=True, choices=["aws"], help="Cloud provider (AWS MVP)."
    )
    pull.add_argument("--secret", required=True, help="Exact secret name or full ARN.")
    pull.add_argument("--profile", help="AWS named profile; default: SDK credential chain.")
    pull.add_argument("--region", help="AWS region; default: selected profile/SDK configuration.")
    pull.add_argument("--output", default=".env", help="Destination file (default: .env).")
    mode = pull.add_mutually_exclusive_group()
    mode.add_argument(
        "--preview", action="store_true", help="Show key names/counts; write no file."
    )
    mode.add_argument(
        "--overwrite", action="store_true", help="Explicitly authorize replacing an existing file."
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    build_parser().parse_args(argv)
    print(
        "estoe: pull is not implemented yet; see docs/TASKS.md for the implementation plan.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
