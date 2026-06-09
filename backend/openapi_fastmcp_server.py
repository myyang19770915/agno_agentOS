import argparse
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx
from fastmcp import FastMCP


# DEFAULT_OPENAPI_URL = "https://test4.txcaix.com/deepseekocr/openapi.json"
DEFAULT_OPENAPI_URL = "https://test4.txcaix.com/ocrapi/openapi.json"
DEFAULT_TRANSPORT = "streamable-http"
DEFAULT_PORT = 8015
DEFAULT_HOST = "0.0.0.0"
DEFAULT_MCP_PATH = "/agent01/mcp"


def _load_openapi_spec(openapi_url: str, openapi_file: str) -> dict[str, Any]:
    if openapi_file:
        return json.loads(Path(openapi_file).read_text(encoding="utf-8"))

    response = httpx.get(openapi_url, timeout=60)
    response.raise_for_status()
    return response.json()


def _derive_server_name(openapi_spec: dict[str, Any]) -> str:
    title = (openapi_spec.get("info") or {}).get("title") or "OpenAPI Server"
    cleaned = re.sub(r"[^a-zA-Z0-9 _-]+", "", title).strip()
    return cleaned or "OpenAPI Server"


def _normalize_openapi_servers(openapi_spec: dict[str, Any], openapi_url: str) -> dict[str, Any]:
    """
    Ensure OpenAPI servers use absolute http(s) URLs.
    FastMCP/from_openapi may fail when spec contains relative servers like '/ocrapi'.
    """
    parsed = urlparse(openapi_url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    servers = openapi_spec.get("servers")

    if not servers:
        openapi_spec["servers"] = [{"url": origin}]
        return openapi_spec

    normalized_servers: list[dict[str, Any]] = []
    for server in servers:
        if not isinstance(server, dict):
            continue

        raw_url = str(server.get("url", "")).strip()
        if not raw_url:
            normalized_servers.append({**server, "url": origin})
            continue

        if raw_url.startswith(("http://", "https://")):
            normalized_servers.append(server)
            continue

        absolute = urljoin(origin + "/", raw_url.lstrip("/"))
        normalized_servers.append({**server, "url": absolute})

    if normalized_servers:
        openapi_spec["servers"] = normalized_servers
    else:
        openapi_spec["servers"] = [{"url": origin}]

    return openapi_spec


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Load OpenAPI JSON and serve it directly as FastMCP tools."
    )
    parser.add_argument(
        "--openapi-url",
        default=DEFAULT_OPENAPI_URL,
        help="OpenAPI JSON URL (e.g. https://host/path/openapi.json)",
    )
    parser.add_argument(
        "--openapi-file",
        default="",
        help="Optional local OpenAPI JSON file path. If provided, it overrides --openapi-url.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help=f"Server port (default: {DEFAULT_PORT})",
    )
    parser.add_argument(
        "--host",
        default=DEFAULT_HOST,
        help=f"Bind host (default: {DEFAULT_HOST})",
    )
    parser.add_argument(
        "--transport",
        default=DEFAULT_TRANSPORT,
        help=f"MCP transport (default: {DEFAULT_TRANSPORT})",
    )
    parser.add_argument(
        "--mcp-path",
        default=DEFAULT_MCP_PATH,
        help=f"MCP endpoint path for HTTP transports (default: {DEFAULT_MCP_PATH})",
    )
    args = parser.parse_args()

    openapi_spec = _load_openapi_spec(args.openapi_url, args.openapi_file)
    openapi_spec = _normalize_openapi_servers(openapi_spec, args.openapi_url)
    print(openapi_spec)
    mcp = FastMCP.from_openapi(
        openapi_spec,
        name=_derive_server_name(openapi_spec),
    )

    try:
        mcp.run(
            transport=args.transport,
            host=args.host,
            port=args.port,
            path=args.mcp_path,
        )
    except Exception as exc:
        if args.transport == "streamable-http":
            mcp.run(
                transport="streamable_http",
                host=args.host,
                port=args.port,
                path=args.mcp_path,
            )
        else:
            raise exc


if __name__ == "__main__":
    main()
