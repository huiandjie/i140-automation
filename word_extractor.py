from __future__ import annotations

import re
from typing import Any

from models import Address, FamilyMember, I140Data

# USPS abbreviations. Full names show up on the newer info questionnaire.
_STATE_BY_NAME = {
    "ALABAMA": "AL",
    "ALASKA": "AK",
    "ARIZONA": "AZ",
    "ARKANSAS": "AR",
    "CALIFORNIA": "CA",
    "COLORADO": "CO",
    "CONNECTICUT": "CT",
    "DELAWARE": "DE",
    "DISTRICT OF COLUMBIA": "DC",
    "FLORIDA": "FL",
    "GEORGIA": "GA",
    "HAWAII": "HI",
    "IDAHO": "ID",
    "ILLINOIS": "IL",
    "INDIANA": "IN",
    "IOWA": "IA",
    "KANSAS": "KS",
    "KENTUCKY": "KY",
    "LOUISIANA": "LA",
    "MAINE": "ME",
    "MARYLAND": "MD",
    "MASSACHUSETTS": "MA",
    "MICHIGAN": "MI",
    "MINNESOTA": "MN",
    "MISSISSIPPI": "MS",
    "MISSOURI": "MO",
    "MONTANA": "MT",
    "NEBRASKA": "NE",
    "NEVADA": "NV",
    "NEW HAMPSHIRE": "NH",
    "NEW JERSEY": "NJ",
    "NEW MEXICO": "NM",
    "NEW YORK": "NY",
    "NORTH CAROLINA": "NC",
    "NORTH DAKOTA": "ND",
    "OHIO": "OH",
    "OKLAHOMA": "OK",
    "OREGON": "OR",
    "PENNSYLVANIA": "PA",
    "RHODE ISLAND": "RI",
    "SOUTH CAROLINA": "SC",
    "SOUTH DAKOTA": "SD",
    "TENNESSEE": "TN",
    "TEXAS": "TX",
    "UTAH": "UT",
    "VERMONT": "VT",
    "VIRGINIA": "VA",
    "WASHINGTON": "WA",
    "WEST VIRGINIA": "WV",
    "WISCONSIN": "WI",
    "WYOMING": "WY",
}
_STATE_ABBREV = set(_STATE_BY_NAME.values())

_STREET_SUFFIXES = {
    "ALY",
    "AVE",
    "AVENUE",
    "BLVD",
    "BOULEVARD",
    "CIR",
    "CIRCLE",
    "CT",
    "COURT",
    "DR",
    "DRIVE",
    "HWY",
    "HIGHWAY",
    "LN",
    "LANE",
    "PKWY",
    "PARKWAY",
    "PL",
    "PLACE",
    "RD",
    "ROAD",
    "ST",
    "STREET",
    "TER",
    "TERRACE",
    "TRL",
    "TRAIL",
    "WAY",
}

# Last token of a birth-place line. US state names stay in city/state.
_COUNTRIES = {
    "ARGENTINA",
    "AUSTRALIA",
    "BANGLADESH",
    "BRAZIL",
    "BURMA",
    "CAMBODIA",
    "CANADA",
    "CHILE",
    "CHINA",
    "COLOMBIA",
    "EGYPT",
    "ENGLAND",
    "ETHIOPIA",
    "FRANCE",
    "GERMANY",
    "GHANA",
    "HONG KONG",
    "INDIA",
    "INDONESIA",
    "IRAN",
    "ITALY",
    "JAPAN",
    "KENYA",
    "KOREA",
    "LAOS",
    "MALAYSIA",
    "MEXICO",
    "MYANMAR",
    "NEPAL",
    "NEW ZEALAND",
    "NIGERIA",
    "NORTH KOREA",
    "PAKISTAN",
    "PERU",
    "PHILIPPINES",
    "RUSSIA",
    "SINGAPORE",
    "SOUTH KOREA",
    "SPAIN",
    "SRI LANKA",
    "TAIWAN",
    "THAILAND",
    "TURKEY",
    "UK",
    "UKRAINE",
    "UNITED KINGDOM",
    "UNITED STATES",
    "US",
    "USA",
    "VENEZUELA",
    "VIETNAM",
}

