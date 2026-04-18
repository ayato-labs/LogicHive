import ast
import logging
import os
import re
from pathlib import Path
from typing import Any, Set

from ..base import BaseEvaluator, EvaluationResult

logger = logging.getLogger(__name__)

class DependencyVouchEvaluator(BaseEvaluator):
    """
    Hallucinated Imports detector inspired by Rigour.
    Verifies that all imports are either stdlib, project local, or declared in manifests.
    """

    @property
    def name(self) -> str:
        return "dependency_vouch"

    async def evaluate(self, code: str, language: str, **kwargs) -> EvaluationResult:
        if language.lower() != "python":
            return EvaluationResult(score=100.0, reason="Dependency check skipped for non-python language.")

        # 1. Extract imports from code
        try:
            tree = ast.parse(code)
            imports = self._extract_imports(tree)
        except Exception as e:
            return EvaluationResult(score=0.0, reason=f"Syntax error prevented dependency analysis: {e}")

        if not imports:
            return EvaluationResult(score=100.0, reason="No external dependencies found.")

        # 2. Filter out stdlib
        # Inline stdlib check to avoid external file dependencies in evaluation plugins
        def check_stdlib(m):
            std = {"os", "sys", "json", "re", "math", "datetime", "typing", "asyncio", "logging", "pathlib", "abc", "collections", "functools", "itertools", "threading", "multiprocessing", "pickle", "shutil", "tempfile", "time", "uuid", "hashlib", "base64", "xml", "html", "unittest", "pytest", "typing_extensions"}
            return m.split(".")[0] in std
        
        # 3. Load project context (manifests)
        cwd = os.getcwd()
        declared_pkgs = self._load_manifest_dependencies(cwd)

        hallucinated = []
        for imp in imports:
            if check_stdlib(imp):
                continue
            
            top_level = imp.split(".")[0]
            
            # 1. Check local files (rough check based on current dir)
            is_local = os.path.exists(os.path.join(cwd, f"{top_level}.py")) or \
                       os.path.exists(os.path.join(cwd, top_level, "__init__.py"))
            
            if is_local:
                continue

            # 2. Check manifests (REQUIRED for external libs)
            normalized_top = top_level.lower().replace("_", "-")
            if normalized_top in declared_pkgs:
                continue
            
            # Special case: allow common libraries ONLY if no manifest exists AND not a strict project
            if not declared_pkgs and top_level in {"pandas", "numpy", "requests", "pydantic", "fastapi", "sqlalchemy", "tqdm", "yaml"}:
                continue

            hallucinated.append(imp)

        if not hallucinated:
            return EvaluationResult(score=100.0, reason="All dependencies are declared or local.")

        score = max(0.0, 100.0 - (len(hallucinated) * 30))
        return EvaluationResult(
            score=score,
            reason=f"Hallucinated imports detected: {', '.join(hallucinated)}. Add them to requirements.txt or pyproject.toml.",
            details={"missing": hallucinated}
        )

    def _extract_imports(self, tree: ast.AST) -> Set[str]:
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.level == 0 and node.module:
                    imports.add(node.module)
        return imports

    def _load_manifest_dependencies(self, cwd: str) -> Set[str]:
        deps = set()
        # 1. requirements.txt
        for req_file in ["requirements.txt", "requirements-dev.txt"]:
            path = Path(cwd) / req_file
            if path.exists():
                content = path.read_text(errors="ignore")
                for line in content.splitlines():
                    line = line.strip()
                    if not line or line.startswith(("#", "-")): continue
                    # Extract package name: e.g. "flask==2.0.1" -> "flask", "pandas>=1.0" -> "pandas"
                    # Split on any character that isn't a letter, digit, underscore, or hyphen
                    name_match = re.match(r'^([a-zA-Z0-9_\-]+)', line)
                    if name_match:
                        deps.add(name_match.group(1).lower().replace("_", "-"))
        
        # 2. pyproject.toml
        pyproj = Path(cwd) / "pyproject.toml"
        if pyproj.exists():
            content = pyproj.read_text(errors="ignore")
            # Simple regex search instead of full toml parser
            matches = re.findall(r'dependencies\s*=\s*\[([\s\S]*?)\]', content)
            for match in matches:
                pkgs = re.findall(r'["\']([^">=<!\s\[]+)', match)
                for p in pkgs: 
                    deps.add(p.lower().replace("_", "-"))
        
        return deps
