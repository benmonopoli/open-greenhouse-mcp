"""Candidate location detection utilities.

Pure utility module — no Greenhouse API calls, no client parameter.
Provides a five-step cascade that extracts a candidate's location from
whatever data is available: screening answers → application → candidate
profile → resume text → phone dial code.
"""
from __future__ import annotations

import re
from typing import Any

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

_LOCATION_KEYWORDS: frozenset[str] = frozenset(
    {
        "location",
        "country",
        "where",
        "city",
        "based",
        "reside",
        "region",
        "state",
        "province",
        "address",
        "live",
        "living",
    }
)

# (dial_code_digits, country_name) — sorted longest-first so that, e.g.,
# "+234" (Nigeria) is tested before "+2" (Egypt) and wins correctly.
_DIAL_CODES: list[tuple[str, str]] = sorted(
    [
        ("1", "United States / Canada"),
        ("7", "Russia / Kazakhstan"),
        ("20", "Egypt"),
        ("27", "South Africa"),
        ("30", "Greece"),
        ("31", "Netherlands"),
        ("32", "Belgium"),
        ("33", "France"),
        ("34", "Spain"),
        ("36", "Hungary"),
        ("39", "Italy"),
        ("40", "Romania"),
        ("41", "Switzerland"),
        ("43", "Austria"),
        ("44", "United Kingdom"),
        ("45", "Denmark"),
        ("46", "Sweden"),
        ("47", "Norway"),
        ("48", "Poland"),
        ("49", "Germany"),
        ("51", "Peru"),
        ("52", "Mexico"),
        ("54", "Argentina"),
        ("55", "Brazil"),
        ("56", "Chile"),
        ("57", "Colombia"),
        ("60", "Malaysia"),
        ("61", "Australia"),
        ("62", "Indonesia"),
        ("63", "Philippines"),
        ("64", "New Zealand"),
        ("65", "Singapore"),
        ("66", "Thailand"),
        ("81", "Japan"),
        ("82", "South Korea"),
        ("84", "Vietnam"),
        ("86", "China"),
        ("90", "Turkey"),
        ("91", "India"),
        ("92", "Pakistan"),
        ("94", "Sri Lanka"),
        ("98", "Iran"),
        ("212", "Morocco"),
        ("213", "Algeria"),
        ("216", "Tunisia"),
        ("218", "Libya"),
        ("220", "Gambia"),
        ("221", "Senegal"),
        ("222", "Mauritania"),
        ("223", "Mali"),
        ("224", "Guinea"),
        ("225", "Ivory Coast"),
        ("226", "Burkina Faso"),
        ("227", "Niger"),
        ("228", "Togo"),
        ("229", "Benin"),
        ("230", "Mauritius"),
        ("231", "Liberia"),
        ("232", "Sierra Leone"),
        ("233", "Ghana"),
        ("234", "Nigeria"),
        ("235", "Chad"),
        ("236", "Central African Republic"),
        ("237", "Cameroon"),
        ("238", "Cape Verde"),
        ("239", "São Tomé and Príncipe"),
        ("240", "Equatorial Guinea"),
        ("241", "Gabon"),
        ("242", "Republic of the Congo"),
        ("243", "DR Congo"),
        ("244", "Angola"),
        ("245", "Guinea-Bissau"),
        ("246", "British Indian Ocean Territory"),
        ("248", "Seychelles"),
        ("249", "Sudan"),
        ("250", "Rwanda"),
        ("251", "Ethiopia"),
        ("252", "Somalia"),
        ("253", "Djibouti"),
        ("254", "Kenya"),
        ("255", "Tanzania"),
        ("256", "Uganda"),
        ("257", "Burundi"),
        ("258", "Mozambique"),
        ("260", "Zambia"),
        ("261", "Madagascar"),
        ("262", "Réunion"),
        ("263", "Zimbabwe"),
        ("264", "Namibia"),
        ("265", "Malawi"),
        ("266", "Lesotho"),
        ("267", "Botswana"),
        ("268", "Eswatini"),
        ("269", "Comoros"),
        ("290", "Saint Helena"),
        ("291", "Eritrea"),
        ("297", "Aruba"),
        ("298", "Faroe Islands"),
        ("299", "Greenland"),
        ("350", "Gibraltar"),
        ("351", "Portugal"),
        ("352", "Luxembourg"),
        ("353", "Ireland"),
        ("354", "Iceland"),
        ("355", "Albania"),
        ("356", "Malta"),
        ("357", "Cyprus"),
        ("358", "Finland"),
        ("359", "Bulgaria"),
        ("370", "Lithuania"),
        ("371", "Latvia"),
        ("372", "Estonia"),
        ("373", "Moldova"),
        ("374", "Armenia"),
        ("375", "Belarus"),
        ("376", "Andorra"),
        ("377", "Monaco"),
        ("378", "San Marino"),
        ("380", "Ukraine"),
        ("381", "Serbia"),
        ("382", "Montenegro"),
        ("383", "Kosovo"),
        ("385", "Croatia"),
        ("386", "Slovenia"),
        ("387", "Bosnia and Herzegovina"),
        ("389", "North Macedonia"),
        ("420", "Czech Republic"),
        ("421", "Slovakia"),
        ("423", "Liechtenstein"),
        ("500", "Falkland Islands"),
        ("501", "Belize"),
        ("502", "Guatemala"),
        ("503", "El Salvador"),
        ("504", "Honduras"),
        ("505", "Nicaragua"),
        ("506", "Costa Rica"),
        ("507", "Panama"),
        ("508", "Saint Pierre and Miquelon"),
        ("509", "Haiti"),
        ("590", "Guadeloupe"),
        ("591", "Bolivia"),
        ("592", "Guyana"),
        ("593", "Ecuador"),
        ("595", "Paraguay"),
        ("596", "Martinique"),
        ("597", "Suriname"),
        ("598", "Uruguay"),
        ("599", "Netherlands Antilles"),
        ("670", "East Timor"),
        ("672", "Norfolk Island"),
        ("673", "Brunei"),
        ("674", "Nauru"),
        ("675", "Papua New Guinea"),
        ("676", "Tonga"),
        ("677", "Solomon Islands"),
        ("678", "Vanuatu"),
        ("679", "Fiji"),
        ("680", "Palau"),
        ("681", "Wallis and Futuna"),
        ("682", "Cook Islands"),
        ("683", "Niue"),
        ("685", "Samoa"),
        ("686", "Kiribati"),
        ("687", "New Caledonia"),
        ("688", "Tuvalu"),
        ("689", "French Polynesia"),
        ("690", "Tokelau"),
        ("691", "Micronesia"),
        ("692", "Marshall Islands"),
        ("850", "North Korea"),
        ("852", "Hong Kong"),
        ("853", "Macau"),
        ("855", "Cambodia"),
        ("856", "Laos"),
        ("880", "Bangladesh"),
        ("886", "Taiwan"),
        ("960", "Maldives"),
        ("961", "Lebanon"),
        ("962", "Jordan"),
        ("963", "Syria"),
        ("964", "Iraq"),
        ("965", "Kuwait"),
        ("966", "Saudi Arabia"),
        ("967", "Yemen"),
        ("968", "Oman"),
        ("970", "Palestinian Territory"),
        ("971", "United Arab Emirates"),
        ("972", "Israel"),
        ("973", "Bahrain"),
        ("974", "Qatar"),
        ("975", "Bhutan"),
        ("976", "Mongolia"),
        ("977", "Nepal"),
        ("992", "Tajikistan"),
        ("993", "Turkmenistan"),
        ("994", "Azerbaijan"),
        ("995", "Georgia"),
        ("996", "Kyrgyzstan"),
        ("998", "Uzbekistan"),
    ],
    key=lambda pair: len(pair[0]),
    reverse=True,
)

