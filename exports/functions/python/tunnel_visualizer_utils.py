import sys
import time

import httpx
import qrcode


def get_ngrok_public_url(port: int = 4040, max_retries: int = 10, delay: int = 2) -> str | None:
    """
    Retrieves the public URL from a running ngrok instance by querying its local API.

    Args:
        port: The local port where ngrok's inspection API is running (default 4040).
        max_retries: Maximum number of attempts to fetch the URL.
        delay: Seconds to wait between retries.

    Returns:
        The public URL string if found, otherwise None.
    """
    api_url = f"http://127.0.0.1:{port}/api/tunnels"
    for _ in range(max_retries):
        try:
            res = httpx.get(api_url)
            tunnels = res.json().get("tunnels", [])
            if tunnels:
                return tunnels[0]["public_url"]
        except httpx.ConnectError:
            # Expected if ngrok hasn't started yet, continue retrying
            pass
        except Exception as e:
            # Print other unexpected errors to stderr instead of silent pass
            print(f"Warning: Unexpected error while polling ngrok: {e}", file=sys.stderr)

        time.sleep(delay)
    return None


def display_terminal_qr(data: str, title: str | None = None):
    """
    Generates an ASCII QR code for the given data and prints it to the terminal.
    """
    if title:
        print(f"\n{'=' * 50}")
        print(f"  {title}")
        print(f"{'=' * 50}")

    print(f"\nData: {data}\n")

    qr = qrcode.QRCode(version=1, box_size=1, border=4)
    qr.add_data(data)
    qr.make(fit=True)
    qr.print_ascii(invert=True)
    print("\nScan the QR code above to open the link on your mobile device.")


def tunnel_visualizer(api_port: int = 4040):
    """
    Unified helper to automatically fetch the ngrok URL and display its QR code.
    Robust against connection retries but logs unexpected failures.
    """
    url = get_ngrok_public_url(port=api_port)
    if url:
        display_terminal_qr(url, title="Tunnel Established")
    else:
        print(
            "Error: ngrok tunnel not found. Make sure ngrok is running and its API port is correct."
        )
