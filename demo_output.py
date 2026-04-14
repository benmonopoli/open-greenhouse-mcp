"""Print a clean demo output for GIF recording."""
import time
import sys


def slow_print(text, delay=0.02):
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(delay)
    print()


def section_pause():
    time.sleep(1.5)


def short_pause():
    time.sleep(0.08)


# --- Startup banner ---
print()
slow_print("open-greenhouse-mcp v0.3.1", 0.02)
slow_print("Profile: recruiter | Tools: 121 | Writes: recruiter-safe | APIs: harvest, ingestion", 0.008)
print()
section_pause()

# --- Scene 1: Talent rediscovery ---
slow_print('> "Search past candidates: backend engineers in London, experience at Stripe', 0.025)
slow_print('   or Monzo, Go or Rust, no junior profiles"', 0.025)
print()
section_pause()

lines1 = [
    "  Scanned 312 resumes across engineering roles",
    "",
    "  Rachel Torres — Senior Engineer (rejected at final, 2024)",
    "    Stripe, 4 years — Go microservices, distributed systems",
    "    London — rejected on timing, strong technical scores",
    "",
    "  James Liu — Platform Engineer (withdrawn, 2025)",
    "    Monzo, 3 years — Rust, event-driven architecture",
    "    London — withdrew for competing offer, may be available now",
    "",
    "  Priya Sharma — Backend Engineer (rejected, 2024)",
    "    Stripe, 5 years — Go, Kubernetes, API platform team",
    "    London — rejected: no headcount, not a skills issue",
    "",
    "  3 matches from your existing pipeline",
]

for line in lines1:
    slow_print(line, 0.008)
    short_pause()

print()
section_pause()

# --- Scene 2: Pipeline review ---
slow_print('> "Review the Senior Engineer pipeline — who should we prioritize?"', 0.025)
print()
section_pause()

lines2 = [
    "  Senior Engineer — 42 active candidates",
    "",
    "  Needs immediate action:",
    "    Kate D. — Offer stage, 773 days inactive — close or withdraw",
    "    Zach S. — Recruiter Screen, 67 days stale — schedule or reject",
    "",
    "  Strong prospects:",
    "    Sergey F. — Face to Face, strong scorecards, waiting on debrief",
    "    Ivan G. — Offer stage, 123 days — pending compensation approval",
    "",
    "  Recommendation: 27 in Application Review need triage.",
    "  15 have been waiting 30+ days with no activity.",
]

for line in lines2:
    slow_print(line, 0.008)
    short_pause()

print()
section_pause()

# --- Scene 3: Hiring report ---
slow_print('> "Give me a hiring report for Q1"', 0.025)
print()
section_pause()

lines3 = [
    "  Q1 2025 Hiring Summary",
    "",
    "  Hires: 14 across 8 roles",
    "  Avg time to hire: 47 days (down from 62 in Q4)",
    "  Top source: Referrals (6 hires, 8.2% conversion)",
    "  Bottleneck: Face to Face → Offer (avg 18 days, 3x other stages)",
    "",
    "  Fastest hire: Karandeep V. — Engineering, 12 days",
    "  Longest: Gleb P. — Senior Engineer, 94 days",
]

for line in lines3:
    slow_print(line, 0.008)
    short_pause()

print()
time.sleep(2.5)
