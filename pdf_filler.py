from __future__ import annotations

import re
from typing import Any

from models import Address, FamilyMember, I140Data


PDF_PREFIX = "form1[0]"

# Unit checkbox on-states (trailing/leading spaces are significant).
_UNIT_ON = {
    "Ste": ("0", "/ STE "),
    "Flr": ("1", "/ FLR "),
    "Apt": ("2", "/ APT "),
}


def _unit_checkbox_fields(prefix: str, unit_field: str, unit_type: str) -> dict[str, str]:
    mapping = _UNIT_ON.get(unit_type.title())
    if not mapping:
        return {}
    index, on_value = mapping
    return {f"{prefix}.{unit_field}[{index}]": on_value}


def _beneficiary_addr_fields(address: Address) -> dict[str, str]:
    prefix = f"{PDF_PREFIX}.#subform[1]"
    fields: dict[str, str] = {}
    if address.street:
        fields[f"{prefix}.Line2b_StreetNumberName[0]"] = address.street
    if address.apt:
        fields[f"{prefix}.Line2c_AptSteFlrNumber[0]"] = address.apt
    fields.update(_unit_checkbox_fields(prefix, "Line2c_Unit", address.unit_type))
    if address.city:
        fields[f"{prefix}.Line2d_CityOrTown[0]"] = address.city
    if address.state:
        fields[f"{prefix}.Line2e_State[0]"] = address.state
    if address.zip_code:
        fields[f"{prefix}.Line2f_ZipCode[0]"] = address.zip_code
    country = address.country or "United States"
    fields[f"{prefix}.Line2i_Country[0]"] = (
        "USA" if country.lower() in {"united states", "usa", "us"} else country
    )
    return fields


def _company_addr_fields(address: Address) -> dict[str, str]:
    """Petitioner mailing address — Part 1 (not foreign address on Part 4)."""
    if not any([address.street, address.city, address.state, address.zip_code]):
        return {}

    prefix = f"{PDF_PREFIX}.#subform[0]"
    fields: dict[str, str] = {}
    if address.street:
        fields[f"{prefix}.Line6b_StreetNumberName[0]"] = address.street
    if address.apt:
        fields[f"{prefix}.Line6c_AptSteFlrNumber[0]"] = address.apt
    fields.update(_unit_checkbox_fields(prefix, "Line6c_Unit", address.unit_type))
    if address.city:
        fields[f"{prefix}.Line6d_CityOrTown[0]"] = address.city
    if address.state:
        fields[f"{prefix}.Line6e_State[0]"] = address.state
    if address.zip_code:
        fields[f"{prefix}.Line6f_ZipCode[0]"] = address.zip_code
    country = address.country or "United States"
    fields[f"{prefix}.Line6i_Country[0]"] = (
        "USA" if country.lower() in {"united states", "usa", "us"} else country
    )
    return fields


def _split_birth_city_state(value: str) -> tuple[str, str]:
    value = value.strip()
    if not value:
        return "", ""
    if "," in value:
        city, state = value.rsplit(",", 1)
        return city.strip(), state.strip()
    return value, ""


def _parse_signer(value: str) -> tuple[str, str]:
    value = value.strip()
    if not value:
        return "", ""

    for sep in (" - ", " – ", " — ", ", "):
        if sep in value:
            name, title = value.split(sep, 1)
            return name.strip(), title.strip()

    return value, ""


def _parse_member_name(name: str) -> tuple[str, str, str]:
    if "," in name:
        last, rest = name.split(",", 1)
        parts = rest.strip().split()
        first = parts[0] if parts else ""
        middle = " ".join(parts[1:]) if len(parts) > 1 else ""
        return last.strip(), first, middle

    parts = name.split()
    if len(parts) <= 1:
        return parts[0] if parts else "", "", ""
    return parts[-1], parts[0], " ".join(parts[1:-1])


