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

The Ingestion API lets you submit applications and prospects programmatically. It is separate from Harvest and uses its own key: set `GREENHOUSE_INGESTION_API_KEY`, plus `GREENHOUSE_USER_ID` for the `On-Behalf-Of` user the Ingestion API requires.

Tools: `post_candidate`, `post_tracking_link`, and read endpoints for jobs, prospects, users, and retrieval.

## Board-Token-Only Mode

If you only set `GREENHOUSE_BOARD_TOKEN` (no Harvest credentials), the Job Board tools work and Harvest tools return a "credentials not configured" error. This is useful for public job board integrations that don't need Harvest API access. Submitting applications through the board also needs `GREENHOUSE_BOARD_API_KEY`.

## Authentication

| Credential | Access |
|---|---|
| `GREENHOUSE_CLIENT_ID` + `GREENHOUSE_CLIENT_SECRET` | Harvest v3 API (OAuth 2.0 client credentials) |
| `GREENHOUSE_USER_ID` | Optional. Writes are made as this user; derives the tool profile from their role |
| `GREENHOUSE_BOARD_TOKEN` | Job Board API reads (public, no auth required) |
| `GREENHOUSE_BOARD_API_KEY` | Job Board application submission |
| `GREENHOUSE_INGESTION_API_KEY` | Ingestion API |

Set Harvest credentials and/or a board token. They can be combined.

### Creating Harvest v3 credentials

1. In Greenhouse: **Configure > Dev Center > API Credentials > Create new API credentials**.
2. Choose **Harvest V3 (OAuth)**. Copy the client ID and client secret (the secret is shown once).
3. Grant the scopes for the tools you plan to use (e.g. `harvest:candidates:list`, `harvest:applications:move`). Missing scopes surface as a 403 from the tool that needs them.

### How tokens are used

The server mints short-lived tokens from `https://auth.greenhouse.io/token`:

- **Reads** use a token for the credential's integration service user. Greenhouse requires Site Admin authorization for v3 list endpoints, so reads work even when `GREENHOUSE_USER_ID` belongs to a recruiter.
- **Writes** use a token minted with `sub=GREENHOUSE_USER_ID` when it is set, so Greenhouse attributes the change to that person. Without it, writes are made as the service user.

Tokens are cached in memory and refreshed before they expire (or after a 401).

### Migrating from 0.4 and earlier (Harvest v1/v2)

Greenhouse retired Harvest v1/v2 on 31 Aug 2026, so `GREENHOUSE_API_KEY` no longer works. Create Harvest V3 (OAuth) credentials as above, replace `GREENHOUSE_API_KEY` with `GREENHOUSE_CLIENT_ID` and `GREENHOUSE_CLIENT_SECRET`, and revoke the old key. `GREENHOUSE_ON_BEHALF_OF` still works as an alias for `GREENHOUSE_USER_ID`. List tools now take a `cursor` (from the previous response's `next_cursor`) instead of `page`.

For development setup and contributing, see [docs/development.md](development.md).
