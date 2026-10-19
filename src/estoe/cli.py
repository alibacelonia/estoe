"""User-facing CLI; errors never include provider payloads."""

from __future__ import annotations

import argparse
import sys
from importlib.metadata import version

from estoe.application import export_secret
from estoe.errors import EstoeError
from estoe.providers import AWSProvider


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="estoe", description="Secret to Env — cloud secrets to local .env files."
    )
    parser.add_argument("--version", action="version", version=f"estoe {version('estoe')}")
    commands = parser.add_subparsers(dest="command", required=True)
    pull = commands.add_parser(
        "pull",
        help="Generate a dotenv file from one AWS JSON secret.",
        description="Expand one flat JSON secret into separate dotenv variables.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  estoe pull --provider aws --secret example/dev/app --profile sandbox\n"
            "  estoe pull --provider aws --secret example/dev/app --region us-east-1\n"
            "  estoe pull --provider aws --secret example/dev/app --output .env.local\n"
            "  estoe pull --provider aws --secret example/dev/app --preview\n\n"
            "AWS credentials must already be configured, including SSO login when needed.\n"
            "Preview will retrieve the secret and may incur AWS charges; it shows keys only.\n"
            "Generated files contain plaintext secrets: keep them out of version control.\n"
            "Load with python-dotenv and interpolate=False to preserve dollar expressions.\n"
            "Do not execute or shell-source generated dotenv content.\n"
            "The output parent must exist, be owned by you, and not be group/world writable."
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
    pull.add_argument(
        "--allow-unignored",
        action="store_true",
        help="Acknowledge writing an unignored Git file (tracked files are always rejected).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    for value, maximum in ((args.secret, 2048), (args.profile, 256), (args.region, 128)):
        if value is not None and (
            not value.strip() or len(value) > maximum or any(ord(c) < 32 for c in value)
        ):
            parser.error(
                "secret, profile, and region must be nonempty bounded text without controls"
            )
    try:

        def confirm() -> bool:
            return input("Replace the existing destination? [y/N] ").strip().lower() in {"y", "yes"}

        result = export_secret(
            AWSProvider(args.profile, args.region),
            args.secret,
            args.output,
            preview=args.preview,
            overwrite=args.overwrite,
            allow_unignored=args.allow_unignored,
            confirm=confirm if sys.stdin.isatty() else None,
        )
        if not result.in_git:
            print(
                "estoe: outside a Git working tree; Git ignore protection cannot be checked.",
                file=sys.stderr,
            )
        if result.preview:
            print(f"Preview: {len(result.keys)} variable(s)")
            print("\n".join(result.keys))
        else:
            print(f"Wrote {len(result.keys)} variable(s) to the selected output (mode 0600).")
        return 0
    except EstoeError as exc:
        print(f"estoe: {exc.code}: {exc}", file=sys.stderr)
        return 1
    except (KeyboardInterrupt, EOFError):
        print("estoe: cancelled: Operation cancelled.", file=sys.stderr)
        return 1
    except Exception:
        # A final guard prevents third-party exception messages from exposing payload values.
        print(
            "estoe: internal: Operation failed; sensitive details were suppressed.", file=sys.stderr
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
