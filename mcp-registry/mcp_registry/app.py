import os

from fastapi import FastAPI, HTTPException, Query

from mcp_registry.finder import Finder
from mcp_registry.importer import Importer
from mcp_registry.promoter import Promoter
from mcp_registry.utils import get_k8s_client, logger

app = FastAPI()
crd_api = get_k8s_client()
registry_name = os.getenv("MCP_REGISTRY_NAME", None)
if not registry_name:
    raise ValueError("Environment variable 'MCP_REGISTRY_NAME' is not set.")
serverpool_name = os.getenv("MCP_SERVERPOOL_NAME", None)
if not serverpool_name:
    raise ValueError("Environment variable 'MCP_SERVERPOOL_NAME' is not set.")

logger.info(
    f"Starting MCP Registry with registry_name: {registry_name}, serverpool_name: {serverpool_name}"
)

finder = Finder(
    crd_api=crd_api,
    registry_name=registry_name,
    serverpool_name=serverpool_name,
)


@app.get("/serverdef")
async def list_server_defs():
    """
    List all server definitions in the MCP registry.
    Returns a list of server definitions with their metadata and specifications.
    """
    return finder.find_server_defs()


@app.get("/server")
async def list_servers():
    """
    List all servers in the MCP registry.
    Returns a list of servers with their metadata and specifications.
    """
    return finder.find_servers()


@app.get("/serverrun")
async def list_server_runs():
    """
    List all MCP server runs in the registry.
    Returns a list of server runs with their metadata and specifications.
    """
    return finder.find_server_runs()


@app.post("/import")
async def import_mcp_server_definitions(
    mcp_registry_source: str = Query(None, description="MCP Registry Source URL"),
):
    """
    Import MCP server definitions from a given source URL.
    This endpoint fetches server definitions from the specified MCP registry source
    and imports them into the MCP registry.
    """
    logger.info(f"Importing MCP server definitions from source: {mcp_registry_source}")
    importer = Importer(
        crd_api, registry_name=registry_name, mcp_registry_source=mcp_registry_source
    )

    while importer.has_next:
        try:
            importer.import_next()
        except Exception as e:
            logger.error(f"Error during import: {e}")
            raise HTTPException(status_code=500, detail=str(e))


@app.post("/promote")
async def promote_server_definition(
    server_definition_name: str = Query(None, description="Server Name"),
):
    """
    Promote a server definition to build a server image.
    This endpoint triggers the build process for an McpServer based on the provided server name.
    """
    logger.info(
        f"Promoting server definition: {server_definition_name} in registry: {registry_name}"
    )

    try:
        server_definition = finder.find_server_def(server_definition_name)
        if not server_definition:
            raise HTTPException(
                status_code=404,
                detail=f"Server definition '{server_definition_name}' not found.",
            )
        promoter = Promoter(
            crd_api, registry=registry_name, server_definition=server_definition
        )
        promoter.promote()
    except Exception as e:
        logger.exception(f"Error during server promotion: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Connect a given MCP Registry (by name)
# List the managed MCP servers
# Create and register a new McpServerRun from an McpServer, a given container or an external URL
# Unregister a given server
