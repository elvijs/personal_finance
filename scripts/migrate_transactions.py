import argparse
import dataclasses
from pathlib import Path


@dataclasses.dataclass(frozen=True)
class Args:
    finances_dir: Path


def _get_cli_args() -> Args:
    parser = argparse.ArgumentParser(description="A simple CLI parser example")
    parser.add_argument(
        "-f",
        "--finances_dir",
        help="Path to the finances dir containing raw statements",
        type=str,
    )

    args_ = parser.parse_args()
    parsed_args = Args(finances_dir=Path(args_.finances_dir))
    return parsed_args


def main(finances_dir: Path) -> None:
    pass
    # TODO:
    #  1. iterate over all months under Docs/Finances,
    #  2. iterate over all recognised statements (insert an account if not there already)
    #  3. insert all transactions


if __name__ == "__main__":
    args = _get_cli_args()
    main(args.finances_dir)