_MONTHS = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}

_PERSON_RE = re.compile(
    r"Family\s+Name\s*:?\s*(?P<last>.+?)\s+First\s+Name\s*:?\s*(?P<first>.+?)"
    r"\s+Middle\s+Name\s*:?\s*(?P<middle>.*)$",
    re.IGNORECASE,
)


def _clean(value: str) -> str:
    value = (
        value.replace("\x07", " ")
        .replace("\x15", " ")
        .replace("\u2002", " ")
        .replace("\xa0", " ")
        .replace("_", " ")
    )
    return re.sub(r"\s+", " ", value).strip(" \t.:")


def _normalize_line(line: str) -> str:
    return _clean(line.replace("\r", " "))


def _parse_name(full_name: str) -> tuple[str, str, str]:
    full_name = _clean(full_name)
    if not full_name:
        return "", "", ""

    if "," in full_name:
        last, rest = full_name.split(",", 1)
        parts = _clean(rest).split()
        first = parts[0] if parts else ""
        middle = " ".join(parts[1:]) if len(parts) > 1 else ""
        return _clean(last), first, middle

    parts = full_name.split()
    if len(parts) == 1:
        return parts[0], "", ""
    if len(parts) == 2:
        return parts[1], parts[0], ""
    return parts[-1], parts[0], " ".join(parts[1:-1])


def _parse_labeled_person(line: str) -> tuple[str, str, str] | None:
    match = _PERSON_RE.search(_normalize_line(line))
    if not match:
        return None
    last = _clean(match.group("last"))
    first = _clean(match.group("first"))
    middle = _clean(match.group("middle"))
    if not last and not first:
        return None
    return last, first, middle


def _format_person(last: str, first: str, middle: str) -> str:
    """'Last, First, Middle' so a multi-word given name is not split later."""
    if last and first and middle:
        return f"{last}, {first}, {middle}"
    if last and first:
        return f"{last}, {first}"
    return last or first or middle


def _parse_signer(value: str) -> tuple[str, str]:
    value = _clean(value)
    if not value:
        return "", ""

    for sep in (" - ", " – ", " — ", ", "):
        if sep in value:
            name, title = value.split(sep, 1)
            return _clean(name), _clean(title)

    return value, ""


def _normalize_state(token: str) -> str:
    key = re.sub(r"\s+", " ", token).strip(" .").upper()
    if key in _STATE_ABBREV:
        return key
    return _STATE_BY_NAME.get(key, "")


def _split_trailing_state(text: str) -> tuple[str, str]:
    words = text.split()
    if not words:
        return "", ""
    for size in (3, 2, 1):
        if len(words) <= size:
            continue
        state = _normalize_state(" ".join(words[-size:]))
        if state:
            return " ".join(words[:-size]), state
    return text, ""


def _split_street_city(text: str) -> tuple[str, str, str, str]:
    text = text.strip(" ,")
    if not text:
        return "", "", "", ""

    if "," in text:
        street, city = text.rsplit(",", 1)
        return _clean(street), _clean(city), "", ""

    tokens = text.split()
    suffix_at = -1
    for index, token in enumerate(tokens):
        if token.upper().rstrip(".") in _STREET_SUFFIXES:
            suffix_at = index
    if suffix_at < 0 or suffix_at == len(tokens) - 1:
        return text, "", "", ""

    rest = tokens[suffix_at + 1 :]
    unit_type = ""
    apt = ""
    if rest and rest[0].upper().rstrip(".") in {"APT", "STE", "FLR"}:
        unit_type = {"APT": "Apt", "STE": "Ste", "FLR": "Flr"}[rest[0].upper().rstrip(".")]
        if len(rest) > 1:
            apt = rest[1].strip(",")
            rest = rest[2:]
        else:
            rest = []
    street = " ".join(tokens[: suffix_at + 1])
    city = " ".join(rest)
    return street, city, unit_type, apt