def _dependent_fields(
    member: FamilyMember,
    person_index: int,
) -> dict[str, str]:
    last, first, middle = _parse_member_name(member.name)
    birth_city, birth_country = member.place_of_birth, ""
    if "," in member.place_of_birth:
        birth_city, birth_country = member.place_of_birth.rsplit(",", 1)
        birth_city = birth_city.strip()
        birth_country = birth_country.strip()

    if person_index == 0:
        prefix = f"{PDF_PREFIX}.#subform[3]"
        return {
            f"{prefix}.Line1a_Person1FamilyName[0]": last,
            f"{prefix}.Line1b_Person1GivenName[0]": first,
            f"{prefix}.Line1c_Person1MiddleName[0]": middle,
            f"{prefix}.Line1d_Person1DateOfBirth[0]": member.date_of_birth,
            f"{prefix}.Line1e_CountryOfBirth[0]": birth_country or birth_city,
            f"{prefix}.Line1f_Relationship[0]": member.relationship,
        }

    if person_index == 1:
        prefix = f"{PDF_PREFIX}.#subform[3]"
        return {
            f"{prefix}.Line2a_Person2FamilyName[0]": last,
            f"{prefix}.Line2b_Person2GivenName[0]": first,
            f"{prefix}.Line2c_Person2MiddleName[0]": middle,
            f"{prefix}.Line2d_DateOfBirth[0]": member.date_of_birth,
            f"{prefix}.Line2e_CountryOfBirth[0]": birth_country or birth_city,
            f"{prefix}.Line2f_Relationship[0]": member.relationship,
        }

    suffix = person_index - 1
    prefix = f"{PDF_PREFIX}.#subform[4]"
    return {
        f"{prefix}.Line2a_Person2FamilyName[{suffix}]": last,
        f"{prefix}.Line2b_Person2GivenName[{suffix}]": first,
        f"{prefix}.Line2c_Person2MiddleName[{suffix}]": middle,
        f"{prefix}.Line2d_DateOfBirth[{suffix}]": member.date_of_birth,
        f"{prefix}.Line2e_CountryOfBirth[{suffix}]": birth_country or birth_city,
        f"{prefix}.Line2f_Relationship[{suffix}]": member.relationship,
    }


def _normalize_ssn(value: str) -> str:
    return re.sub(r"\D", "", value)


def _format_money(value: str) -> str:
    raw = value.replace(",", "").strip().lstrip("$")
    if not raw:
        return ""
    try:
        return f"{float(raw):.2f}"
    except ValueError:
        return raw


