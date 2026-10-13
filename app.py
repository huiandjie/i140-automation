#!/usr/bin/env python3
"""Gradio UI for filling USCIS Form I-140 from a Word info document."""

from __future__ import annotations

import base64
import os
import shutil
import sys
import tempfile
from pathlib import Path


def _prepare_frozen_env() -> None:
    """Stabilize paths when running from a PyInstaller / Nuitka build."""
    if not getattr(sys, "frozen", False):
        return
    exe_dir = Path(sys.executable).resolve().parent
    try:
        os.chdir(exe_dir)
    except OSError:
        pass
    # Prefer the bundle dir for package data lookups
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        os.environ.setdefault("GRADIO_TEMP_DIR", str(exe_dir / "output" / "gradio_tmp"))


_prepare_frozen_env()

import gradio as gr

from models import Address, FamilyMember, I140Data
from pdf_filler import fill_pdf
from word_extractor import read_word_document


def _writable_root() -> Path:
    """Directory next to the exe (or project root) — safe for output/."""
    if getattr(sys, "frozen", False) or "__compiled__" in globals():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def _bundle_root() -> Path:
    """Where packaged assets live (PyInstaller _MEIPASS or exe/project dir)."""
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return Path(meipass)
    return _writable_root()


ROOT = _writable_root()
BUNDLE = _bundle_root()
DEFAULT_TEMPLATE = BUNDLE / "assets" / "i-140-uscis.pdf"
if not DEFAULT_TEMPLATE.is_file():
    DEFAULT_TEMPLATE = ROOT / "assets" / "i-140-uscis.pdf"
if not DEFAULT_TEMPLATE.is_file():
    DEFAULT_TEMPLATE = ROOT / "test" / "i-140-uscis.pdf"
WORK_DIR = ROOT / "output"
WORK_DIR.mkdir(exist_ok=True)

UNIT_CHOICES = ["", "Apt", "Ste", "Flr"]
YN_CHOICES = ["Unknown", "Yes", "No"]


def _yn_to_bool(value: str) -> bool | None:
    if value == "Yes":
        return True
    if value == "No":
        return False
    return None


def _bool_to_yn(value: bool | None) -> str:
    if value is True:
        return "Yes"
    if value is False:
        return "No"
    return "Unknown"


def _pdf_preview_html(pdf_path: str | None) -> str:
    if not pdf_path or not Path(pdf_path).is_file():
        return (
            "<div style='padding:1.5rem;color:#555;border:1px dashed #ccc;"
            "border-radius:8px;text-align:center'>"
            "Generate a PDF to preview it here."
            "</div>"
        )
    data = base64.b64encode(Path(pdf_path).read_bytes()).decode("ascii")
    return (
        f"<iframe src='data:application/pdf;base64,{data}' "
        "width='100%' height='820px' style='border:1px solid #ddd;border-radius:8px;'>"
        "</iframe>"
    )


def data_to_form(data: I140Data) -> list:
    spouse = data.spouse or FamilyMember()
    children = list(data.children) + [FamilyMember()] * 3
    children = children[:3]
    addr = data.current_address
    company = data.company_address
    return [
        data.last_name,
        data.first_name,
        data.middle_name,
        data.date_of_birth,
        data.ssn,
        data.current_wage,
        data.wage_per or "year",
        _bool_to_yn(data.premium_processing),
        _bool_to_yn(
            data.prior_immigrant_petition_filed
            if data.prior_immigrant_petition_filed is not None
            else data.previously_approved_i140
        ),
        addr.street,
        addr.unit_type,
        addr.apt,
        addr.city,
        addr.state,
        addr.zip_code,
        addr.country,
        data.i94_number,
        data.date_of_last_arrival,
        data.current_nonimmigrant_status,
        data.h1_expiration,
        data.passport_number,
        data.passport_country,
        data.passport_expiration,
        data.birth_city_state,
        data.birth_country,
        data.citizenship_country,
        data.company_name,
        data.company_ein,
        company.street,
        company.unit_type,
        company.apt,
        company.city,
        company.state,
        company.zip_code,
        company.country,
        data.company_employees,
        data.company_gross_income,
        data.signer_name,
        data.signer_title,
        spouse.name,
        spouse.date_of_birth,
        spouse.place_of_birth,
        spouse.relationship,
        children[0].name,
        children[0].date_of_birth,
        children[0].place_of_birth,
        children[1].name,
        children[1].date_of_birth,
        children[1].place_of_birth,
        children[2].name,
        children[2].date_of_birth,
        children[2].place_of_birth,
    ]