def _parse_us_address(raw: str) -> Address:
    raw = _clean(raw)
    if not raw:
        return Address()

    # Prefer Apt/Ste/Flr form so unit is not swallowed into street.
    apt_match = re.match(
        r"^(?P<street>.+?)\s+(?P<unit_type>Apt|Ste|Flr)\.?\s+(?P<apt>[^,]+),\s*"
        r"(?P<city>[^,]+),\s*(?P<state>[A-Za-z]{2})\s+(?P<zip>\d{5}(?:-\d{4})?)$",
        raw,
        re.IGNORECASE,
    )
    if apt_match:
        return Address(
            street=apt_match.group("street"),
            unit_type=apt_match.group("unit_type").title(),
            apt=apt_match.group("apt").strip(),
            city=apt_match.group("city").strip(),
            state=apt_match.group("state").upper(),
            zip_code=apt_match.group("zip"),
        )

    match = re.match(
        r"^(?P<street>.+?),\s*(?P<city>[^,]+),\s*(?P<state>[A-Za-z]{2})\s+(?P<zip>\d{5}(?:-\d{4})?)$",
        raw,
        re.IGNORECASE,
    )
    if match:
        return Address(
            street=match.group("street"),
            city=match.group("city").strip(),
            state=match.group("state").upper(),
            zip_code=match.group("zip"),
        )

    zip_match = re.search(r"(?P<zip>\d{5}(?:-\d{4})?)\s*$", raw)
    if not zip_match:
        return Address(street=raw)

    left, state = _split_trailing_state(raw[: zip_match.start()].strip(" ,"))
    if not state:
        return Address(street=raw)

    street, city, unit_type, apt = _split_street_city(left)
    return Address(
        street=street or left,
        unit_type=unit_type,
        apt=apt,
        city=city,
        state=state,
        zip_code=zip_match.group("zip"),
    )


def _split_birth(raw: str) -> tuple[str, str]:
    """Return (city or city/state, country). Country is set only when recognized."""
    raw = _clean(raw)
    if not raw:
        return "", ""

    if "," in raw:
        left, right = raw.rsplit(",", 1)
        if right.strip().upper() in _COUNTRIES:
            return left.strip(), right.strip()
        return raw, ""

    parts = raw.split()
    if len(parts) >= 3 and " ".join(parts[-2:]).upper() in _COUNTRIES:
        return " ".join(parts[:-2]), " ".join(parts[-2:])
    if len(parts) >= 2 and parts[-1].upper() in _COUNTRIES:
        return " ".join(parts[:-1]), parts[-1]
    return raw, ""


def _format_place(raw: str) -> str:
    city, country = _split_birth(raw)
    if city and country:
        return f"{city}, {country}"
    return city or _clean(raw)


def _fmt_date(month: int, day: int, year: int) -> str:
    if year < 100:
        year += 1900 if year >= 50 else 2000
    return f"{month:02d}/{day:02d}/{year:04d}"


def _normalize_date(value: str) -> str:
    value = _clean(value)
    if not value:
        return ""

    numeric = re.search(r"(\d{1,2})/(\d{1,2})/(\d{2,4})", value)
    if numeric:
        return _fmt_date(int(numeric.group(1)), int(numeric.group(2)), int(numeric.group(3)))

    written = re.search(
        r"\b("
        r"jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|"
        r"jun(?:e)?|jul(?:y)?|aug(?:ust)?|"
        r"sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?"
        r")\.?,?\s+(\d{1,2}),?\s+(\d{4})\b",
        value,
        re.IGNORECASE,
    )
    if written:
        month = _MONTHS[written.group(1).lower().rstrip(".")]
        return _fmt_date(month, int(written.group(2)), int(written.group(3)))
    return value


