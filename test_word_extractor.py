import unittest

from word_extractor import extract_from_word_fields


OLD_FORM = """
I-140 Information Request
Do you want premium processing: no
Last name, First name: Zhang, San
Your current wage: $110068
Do you have a previously approved I-140: yes
Your current address: 6110 Saintsbury Dr Apt 239, The Colony, TX 75056
Date of Birth: 12/10/1989
Your Social Security# 000-00-0000
Most recent I-94# if you have a new one: 269983670A4 .
Date of Last Arrival (MM/DD/YY): 11/19/2024
Passport #X0000000; Country issuedIndia
Expiration date 05/18/2032
City/Town/Village and State of Birth: Aligarh,Jawan, Uttar Pradesh
H-1 Expiration Date: 09/30/2027
Name and title who is to sign papers: Rahela Parween - Operations and HR Coordinator
Company’s current address: 6515 Shiloh Road Ste 110A, Alpharetta, GA 30005
Your family member information:
Name of each:
Date of birth:
Place of birth (city and country):
Relationship to you:
Wife
Husband
Name of each Child
Date of birth:
Place of birth (city and country):
Company’s number of employees27, company’s gross income 4096684
"""

NEW_FORM_FIELDS = """
I-140 Information Request
Employee:
Will you apply your I-140 under regular processing or premium processing? Premium processing fee is $2965 now charged by USCIS.
Do you have previous I-140 approval? If yes, please give us a copy and tell us:
Family Name Rao  First Name Arun Kumar  Middle Name___________
Your current wage: $85 PER HOUR
Your current address:100 OAK DR CINCINNATI OHIO 45202
Date of Birth:   08/09/1981
City/Town/Village, State/Province, and country of Birth: NAGULAPALEM INDIA
Your Social Security# 000 00 0000
Date of Last Arrival (MM/DD/YY): 08/15/2024
Most recent I-94# and expiration date: 120101511 A4 07/19/2027
H-1 Expiration Date: 07/19/2027
Your Passport Number: X0000001
Expiration date of your passport: 06/22/2032
Phone Number 000 000 0000
Your family member information:
Family Name:        Rao        First Name:     Meera           Middle Name:
Date of birth: 12/06/1982
Place of birth (city and country): VIJAYAWADA INDIA
Current status: H4
Relationship to you:
Name of each Child
Family Name:  Rao              First Name:    Anika Priya            Middle Name:
Date of birth: 02/26/2010
Place of birth (city and country): HYDERABAD INDIA
Name of each Child
Family Name:    Rao            First Name:     Dev           Middle Name:
Date of birth: 08/08/2016
Place of birth (city and country): MUMBAI INDIA
Name of each Child
Family Name:                First Name:                Middle Name:
Date of birth:
Place of birth (city and country):
"""

NEW_FORM_TYPED = """
I-140 Information Request
Employee: Mina Chen
Will you apply your I-140 under regular processing or premium processing? Premium processing fee is $2965 now charged by USCIS.  regular processing
Do you have previous I-140 approval? If yes, please give us a copy and tell us: No
Family Name___Chen_______  First Name_Mina_______  Middle Name___________
Your current wage: $57970
Your current address: 10 Park Dr, Novi MI 48374
Date of Birth:   March, 11, 1992
City/Town/Village, State/Province, and country of Birth: Shandong, CHINA
Your Social Security# 000-00-0001
Date of Last Arrival (MM/DD/YY): Jan, 12 2025
Most recent I-94# and expiration date: 142077421A2, No idea about expiration date
H-1 Expiration Date: 01/23/2028   (Jan. 23, 2028)
Your Passport Number: Y0000002
Expiration date of your passport: Feb, 03 2030
Your family member information:
Family Name:    Park            First Name:   Min             Middle Name:
Date of birth: 10/22/1993
Place of birth (city and country): Shenzhen, CHINA
Name of each Child
Family Name:                First Name:                Middle Name:
Date of birth:
"""


def _checks(*pairs: tuple[str, str]) -> list[dict]:
    fields = []
    for index, (context, result) in enumerate(pairs, start=1):
        fields.append(
            {"index": index, "type": 71, "result": result, "context": context}
        )
    return fields