def form_to_data(*values) -> I140Data:
    (
        last_name,
        first_name,
        middle_name,
        date_of_birth,
        ssn,
        current_wage,
        wage_per,
        premium_processing,
        prior_petition,
        street,
        unit_type,
        apt,
        city,
        state,
        zip_code,
        country,
        i94_number,
        date_of_last_arrival,
        current_status,
        h1_expiration,
        passport_number,
        passport_country,
        passport_expiration,
        birth_city_state,
        birth_country,
        citizenship_country,
        company_name,
        company_ein,
        c_street,
        c_unit_type,
        c_apt,
        c_city,
        c_state,
        c_zip,
        c_country,
        company_employees,
        company_gross_income,
        signer_name,
        signer_title,
        spouse_name,
        spouse_dob,
        spouse_pob,
        spouse_rel,
        child1_name,
        child1_dob,
        child1_pob,
        child2_name,
        child2_dob,
        child2_pob,
        child3_name,
        child3_dob,
        child3_pob,
    ) = values

    prior = _yn_to_bool(prior_petition)
    children: list[FamilyMember] = []
    for name, dob, pob in (
        (child1_name, child1_dob, child1_pob),
        (child2_name, child2_dob, child2_pob),
        (child3_name, child3_dob, child3_pob),
    ):
        if (name or "").strip():
            children.append(
                FamilyMember(
                    name=name.strip(),
                    date_of_birth=(dob or "").strip(),
                    place_of_birth=(pob or "").strip(),
                    relationship="Child",
                )
            )

    spouse = None
    if (spouse_name or "").strip():
        spouse = FamilyMember(
            name=spouse_name.strip(),
            date_of_birth=(spouse_dob or "").strip(),
            place_of_birth=(spouse_pob or "").strip(),
            relationship=(spouse_rel or "Spouse").strip(),
        )

    return I140Data(
        last_name=(last_name or "").strip(),
        first_name=(first_name or "").strip(),
        middle_name=(middle_name or "").strip(),
        date_of_birth=(date_of_birth or "").strip(),
        ssn=(ssn or "").strip(),
        current_wage=(current_wage or "").strip(),
        wage_per=(wage_per or "year").strip() or "year",
        premium_processing=_yn_to_bool(premium_processing),
        previously_approved_i140=prior,
        prior_immigrant_petition_filed=prior,
        current_address=Address(
            street=(street or "").strip(),
            unit_type=(unit_type or "").strip(),
            apt=(apt or "").strip(),
            city=(city or "").strip(),
            state=(state or "").strip(),
            zip_code=(zip_code or "").strip(),
            country=(country or "United States").strip() or "United States",
        ),
        i94_number=(i94_number or "").strip(),
        date_of_last_arrival=(date_of_last_arrival or "").strip(),
        current_nonimmigrant_status=(current_status or "").strip(),
        h1_expiration=(h1_expiration or "").strip(),
        passport_number=(passport_number or "").strip(),
        passport_country=(passport_country or "").strip(),
        passport_expiration=(passport_expiration or "").strip(),
        birth_city_state=(birth_city_state or "").strip(),
        birth_country=(birth_country or "").strip(),
        citizenship_country=(citizenship_country or "").strip(),
        company_name=(company_name or "").strip(),
        company_ein=(company_ein or "").strip(),
        company_address=Address(
            street=(c_street or "").strip(),
            unit_type=(c_unit_type or "").strip(),
            apt=(c_apt or "").strip(),
            city=(c_city or "").strip(),
            state=(c_state or "").strip(),
            zip_code=(c_zip or "").strip(),
            country=(c_country or "United States").strip() or "United States",
        ),
        company_employees=(company_employees or "").strip(),
        company_gross_income=(company_gross_income or "").strip(),
        signer_name=(signer_name or "").strip(),
        signer_title=(signer_title or "").strip(),
        spouse=spouse,
        children=children,
    )


def _output_pdf_path(data: I140Data) -> Path:
    first = (data.first_name or "unknown").strip().replace(" ", "-")
    last = (data.last_name or "unknown").strip().replace(" ", "-")
    return WORK_DIR / f"i-140-uscis-{first}-{last}.pdf"


def confirm_save(pdf_file, save_folder: str, *form_values):
    src = _as_path(pdf_file)
    if src is None or not src.is_file():
        raise gr.Error("No PDF to save. Extract or regenerate first.")

    data = form_to_data(*form_values)
    folder = (
        Path(save_folder.strip())
        if save_folder and save_folder.strip()
        else Path.home() / "Downloads"
    )
    folder.mkdir(parents=True, exist_ok=True)
    dest = folder / _output_pdf_path(data).name
    shutil.copy2(src, dest)

    # Gradio can only serve files under cwd/temp/allowed_paths — keep a
    # project-local copy for the File widget while still saving to dest.
    served = WORK_DIR / dest.name
    if dest.resolve() != served.resolve():
        shutil.copy2(dest, served)

    return str(served), f"Saved to `{dest}`"