def _parse_yes_no(line: str) -> bool | None:
    if re.search(r"yes\b[^\n]*[xX✓/]", line, re.IGNORECASE):
        return True
    if re.search(r"no\b[^\n]*[xX✓/]", line, re.IGNORECASE):
        return False
    if re.search(r":\s*yes\s*$", line, re.IGNORECASE):
        return True
    if re.search(r":\s*no\s*$", line, re.IGNORECASE):
        return False
    return None


def _parse_premium(line: str) -> bool | None:
    lower = line.lower()
    if "do you want premium processing" in lower:
        return _parse_yes_no(line)

    tail = ""
    fee = re.search(r"charged by USCIS\.?\s*(.*)$", line, re.IGNORECASE)
    if fee:
        tail = _clean(fee.group(1)).lower()
    elif "?" in line:
        tail = _clean(line.split("?")[-1]).lower()
    if tail in {"regular", "regular processing"}:
        return False
    if tail in {"premium", "premium processing"}:
        return True
    return None


def _parse_prior(line: str) -> bool | None:
    if ":" in line:
        tail = _clean(line.split(":")[-1]).lower()
        if tail in {"yes", "y"}:
            return True
        if tail in {"no", "n"}:
            return False
    return _parse_yes_no(line)


def _parse_wage(raw: str) -> tuple[str, str]:
    text = _clean(raw).lstrip("$").strip()
    period = "year"
    period_match = re.search(r"\bper\s+(hour|week|month|year|annum)\b", text, re.IGNORECASE)
    if period_match:
        word = period_match.group(1).lower()
        period = "year" if word == "annum" else word
        text = text[: period_match.start()]
    elif re.search(r"\bhourly\b", text, re.IGNORECASE):
        period = "hour"
    amount_match = re.search(r"\d+(?:\.\d+)?", text.replace(",", ""))
    amount = amount_match.group(0) if amount_match else ""
    return amount, period


def _parse_i94(raw: str) -> str:
    raw = _clean(raw)
    if not raw:
        return ""
    token = re.split(r"[\s,]+", raw)[0].strip(".")
    if re.fullmatch(r"\d{9,11}(?:[A-Za-z]\d{0,2})?", token):
        return token
    match = re.search(r"\d{9,11}(?:[A-Za-z]\d{0,2})?", raw)
    return match.group(0) if match else ""


def _value_after(lines: list[str], pattern: str) -> str:
    compiled = re.compile(pattern, re.IGNORECASE)
    for line in lines:
        match = compiled.search(line)
        if not match:
            continue
        value = match.group(1) if match.lastindex else line[match.end() :]
        cleaned = _clean(value)
        if cleaned:
            return cleaned
    return ""


def _document_lines(document_text: str) -> list[str]:
    lines = []
    for line in document_text.replace("\r", "\n").split("\n"):
        normalized = _normalize_line(line)
        if normalized:
            lines.append(normalized)
    return lines


def _header_lines(lines: list[str]) -> list[str]:
    header = []
    for line in lines:
        if "family member information" in line.lower():
            break
        header.append(line)
    return header


def _family_chunks(lines: list[str]) -> list[list[str]]:
    start = None
    for index, line in enumerate(lines):
        if "family member information" in line.lower():
            start = index + 1
            break
    if start is None:
        return []

    chunks: list[list[str]] = []
    current: list[str] = []
    for line in lines[start:]:
        lower = line.lower()
        if lower.startswith("note:") or lower.startswith("note ") or lower.startswith("company"):
            break
        if re.match(r"name of each child\b", line, re.IGNORECASE):
            if current:
                chunks.append(current)
            current = [line]
            continue
        current.append(line)
    if current:
        chunks.append(current)
    return chunks


def _chunk_value(chunk: list[str], pattern: str) -> str:
    return _value_after(chunk, pattern)


def _person_from_chunk(chunk: list[str]) -> tuple[str, str, str]:
    for line in chunk:
        labeled = _parse_labeled_person(line)
        if labeled:
            return labeled
    name_line = _value_after(chunk, r"Name of each(?:\s+Child)?\s*:?\s*(.*)$")
    if name_line and not re.match(r"family name\b", name_line, re.IGNORECASE):
        return _parse_name(name_line)
    return "", "", ""


