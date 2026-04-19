import platform
import sys
from datetime import datetime


class SystemFingerprint:
    """
    Generates and manages a deterministic 'fingerprint' of the system environment.
    Used to detect environment drift (Bit Rot) in logic assets.
    """

    @staticmethod
    def get_current() -> dict:
        """
        Collects essential system metadata to create a fingerprint.
        """
        try:
            # We focus on fields that impact binary compatibility and runtime behavior
            from core.config import EXECUTION_DRIVER

            fingerprint = {
                "os": platform.system(),
                "os_release": platform.release(),
                "os_version": platform.version(),
                "python_version": sys.version.split()[0],
                "python_implementation": platform.python_implementation(),
                "cpu_arch": platform.machine(),
                "execution_driver": EXECUTION_DRIVER,
                "timestamp": datetime.now().isoformat(),  # For tracking when the check occurred
            }
            return fingerprint
        except Exception as e:
            return {"error": f"Failed to collect system info: {str(e)}", "os": platform.system()}

    @staticmethod
    def compare(stored: dict, current: dict) -> list[str]:
        """
        Compares two fingerprints and returns a list of significant differences.
        """
        diffs = []

        # 1. Critical: OS Change
        if stored.get("os") != current.get("os"):
            diffs.append(f"OS mismatch: Stored={stored.get('os')}, Current={current.get('os')}")

        # 2. Critical: Python Major/Minor version change
        stored_py = ".".join(stored.get("python_version", "0.0.0").split(".")[:2])
        current_py = ".".join(current.get("python_version", "0.0.0").split(".")[:2])
        if stored_py != current_py:
            diffs.append(
                f"Python Version Drift: Stored={stored.get('python_version')}, Current={current.get('python_version')}"
            )

        # 3. High: CPU Arch change
        if stored.get("cpu_arch") != current.get("cpu_arch"):
            diffs.append(
                f"Architecture Drift: Stored={stored.get('cpu_arch')}, Current={current.get('cpu_arch')}"
            )

        # 4. Moderate: Execution Driver change (behavior may differ between venv and docker)
        if stored.get("execution_driver") != current.get("execution_driver"):
            diffs.append(
                f"Execution Driver Change: Stored={stored.get('execution_driver')}, Current={current.get('execution_driver')}"
            )

        return diffs

    @staticmethod
    def generate_warning_msg(stored: dict) -> str | None:
        """
        Helper to generate a human-friendly warning message if drift is detected.
        """
        current = SystemFingerprint.get_current()
        diffs = SystemFingerprint.compare(stored, current)

        if not diffs:
            return None

        msg = "[ENVIRONMENT DRIFT WARNING] This logic was verified in a different environment:\n"
        for d in diffs:
            msg += f"- {d}\n"
        msg += "Expect potential runtime errors or behavior changes."
        return msg
