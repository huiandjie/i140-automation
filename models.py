from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Address:
    street: str = ""
    apt: str = ""
    unit_type: str = ""  # Apt, Ste, Flr
    city: str = ""
    state: str = ""
    zip_code: str = ""
    country: str = "United States"


@dataclass
class FamilyMember:
    name: str = ""
    date_of_birth: str = ""
    place_of_birth: str = ""
    relationship: str = ""


@dataclass
class I140Data:
    last_name: str = ""
    first_name: str = ""
    middle_name: str = ""
    current_wage: str = ""
    # year, hour, week, or month — I-140 "per" for the wage offered
    wage_per: str = "year"
    premium_processing: bool | None = None
    previously_approved_i140: bool | None = None
    # PDF Part 4 Item 8: "Has any immigrant visa petition ever been filed..."
    prior_immigrant_petition_filed: bool | None = None
    current_address: Address = field(default_factory=Address)
    date_of_birth: str = ""
    ssn: str = ""
    i94_number: str = ""
    date_of_last_arrival: str = ""
    passport_number: str = ""
    passport_country: str = ""
    passport_expiration: str = ""
    birth_city_state: str = ""
    birth_country: str = ""
    citizenship_country: str = ""
    # I-94 / H-1 authorized stay expiration (mm/dd/yyyy)
    h1_expiration: str = ""
    # Form I-94 status, e.g. H-1B
    current_nonimmigrant_status: str = ""
    signer_name: str = ""
    signer_title: str = ""
    company_name: str = ""
    company_ein: str = ""
    company_address: Address = field(default_factory=Address)
    spouse: FamilyMember | None = None
    children: list[FamilyMember] = field(default_factory=list)
    company_employees: str = ""
    company_gross_income: str = ""
