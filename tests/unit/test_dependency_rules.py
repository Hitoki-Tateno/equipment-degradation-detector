"""依存方向の制約テスト。

アーキテクチャで定めた依存ルールをコードレベルで検証する。
- analysis/ と ingestion/ は interfaces/ にのみ依存可
- store/ と result_store/ への直接依存は禁止
"""

import ast
from pathlib import Path

BACKEND_ROOT = Path(__file__).parent.parent.parent / "backend"

# これらのモジュールは interfaces/ にのみ依存すべき
RESTRICTED_MODULES = ["analysis", "ingestion"]

# これらへの直接依存を禁止
FORBIDDEN_IMPORTS = ["backend.store", "backend.result_store"]


def _collect_imports(filepath: Path) -> list[str]:
    """Pythonファイルからimport文を抽出する。"""
    source = filepath.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
    return imports


def test_no_direct_store_imports():
    """analysis/ と ingestion/ が store/ や result_store/ を直接importしていないことを検証。"""
    violations = []

    for module_name in RESTRICTED_MODULES:
        module_dir = BACKEND_ROOT / module_name
        if not module_dir.exists():
            continue

        for py_file in module_dir.rglob("*.py"):
            imports = _collect_imports(py_file)
            for imp in imports:
                for forbidden in FORBIDDEN_IMPORTS:
                    if imp.startswith(forbidden):
                        rel_path = py_file.relative_to(BACKEND_ROOT.parent)
                        violations.append(f"{rel_path}: imports {imp}")

    assert violations == [], "依存方向違反を検出:\n" + "\n".join(f"  - {v}" for v in violations)
