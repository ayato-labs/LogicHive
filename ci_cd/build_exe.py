import os
import shutil
import subprocess
from pathlib import Path


def build():
    project_root = Path(__file__).parent.parent.resolve()
    os.chdir(project_root)

    print(f"Building LogicHive.exe in {project_root}...")

    # Clean old builds
    for folder in ["build", "dist", "release"]:
        if os.path.exists(folder):
            print(f"Cleaning {folder}...")
            shutil.rmtree(folder)

    # Run PyInstaller
    try:
        # We use the new LogicHive.spec
        subprocess.run(["pyinstaller", "--noconfirm", "LogicHive.spec"], check=True)
        print(
            "\n[SUCCESS] Build complete! You can find the executable in the 'dist' folder."
        )

        # Move to a 'release' folder for distribution
        release_dir = project_root / "release"
        release_dir.mkdir(exist_ok=True)

        # PyInstaller 'COLLECT' mode creates a directory by default in the spec
        # Let's zip it for the release
        shutil.make_archive("release/LogicHive-Windows", "zip", "dist/LogicHive")

        print(f"Zipped release created at {release_dir / 'LogicHive-Windows.zip'}")

    except subprocess.CalledProcessError as e:
        print(f"\n[ERROR] Build failed: {e}")
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")


if __name__ == "__main__":
    build()
