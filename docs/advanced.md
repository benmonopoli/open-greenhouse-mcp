# Advanced Setup

## Webhook Receiver

The built-in webhook receiver stores Greenhouse events in SQLite for querying via MCP tools.

```bash
# Set your webhook secret (from Greenhouse settings)
export GREENHOUSE_WEBHOOK_SECRET=your-secret

# Start the receiver
open-greenhouse-mcp-receiver
```

Configure the webhook URL in Greenhouse to point to `http://your-host:8080/webhooks/greenhouse`.

Environment variables:

| Variable | Default | Description |
|---|---|---|
| `GREENHOUSE_WEBHOOK_SECRET` | Required | HMAC secret for verifying webhook signatures |
| `WEBHOOK_DB_PATH` | `~/.open-greenhouse-mcp/webhooks.db` | SQLite database location |
| `PORT` | `8080` | HTTP server port |

## Ingestion API

The Ingestion API lets you submit applications and prospects programmatically. It requires both `GREENHOUSE_API_KEY` and `GREENHOUSE_ON_BEHALF_OF`.

Tools: `post_candidate`, `post_tracking_link`, and read endpoints for jobs, prospects, users, and retrieval.

## Board-Token-Only Mode

If you only set `GREENHOUSE_BOARD_TOKEN` (no API key), the server automatically registers only the 13 Job Board tools. This is useful for public job board integrations that don't need Harvest API access.

## Authentication

| Credential | Access |
|---|---|
| `GREENHOUSE_API_KEY` | Full Harvest API, Ingestion API, Webhooks |
| `GREENHOUSE_BOARD_TOKEN` | Job Board API only (public, no auth required) |

Set at least one. Both can be configured simultaneously.

You can find your API key in Greenhouse under Configure > Dev Center > API Credential Management.

For development setup and contributing, see [docs/development.md](development.md).
