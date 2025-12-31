#!/usr/bin/env python3
"""
Client for fbcp-ili9341 tone mapping control socket.

Usage:
    python3 dimming_client.py PROFILE factory_fix
    python3 dimming_client.py PROFILE night
    python3 dimming_client.py PROFILE punchy
    python3 dimming_client.py SET gain 0.82
    python3 dimming_client.py SET gamma 1.18
    python3 dimming_client.py SET knee 0.85
    python3 dimming_client.py SET knee_strength 0.55
    python3 dimming_client.py GET
    python3 dimming_client.py ENABLE
    python3 dimming_client.py DISABLE
"""

import socket
import sys

SOCK = "/run/fbcp-ili9341.sock"

def cmd(s: str) -> str:
    """Send a command to the fbcp-ili9341 control socket and return the response."""
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as c:
        c.connect(SOCK)
        c.sendall((s.strip() + "\n").encode())
        return c.recv(4096).decode(errors="replace")

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    # Join all arguments into a single command
    command = " ".join(sys.argv[1:])
    
    try:
        response = cmd(command)
        print(response, end="")
    except FileNotFoundError:
        print(f"Error: Socket not found at {SOCK}")
        print("Make sure fbcp-ili9341 is running.")
        sys.exit(1)
    except ConnectionRefusedError:
        print(f"Error: Connection refused at {SOCK}")
        print("Make sure fbcp-ili9341 is running.")
        sys.exit(1)

if __name__ == "__main__":
    main()
