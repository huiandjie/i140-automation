from __future__ import annotations

import re
from typing import Any

from models import Address, FamilyMember, I140Data


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\x07", "").strip())


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


def _parse_signer(value: str) -> tuple[str, str]:
    value = _clean(value)
    if not value:
        return "", ""

    for sep in (" - ", " – ", " — ", ", "):
        if sep in value:
            name, title = value.split(sep, 1)
            return _clean(name), _clean(title)

    return value, ""


def _parse_us_address(raw: str) -> Address:
    raw = _clean(raw)
    if not raw:
        return Address()

    # Prefer Apt/Ste/Flr form so unit is not swallowed into street.
    apt_match = re.match(
        r"^(?P<street>.+?)\s+(?P<unit_type>Apt|Ste|Flr)\.?\s+(?P<apt>[^,]+),\s*"
        r"(?P<city>[^,]+),\s*(?P<state>[A-Z]{2})\s+(?P<zip>\d{5}(?:-\d{4})?)$",
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
        r"^(?P<street>.+?),\s*(?P<city>[^,]+),\s*(?P<state>[A-Z]{2})\s+(?P<zip>\d{5}(?:-\d{4})?)$",
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

    return Address(street=raw)


def _parse_birth_place(raw: str) -> tuple[str, str]:
    raw = _clean(raw)
    if not raw:
        return "", ""

    if "," in raw:
        city, country = raw.rsplit(",", 1)
        return _clean(city), _clean(country)

    return raw, ""


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


def _field_value(form_field: dict[str, Any]) -> str:
    result = str(form_field.get("result", "")).strip()
    if result == "$":
        return ""
    return result


def _checkbox_checked(form_field: dict[str, Any]) -> bool:
    return str(form_field.get("result", "0")) == "1"


def extract_from_word_fields(
    form_fields: list[dict[str, Any]],
    document_text: str,
) -> I140Data:
    data = I140Data()
    lines = [line.strip() for line in document_text.replace("\r", "\n").split("\n")]

    for line in lines:
        if line.lower().startswith("last name, first name:"):
            value = line.split(":", 1)[1].strip()
            if value:
                last, first, middle = _parse_name(value)
                data.last_name = last
                data.first_name = first
                data.middle_name = middle
            break

    premium_line = next(
        (line for line in lines if "premium processing" in line.lower()),
        "",
    )
    if premium_line:
        data.premium_processing = _parse_yes_no(premium_line)

    i140_line = next(
        (line for line in lines if "previously approved i-140" in line.lower()),
        "",
    )
    if i140_line:
        answered = _parse_yes_no(i140_line)
        data.previously_approved_i140 = answered
        # Word form wording says "approved"; PDF Part 4 Item 8 is "ever filed".
        data.prior_immigrant_petition_filed = answered

    indexed = {field["index"]: field for field in form_fields}

    wage = _field_value(indexed.get(1, {}))
    data.current_wage = wage.lstrip("$").strip()

    data.current_address = _parse_us_address(_field_value(indexed.get(2, {})))
    data.date_of_birth = _field_value(indexed.get(3, {}))
    data.ssn = _field_value(indexed.get(4, {}))
    data.i94_number = _field_value(indexed.get(5, {}))
    data.date_of_last_arrival = _field_value(indexed.get(6, {}))
    data.passport_number = _field_value(indexed.get(7, {}))
    data.passport_country = _field_value(indexed.get(8, {}))
    data.passport_expiration = _field_value(indexed.get(9, {}))
    data.birth_city_state = _field_value(indexed.get(10, {}))
    data.h1_expiration = _field_value(indexed.get(11, {}))
    if data.h1_expiration and not data.current_nonimmigrant_status:
        data.current_nonimmigrant_status = "H-1B"
    if data.passport_country:
        if not data.birth_country:
            data.birth_country = data.passport_country
        if not data.citizenship_country:
            data.citizenship_country = data.passport_country

    signer_name, signer_title = _parse_signer(_field_value(indexed.get(12, {})))
    data.signer_name = signer_name
    data.signer_title = signer_title
    data.company_address = _parse_us_address(_field_value(indexed.get(13, {})))

    spouse_name = _field_value(indexed.get(14, {}))
    if spouse_name:
        last, first, middle = _parse_name(spouse_name)
        relationship = "Wife" if _checkbox_checked(indexed.get(17, {})) else "Husband"
        if not _checkbox_checked(indexed.get(17, {})) and not _checkbox_checked(indexed.get(18, {})):
            relationship = "Spouse"
        data.spouse = FamilyMember(
            name=spouse_name,
            date_of_birth=_field_value(indexed.get(15, {})),
            place_of_birth=_field_value(indexed.get(16, {})),
            relationship=relationship,
        )

    child_blocks = [
        (19, 22, 23),
        (24, 27, 28),
        (29, 32, 33),
    ]
    for name_idx, dob_idx, pob_idx in child_blocks:
        child_name = _field_value(indexed.get(name_idx, {}))
        if not child_name:
            continue
        data.children.append(
            FamilyMember(
                name=child_name,
                date_of_birth=_field_value(indexed.get(dob_idx, {})),
                place_of_birth=_field_value(indexed.get(pob_idx, {})),
                relationship="Child",
            )
        )

    data.company_employees = _field_value(indexed.get(34, {}))
    data.company_gross_income = _field_value(indexed.get(35, {}))

    return data


def read_word_document(path: str) -> I140Data:
    import win32com.client

    word = win32com.client.Dispatch("Word.Application")
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