def build_pdf_field_map(data: I140Data) -> dict[str, Any]:
    fields: dict[str, Any] = {}
    beneficiary = f"{PDF_PREFIX}.#subform[1]"
    petitioner = f"{PDF_PREFIX}.#subform[0]"

    fields[f"{beneficiary}.Pt3Line1a_FamilyName[0]"] = data.last_name
    fields[f"{beneficiary}.Pt3Line1b_GivenName[0]"] = data.first_name
    fields[f"{beneficiary}.Pt3Line1c_MiddleName[0]"] = data.middle_name
    fields[f"{beneficiary}.Line5_DateOfBirth[0]"] = data.date_of_birth
    fields[f"{beneficiary}.Line12_SSN[0]"] = _normalize_ssn(data.ssn)
    fields[f"{beneficiary}.Line13_DateOArrival[0]"] = data.date_of_last_arrival
    fields[
        f"{beneficiary}.Line14_I94Number[0].Line14a_ArrivalDeparture[0]"
    ] = data.i94_number
    fields[f"{beneficiary}.Line14b_Passport[0]"] = data.passport_number
    fields[f"{beneficiary}.Line14d_CountryOfIssuance[0]"] = data.passport_country
    # Passport expiration
    fields[f"{beneficiary}.Line14e_ExpDate[0]"] = data.passport_expiration
    # I-94 authorized stay expiration
    fields[f"{beneficiary}.Line14e_ExpDate[1]"] = data.h1_expiration
    # I-94 status (e.g. H-1B), not the expiration date
    status = data.current_nonimmigrant_status
    if not status and data.h1_expiration:
        status = "H-1B"
    fields[f"{beneficiary}.Line15_CurrentNon[0]"] = status

    birth_city, birth_state = _split_birth_city_state(data.birth_city_state)
    fields[f"{beneficiary}.Line6_CityTownOfBirth[0]"] = birth_city
    fields[f"{beneficiary}.Line7_StateProvinceOfBirth[0]"] = birth_state
    fields[f"{beneficiary}.Line8_Country[0]"] = (
        data.birth_country or data.passport_country
    )
    fields[f"{beneficiary}.Line9_Country[0]"] = (
        data.citizenship_country or data.passport_country
    )

    fields.update(_beneficiary_addr_fields(data.current_address))

    if data.current_wage:
        fields[f"{PDF_PREFIX}.#subform[3].Line8_Wages[0]"] = _format_money(
            data.current_wage
        )
        fields[f"{PDF_PREFIX}.#subform[3].Line8_Per[0]"] = "year"

    if data.company_name:
        fields[f"{petitioner}.Line2_CompanyName[0]"] = data.company_name
    if data.company_ein:
        fields[f"{petitioner}.Pt1Line3_TaxNumber[0]"] = re.sub(
            r"\D", "", data.company_ein
        )

    if data.company_employees:
        fields[f"{PDF_PREFIX}.#subform[2].Line2c_NumberofEmployees[0]"] = (
            data.company_employees
        )
    if data.company_gross_income:
        fields[f"{PDF_PREFIX}.#subform[2].Line2d_GrossAnnualIncome[0]"] = (
            _format_money(data.company_gross_income)
        )

    fields.update(_company_addr_fields(data.company_address))

    if data.signer_name:
        signer_name = data.signer_name
        signer_title = data.signer_title
        if not signer_title:
            signer_name, signer_title = _parse_signer(data.signer_name)
        signer_last, signer_first, _ = _parse_member_name(signer_name)
        fields[f"{PDF_PREFIX}.#subform[5].Part7_Item3a_FamilyName[0]"] = signer_last
        fields[f"{PDF_PREFIX}.#subform[5].Part7_Item3b_GivenName[0]"] = signer_first
        fields[f"{PDF_PREFIX}.#subform[5].Part7_Item4_Title[0]"] = signer_title

    prior_filed = data.prior_immigrant_petition_filed
    if prior_filed is None:
        prior_filed = data.previously_approved_i140
    if prior_filed is True:
        fields[f"{PDF_PREFIX}.#subform[2].Line6_Yes[0]"] = "/Y"
    elif prior_filed is False:
        fields[f"{PDF_PREFIX}.#subform[2].Line6_No[0]"] = "/N"

    dependents: list[FamilyMember] = []
    if data.spouse:
        dependents.append(data.spouse)
    dependents.extend(data.children)

    for index, member in enumerate(dependents[:6]):
        fields.update(_dependent_fields(member, index))

    return {key: value for key, value in fields.items() if value}


def fill_pdf(template_path: str, output_path: str, data: I140Data) -> dict[str, Any]:
    from pypdf import PdfReader, PdfWriter
    from pypdf.generic import BooleanObject, NameObject

    field_map = build_pdf_field_map(data)
    reader = PdfReader(template_path)
    writer = PdfWriter()
    writer.append(reader)

    # NeedAppearances asks the viewer to redraw field values.
    for page in writer.pages:
        writer.update_page_form_field_values(
            page,
            field_map,
            auto_regenerate=True,
        )

    # USCIS I-140 is an XFA hybrid. Adobe/web viewers often render the empty
    # XFA layer instead of AcroForm /V values, so strip XFA after filling.
    acro_form = writer._root_object.get("/AcroForm")
    if acro_form is not None:
        acro_form = acro_form.get_object()
        if NameObject("/XFA") in acro_form:
            del acro_form[NameObject("/XFA")]
        acro_form[NameObject("/NeedAppearances")] = BooleanObject(True)

    with open(output_path, "wb") as output_file:
        writer.write(output_file)

    return field_map
