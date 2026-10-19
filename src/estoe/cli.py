"""User-facing CLI; errors never include provider payloads."""

from __future__ import annotations

import argparse
import re
import sys
from importlib.metadata import version

from estoe.application import export_secret
from estoe.azure_provider import AzureProvider, valid_vault_url
from estoe.errors import EstoeError
from estoe.gcp_provider import GCPProvider, valid_project
from estoe.providers import AWSProvider


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="estoe", description="Secret to Env — cloud secrets to local .env files."
    )
    parser.add_argument("--version", action="version", version=f"estoe {version('estoe')}")
    commands = parser.add_subparsers(dest="command", required=True)
    pull = commands.add_parser(
        "pull",
        help="Generate a dotenv file from one AWS, Azure, or GCP JSON secret.",
        description="Expand one flat JSON secret into separate dotenv variables.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  estoe pull --provider aws --secret example/dev/app --profile sandbox\n"
            "  estoe pull --provider aws --secret example/dev/app --region us-east-1\n"
            "  estoe pull --provider aws --secret example/dev/app --output .env.local\n"
            "  estoe pull --provider aws --secret example/dev/app --preview\n\n"
            "  estoe pull --provider azure --secret estoe-dev-app "
            "--vault-url https://example-vault.vault.azure.net/\n"
            "  estoe pull --provider gcp --secret estoe-dev-app --project example-project\n\n"
            "AWS: existing credential chain/profile (including SSO login when needed).\n"
            "Azure: existing az login session; --tenant-id optionally selects its tenant.\n"
            "GCP: Application Default Credentials (gcloud auth application-default login).\n"
            "Preview retrieves the secret and may incur cloud charges; it shows keys only.\n"
            "Generated files contain plaintext secrets: keep them out of version control.\n"
            "Load with python-dotenv and interpolate=False to preserve dollar expressions.\n"
            "Do not execute or shell-source generated dotenv content.\n"
            "The output parent must exist, be owned by you, and not be group/world writable."
        ),
    )
    pull.add_argument(
        "--provider",
        required=True,
        choices=["aws", "azure", "gcp"],
        help="Cloud provider (required).",
    )
    pull.add_argument("--secret", required=True, help="AWS name/ARN; Azure name; GCP secret ID.")
    pull.add_argument("--profile", help="AWS only: named profile; default: SDK credential chain.")
    pull.add_argument("--region", help="AWS only: region; default: profile/SDK configuration.")
    pull.add_argument("--vault-url", help="Azure only (required): https://NAME.vault.azure.net/.")
    pull.add_argument(
        "--tenant-id", help="Azure only: optional tenant UUID for existing CLI login."
    )
    pull.add_argument(
        "--project", help="GCP only (required): project ID or project number; uses ADC."
    )
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


def validate_options(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    groups = {
        "aws": ("profile", "region"),
        "azure": ("vault_url", "tenant_id"),
        "gcp": ("project",),
    }
    for provider, options in groups.items():
        if args.provider != provider and any(getattr(args, name) is not None for name in options):
            parser.error(f"{provider}-specific options cannot be used with this provider")
    if args.provider == "azure":
        if not args.vault_url or not valid_vault_url(args.vault_url):
            parser.error("Azure requires --vault-url with an HTTPS public Key Vault hostname")
        if not re.fullmatch(r"[A-Za-z0-9-]{1,127}", args.secret):
            parser.error("Azure --secret must be a secret name of 1–127 letters, digits or hyphens")
        if args.tenant_id is not None and not re.fullmatch(
            r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}", args.tenant_id
        ):
            parser.error("Azure --tenant-id must be a tenant UUID")
    if args.provider == "gcp":
        if not args.project or not valid_project(args.project):
            parser.error("GCP requires --project with a project ID or project number")
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,255}", args.secret):
            parser.error(
                "GCP --secret must be an ID of 1–255 letters, digits, underscores or hyphens"
            )


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
    validate_options(parser, args)
    try:

        def confirm() -> bool:
            return input("Replace the existing destination? [y/N] ").strip().lower() in {"y", "yes"}

        if args.provider == "aws":
            provider = AWSProvider(args.profile, args.region)
        elif args.provider == "azure":
            provider = AzureProvider(args.vault_url, args.tenant_id)
        else:
            provider = GCPProvider(args.project)
        result = export_secret(
            provider,
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
