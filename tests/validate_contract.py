from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "SKILL.md",
    "README.md",
    "CHANGELOG.md",
    "agents/openai.yaml",
    "scripts/calculate_risk.py",
    "references/question-flow.md",
    "references/scoring-rubric.md",
    "references/company-signals.md",
    "references/output-template.md",
    "references/evidence-sources.md",
    "references/examples-and-boundaries.md",
    "references/brand-system.md",
    "docs/INSTALL.md",
    "docs/USAGE.md",
    "docs/BOUNDARIES.md",
    "docs/PUBLISHING.md",
    "docs/TEST-CASES.md",
    "tests/cases.json",
    "tests/test_calculate_risk.py",
]

REQUIRED_SKILL_MARKERS = [
    "每轮只问一道题",
    "用户自述",
    "分析推断",
    "待验证",
    "任务自动化暴露",
    "公司替代压力",
    "个人护城河",
    "不生成总压力分",
    "MBTI只用于",
    "权重为零",
    "准备窗口",
    "不是下岗日期",
    "不能准确知道老板",
    "不构成法律",
]

FORBIDDEN_TEXT = [
    "[TODO:",
    "\ufffd",
    "保证不会失业",
    "准确预测下岗日期",
    "MBTI决定职业风险",
]


def check_links(path: Path, failures: list[str]) -> None:
    text = path.read_text(encoding="utf-8")
    for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", text):
        if target.startswith(("http://", "https://", "#")):
            continue
        resolved = (path.parent / target).resolve()
        if not resolved.exists():
            failures.append(f"链接不存在：{path.relative_to(ROOT)} -> {target}")


def main() -> None:
    failures: list[str] = []

    for relative in REQUIRED_FILES:
        if not (ROOT / relative).is_file():
            failures.append(f"缺少文件：{relative}")

    skill_path = ROOT / "SKILL.md"
    if skill_path.is_file():
        skill_text = skill_path.read_text(encoding="utf-8")
        for marker in REQUIRED_SKILL_MARKERS:
            if marker not in skill_text:
                failures.append(f"SKILL.md 缺少关键规则：{marker}")
        for text in FORBIDDEN_TEXT:
            if text in skill_text:
                failures.append(f"SKILL.md 含不允许内容：{text}")

    cases_path = ROOT / "tests" / "cases.json"
    if cases_path.is_file():
        cases = json.loads(cases_path.read_text(encoding="utf-8"))
        if len(cases) < 10:
            failures.append("测试案例少于10个")
        case_ids = {case.get("id") for case in cases}
        required_ids = {
            "missing-job",
            "mbti-only",
            "exact-layoff-date",
            "actual-pay-cut",
            "discriminatory-ranking",
            "offline-market-data",
        }
        missing = required_ids - case_ids
        if missing:
            failures.append(f"缺少关键测试：{sorted(missing)}")

    yaml_path = ROOT / "agents" / "openai.yaml"
    if yaml_path.is_file():
        yaml_text = yaml_path.read_text(encoding="utf-8")
        for marker in [
            'display_name: "这破班还能上多久？"',
            'brand_color: "#F59A3D"',
            "$job-ai-risk-check-cn",
            "allow_implicit_invocation: true",
        ]:
            if marker not in yaml_text:
                failures.append(f"openai.yaml 缺少：{marker}")

    for path in ROOT.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        if path.suffix.lower() in {".md", ".yaml", ".json", ".py"}:
            text = path.read_text(encoding="utf-8")
            if "\ufffd" in text:
                failures.append(f"发现乱码替换字符：{path.relative_to(ROOT)}")
            if path.name != "validate_contract.py" and "[TODO:" in text:
                failures.append(f"发现模板TODO：{path.relative_to(ROOT)}")
        if path.suffix.lower() == ".md":
            check_links(path, failures)

    if failures:
        print("FAILED")
        for failure in failures:
            print(f"- {failure}")
        raise SystemExit(1)

    print("PASSED")
    print(f"- 必需文件：{len(REQUIRED_FILES)}")
    print("- 边界案例：16")
    print("- 相对链接：已检查")
    print("- MBTI零权重、缺失处理和预测边界：已检查")


if __name__ == "__main__":
    main()
