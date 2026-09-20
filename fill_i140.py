#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from models import Address, FamilyMember, I140Data
from pdf_filler import build_pdf_field_map, fill_pdf
from word_extractor import read_word_document


def _address_from_dict(raw: dict | None) -> Address:
    if not raw:
        return Address()
    return Address(
        street=raw.get("street", ""),
        apt=raw.get("apt", ""),
        unit_type=raw.get("unit_type", ""),
        city=raw.get("city", ""),
        state=raw.get("state", ""),
        zip_code=raw.get("zip_code", ""),
        country=raw.get("country", "United States"),
    )


def _member_from_dict(raw: dict | None) -> FamilyMember | None:
    if not raw:
        return None
    return FamilyMember(
        name=raw.get("name", ""),
        date_of_birth=raw.get("date_of_birth", ""),
        place_of_birth=raw.get("place_of_birth", ""),
        relationship=raw.get("relationship", ""),
    )


def load_json_data(path: str) -> I140Data:
    with open(path, encoding="utf-8") as handle:
        raw = json.load(handle)

    return I140Data(
        last_name=raw.get("last_name", ""),
        first_name=raw.get("first_name", ""),
        middle_name=raw.get("middle_name", ""),
        current_wage=raw.get("current_wage", ""),
        premium_processing=raw.get("premium_processing"),
        previously_approved_i140=raw.get("previously_approved_i140"),
        prior_immigrant_petition_filed=raw.get("prior_immigrant_petition_filed"),
        current_address=_address_from_dict(raw.get("current_address")),
        date_of_birth=raw.get("date_of_birth", ""),
        ssn=raw.get("ssn", ""),
        i94_number=raw.get("i94_number", ""),
        date_of_last_arrival=raw.get("date_of_last_arrival", ""),
        passport_number=raw.get("passport_number", ""),
        passport_country=raw.get("passport_country", ""),
        passport_expiration=raw.get("passport_expiration", ""),
        birth_city_state=raw.get("birth_city_state", ""),
        birth_country=raw.get("birth_country", ""),
        citizenship_country=raw.get("citizenship_country", ""),
        h1_expiration=raw.get("h1_expiration", ""),
        current_nonimmigrant_status=raw.get("current_nonimmigrant_status", ""),
        signer_name=raw.get("signer_name", ""),
        signer_title=raw.get("signer_title", ""),
        company_name=raw.get("company_name", ""),
        company_ein=raw.get("company_ein", ""),
        company_address=_address_from_dict(raw.get("company_address")),
        spouse=_member_from_dict(raw.get("spouse")),
        children=[
            member
            for child in raw.get("children", [])
            if (member := _member_from_dict(child)) is not None
        ],
        company_employees=raw.get("company_employees", ""),
        company_gross_income=raw.get("company_gross_income", ""),
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Populate USCIS Form I-140 from a filled Word information document."
    )
    parser.add_argument(
        "--word",
        help="Path to the filled 1-140 info Word document (.doc or .docx)",
    )
    parser.add_argument(
        "--json",
        help="Optional JSON file with the same data instead of Word input",
    )
    parser.add_argument(
        "--pdf-template",
        default=r"C:\Users\266753\Downloads\i-140-uscis.pdf",
        help="Path to the blank I-140 PDF template",
    )
    parser.add_argument(
        "--output",
        default=r"C:\Users\266753\Downloads\i-140-filled.pdf",
        help="Path for the filled output PDF",
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Print the PDF field mapping without writing a file",
    )
    args = parser.parse_args()

    if not args.word and not args.json:
        parser.error("Provide --word or --json")

    if args.json:
        data = load_json_data(args.json)
    else:
        data = read_word_document(args.word)

    field_map = build_pdf_field_map(data)

    if args.preview:
        print(json.dumps(field_map, indent=2))
        return 0

    fill_pdf(args.pdf_template, args.output, data)
    print(f"Created: {args.output}")
    print(f"Mapped {len(field_map)} PDF fields")
    if args.word:
        print(f"Source: {args.word}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
