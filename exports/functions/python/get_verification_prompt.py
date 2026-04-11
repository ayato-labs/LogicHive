    def get_verification_prompt(self, name: str, code: str, description: str) -> str:
        """Generates a prompt for AI-driven quality/security review."""
        return (
            f"Review this Python function for the LogicHive Store.\n"
            f"Name: {name}\n"
            f"Description: {description}\n"
            f"Code:\n{code}\n\n"
            f"Task: Evaluate the implementation quality, potential bugs, and security risks. "
            f"Provide a brief 1-sentence feedback and a 'Reliability Score' between 0 and 100. "
            f"Output format: JSON with 'feedback' and 'score' keys."
        )
