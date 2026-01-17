"""Helper script to request a Global Forest Watch (GFW) API key.

Docs:
- https://data-api.globalforestwatch.org/openapi
- https://www.globalforestwatch.org/help/developers/guides/create-and-use-an-api-key/
"""

from __future__ import annotations

import json
from typing import Any

import httpx

API_BASE_URL = "https://data-api.globalforestwatch.org"
API_KEY_ENDPOINT = f"{API_BASE_URL}/v1/api-key"


def _prompt_required(label: str) -> str:
    value = ""
    while not value.strip():
        value = input(f"{label}: ").strip()
    return value


def _prompt_optional(label: str) -> str:
    return input(f"{label} (optional): ").strip()


def _parse_domains(domains_raw: str) -> list[str]:
    if not domains_raw:
        return []
    return [domain.strip() for domain in domains_raw.split(",") if domain.strip()]


def request_api_key(payload: dict[str, Any]) -> dict[str, Any]:
    """Request a GFW API key.

    Args:
        payload: Request payload for /v1/api-key

    Returns:
        Response JSON as dict
    """
    with httpx.Client(timeout=30.0) as client:
        response = client.post(API_KEY_ENDPOINT, json=payload)
        response.raise_for_status()
        return response.json()


def main() -> int:
    print("Global Forest Watch API Key Helper")
    print("Documentation: https://data-api.globalforestwatch.org/openapi")
    print(
        "Signup guide: https://www.globalforestwatch.org/help/developers/guides/create-and-use-an-api-key/"
    )
    print()

    alias = _prompt_required("Alias (nickname for key)")
    organization = _prompt_required("Organization")
    email = _prompt_required("Contact email")
    domains_raw = _prompt_optional(
        "Allowed domains (comma-separated, e.g., *.myorg.com, localhost)"
    )

    payload = {
        "alias": alias,
        "organization": organization,
        "email": email,
        "domains": _parse_domains(domains_raw),
    }

    try:
        result = request_api_key(payload)
    except httpx.HTTPStatusError as exc:
        print("\nRequest failed:")
        print(f"HTTP {exc.response.status_code}: {exc.response.text}")
        return 1
    except httpx.RequestError as exc:
        print("\nNetwork error:")
        print(str(exc))
        return 1

    api_key = result.get("apiKey")
    if not api_key:
        print("\nUnexpected response:")
        print(json.dumps(result, indent=2))
        return 1

    print("\nAPI key created successfully.")
    print(f"API key: {api_key}")
    print("\nSet this environment variable for use in scripts:")
    print("Windows (PowerShell):")
    print(f'  $env:GFW_API_KEY = "{api_key}"')
    print("Windows (cmd.exe):")
    print(f"  set GFW_API_KEY={api_key}")
    print("macOS/Linux (bash/zsh):")
    print(f'  export GFW_API_KEY="{api_key}"')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
