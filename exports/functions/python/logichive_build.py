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
        # Run PyInstaller using the spec file
        subprocess.run(["pyinstaller", "--noconfirm", "LogicHive.spec"], check=True)
        print("\n[SUCCESS] Build complete! You can find the executable in the 'dist' folder.")

        # Move to a 'release' folder for distribution if needed
        # (For now, let's just keep it in dist/ for simplicity as per MVP)

    except subprocess.CalledProcessError as e:
        print(f"\n[ERROR] Build failed: {e}")
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
