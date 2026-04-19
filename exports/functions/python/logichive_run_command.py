def run_command(command, check=True):
    print(f"[EXEC] {' '.join(command)}")
    result = subprocess.run(command, capture_output=True, text=True)
    if check and result.returncode != 0:
        print(f"[ERROR] {result.stderr}")
        sys.exit(result.returncode)
    return result
