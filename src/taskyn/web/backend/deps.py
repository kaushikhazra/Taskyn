"""FastAPI dependencies — MCP integration via FastMCP Client.

Supports two transports:
- HTTP:  set TASKYN_MCP_URL  (production, Docker)
- stdio: set TASKYN_MCP_CMD  (testing, local dev)

If the global _mcp_client is already set (e.g. by a test fixture), the
lifespan init is a no-op.
"""

import logging
import os
from functools import lru_cache
from typing import Annotated, Any

from fastapi import Depends, HTTPException
from fastmcp import Client
from fastmcp.exceptions import ClientError

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# MCP Client Configuration
# ---------------------------------------------------------------------------


@lru_cache
def get_mcp_settings() -> dict[str, Any]:
    """Get MCP client configuration from environment variables."""
    url = os.environ.get("TASKYN_MCP_URL")
    cmd = os.environ.get("TASKYN_MCP_CMD")
    if not url and not cmd:
        raise RuntimeError(
            "Either TASKYN_MCP_URL or TASKYN_MCP_CMD environment variable is required"
        )
    return {
        "url": url,
        "cmd": cmd,
        "timeout": float(os.environ.get("TASKYN_MCP_TIMEOUT", "30")),
    }


# Global client instance (managed by lifespan in main.py)
_mcp_client: Client | None = None
# Whether the lifespan created the client (vs. externally injected by tests)
_mcp_client_owned: bool = False


async def init_mcp_client() -> None:
    """Initialize global MCP client. Called during app startup.

    No-op if _mcp_client is already set (e.g. by a test fixture).
    """
    global _mcp_client, _mcp_client_owned
    if _mcp_client is not None:
        logger.info("MCP client already initialized, skipping")
        return

    settings = get_mcp_settings()
    if settings["cmd"]:
        logger.info("Connecting to MCP server via stdio: %s", settings["cmd"])
        _mcp_client = Client(settings["cmd"])
    else:
        logger.info("Connecting to MCP server at %s", settings["url"])
        _mcp_client = Client(settings["url"], timeout=settings["timeout"])

    await _mcp_client.__aenter__()
    _mcp_client_owned = True
    logger.info("MCP client connected successfully")


async def close_mcp_client() -> None:
    """Close global MCP client. Called during app shutdown.

    Only closes the client if the lifespan created it. Externally
    injected clients (test fixtures) are managed by their owner.
    """
    global _mcp_client, _mcp_client_owned
    if _mcp_client and _mcp_client_owned:
        logger.info("Closing MCP client connection")
        await _mcp_client.__aexit__(None, None, None)
    _mcp_client = None
    _mcp_client_owned = False


def get_mcp_client() -> Client:
    """Dependency to get MCP client instance."""
    if _mcp_client is None:
        raise HTTPException(503, detail="MCP client not initialized")
    return _mcp_client


# Type alias for dependency injection
MCPClient = Annotated[Client, Depends(get_mcp_client)]


# ---------------------------------------------------------------------------
# MCP Tool Invocation
# ---------------------------------------------------------------------------


async def call_mcp_tool(tool_name: str, args: dict) -> Any:
    """Call an MCP tool via FastMCP Client and map errors to HTTP exceptions.

    This function communicates with the Taskyn MCP server over HTTP using
    the FastMCP Client library. Errors from the MCP server are mapped to
    appropriate HTTP status codes.
    """
    client = get_mcp_client()

    try:
        result = await client.call_tool(tool_name, args)
        # FastMCP returns CallToolResult - extract data from various formats

        # Check if the tool call resulted in an error
        if hasattr(result, 'isError') and result.isError:
            # Extract error message from content
            error_msg = "MCP tool error"
            if hasattr(result, 'content') and result.content:
                for item in result.content:
                    if hasattr(item, 'text'):
                        error_msg = item.text
                        break
            # Map error to appropriate HTTP status
            msg_lower = error_msg.lower()
            if "not found" in msg_lower:
                raise HTTPException(404, detail=error_msg)
            elif "cycle" in msg_lower or "already exists" in msg_lower:
                raise HTTPException(409, detail=error_msg)
            elif "validation" in msg_lower or "invalid" in msg_lower:
                raise HTTPException(422, detail=error_msg)
            else:
                raise HTTPException(422, detail=error_msg)

        # Try structured_content first (preferred format)
        if hasattr(result, 'structured_content') and result.structured_content:
            sc = result.structured_content
            # Check for 'result' key (our MCP server format)
            if 'result' in sc:
                return sc['result']
            # Otherwise return the whole structured_content
            return sc

        # Fallback: try to parse from content text (TextContent format)
        if hasattr(result, 'content') and result.content:
            import json
            for content_item in result.content:
                if hasattr(content_item, 'text'):
                    try:
                        return json.loads(content_item.text)
                    except json.JSONDecodeError:
                        return content_item.text

        # Last resort: try .data attribute
        if hasattr(result, 'data'):
            return result.data

        return None

    except ClientError as e:
        # Map error messages to HTTP status codes
        message = str(e)
        msg_lower = message.lower()

        if "not found" in msg_lower:
            raise HTTPException(404, detail=message)
        elif "cycle" in msg_lower:
            raise HTTPException(409, detail=message)
        elif "already exists" in msg_lower:
            raise HTTPException(409, detail=message)
        elif "validation" in msg_lower or "invalid" in msg_lower:
            raise HTTPException(422, detail=message)
        else:
            raise HTTPException(422, detail=message)

    except ConnectionError as e:
        logger.error("MCP server connection error: %s", e)
        raise HTTPException(503, detail=f"MCP server unavailable: {e}")

    except TimeoutError as e:
        logger.error("MCP server timeout: %s", e)
        raise HTTPException(504, detail=f"MCP server timeout: {e}")

    except Exception as e:
        # Check if the exception message contains known error patterns
        message = str(e)
        msg_lower = message.lower()

        if "not found" in msg_lower:
            raise HTTPException(404, detail=message)
        elif "already exists" in msg_lower:
            raise HTTPException(409, detail=message)
        elif "cycle" in msg_lower:
            raise HTTPException(409, detail=message)
        elif "validation" in msg_lower or "invalid" in msg_lower:
            raise HTTPException(422, detail=message)

        logger.exception("Unexpected error calling MCP tool %s", tool_name)
        raise HTTPException(500, detail=f"MCP client error: {e}")
