# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in open-greenhouse-mcp, please report it responsibly by emailing **ben.monopoli@ahrefs.com**. Do not open a public issue.

You should receive a response within 48 hours. If the issue is confirmed, a fix will be released as soon as possible.

## Credentials

This project handles Greenhouse Harvest v3 OAuth credentials and webhook secrets. Key security considerations:

- **Never commit credentials.** Use environment variables or `.env` files (which are `.gitignore`d).
- **Harvest v3 uses OAuth 2.0 client credentials.** The client secret is only sent to `auth.greenhouse.io` (HTTP Basic, over HTTPS) to mint short-lived bearer tokens. Tokens are held in memory, refreshed before expiry, and never logged or written to disk.
- **Least privilege:** grant the Harvest V3 credential only the scopes for the tools you use, and start with the `read-only` profile.
- **Write attribution:** when `GREENHOUSE_USER_ID` is set, writes use a token minted for that user (`sub`), so Greenhouse records who made each change.
- **Webhook HMAC verification** is enforced by default. The receiver validates every incoming webhook against `GREENHOUSE_WEBHOOK_SECRET`.

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.5.x   | Yes       |
| < 0.5   | No — these use Harvest v1/v2, which Greenhouse retired on 31 Aug 2026 |
