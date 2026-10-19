"""Точка входа: выбор источника ввода и сборка приложения."""

import argparse
import sys
from pathlib import Path

from vyshkat.container import Container


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Учёт парка кикшеринга «ВышКат»")
    parser.add_argument("--script", type=Path, help="файл UTF-8 с ответами на вопросы меню")
    args = parser.parse_args(argv)
    app = Container().console()
    if args.script is None:
        return app.run(sys.stdin, sys.stdout)
    try:
        with args.script.open(encoding="utf-8-sig") as source:
            return app.run(source, sys.stdout, echo=True)
    except (OSError, UnicodeError) as error:
        print(f"Не удалось прочитать файл сценария: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
