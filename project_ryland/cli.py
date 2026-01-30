import argparse
from project_ryland.templates.quickstart import create_quickstart

def main():
    parser = argparse.ArgumentParser(
        description="Project Ryland CLI: Quickly scaffold a starter project"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Subcommand for quickstart
    qs_parser = subparsers.add_parser(
        "quickstart", help="Create a starter project from template"
    )
    qs_parser.add_argument(
        "--dest", type=str, default=".",
        help="Destination directory for the starter project"
    )
    qs_parser.add_argument(
        "--overwrite", action="store_true",
        help="Overwrite existing files if they exist"
    )

    args = parser.parse_args()

    if args.command == "quickstart":
        create_quickstart(dest=args.dest, overwrite=args.overwrite)

if __name__ == "__main__":
    main()