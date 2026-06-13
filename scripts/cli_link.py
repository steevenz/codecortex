"""
CLI Linker for Cross-Cortex Integration.
Performs symmetrical handshake using Client Key (HMAC) to receive an Operational Key.
Supports the 2-step (init/complete) challenge-response flow.

:project: Cognitive Server
:package: Scripts
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
"""

import os
import sys
import hmac
import hashlib
import time
import secrets
import argparse
import requests
from dotenv import set_key
from pathlib import Path

def get_project_root() -> Path:
    return Path(__file__).parent.parent

def generate_proof(client_key: str, handshake_id: str, ide: str, challenge: str) -> str:
    message = f"{handshake_id}:{ide}:{challenge}".encode('utf-8')
    secret = client_key.encode('utf-8')
    return hmac.new(secret, message, hashlib.sha256).hexdigest()

def perform_handshake(target: str, url: str, client_key: str):
    print(f"[*] Initiating 2-step handshake with {target} at {url}...")

    headers = {
        "Content-Type": "application/json",
        "X-CLIENT-KEY": client_key,
        "X-IDE-ORIGIN": "cli_link"
    }

    ide_name = f"cli_{secrets.token_hex(4)}"
    nonce = secrets.token_hex(8)

    # Determine correct endpoint prefix based on target
    prefix = "/codecortex-api/v1/auth" if target.lower() == "codecortex" else "/neocortex-api/v1/auth"
    base_url = url.rstrip('/')

    try:
        # Step 1: Init
        init_payload = {"llm_instance_id": ide_name, "client_nonce": nonce}
        init_resp = requests.post(f"{base_url}{prefix}/handshake/init", json=init_payload, headers=headers)
        init_resp.raise_for_status()
        init_data = init_resp.json().get("data", {})

        handshake_id = init_data.get("handshake_id")
        challenge = init_data.get("challenge")

        if not handshake_id or not challenge:
            print("[-] Invalid response from /init")
            return

        print(f"[*] Challenge received. Computing proof...")

        # Step 2: Complete
        proof = generate_proof(client_key, handshake_id, ide_name, challenge)
        complete_payload = {"handshake_id": handshake_id, "client_proof": proof}

        comp_resp = requests.post(f"{base_url}{prefix}/handshake/complete", json=complete_payload, headers=headers)
        comp_resp.raise_for_status()
        comp_data = comp_resp.json().get("data", {})

        operational_key = comp_data.get("api_key")

        if operational_key:
            print(f"[+] Handshake successful! Received Operational Key.")

            # Write to .env
            env_path = get_project_root() / ".env"
            if not env_path.exists():
                env_path.touch()

            env_var = f"{target.upper()}_API_KEY"
            set_key(str(env_path), env_var, operational_key)
            print(f"[+] Successfully injected {env_var} into .env")
        else:
            print("[-] Handshake succeeded but no operational key was returned.")

    except requests.exceptions.RequestException as e:
        print(f"[-] Network error during handshake: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"[-] Server Response: {e.response.text}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Link with another Cortex server via Handshake.")
    parser.add_argument("--target", required=True, help="Target system name (e.g., codecortex, neocortex)")
    parser.add_argument("--url", required=True, help="Base URL of the target server")
    parser.add_argument("--client-key", required=True, help="The Master Client Key of the target server")

    args = parser.parse_args()

    perform_handshake(args.target, args.url, args.client_key)
