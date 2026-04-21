from klaviyo_mcp_server.utils.utils import clean_result, get_klaviyo_client
from klaviyo_mcp_server.utils.tool_decorator import mcp_tool


@mcp_tool(has_writes=False)
def get_account_details() -> dict:
    """Get the details of the account. Getting information about the catalog may also be useful (use the get_catalog_items tool for this).

    You can view and edit your account details flow in the Klaviyo UI at https://www.klaviyo.com/settings/account
    """
    response = get_klaviyo_client().Accounts.get_accounts()
    clean_result(response["data"])
    return response
