from klaviyo_mcp_server.tools import *  # noqa: F401, F403
from klaviyo_mcp_server.prompts import *  # noqa: F401, F403
from klaviyo_mcp_server.server import mcp


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    # Initialize and run the server
    main()
