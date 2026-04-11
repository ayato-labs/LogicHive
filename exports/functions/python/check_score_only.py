    def check_score_only(
        self,
        name: str,
        code: str,
        description: str = "",
        dependencies: List[str] = None,
    ) -> Dict[str, Any]:
        """
        Ultra-fast quality check using ONLY Ruff.
        """
        report = {
            "status": "evaluated",
            "final_score": 100,
            "reliability": "high",
            "linter": {"passed": True, "errors": []},
            "formatter": {"passed": True, "feedback": ""},
            "metadata": {"quality_feedback": ""},
        }

        # 1. Linter (Normalized by Error Density: errors / lines)
        l_pass, l_errs = self.processor.lint(code)
        report["linter"] = {"passed": l_pass, "errors": l_errs}

        # Calculate line count (min 1 to avoid ZeroDivision)
        line_count = max(code.count("\n") + 1, 1)
        error_density = len(l_errs) / line_count

        # Linter Penalty: Density-based scaling (max 70 points)
        linter_penalty = min(error_density * 500, 70)

        # 2. Formatter (Flat 30 points penalty if fails)
        f_pass, f_msg = self.processor.format_check(code)
        report["formatter"] = {"passed": f_pass, "feedback": f_msg}
        formatter_penalty = 0 if f_pass else 30

        # 3. Security Audit
        s_bandit = self.security_auditor.run_bandit(code)
        s_safety = self.security_auditor.run_safety(dependencies or [])

        report["security"] = {"bandit": s_bandit, "safety": s_safety}
        security_penalty = s_bandit["score_penalty"] + s_safety["score_penalty"]

        final_score = max(
            0, 100 - linter_penalty - formatter_penalty - security_penalty
        )
        report["final_score"] = int(final_score)

        # Re-evaluate reliability tier
        if report["final_score"] >= 80:
            report["reliability"] = "high"
        elif report["final_score"] >= 50:
            report["reliability"] = "medium"
        else:
            report["reliability"] = "low"

        return report
