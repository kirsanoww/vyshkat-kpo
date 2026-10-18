import io
import unittest
from contextlib import redirect_stderr, redirect_stdout
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from vyshkat.__main__ import main
from vyshkat.cli import parse_bool, parse_energy, parse_score
from vyshkat.container import Container

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class ConsoleTests(unittest.TestCase):
    def run_dialog(self, text, *, echo=False):
        container = Container()
        output = io.StringIO()
        status = container.console().run(io.StringIO(text), output, echo=echo)
        return status, output.getvalue(), container.fleet()

    def test_empty_reports_and_exit(self):
        status, output, fleet = self.run_dialog("3\n4\n5\n0\n")
        self.assertEqual(status, 0)
        self.assertIn("Всего на балансе: 0", output)
        self.assertIn("Баланс пуст", output)
        self.assertIn("Нет транспорта для новичков", output)
        self.assertEqual(fleet.inventory(), ())

    def test_user_supplies_data_and_menu_shows_results(self):
        status, output, fleet = self.run_dialog("1\n1\nМой самокат\nUSER-42\n6\nда\n2,75\n5\n0\n")
        self.assertEqual(status, 0)
        self.assertIn("USER-42 | Мой самокат", output)
        self.assertEqual(fleet.report().total_energy_kwh, Decimal("2.75"))

    def test_full_demo_file_covers_business_and_error_scenarios(self):
        scenario = (PROJECT_ROOT / "examples/demo.txt").read_text(encoding="utf-8")
        status, output, fleet = self.run_dialog(scenario, echo=True)
        self.assertEqual(status, 0)
        report = fleet.report()
        self.assertEqual((report.vehicle_count, report.item_count, report.total_count), (5, 4, 9))
        self.assertEqual(report.vehicle_energy_kwh, Decimal("5.6"))
        self.assertEqual(report.total_energy_kwh, Decimal("10.5"))
        self.assertEqual(
            [asset.inventory_number for asset in fleet.beginner_vehicles()],
            ["TR-001", "TR-003", "TR-004", "TR-005"],
        )
        for expected in (
            "Отклонено: Самокат с неисправным тормозом",
            "уже занят",
            "Неизвестная команда",
            "Выберите один из перечисленных типов",
            "Текстовое поле не может быть пустым",
            "Введите целое число",
            "Введите «да» или «нет»",
            "конечным неотрицательным числом",
            "Введите расход числом",
            "Всего на балансе: 9",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, output)

    def test_eof_at_menu_is_normal_exit(self):
        status, output, _ = self.run_dialog("")
        self.assertEqual(status, 0)
        self.assertIn("Ввод завершён", output)

    def test_eof_during_creation_does_not_add_partial_asset(self):
        status, output, fleet = self.run_dialog("1\n1\nСамокат\n")
        self.assertEqual(status, 1)
        self.assertIn("незавершённый объект не добавлен", output)
        self.assertEqual(fleet.inventory(), ())

    def test_comments_are_ignored(self):
        status, output, _ = self.run_dialog("# комментарий\n  # ещё один\n0\n", echo=True)
        self.assertEqual(status, 0)
        self.assertIn("Команда: 0", output)
        self.assertNotIn("комментарий", output)


class InputParsingTests(unittest.TestCase):
    def test_boolean_aliases(self):
        for value in ("да", "ДА", "д", "yes", "y", "1"):
            with self.subTest(value=value):
                self.assertTrue(parse_bool(value))
        for value in ("нет", "НЕТ", "н", "no", "n", "0"):
            with self.subTest(value=value):
                self.assertFalse(parse_bool(value))

    def test_invalid_boolean(self):
        with self.assertRaises(ValueError):
            parse_bool("возможно")

    def test_energy_accepts_comma_and_dot(self):
        self.assertEqual(parse_energy("1,25"), Decimal("1.25"))
        self.assertEqual(parse_energy("1.25"), Decimal("1.25"))

    def test_invalid_energy_is_a_validation_error(self):
        for raw in ("", "abc", "-1", "NaN", "sNaN", "Infinity", "-Infinity"):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                parse_energy(raw)

    def test_invalid_score_is_a_validation_error(self):
        for raw in ("", "abc", "0", "11", "6.5"):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                parse_score(raw)


class EntryPointTests(unittest.TestCase):
    def test_main_reads_standard_input(self):
        output = io.StringIO()
        with patch("sys.stdin", io.StringIO("0\n")), redirect_stdout(output):
            self.assertEqual(main([]), 0)
        self.assertIn("Работа завершена", output.getvalue())

    def test_main_reads_demo_file(self):
        output = io.StringIO()
        with redirect_stdout(output):
            status = main(["--script", str(PROJECT_ROOT / "examples/demo.txt")])
        self.assertEqual(status, 0)
        self.assertIn("Всего на балансе: 9", output.getvalue())

    def test_missing_file_reports_error_without_traceback(self):
        with TemporaryDirectory() as directory:
            errors = io.StringIO()
            with redirect_stderr(errors):
                status = main(["--script", str(Path(directory) / "missing.txt")])
        self.assertEqual(status, 2)
        self.assertIn("Не удалось прочитать файл сценария", errors.getvalue())

    def test_wrong_encoding_reports_error(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.txt"
            path.write_bytes(b"\xff\xfe")
            errors = io.StringIO()
            with redirect_stdout(io.StringIO()), redirect_stderr(errors):
                status = main(["--script", str(path)])
        self.assertEqual(status, 2)
        self.assertIn("Не удалось прочитать файл сценария", errors.getvalue())

    def test_utf8_bom_is_supported(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "input.txt"
            path.write_text("0\n", encoding="utf-8-sig")
            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(main(["--script", str(path)]), 0)
        self.assertNotIn("Неизвестная команда", output.getvalue())