def _spouse_relationship(form_fields: list[dict[str, Any]]) -> str:
    wife = False
    husband = False
    for field in form_fields:
        if int(field.get("type") or 0) != 71:
            continue
        context = _normalize_line(str(field.get("context", ""))).lower()
        checked = str(field.get("result", "0")).strip() == "1"
        if "wife" in context and "husband" not in context:
            wife = wife or checked
        elif "husband" in context and "wife" not in context:
            husband = husband or checked
    if wife and not husband:
        return "Wife"
    if husband and not wife:
        return "Husband"
    return "Spouse"


def _fill_beneficiary(data: I140Data, header: list[str]) -> None:
    for line in header:
        labeled = _parse_labeled_person(line)
        if labeled:
            data.last_name, data.first_name, data.middle_name = labeled
            break
    if not data.last_name and not data.first_name:
        legacy = _value_after(header, r"Last name,\s*First name:\s*(.*)$")
        if legacy:
            data.last_name, data.first_name, data.middle_name = _parse_name(legacy)
    if not data.last_name and not data.first_name:
        employee = _value_after(header, r"^Employee:\s*(.*)$")
        if employee:
            data.last_name, data.first_name, data.middle_name = _parse_name(employee)

    for line in header:
        if "premium processing" in line.lower():
            data.premium_processing = _parse_premium(line)
            break

    for line in header:
        lower = line.lower()
        if "previously approved i-140" in lower or "previous i-140" in lower:
            answered = _parse_prior(line)
            data.previously_approved_i140 = answered
            data.prior_immigrant_petition_filed = answered
            break

    wage_raw = _value_after(header, r"Your current wage:\s*(.*)$")
    if wage_raw:
        data.current_wage, data.wage_per = _parse_wage(wage_raw)

    data.current_address = _parse_us_address(
        _value_after(header, r"Your current address:\s*(.*)$")
    )
    data.date_of_birth = _normalize_date(
        _value_after(header, r"Date of Birth:\s*(.*)$")
    )
    data.ssn = _value_after(header, r"Your Social Security#\s*(.*)$")
    data.date_of_last_arrival = _normalize_date(
        _value_after(header, r"Date of Last Arrival[^:]*:\s*(.*)$")
    )
    data.i94_number = _parse_i94(
        _value_after(header, r"Most recent I-94[^:]*:\s*(.*)$")
    )
    data.h1_expiration = _normalize_date(
        _value_after(header, r"H-1 Expiration Date:\s*(.*)$")
    )
    if data.h1_expiration and not data.current_nonimmigrant_status:
        data.current_nonimmigrant_status = "H-1B"

    passport_line = next(
        (line for line in header if re.search(r"passport", line, re.IGNORECASE)),
        "",
    )
    if passport_line:
        issued = re.search(
            r"Passport\s*#\s*(.*?)\s*;\s*Country issued\s*(.*)$",
            passport_line,
            re.IGNORECASE,
        )
        if issued:
            data.passport_number = _clean(issued.group(1))
            data.passport_country = _clean(issued.group(2))
        elif re.search(r"passport\s*(?:number|#)", passport_line, re.IGNORECASE):
            data.passport_number = _value_after(
                [passport_line],
                r"(?:Your\s+)?Passport(?:\s+Number)?\s*#?\s*:?\s*(.*)$",
            )

    data.passport_expiration = _normalize_date(
        _value_after(header, r"Expiration date of your passport:\s*(.*)$")
        or _value_after(header, r"^Expiration date\s+(.*)$")
    )

    birth_raw = _value_after(
        header, r"City/Town/Village[^:]*Birth:\s*(.*)$"
    )
    birth_city, birth_country = _split_birth(birth_raw)
    data.birth_city_state = birth_city
    if birth_country:
        data.birth_country = birth_country
    if data.passport_country:
        if not data.birth_country:
            data.birth_country = data.passport_country
        if not data.citizenship_country:
            data.citizenship_country = data.passport_country

    signer_name, signer_title = _parse_signer(
        _value_after(header, r"Name and title who is to sign papers:\s*(.*)$")
    )
    data.signer_name = signer_name
    data.signer_title = signer_title
    data.company_address = _parse_us_address(
        _value_after(header, r"Company.s current address:\s*(.*)$")
    )


