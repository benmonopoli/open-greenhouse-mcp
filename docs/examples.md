# Usage Examples

Real conversations showing what you can ask and what comes back.

---

## "Show me the pipeline for the Senior Engineer role"

**Tool used:** `pipeline_summary`

```
Job: Senior Engineer
Active candidates: 42

Application Review (27)
  Chris A. — 48 days since activity
  Meghana T. — 41 days since activity
  Tom Z. — 39 days since activity
  ... 24 more

Recruiter Screen (5)
  Zach S. — 67 days since activity
  Wenhua L. — 125 days since activity
  Yiyun L. — 48 days since activity
  ... 2 more

Department Screen (4)
  Tzu-Chi L. — 216 days since activity
  Gabriel S. — 202 days since activity
  ... 2 more

Face to Face (1)
  Sergey F. — 118 days since activity

Offer (2)
  Kate D. — 773 days since activity
  Ivan G. — 123 days since activity
```

One call. No manual pagination. Names resolved automatically.

---

## "Find that candidate Sarah"

**Tool used:** `search_candidates_by_name`

```
Found 4 matches (scanned 2,500 candidates):

  Sarah Chen — sarah.chen@gmail.com — applied to Product Manager
  Sarah O'Brien — s.obrien@outlook.com — applied to Engineering Manager
  Sarah Kim — sarahkim@company.co — applied to Data Analyst
  Sarah Lopez — sarah.lopez@yahoo.com — prospect (no active application)
```

Searches by first name, last name, or full name. Case-insensitive substring match.

---

## "Which sources are actually producing hires?"

**Tool used:** `source_effectiveness`

```
Total applications: 3,241 from 12 sources

  LinkedIn            1,847 apps   63 hired   3.4% hire rate
  Referral              412 apps   28 hired   6.8% hire rate
  Indeed                389 apps    8 hired   2.1% hire rate
  Company Website       201 apps   12 hired   6.0% hire rate
  Greenhouse Event      145 apps    4 hired   2.8% hire rate
  ...7 more sources
```

Referrals have 2x the hire rate of LinkedIn. That's the kind of insight that changes budget allocation.

---

## "How long does it take us to hire?"

**Tool used:** `time_to_hire`

```
Total hires analyzed: 123

  Average:  164.9 days
  Median:   131 days
  Fastest:    3 days
  Slowest:  773 days

Recent hires:
  Patrick L. — 66 days (Product Manager)
  Karandeep V. — 43 days (Engineering)
  Gleb P. — 509 days (Senior Engineer)
```

---

## "What needs my attention?"

**Tool used:** `candidates_needing_action`

```
Stale applications (no activity in 7+ days): 1,477
Missing scorecards: 12

Top stale candidates:
  Philson C. — Test Task — 1,713 days inactive
  Isaac C. — Test Task — 1,713 days inactive
  John B. — (no stage) — 1,664 days inactive
  Blake P. — Recruiter Screen — 1,623 days inactive
  Anmar A. — Recruiter Screen — 1,623 days inactive

Missing scorecards:
  Interview: Technical Screen — scheduled 2025-01-15
    Missing from: Jane Smith, Mike Johnson
```

---

## "What are our conversion rates for the Senior Engineer role?"

**Tool used:** `pipeline_metrics`

```
Job: Senior Engineer
Total applications: 1,255

  Hired: 17 (1.4%)
  Rejected: 1,196 (95.3%)
  Active: 42 (3.3%)

Stage breakdown:
  Application Review    1,255 reached   100.0% of total   avg 89 days in pipeline
  Recruiter Screen        187 reached    14.9% of total   avg 203 days
  Department Screen        98 reached     7.8% of total   avg 267 days
  Face to Face             45 reached     3.6% of total   avg 312 days
  Offer                    22 reached     1.8% of total   avg 401 days
```

---

## "Reject all stale candidates from that old req"

**Tool used:** `stale_applications` then `bulk_reject`

First, find them:
```
> stale_applications(job_id=4065918004, days=90)

Found 15 stale applications (90+ days inactive):
  Kate D. — Offer — 773 days
  Tzu-Chi L. — Department Screen — 216 days
  Gabriel S. — Department Screen — 202 days
  ... 12 more
```

Then act:
```
> bulk_reject(application_ids=[...], rejection_reason_id=12345)

Rejected 15 applications:
  Succeeded: 15
  Failed: 0
```

Rate-limited to stay under Greenhouse's 50 req/10s limit.

---

## "Pull up this candidate's resume"

**Tool used:** `read_candidate_resume`

```
Candidate: Philson Co
File: Philson_Co_Resume.pdf (125 KB)
Content type: application/pdf
Content: [base64-encoded PDF data]
```

The AI assistant can then analyze the resume content directly — screening for skills, experience, or qualifications without leaving the conversation.