_RESUME_LOCATION_PATTERN: re.Pattern[str] = re.compile(
    r"(?:based\s+in|locate[d]?\s+in|location\s*:\s*|city\s*:\s*|address\s*:\s*)"
    r"\s*([A-Z][a-zA-Z\s,]+)",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Step 1 — screening answers
# ---------------------------------------------------------------------------


def detect_location_from_answers(
    answers: list[dict[str, Any]],
) -> tuple[str | None, str]:
    """Scan application screening Q&A for location-related questions.

    Returns (answer_text, source_label) for the first match where the question
    contains a location keyword and the answer is non-empty.  Returns
    (None, "") if no match is found.
    """
    for entry in answers:
        question: str = str(entry.get("question") or "")
        answer: str = str(entry.get("answer") or "")
        if not answer.strip():
            continue
        question_lower = question.lower()
        if any(kw in question_lower for kw in _LOCATION_KEYWORDS):
            return answer, f"screening_answer: {question}"
    return None, ""


# ---------------------------------------------------------------------------
# Step 2 — application object
# ---------------------------------------------------------------------------


def detect_location_from_application(
    application: dict[str, Any],
) -> tuple[str | None, str]:
    """Extract location from the Greenhouse application object.

    The ``location`` field can be a dict with an ``"address"`` key or a plain
    string.  Returns (location_string, "application_location") or (None, "").
    """
    raw = application.get("location")
    if raw is None:
        return None, ""

    if isinstance(raw, dict):
        address: str = str(raw.get("address") or "")
        if address.strip():
            return address, "application_location"
        return None, ""

    text = str(raw).strip()
    if text:
        return text, "application_location"
    return None, ""


# ---------------------------------------------------------------------------
# Step 3 — candidate profile addresses
# ---------------------------------------------------------------------------


def detect_location_from_candidate(
    candidate: dict[str, Any],
) -> tuple[str | None, str]:
    """Extract location from the candidate's addresses list.

    Each address is expected to be a ``{"value": "...", "type": "..."}`` dict.
    Returns the first non-empty value with a source like
    ``"candidate_address (home)"``, or (None, "").
    """
    for addr in candidate.get("addresses", []):
        value: str = str(addr.get("value") or "").strip()
        if value:
            addr_type: str = str(addr.get("type") or "")
            source = f"candidate_address ({addr_type})" if addr_type else "candidate_address"
            return value, source
    return None, ""


# ---------------------------------------------------------------------------
# Step 4 — resume text
# ---------------------------------------------------------------------------


def detect_location_from_resume(
    resume_text: str,
) -> tuple[str | None, str]:
    """Scan the first 2 000 characters of resume text for location patterns.

    Recognised patterns: "Based in X", "Located in X", "Location: X",
    "City: X", "Address: X".  Returns (matched_text, "resume_text") or
    (None, "").
    """
    if not resume_text:
        return None, ""

    snippet = resume_text[:2000]
    match = _RESUME_LOCATION_PATTERN.search(snippet)
    if match:
        return match.group(1).strip(), "resume_text"
    return None, ""


# ---------------------------------------------------------------------------
# Step 5 — phone dial code
# ---------------------------------------------------------------------------


def detect_location_from_phone(
    phone_numbers: list[dict[str, Any]],
) -> tuple[str | None, str]:
    """Infer country from a phone number's international dial code.

    Strips all non-digit characters (and leading zeros) from each phone value,
    then tests against *_DIAL_CODES* sorted longest-first so that longer
    prefixes always win over shorter ambiguous ones.

    Returns (country_name, f"phone_dial_code (+{code})") or (None, "").
    """
    for phone in phone_numbers:
        raw: str = str(phone.get("value") or "")
        # Strip everything that isn't a digit or a leading '+'
        digits = re.sub(r"[^\d]", "", raw)
        digits = digits.lstrip("0")
        if not digits:
            continue
        for code, country in _DIAL_CODES:
            if digits.startswith(code):
                return country, f"phone_dial_code (+{code})"
    return None, ""


# ---------------------------------------------------------------------------
# Cascade orchestrator
# ---------------------------------------------------------------------------


def detect_candidate_location(
    application: dict[str, Any],
    candidate: dict[str, Any],
    answers: list[dict[str, Any]] | None = None,
    resume_text: str = "",
) -> dict[str, Any]:
    """Run the five-step location cascade and return the first match.

    Priority order (highest to lowest):
      1. Screening answers    → confidence "high"
      2. Application location → confidence "high"
      3. Candidate addresses  → confidence "high"
      4. Resume text          → confidence "medium"
      5. Phone dial code      → confidence "low"

    Returns a dict::

        {
            "location": str | None,
            "source": str,
            "confidence": "high" | "medium" | "low" | "none",
        }
    """
    # Step 1 — answers
    if answers is not None:
        loc, source = detect_location_from_answers(answers)
        if loc:
            return {"location": loc, "source": source, "confidence": "high"}

    # Step 2 — application
    loc, source = detect_location_from_application(application)
    if loc:
        return {"location": loc, "source": source, "confidence": "high"}

    # Step 3 — candidate addresses
    loc, source = detect_location_from_candidate(candidate)
    if loc:
        return {"location": loc, "source": source, "confidence": "high"}

    # Step 4 — resume text
    loc, source = detect_location_from_resume(resume_text)
    if loc:
        return {"location": loc, "source": source, "confidence": "medium"}

    # Step 5 — phone dial code
    phone_numbers: list[dict[str, Any]] = candidate.get("phone_numbers", [])
    loc, source = detect_location_from_phone(phone_numbers)
    if loc:
        return {"location": loc, "source": source, "confidence": "low"}

    return {"location": None, "source": "", "confidence": "none"}