def _as_path(file_value) -> Path | None:
    if file_value is None:
        return None
    if isinstance(file_value, dict):
        path = file_value.get("path") or file_value.get("name")
        return Path(path) if path else None
    return Path(str(file_value))


def extract_from_word(word_file, template_path: str):
    if not word_file:
        raise gr.Error("Upload an I-140 info Word document (.doc or .docx).")

    template = Path(template_path.strip()) if template_path else DEFAULT_TEMPLATE
    if not template.is_file():
        raise gr.Error(f"PDF template not found: {template}")

    src = _as_path(word_file)
    if src is None or not src.is_file():
        raise gr.Error("Could not read the uploaded Word file.")

    suffix = src.suffix.lower() or ".docx"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp_path = Path(tmp.name)
    shutil.copy2(src, tmp_path)

    try:
        data = read_word_document(str(tmp_path.resolve()))
    except Exception as exc:  # noqa: BLE001 - surface Word/COM errors in UI
        raise gr.Error(f"Failed to read Word document: {exc}") from exc
    finally:
        tmp_path.unlink(missing_ok=True)

    out_path = _output_pdf_path(data)
    fill_pdf(str(template), str(out_path), data)
    form_values = data_to_form(data)
    status = (
        f"Extracted **{data.first_name} {data.last_name}**. "
        "Review fields below, edit if needed, regenerate, then confirm & save."
    )
    return (*form_values, str(out_path), _pdf_preview_html(str(out_path)), status)


def regenerate_pdf(template_path: str, *form_values):
    template = Path(template_path.strip()) if template_path else DEFAULT_TEMPLATE
    if not template.is_file():
        raise gr.Error(f"PDF template not found: {template}")

    data = form_to_data(*form_values)
    if not data.last_name and not data.first_name:
        raise gr.Error("Fill at least first and last name before generating.")

    out_path = _output_pdf_path(data)
    fill_pdf(str(template), str(out_path), data)
    status = f"Updated PDF: `{out_path.name}`"
    return str(out_path), _pdf_preview_html(str(out_path)), status


