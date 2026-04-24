# klaviyo-mcp-server-extended

**A community fork of Klaviyo's official [`klaviyo-mcp-server`](https://pypi.org/project/klaviyo-mcp-server/) (v0.4.1) adding missing campaign/template traversal tools plus universal content support that the official server does not expose.**

This is an unofficial, unsupported patch. It layers the missing tools onto the official code without changing any existing behavior — everything that works in the official server continues to work identically here.

## Why this exists

As of April 2026, the official Klaviyo MCP server (v0.4.1) does not expose tools to:

1. List email templates (only fetch by known ID)
2. Traverse from a campaign or campaign message to its associated template
3. Clone a campaign or a template

These gaps make it impossible to clone an email campaign end-to-end through the MCP server or safely manage Klaviyo's newer reusable universal content blocks, even though the underlying REST API fully supports all of these operations and the bundled `klaviyo-api` Python SDK already has the methods wired up. This fork simply exposes them.

## Tools added

These tools are thin wrappers around methods that already exist in the official `klaviyo-api` SDK. They follow the same style conventions as the surrounding code (`@mcp_tool`, `get_klaviyo_client()`, `clean_result()`).

| Tool | Writes? | REST endpoint |
|------|---------|---------------|
| `klaviyo_get_email_templates` | no | `GET /api/templates` |
| `klaviyo_clone_email_template` | yes | `POST /api/template-clone` |
| `klaviyo_get_messages_for_campaign` | no | `GET /api/campaigns/{id}/campaign-messages` |
| `klaviyo_get_template_for_campaign_message` | no | `GET /api/campaign-messages/{id}/template` |
| `klaviyo_get_template_id_for_campaign_message` | no | `GET /api/campaign-messages/{id}/relationships/template` |
| `klaviyo_clone_campaign` | yes | `POST /api/campaign-clone` |
| `klaviyo_get_universal_content_blocks` | no | `GET /api/template-universal-content` |
| `klaviyo_get_universal_content_block` | no | `GET /api/template-universal-content/{id}` |
| `klaviyo_create_universal_content_block` | yes | `POST /api/template-universal-content` |
| `klaviyo_update_universal_content_block` | yes | `PATCH /api/template-universal-content/{id}` |
| `klaviyo_delete_universal_content_block` | yes | `DELETE /api/template-universal-content/{id}` |
| `klaviyo_get_universal_content_block_html` | no | `GET /api/template-universal-content/{id}` |
| `klaviyo_get_universal_content_blocks_for_template` | no | derived from template HTML + definition scan |
| `klaviyo_get_universal_content_blocks_for_campaign` | no | derived from campaign messages -> template traversal |
| `klaviyo_get_templates_using_universal_content_block` | no | derived reverse relationship scan |
| `klaviyo_get_campaigns_using_universal_content_block` | no | derived reverse relationship scan |

All other tools from the official server are preserved unchanged.

## Universal content workflow

For Klaviyo's newer reusable template blocks:

1. discover blocks with `klaviyo_get_universal_content_blocks`
2. inspect a block with `klaviyo_get_universal_content_block`
3. create or update reusable blocks with the universal content write tools
4. embed the returned block ID into template HTML with:

```html
<div data-klaviyo-universal-block="block_id">&nbsp;<div>
```

Warning: updating or deleting a universal content block affects every template that uses it.

Relationship helpers are also available:

- template -> universal content blocks
- campaign -> universal content blocks
- universal content block -> templates using it
- universal content block -> campaigns using it

Reverse-usage relationship tools are paged so they can handle larger accounts without returning oversized responses.

## Authentication

Identical to the official local server: private API key via the `PRIVATE_API_KEY` environment variable. This fork does **not** provide OAuth or any remote hosting — OAuth is Klaviyo's own gateway at `https://mcp.klaviyo.com/mcp` and is not part of the open-source package.

The private API key needs the same scopes as the official server. For the new tools specifically:

- `templates:read` — for `get_email_templates`, `get_template_for_campaign_message`, `get_universal_content_blocks`, `get_universal_content_block`, `get_universal_content_block_html`
- `templates:write` — for `clone_email_template`, `create_universal_content_block`, `update_universal_content_block`, `delete_universal_content_block`
- `campaigns:read` — for `get_messages_for_campaign`, `get_template_id_for_campaign_message`
- `campaigns:write` — for `clone_campaign`

The full recommended scope set from Klaviyo's docs already covers all of these.

## Installation

### From PyPI

After this package is published, install and run the fork with:

```bash
uvx --from klaviyo-mcp-server-extended klaviyo-mcp-server
```

Pin the release version for reproducible MCP client configs:

```bash
uvx --from klaviyo-mcp-server-extended==0.4.6 klaviyo-mcp-server
```

### From a local wheel

Build the wheel first:

```bash
uv build
```

Then run the generated wheel from `dist/`:

```bash
uvx --from ./dist/klaviyo_mcp_server_extended-0.4.6-py3-none-any.whl klaviyo-mcp-server
```

### MCP client config (Claude Desktop, Cursor, VS Code)

Replace the official `uvx klaviyo-mcp-server@latest` invocation with `uvx --from klaviyo-mcp-server-extended==0.4.6 klaviyo-mcp-server`. For example, in Claude Desktop:

```json
{
  "mcpServers": {
    "klaviyo": {
      "command": "uvx",
      "args": [
        "--from",
        "klaviyo-mcp-server-extended==0.4.6",
        "klaviyo-mcp-server"
      ],
      "env": {
        "PRIVATE_API_KEY": "YOUR_API_KEY",
        "READ_ONLY": "false",
        "ALLOW_USER_GENERATED_CONTENT": "false"
      }
    }
  }
}
```

The entry point command (`klaviyo-mcp-server`) is unchanged, so no downstream agent code needs to change — only the `--from` package is new.

### Verifying the fork loaded

After restarting your MCP client, your tool list should include the six new tools alongside the existing ones. In Claude Desktop, click **Search and tools → klaviyo** to confirm.

## Upstream relationship

- Based on `klaviyo-mcp-server==0.4.1` from PyPI (published 2026-03-05)
- Version `0.4.6`, based on the upstream `0.4.1` base plus added campaign/template traversal, universal content, relationship, cache, and paged reverse-usage support
- No changes to existing tools, models, utilities, prompts, or scripts
- The added tools are the only diff

If Klaviyo eventually ships equivalent tools upstream, uninstall this fork and revert to the official `klaviyo-mcp-server@latest`.

## License

MIT, matching the upstream package. See `LICENSE`.
