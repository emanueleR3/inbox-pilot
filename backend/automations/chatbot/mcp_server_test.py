from mcp.server.fastmcp import FastMCP

mcp = FastMCP("jerry", port=6969)

@mcp.tool()
async def greet_from_jerry(location: str) -> str:
    """Get greeting from Jerry based on location."""
    print("Agg trasut")
    return "Ciao from Jerry in " + location

if __name__ == "__main__":
    mcp.run(transport="streamable-http")