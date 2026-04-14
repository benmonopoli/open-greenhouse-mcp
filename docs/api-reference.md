# API Reference

Full tool breakdown by category and API surface.

## Harvest API (148 tools)

| Category | Tools | Category | Tools |
|---|---|---|---|
| Candidates | 15 | Applications | 14 |
| Jobs | 4 | Job Posts | 7 |
| Job Stages | 3 | Job Openings | 5 |
| Offers | 5 | Scorecards | 3 |
| Interviews | 6 | Users | 8 |
| User Permissions | 6 | User Roles | 1 |
| Departments | 4 | Offices | 4 |
| Custom Fields | 9 | Sources | 1 |
| Rejection Reasons | 1 | Email Templates | 2 |
| Tags | 6 | Activity Feed | 1 |
| EEOC | 2 | Demographics | 11 |
| Approvals | 6 | Hiring Team | 4 |
| Prospect Pools | 2 | Close Reasons | 1 |
| Tracking Links | 1 | Education | 3 |

## Job Board API (13 tools)

List boards, jobs, posts, departments, offices, and questions from public job boards. Only requires `GREENHOUSE_BOARD_TOKEN`.

## Ingestion API (6 tools)

Submit applications and prospects programmatically. Requires `GREENHOUSE_API_KEY` and `GREENHOUSE_ON_BEHALF_OF`.

## Webhook Management (8 tools)

Create, list, update, and delete webhook subscriptions. Query received events with filtering.

## Tool Profiles

Not all tools are available in every profile:

| Profile | Composite | Harvest Read | Harvest Write | Job Board | Ingestion | Webhooks |
|---|---|---|---|---|---|---|
| `full` | All 13 | All | All | All | All | All |
| `recruiter` | All 13 | All | Recruiter-safe | All | None | Read-only |
| `read-only` | All 13 | All | None | Read-only | None | Read-only |

See the main [README](../README.md) for profile configuration.