def build_ui() -> gr.Blocks:
    with gr.Blocks(title="I-140 PDF Filler") as demo:
        gr.Markdown(
            """
            # I-140 PDF Filler
            Upload a filled **I-140 info Word document**, review/edit the extracted data,
            preview the populated USCIS PDF, then save it to your PC.
            """
        )

        with gr.Row():
            word_input = gr.File(
                label="I-140 info Word document",
                file_types=[".doc", ".docx"],
                type="filepath",
            )
            template_input = gr.Textbox(
                label="Blank I-140 PDF template path",
                value=str(DEFAULT_TEMPLATE),
            )

        extract_btn = gr.Button("Extract & populate PDF", variant="primary")
        status = gr.Markdown("Ready.")

        with gr.Tabs():
            with gr.Tab("Beneficiary"):
                with gr.Row():
                    last_name = gr.Textbox(label="Last name")
                    first_name = gr.Textbox(label="First name")
                    middle_name = gr.Textbox(label="Middle name")
                with gr.Row():
                    date_of_birth = gr.Textbox(label="Date of birth")
                    ssn = gr.Textbox(label="SSN")
                    current_wage = gr.Textbox(label="Current wage")
                    wage_per = gr.Dropdown(
                        ["year", "hour", "week", "month"],
                        value="year",
                        label="Wage per",
                    )
                with gr.Row():
                    premium_processing = gr.Dropdown(
                        YN_CHOICES, value="Unknown", label="Premium processing"
                    )
                    prior_petition = gr.Dropdown(
                        YN_CHOICES,
                        value="Unknown",
                        label="Prior immigrant petition filed",
                    )

            with gr.Tab("Address"):
                street = gr.Textbox(label="Street")
                with gr.Row():
                    unit_type = gr.Dropdown(UNIT_CHOICES, value="", label="Unit type")
                    apt = gr.Textbox(label="Apt / Ste / Flr #")
                with gr.Row():
                    city = gr.Textbox(label="City")
                    state = gr.Textbox(label="State")
                    zip_code = gr.Textbox(label="ZIP")
                    country = gr.Textbox(label="Country", value="United States")

            with gr.Tab("Immigration"):
                with gr.Row():
                    i94_number = gr.Textbox(label="I-94 number")
                    date_of_last_arrival = gr.Textbox(label="Date of last arrival")
                with gr.Row():
                    current_status = gr.Textbox(label="Current nonimmigrant status")
                    h1_expiration = gr.Textbox(
                        label="Authorized stay / H-1 expiration"
                    )
                with gr.Row():
                    passport_number = gr.Textbox(label="Passport #")
                    passport_country = gr.Textbox(label="Passport country")
                    passport_expiration = gr.Textbox(label="Passport expiration")
                with gr.Row():
                    birth_city_state = gr.Textbox(label="City/state of birth")
                    birth_country = gr.Textbox(label="Country of birth")
                    citizenship_country = gr.Textbox(label="Citizenship country")

            with gr.Tab("Company & signer"):
                with gr.Row():
                    company_name = gr.Textbox(label="Company name")
                    company_ein = gr.Textbox(label="EIN")
                c_street = gr.Textbox(label="Company street")
                with gr.Row():
                    c_unit_type = gr.Dropdown(
                        UNIT_CHOICES, value="", label="Unit type"
                    )
                    c_apt = gr.Textbox(label="Apt / Ste / Flr #")
                with gr.Row():
                    c_city = gr.Textbox(label="City")
                    c_state = gr.Textbox(label="State")
                    c_zip = gr.Textbox(label="ZIP")
                    c_country = gr.Textbox(label="Country", value="United States")
                with gr.Row():
                    company_employees = gr.Textbox(label="Number of employees")
                    company_gross_income = gr.Textbox(label="Gross annual income")
                with gr.Row():
                    signer_name = gr.Textbox(label="Signer name")
                    signer_title = gr.Textbox(label="Signer title")

            with gr.Tab("Family"):
                gr.Markdown("### Spouse")
                with gr.Row():
                    spouse_name = gr.Textbox(label="Name")
                    spouse_dob = gr.Textbox(label="Date of birth")
                    spouse_pob = gr.Textbox(label="Place of birth")
                    spouse_rel = gr.Textbox(label="Relationship")
                gr.Markdown("### Children (up to 3)")
                with gr.Row():
                    child1_name = gr.Textbox(label="Child 1 name")
                    child1_dob = gr.Textbox(label="DOB")
                    child1_pob = gr.Textbox(label="Place of birth")
                with gr.Row():
                    child2_name = gr.Textbox(label="Child 2 name")
                    child2_dob = gr.Textbox(label="DOB")
                    child2_pob = gr.Textbox(label="Place of birth")
                with gr.Row():
                    child3_name = gr.Textbox(label="Child 3 name")
                    child3_dob = gr.Textbox(label="DOB")
                    child3_pob = gr.Textbox(label="Place of birth")

        form_fields = [
            last_name,
            first_name,
            middle_name,
            date_of_birth,
            ssn,
            current_wage,
            wage_per,
            premium_processing,
            prior_petition,
            street,
            unit_type,
            apt,
            city,
            state,
            zip_code,
            country,
            i94_number,
            date_of_last_arrival,
            current_status,
            h1_expiration,
            passport_number,
            passport_country,
            passport_expiration,
            birth_city_state,
            birth_country,
            citizenship_country,
            company_name,
            company_ein,
            c_street,
            c_unit_type,
            c_apt,
            c_city,
            c_state,
            c_zip,
            c_country,
            company_employees,
            company_gross_income,
            signer_name,
            signer_title,
            spouse_name,
            spouse_dob,
            spouse_pob,
            spouse_rel,
            child1_name,
            child1_dob,
            child1_pob,
            child2_name,
            child2_dob,
            child2_pob,
            child3_name,
            child3_dob,
            child3_pob,
        ]

        regen_btn = gr.Button("Apply edits & regenerate PDF", variant="secondary")

        gr.Markdown("### PDF preview")
        pdf_preview = gr.HTML(value=_pdf_preview_html(None))
        pdf_file = gr.File(label="Generated PDF file", file_types=[".pdf"])

        gr.Markdown("### Confirm & save")
        with gr.Row():
            save_folder = gr.Textbox(
                label="Save folder on this PC",
                value=str(Path.home() / "Downloads"),
                scale=3,
            )
            save_btn = gr.Button("Confirm & save PDF", variant="primary", scale=1)
        saved_file = gr.File(label="Saved copy (open / re-download)")

        extract_btn.click(
            fn=extract_from_word,
            inputs=[word_input, template_input],
            outputs=[*form_fields, pdf_file, pdf_preview, status],
        )
        regen_btn.click(
            fn=regenerate_pdf,
            inputs=[template_input, *form_fields],
            outputs=[pdf_file, pdf_preview, status],
        )
        save_btn.click(
            fn=confirm_save,
            inputs=[pdf_file, save_folder, *form_fields],
            outputs=[saved_file, status],
        )

    return demo


if __name__ == "__main__":
    build_ui().queue().launch(
        server_name="127.0.0.1",
        server_port=7860,
        inbrowser=True,
        show_error=True,
        allowed_paths=[
            str(WORK_DIR),
            str(ROOT / "assets"),
            str(ROOT / "test"),
            str(BUNDLE / "assets"),
            str(Path.home() / "Downloads"),
        ],
    )
