# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in open-greenhouse-mcp, please report it responsibly by emailing **ben.monopoli@ahrefs.com**. Do not open a public issue.

You should receive a response within 48 hours. If the issue is confirmed, a fix will be released as soon as possible.

## Credentials

This project handles Greenhouse API keys and webhook secrets. Key security considerations:

- **Never commit API keys.** Use environment variables or `.env` files (which are `.gitignore`d).
- **Webhook HMAC verification** is enforced by default. The receiver validates every incoming webhook against `GREENHOUSE_WEBHOOK_SECRET`.
- **API keys are sent via HTTP Basic Auth** over HTTPS only (enforced by the Greenhouse API).
- **The `On-Behalf-Of` header** is included on all write operations for audit trail purposes.

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.2.x   | Yes       |
| < 0.2   | No        |
