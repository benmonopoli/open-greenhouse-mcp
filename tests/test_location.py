"""Tests for the candidate location detection module."""
from __future__ import annotations

# ---------------------------------------------------------------------------
# detect_location_from_answers
# ---------------------------------------------------------------------------

def test_answers_finds_location_keyword() -> None:
    from greenhouse_mcp.location import detect_location_from_answers

    answers = [
        {"question": "What is your current location?", "answer": "London, UK"},
    ]
    loc, source = detect_location_from_answers(answers)
    assert loc == "London, UK"
    assert source == "screening_answer: What is your current location?"


def test_answers_finds_country_keyword() -> None:
    from greenhouse_mcp.location import detect_location_from_answers

    answers = [
        {"question": "Which country do you live in?", "answer": "Germany"},
    ]
    loc, source = detect_location_from_answers(answers)
    assert loc == "Germany"
    assert "country" in source or "screening_answer" in source


def test_answers_skips_non_location_question() -> None:
    from greenhouse_mcp.location import detect_location_from_answers

    answers = [
        {"question": "Why do you want this role?", "answer": "Berlin, Germany"},
    ]
    loc, source = detect_location_from_answers(answers)
    assert loc is None
    assert source == ""


def test_answers_skips_empty_answer() -> None:
    from greenhouse_mcp.location import detect_location_from_answers

    answers = [
        {"question": "Where are you based?", "answer": ""},
        {"question": "Where do you live?", "answer": "Singapore"},
    ]
    loc, source = detect_location_from_answers(answers)
    assert loc == "Singapore"


def test_answers_empty_list() -> None:
    from greenhouse_mcp.location import detect_location_from_answers

    loc, source = detect_location_from_answers([])
    assert loc is None
    assert source == ""


def test_answers_all_empty_answers() -> None:
    from greenhouse_mcp.location import detect_location_from_answers

    answers = [
        {"question": "Where are you based?", "answer": ""},
    ]
    loc, source = detect_location_from_answers(answers)
    assert loc is None
    assert source == ""


def test_answers_keyword_case_insensitive() -> None:
    from greenhouse_mcp.location import detect_location_from_answers

    answers = [
        {"question": "Current CITY of residence?", "answer": "Tokyo"},
    ]
    loc, source = detect_location_from_answers(answers)
    assert loc == "Tokyo"


# ---------------------------------------------------------------------------
# detect_location_from_application
# ---------------------------------------------------------------------------

def test_application_dict_location() -> None:
    from greenhouse_mcp.location import detect_location_from_application

    application = {"location": {"address": "New York, NY"}}
    loc, source = detect_location_from_application(application)
    assert loc == "New York, NY"
    assert source == "application_location"


def test_application_string_location() -> None:
    from greenhouse_mcp.location import detect_location_from_application

    application = {"location": "Paris, France"}
    loc, source = detect_location_from_application(application)
    assert loc == "Paris, France"
    assert source == "application_location"


def test_application_missing_location() -> None:
    from greenhouse_mcp.location import detect_location_from_application

    loc, source = detect_location_from_application({})
    assert loc is None
    assert source == ""


def test_application_null_location() -> None:
    from greenhouse_mcp.location import detect_location_from_application

    loc, source = detect_location_from_application({"location": None})
    assert loc is None
    assert source == ""


def test_application_empty_address() -> None:
    from greenhouse_mcp.location import detect_location_from_application

    loc, source = detect_location_from_application({"location": {"address": ""}})
    assert loc is None
    assert source == ""


def test_application_dict_no_address_key() -> None:
    from greenhouse_mcp.location import detect_location_from_application

    loc, source = detect_location_from_application({"location": {}})
    assert loc is None
    assert source == ""


# ---------------------------------------------------------------------------
# detect_location_from_candidate
# ---------------------------------------------------------------------------

def test_candidate_first_address() -> None:
    from greenhouse_mcp.location import detect_location_from_candidate

    candidate = {
        "addresses": [
            {"value": "123 Main St, Austin, TX", "type": "home"},
        ]
    }
    loc, source = detect_location_from_candidate(candidate)
    assert loc == "123 Main St, Austin, TX"
    assert "home" in source


def test_candidate_skips_empty_values() -> None:
    from greenhouse_mcp.location import detect_location_from_candidate

    candidate = {
        "addresses": [
            {"value": "", "type": "home"},
            {"value": "Toronto, Canada", "type": "work"},
        ]
    }
    loc, source = detect_location_from_candidate(candidate)
    assert loc == "Toronto, Canada"
    assert "work" in source