def _fill_company_totals(data: I140Data, lines: list[str]) -> None:
    for line in lines:
        match = re.search(
            r"number of employees\s*(.*?)\s*,\s*company.s gross income\s*(.*)$",
            line,
            re.IGNORECASE,
        )
        if not match:
            continue
        data.company_employees = _clean(match.group(1))
        data.company_gross_income = _clean(match.group(2)).lstrip("$")
        break


def _fill_family(data: I140Data, lines: list[str], form_fields: list[dict[str, Any]]) -> None:
    chunks = _family_chunks(lines)
    if not chunks:
        return

    relationship = _spouse_relationship(form_fields)
    spouse_chunk = chunks[0]
    if not re.match(r"name of each child\b", spouse_chunk[0], re.IGNORECASE):
        last, first, middle = _person_from_chunk(spouse_chunk)
        name = _format_person(last, first, middle)
        if name:
            data.spouse = FamilyMember(
                name=name,
                date_of_birth=_normalize_date(
                    _chunk_value(spouse_chunk, r"Date of birth:\s*(.*)$")
                ),
                place_of_birth=_format_place(
                    _chunk_value(
                        spouse_chunk, r"Place of birth \(city and country\):\s*(.*)$"
                    )
                ),
                relationship=relationship,
            )
        child_chunks = chunks[1:]
    else:
        child_chunks = chunks

    for chunk in child_chunks:
        last, first, middle = _person_from_chunk(chunk)
        name = _format_person(last, first, middle)
        if not name:
            continue
        data.children.append(
            FamilyMember(
                name=name,
                date_of_birth=_normalize_date(
                    _chunk_value(chunk, r"Date of birth:\s*(.*)$")
                ),
                place_of_birth=_format_place(
                    _chunk_value(chunk, r"Place of birth \(city and country\):\s*(.*)$")
                ),
                relationship="Child",
            )
        )


def extract_from_word_fields(
    form_fields: list[dict[str, Any]],
    document_text: str,
) -> I140Data:
    """Read either info-questionnaire layout.

    The original form stores answers in a fixed FormField order. Later copies
    type the same answers into the paragraph (sometimes removing those fields)
    and use a different field order, so values are taken from labels in the
    document text. Checkboxes are still read from form fields.
    """
    data = I140Data()
    lines = _document_lines(document_text)
    _fill_beneficiary(data, _header_lines(lines))
    _fill_company_totals(data, lines)
    _fill_family(data, lines, form_fields)
    return data


def read_word_document(path: str) -> I140Data:
    import win32com.client

    word = win32com.client.DispatchEx("Word.Application")
    word.Visible = False
    word.DisplayAlerts = 0

    try:
        doc = word.Documents.Open(
            path,
            ConfirmConversions=False,
            ReadOnly=True,
            AddToRecentFiles=False,
        )
        document_text = doc.Content.Text
        form_fields: list[dict[str, Any]] = []

        for i in range(1, doc.FormFields.Count + 1):
            ff = doc.FormFields(i)
            context = ""
            try:
                context = ff.Range.Paragraphs(1).Range.Text
            except Exception:
                pass

            form_fields.append(
                {
                    "index": i,
                    "name": ff.Name,
                    "type": ff.Type,
                    "result": str(ff.Result),
                    "context": context.replace("\r", " ").replace("\x07", "").strip(),
                }
            )

        doc.Close(False)
    finally:
        word.Quit()

    return extract_from_word_fields(form_fields, document_text)