class ExtractorTests(unittest.TestCase):
    def test_original_form_layout(self):
        data = extract_from_word_fields([], OLD_FORM)
        self.assertEqual(data.last_name, "Zhang")
        self.assertEqual(data.first_name, "San")
        self.assertEqual(data.current_wage, "110068")
        self.assertEqual(data.wage_per, "year")
        self.assertIs(data.premium_processing, False)
        self.assertIs(data.prior_immigrant_petition_filed, True)
        self.assertEqual(data.current_address.street, "6110 Saintsbury Dr")
        self.assertEqual(data.current_address.apt, "239")
        self.assertEqual(data.current_address.unit_type, "Apt")
        self.assertEqual(data.current_address.city, "The Colony")
        self.assertEqual(data.current_address.state, "TX")
        self.assertEqual(data.current_address.zip_code, "75056")
        self.assertEqual(data.date_of_birth, "12/10/1989")
        self.assertEqual(data.i94_number, "269983670A4")
        self.assertEqual(data.passport_number, "X0000000")
        self.assertEqual(data.passport_country, "India")
        self.assertEqual(data.birth_country, "India")
        self.assertEqual(data.citizenship_country, "India")
        self.assertEqual(data.birth_city_state, "Aligarh,Jawan, Uttar Pradesh")
        self.assertEqual(data.signer_name, "Rahela Parween")
        self.assertEqual(data.signer_title, "Operations and HR Coordinator")
        self.assertEqual(data.company_address.street, "6515 Shiloh Road")
        self.assertEqual(data.company_address.apt, "110A")
        self.assertEqual(data.company_address.unit_type, "Ste")
        self.assertEqual(data.company_address.city, "Alpharetta")
        self.assertEqual(data.company_employees, "27")
        self.assertEqual(data.company_gross_income, "4096684")
        self.assertIsNone(data.spouse)
        self.assertEqual(data.children, [])

    def test_newer_form_with_hourly_wage_and_family(self):
        data = extract_from_word_fields(
            _checks(("Wife", "1"), ("Husband", "0")),
            NEW_FORM_FIELDS,
        )
        self.assertEqual(
            (data.last_name, data.first_name, data.middle_name),
            ("Rao", "Arun Kumar", ""),
        )
        self.assertEqual(data.current_wage, "85")
        self.assertEqual(data.wage_per, "hour")
        self.assertIsNone(data.premium_processing)
        self.assertIsNone(data.prior_immigrant_petition_filed)
        self.assertEqual(data.current_address.street, "100 OAK DR")
        self.assertEqual(data.current_address.city, "CINCINNATI")
        self.assertEqual(data.current_address.state, "OH")
        self.assertEqual(data.current_address.zip_code, "45202")
        self.assertEqual(data.date_of_birth, "08/09/1981")
        self.assertEqual(data.birth_city_state, "NAGULAPALEM")
        self.assertEqual(data.birth_country, "INDIA")
        self.assertEqual(data.i94_number, "120101511")
        self.assertEqual(data.h1_expiration, "07/19/2027")
        self.assertEqual(data.passport_number, "X0000001")
        self.assertEqual(data.passport_expiration, "06/22/2032")
        self.assertEqual(data.current_nonimmigrant_status, "H-1B")
        self.assertIsNotNone(data.spouse)
        self.assertEqual(data.spouse.name, "Rao, Meera")
        self.assertEqual(data.spouse.relationship, "Wife")
        self.assertEqual(data.spouse.date_of_birth, "12/06/1982")
        self.assertEqual(data.spouse.place_of_birth, "VIJAYAWADA, INDIA")
        self.assertEqual(
            [child.name for child in data.children],
            ["Rao, Anika Priya", "Rao, Dev"],
        )
        self.assertEqual(data.children[0].date_of_birth, "02/26/2010")
        self.assertEqual(data.children[0].place_of_birth, "HYDERABAD, INDIA")

    def test_newer_form_typed_over_blank_fields(self):
        data = extract_from_word_fields(
            _checks(("Wife", "0"), ("Husband", "1")),
            NEW_FORM_TYPED,
        )
        self.assertEqual((data.last_name, data.first_name), ("Chen", "Mina"))
        self.assertEqual(data.middle_name, "")
        self.assertIs(data.premium_processing, False)
        self.assertIs(data.prior_immigrant_petition_filed, False)
        self.assertEqual(data.current_wage, "57970")
        self.assertEqual(data.wage_per, "year")
        self.assertEqual(data.current_address.street, "10 Park Dr")
        self.assertEqual(data.current_address.city, "Novi")
        self.assertEqual(data.current_address.state, "MI")
        self.assertEqual(data.current_address.zip_code, "48374")
        self.assertEqual(data.date_of_birth, "03/11/1992")
        self.assertEqual(data.date_of_last_arrival, "01/12/2025")
        self.assertEqual(data.birth_city_state, "Shandong")
        self.assertEqual(data.birth_country, "CHINA")
        self.assertEqual(data.i94_number, "142077421A2")
        self.assertEqual(data.h1_expiration, "01/23/2028")
        self.assertEqual(data.passport_number, "Y0000002")
        self.assertEqual(data.passport_expiration, "02/03/2030")
        self.assertEqual(data.spouse.name, "Park, Min")
        self.assertEqual(data.spouse.relationship, "Husband")
        self.assertEqual(data.spouse.place_of_birth, "Shenzhen, CHINA")
        self.assertEqual(data.children, [])


if __name__ == "__main__":
    unittest.main()