def test_candidate_no_addresses() -> None:
    from greenhouse_mcp.location import detect_location_from_candidate

    candidate = {"addresses": []}
    loc, source = detect_location_from_candidate(candidate)
    assert loc is None
    assert source == ""


def test_candidate_missing_addresses_key() -> None:
    from greenhouse_mcp.location import detect_location_from_candidate

    loc, source = detect_location_from_candidate({})
    assert loc is None
    assert source == ""


def test_candidate_all_empty_addresses() -> None:
    from greenhouse_mcp.location import detect_location_from_candidate

    candidate = {
        "addresses": [
            {"value": "", "type": "home"},
            {"value": "  ", "type": "work"},
        ]
    }
    loc, source = detect_location_from_candidate(candidate)
    assert loc is None
    assert source == ""


# ---------------------------------------------------------------------------
# detect_location_from_resume
# ---------------------------------------------------------------------------

def test_resume_based_in_pattern() -> None:
    from greenhouse_mcp.location import detect_location_from_resume

    text = "John Smith\nBased in San Francisco, CA\nSoftware Engineer"
    loc, source = detect_location_from_resume(text)
    assert loc is not None
    assert "San Francisco" in loc
    assert source == "resume_text"


def test_resume_location_colon_pattern() -> None:
    from greenhouse_mcp.location import detect_location_from_resume

    text = "Jane Doe\nLocation: Berlin, Germany\nProduct Manager"
    loc, source = detect_location_from_resume(text)
    assert loc is not None
    assert "Berlin" in loc
    assert source == "resume_text"


def test_resume_located_in_pattern() -> None:
    from greenhouse_mcp.location import detect_location_from_resume

    text = "Located in Sydney, Australia"
    loc, source = detect_location_from_resume(text)
    assert loc is not None
    assert "Sydney" in loc


def test_resume_city_colon_pattern() -> None:
    from greenhouse_mcp.location import detect_location_from_resume

    text = "City: Mumbai"
    loc, source = detect_location_from_resume(text)
    assert loc is not None
    assert "Mumbai" in loc


def test_resume_address_colon_pattern() -> None:
    from greenhouse_mcp.location import detect_location_from_resume

    # Pattern requires match to start with [A-Z]; use a letter-starting address
    text = "Address: Baker Street, London"
    loc, source = detect_location_from_resume(text)
    assert loc is not None
    assert "Baker" in loc or "London" in loc


def test_resume_no_match() -> None:
    from greenhouse_mcp.location import detect_location_from_resume

    text = "John Smith\nSoftware Engineer\n10 years experience"
    loc, source = detect_location_from_resume(text)
    assert loc is None
    assert source == ""


def test_resume_empty_text() -> None:
    from greenhouse_mcp.location import detect_location_from_resume

    loc, source = detect_location_from_resume("")
    assert loc is None
    assert source == ""


def test_resume_only_scans_first_2000_chars() -> None:
    from greenhouse_mcp.location import detect_location_from_resume

    # Put location keyword only beyond 2000 chars
    padding = "x" * 2001
    text = padding + "\nBased in Remote City"
    loc, source = detect_location_from_resume(text)
    assert loc is None


def test_resume_finds_match_within_first_2000_chars() -> None:
    from greenhouse_mcp.location import detect_location_from_resume

    # Put location keyword within first 2000 chars, plus trailing garbage
    text = "Based in Chicago, IL\n" + "x" * 3000
    loc, source = detect_location_from_resume(text)
    assert loc is not None
    assert "Chicago" in loc


# ---------------------------------------------------------------------------
# detect_location_from_phone
# ---------------------------------------------------------------------------

def test_phone_uk_code() -> None:
    from greenhouse_mcp.location import detect_location_from_phone

    phones = [{"value": "+44 7911 123456", "type": "mobile"}]
    loc, source = detect_location_from_phone(phones)
    assert loc == "United Kingdom"
    assert "+44" in source


def test_phone_india_code() -> None:
    from greenhouse_mcp.location import detect_location_from_phone

    phones = [{"value": "+919876543210", "type": "mobile"}]
    loc, source = detect_location_from_phone(phones)
    assert loc == "India"
    assert "+91" in source


def test_phone_singapore_code() -> None:
    from greenhouse_mcp.location import detect_location_from_phone

    phones = [{"value": "+6512345678", "type": "mobile"}]
    loc, source = detect_location_from_phone(phones)
    assert loc == "Singapore"
    assert "+65" in source


