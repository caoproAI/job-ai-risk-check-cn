from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "calculate_risk.py"
SPEC = importlib.util.spec_from_file_location("calculate_risk", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def full_task(
    digital: int = 0,
    repetition: int = 0,
    rules: int = 0,
    ai_can_do: int = 0,
    human_judgment: int = 4,
    relationship: int = 4,
    physical_presence: int = 4,
    accountability: int = 4,
) -> dict:
    return locals()


def full_company(value: int = 0, **overrides: int) -> dict:
    data = {field: value for field in MODULE.COMPANY_WEIGHTS}
    data.update(overrides)
    return data


def full_buffer(value: int = 4) -> dict:
    return {field: value for field in MODULE.BUFFER_WEIGHTS}


class RiskCalculationTests(unittest.TestCase):
    def test_high_pressure_is_immediate(self) -> None:
        result = MODULE.calculate(
            {
                "task": full_task(4, 4, 4, 4, 0, 0, 0, 0),
                "company": full_company(2),
                "buffer": full_buffer(0),
            }
        )
        self.assertEqual(result["total_pressure"]["score"], 100)
        self.assertEqual(result["preparation_window"]["label"], "立即准备")

    def test_low_pressure_has_no_urgent_evidence(self) -> None:
        result = MODULE.calculate(
            {
                "task": full_task(),
                "company": full_company(0),
                "buffer": full_buffer(4),
            }
        )
        self.assertEqual(result["total_pressure"]["score"], 0)
        self.assertEqual(result["preparation_window"]["label"], "暂无迫近证据")

    def test_missing_dimension_prevents_total(self) -> None:
        result = MODULE.calculate(
            {
                "task": {"digital": 4},
                "company": full_company(1),
                "buffer": full_buffer(2),
            }
        )
        self.assertIsNone(result["task_exposure"]["score"])
        self.assertIsNone(result["total_pressure"]["score"])
        self.assertEqual(result["preparation_window"]["label"], "资料不足")

    def test_medium_term_when_tasks_exposed_but_company_is_slow(self) -> None:
        result = MODULE.calculate(
            {
                "task": full_task(4, 4, 4, 4, 0, 0, 0, 0),
                "company": full_company(0),
                "buffer": full_buffer(2),
            }
        )
        self.assertEqual(result["preparation_window"]["label"], "中期转型窗口")

    def test_next_cycle_when_both_pressures_exist(self) -> None:
        result = MODULE.calculate(
            {
                "task": full_task(3, 3, 3, 3, 1, 1, 1, 1),
                "company": full_company(1),
                "buffer": full_buffer(2),
            }
        )
        self.assertEqual(result["preparation_window"]["label"], "下个绩效或预算周期")

    def test_mbti_is_ignored(self) -> None:
        base = {
            "task": full_task(),
            "company": full_company(0),
            "buffer": full_buffer(4),
        }
        with_mbti = dict(base)
        with_mbti["mbti"] = "INTJ"
        self.assertEqual(
            MODULE.calculate(base)["total_pressure"],
            MODULE.calculate(with_mbti)["total_pressure"],
        )

    def test_out_of_range_value_fails(self) -> None:
        with self.assertRaises(ValueError):
            MODULE.calculate(
                {
                    "task": full_task(digital=5),
                    "company": full_company(0),
                    "buffer": full_buffer(4),
                }
            )

    def test_hard_signals_count_only_confirmed_values(self) -> None:
        result = MODULE.calculate(
            {
                "task": full_task(),
                "company": full_company(0, no_backfill=2, role_merge=1),
                "buffer": full_buffer(4),
            }
        )
        self.assertEqual(result["hard_signals_confirmed"], 1)


if __name__ == "__main__":
    unittest.main()
