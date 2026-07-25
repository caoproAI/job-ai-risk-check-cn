#!/usr/bin/env python3
"""Deterministic scoring for job AI-change and company-pressure signals."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


TASK_WEIGHTS = {
    "digital": 10,
    "repetition": 20,
    "rules": 15,
    "ai_can_do": 20,
    "human_judgment": 10,
    "relationship": 10,
    "physical_presence": 5,
    "accountability": 10,
}

TASK_INVERSE = {
    "human_judgment",
    "relationship",
    "physical_presence",
    "accountability",
}

COMPANY_WEIGHTS = {
    "ai_mandate": 15,
    "hiring_freeze": 10,
    "no_backfill": 15,
    "role_merge": 15,
    "output_quota": 10,
    "outsourcing": 10,
    "pay_change": 15,
    "pip_pressure": 10,
}

HARD_SIGNAL_KEYS = {
    "hiring_freeze",
    "no_backfill",
    "role_merge",
    "outsourcing",
    "pay_change",
    "pip_pressure",
}

BUFFER_WEIGHTS = {
    "business_outcomes": 20,
    "customer_trust": 15,
    "complex_judgment": 20,
    "cross_team_delivery": 15,
    "ai_collaboration": 15,
    "transferable_proof": 15,
}


def _number_or_none(value: Any, maximum: float, field: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} 必须是数字或 null")
    if value < 0 or value > maximum:
        raise ValueError(f"{field} 必须在 0 到 {maximum:g} 之间")
    return float(value)


def _weighted_score(
    values: dict[str, Any],
    weights: dict[str, int],
    maximum: float,
    coverage_threshold: float,
    inverse: set[str] | None = None,
) -> dict[str, Any]:
    inverse = inverse or set()
    observed_weight = 0
    weighted_total = 0.0

    for field, weight in weights.items():
        value = _number_or_none(values.get(field), maximum, field)
        if value is None:
            continue
        observed_weight += weight
        normalized = value / maximum
        if field in inverse:
            normalized = 1 - normalized
        weighted_total += normalized * weight

    coverage = observed_weight / sum(weights.values())
    score = None
    if coverage >= coverage_threshold:
        score = round(weighted_total / observed_weight * 100)

    return {
        "score": score,
        "coverage": round(coverage, 2),
        "observed_weight": observed_weight,
        "required_coverage": coverage_threshold,
    }


def _pressure_band(score: int | None) -> str:
    if score is None:
        return "未评分"
    if score <= 29:
        return "当前压力较低"
    if score <= 49:
        return "已需要适应"
    if score <= 69:
        return "风险较高，应开始转型准备"
    return "信号集中，应立即准备并核实"


def _window(
    task_score: int | None,
    company_score: int | None,
    total_score: int | None,
    hard_signals: int,
) -> dict[str, str]:
    if task_score is None or company_score is None or total_score is None:
        return {
            "label": "资料不足",
            "range": "暂不能判断",
            "note": "补齐缺失维度后再判断准备窗口。",
        }
    if company_score >= 70 and hard_signals >= 2:
        return {
            "label": "立即准备",
            "range": "未来0至3个月重点观察",
            "note": "公司压力较高且至少两个硬信号已确认。",
        }
    if 45 <= company_score <= 69 and task_score >= 55:
        return {
            "label": "下个绩效或预算周期",
            "range": "约3至12个月",
            "note": "任务暴露与公司压力同时出现，但尚未形成集中硬信号。",
        }
    if task_score >= 60 and company_score < 45:
        return {
            "label": "中期转型窗口",
            "range": "约1至3年",
            "note": "任务暴露较高，但公司当前替代压力不高，实际速度取决于公司采用AI的进度。",
        }
    if total_score < 35 and hard_signals == 0:
        return {
            "label": "暂无迫近证据",
            "range": "至少每3个月复查",
            "note": "当前未观察到集中硬信号，不代表永久安全。",
        }
    return {
        "label": "继续观察",
        "range": "暂不能给出稳定时间范围",
        "note": "证据方向不一致，等待新的公司动作或任务变化。",
    }


def calculate(data: dict[str, Any]) -> dict[str, Any]:
    task_values = data.get("task") or {}
    company_values = data.get("company") or {}
    buffer_values = data.get("buffer") or {}

    if not isinstance(task_values, dict):
        raise ValueError("task 必须是对象")
    if not isinstance(company_values, dict):
        raise ValueError("company 必须是对象")
    if not isinstance(buffer_values, dict):
        raise ValueError("buffer 必须是对象")

    task = _weighted_score(
        task_values,
        TASK_WEIGHTS,
        maximum=4,
        coverage_threshold=0.65,
        inverse=TASK_INVERSE,
    )
    company = _weighted_score(
        company_values,
        COMPANY_WEIGHTS,
        maximum=2,
        coverage_threshold=0.50,
    )
    buffer = _weighted_score(
        buffer_values,
        BUFFER_WEIGHTS,
        maximum=4,
        coverage_threshold=0.65,
    )

    hard_signals = sum(
        1
        for field in HARD_SIGNAL_KEYS
        if _number_or_none(company_values.get(field), 2, field) == 2
    )

    total_score = None
    if (
        task["score"] is not None
        and company["score"] is not None
        and buffer["score"] is not None
    ):
        total_score = round(
            task["score"] * 0.45
            + company["score"] * 0.35
            + (100 - buffer["score"]) * 0.20
        )

    return {
        "task_exposure": task,
        "company_pressure": company,
        "personal_buffer": buffer,
        "hard_signals_confirmed": hard_signals,
        "total_pressure": {
            "score": total_score,
            "band": _pressure_band(total_score),
        },
        "preparation_window": _window(
            task["score"],
            company["score"],
            total_score,
            hard_signals,
        ),
        "disclaimer": "分数衡量已观察到的改变压力，不是失业概率；时间是准备窗口，不是下岗日期。",
    }


def _read_input(args: argparse.Namespace) -> dict[str, Any]:
    if args.json_text:
        return json.loads(args.json_text)
    if args.input_path:
        return json.loads(Path(args.input_path).read_text(encoding="utf-8"))
    if args.stdin:
        return json.load(sys.stdin)
    raise ValueError("请提供 --json、--input 或 --stdin")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", dest="json_text", help="直接传入JSON字符串")
    parser.add_argument("--input", dest="input_path", help="读取UTF-8 JSON文件")
    parser.add_argument("--stdin", action="store_true", help="从标准输入读取JSON")
    args = parser.parse_args()

    try:
        result = calculate(_read_input(args))
    except (ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False, indent=2))
        raise SystemExit(2) from exc

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
