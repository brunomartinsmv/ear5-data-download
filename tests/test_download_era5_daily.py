"""Tests for the ERA5 download CLI and library."""

from __future__ import annotations

import io
import json
import subprocess
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import download_era5_daily as era5  # noqa: E402


class BuildRequestTests(unittest.TestCase):
    def test_hourly_request_omits_area_when_unset(self) -> None:
        args = era5.argparse.Namespace(
            area=None,
            format="grib",
            download_format="zip",
            pressure_levels=["850"],
        )
        request = era5._build_hourly_request(
            args,
            era5.DATASET_SINGLE_LEVELS,
            ["2m_temperature"],
            "2020",
            ["01"],
        )
        self.assertNotIn("area", request)
        self.assertEqual(request["product_type"], "reanalysis")

    def test_hourly_request_includes_area_when_set(self) -> None:
        area = [-15.0, -56.5, -16.5, -55.5]
        args = era5.argparse.Namespace(
            area=area,
            format="grib",
            download_format="zip",
            pressure_levels=["850"],
        )
        request = era5._build_hourly_request(
            args,
            era5.DATASET_SINGLE_LEVELS,
            ["2m_temperature"],
            "2020",
            ["01"],
        )
        self.assertEqual(request["area"], area)

    def test_daily_statistics_request_omits_area_when_unset(self) -> None:
        args = era5.argparse.Namespace(
            variables=["2m_temperature"],
            start_year=2020,
            end_year=2020,
            months=None,
            statistic="daily_mean",
            time_zone="utc+00:00",
            frequency="1_hourly",
            output=None,
            output_dir="downloads",
            area=None,
        )
        targets = era5.build_daily_statistics_target(args)
        self.assertNotIn("area", targets[0].request)


class ModelLevelTargetTests(unittest.TestCase):
    def test_custom_output_prefix(self) -> None:
        args = era5.argparse.Namespace(
            start_year=2020,
            end_year=2020,
            start_month=1,
            end_month=1,
            variables=["t", "q"],
            area=era5.DEFAULT_AREA_CUIABA,
            output_dir="downloads/model_levels",
            output_prefix="custom_prefix",
            chunk="month",
            levelist=era5.DEFAULT_MODEL_LEVELS,
            grid=era5.DEFAULT_GRID,
            format="grib",
        )
        targets = era5.build_model_level_targets(args)
        self.assertEqual(len(targets), 1)
        self.assertTrue(targets[0].output.name.startswith("custom_prefix_2020_01"))

    def test_model_level_request_uses_mars_area_string(self) -> None:
        args = era5.argparse.Namespace(
            levelist=era5.DEFAULT_MODEL_LEVELS,
            area=era5.DEFAULT_AREA_CUIABA,
            grid=era5.DEFAULT_GRID,
            format="grib",
        )
        request = era5._build_model_level_request(args, ["t"], "2020-01-01/to/2020-01-31")
        self.assertEqual(request["area"], "-15/-56.5/-16.5/-55.5")
        self.assertEqual(request["param"], "130")


class TemperatureRegimeScriptTests(unittest.TestCase):
    def test_year_chunk_respects_month_bounds(self) -> None:
        from scripts.download_era5_temperature_regime_vars import build_targets

        targets = build_targets("single-levels", 2020, 2020, 6, 8, "year")
        self.assertEqual(len(targets), 1)
        year, months, _path = targets[0]
        self.assertEqual(year, 2020)
        self.assertEqual(months, ["06", "07", "08"])


class CliDryRunTests(unittest.TestCase):
    def _run(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(ROOT / "download_era5_daily.py"), *args],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_all_presets_exit_zero_on_dry_run(self) -> None:
        commands = [
            ("daily-statistics", "--variables", "2m_temperature", "--start-year", "2020", "--end-year", "2020"),
            ("single-levels", "--start-year", "2020", "--end-year", "2020", "--start-month", "6", "--end-month", "8"),
            ("land", "--start-year", "2020", "--end-year", "2020", "--start-month", "1", "--end-month", "2"),
            ("pressure-levels", "--start-year", "2020", "--end-year", "2020", "--start-month", "1", "--end-month", "1"),
            ("model-levels", "--start-year", "2020", "--end-year", "2020", "--start-month", "1", "--end-month", "1"),
        ]
        for preset_args in commands:
            with self.subTest(preset=preset_args[0]):
                result = self._run(*preset_args, "--dry-run")
                self.assertEqual(result.returncode, 0, msg=result.stderr or result.stdout)

    def test_auxiliary_scripts_exit_zero_on_dry_run(self) -> None:
        scripts = [
            (
                ROOT / "scripts" / "download_era5_model_levels.py",
                ["--start-year", "2020", "--end-year", "2020", "--start-month", "1", "--end-month", "1"],
            ),
            (
                ROOT / "scripts" / "download_era5_temperature_regime_vars.py",
                ["--start-year", "2020", "--end-year", "2020", "--start-month", "6", "--end-month", "8", "--preset", "single-levels"],
            ),
        ]
        for script, args in scripts:
            with self.subTest(script=script.name):
                result = subprocess.run(
                    [sys.executable, str(script), *args, "--dry-run"],
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, msg=result.stderr or result.stdout)


class PrintDryRunTests(unittest.TestCase):
    def test_print_dry_run_includes_first_request_json(self) -> None:
        target = era5.DownloadTarget(
            label="2020",
            request={"variable": ["2m_temperature"], "year": "2020"},
            output=Path("downloads/example.nc"),
        )
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            era5.print_dry_run(era5.DATASET_DAILY, [target], overwrite=False)
        output = buffer.getvalue()
        self.assertIn("First request:", output)
        payload = output.split("First request:\n", 1)[1].strip()
        self.assertEqual(json.loads(payload)["year"], "2020")


if __name__ == "__main__":
    unittest.main()