def test_phone_nigeria_code() -> None:
    from greenhouse_mcp.location import detect_location_from_phone

    phones = [{"value": "+2348012345678", "type": "mobile"}]
    loc, source = detect_location_from_phone(phones)
    assert loc == "Nigeria"
    assert "+234" in source


def test_phone_no_phones() -> None:
    from greenhouse_mcp.location import detect_location_from_phone

    loc, source = detect_location_from_phone([])
    assert loc is None
    assert source == ""


def test_phone_empty_value() -> None:
    from greenhouse_mcp.location import detect_location_from_phone

    phones = [{"value": "", "type": "mobile"}]
    loc, source = detect_location_from_phone(phones)
    assert loc is None
    assert source == ""


def test_phone_longer_code_wins() -> None:
    """Nigeria (+234) should win over a shorter prefix (+2) if one existed."""
    from greenhouse_mcp.location import detect_location_from_phone

    # +234 is Nigeria; a naive match might grab +2 (Egypt) first if not sorted longest-first
    phones = [{"value": "+2348012345678", "type": "mobile"}]
    loc, source = detect_location_from_phone(phones)
    assert loc == "Nigeria"


def test_phone_us_canada_code() -> None:
    from greenhouse_mcp.location import detect_location_from_phone

    phones = [{"value": "+12025551234", "type": "mobile"}]
    loc, source = detect_location_from_phone(phones)
    # +1 covers US/Canada — accept either
    assert loc in ("United States / Canada", "United States", "Canada", "US/Canada")


# ---------------------------------------------------------------------------
# detect_candidate_location (cascade)
# ---------------------------------------------------------------------------

def test_cascade_answers_win_over_all() -> None:
    from greenhouse_mcp.location import detect_candidate_location

    application = {"location": {"address": "New York"}}
    candidate = {"addresses": [{"value": "Berlin", "type": "home"}], "phone_numbers": []}
    answers = [{"question": "Where are you based?", "answer": "Tokyo"}]
    result = detect_candidate_location(application, candidate, answers=answers)
    assert result["location"] == "Tokyo"
    assert result["source"].startswith("screening_answer")
    assert result["confidence"] == "high"


def test_cascade_application_wins_over_candidate() -> None:
    from greenhouse_mcp.location import detect_candidate_location

    application = {"location": "Sydney"}
    candidate = {"addresses": [{"value": "Mumbai", "type": "home"}], "phone_numbers": []}
    result = detect_candidate_location(application, candidate)
    assert result["location"] == "Sydney"
    assert result["source"] == "application_location"
    assert result["confidence"] == "high"


def test_cascade_candidate_wins_over_resume() -> None:
    from greenhouse_mcp.location import detect_candidate_location

    application = {}
    candidate = {"addresses": [{"value": "Lagos", "type": "home"}], "phone_numbers": []}
    result = detect_candidate_location(
        application, candidate, resume_text="Based in Cairo, Egypt"
    )
    assert result["location"] == "Lagos"
    assert result["confidence"] == "high"


def test_cascade_resume_wins_over_phone() -> None:
    from greenhouse_mcp.location import detect_candidate_location

    application = {}
    candidate = {
        "addresses": [],
        "phone_numbers": [{"value": "+44 7911 000000", "type": "mobile"}],
    }
    result = detect_candidate_location(
        application, candidate, resume_text="Based in Amsterdam, Netherlands"
    )
    assert result["location"] is not None
    assert "Amsterdam" in result["location"]
    assert result["confidence"] == "medium"


def test_cascade_phone_fallback() -> None:
    from greenhouse_mcp.location import detect_candidate_location

    application = {}
    candidate = {
        "addresses": [],
        "phone_numbers": [{"value": "+919876543210", "type": "mobile"}],
    }
    result = detect_candidate_location(application, candidate)
    assert result["location"] == "India"
    assert result["confidence"] == "low"


def test_cascade_no_data() -> None:
    from greenhouse_mcp.location import detect_candidate_location

    result = detect_candidate_location({}, {"addresses": [], "phone_numbers": []})
    assert result["location"] is None
    assert result["confidence"] == "none"
    assert result["source"] == ""


def test_cascade_none_answers_handled() -> None:
    from greenhouse_mcp.location import detect_candidate_location

    application = {"location": "Berlin"}
    candidate = {"addresses": [], "phone_numbers": []}
    # answers=None (default) should not raise
    result = detect_candidate_location(application, candidate, answers=None)
    assert result["location"] == "Berlin"
    assert result["confidence"] == "high"
