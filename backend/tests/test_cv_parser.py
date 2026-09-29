from datetime import datetime

from app.services.rule_based import merge_candidate_parses, parse_candidate_from_cv


SAMPLE_CV = """
NGUYEN VAN AN
Senior Backend Engineer
Ho Chi Minh City, Vietnam
an.nguyen@example.com | +84 912 345 678
linkedin.com/in/nguyenvanan | https://github.com/nguyenvanan

PROFESSIONAL SUMMARY
Backend engineer building payment platforms and distributed systems for more than 7 years.

TECHNICAL SKILLS
Python, FastAPI, PostgreSQL, Redis, Docker, Kubernetes, AWS, Kafka, Team leadership

WORK EXPERIENCE
Senior Backend Engineer | FinPay JSC
2021 - Present
- Improved payment throughput by 45% and led a team of 6 engineers.
Backend Engineer | ShopNow Ltd
2018 - 2021
- Built ecommerce APIs with Python and PostgreSQL.

PROJECTS
Fraud detection platform | Python, machine learning, Kafka
Merchant settlement service | FastAPI, PostgreSQL

EDUCATION
Bachelor of Computer Science | University of Technology | 2014 - 2018

CERTIFICATIONS
AWS Certified Solutions Architect

LANGUAGES
Vietnamese - Native | English - Professional
"""


def test_parser_extracts_full_candidate_profile():
    parsed = parse_candidate_from_cv(SAMPLE_CV)

    assert parsed["name"] == "NGUYEN VAN AN"
    assert parsed["email"] == "an.nguyen@example.com"
    assert parsed["current_title"] == "Senior Backend Engineer"
    assert parsed["years_of_experience"] == 7
    assert parsed["previous_companies"] == ["FinPay JSC", "ShopNow Ltd"]
    assert parsed["experience_timeline"][0]["company"] == "FinPay JSC"
    assert "python" in parsed["skills"]
    assert "github" not in parsed["skills"]
    assert len(parsed["projects"]) == 2
    assert parsed["achievements"]
    assert parsed["completeness_score"] >= 90
    assert parsed["missing_critical_fields"] == []


def test_ai_merge_keeps_document_contact_when_model_disagrees():
    local = parse_candidate_from_cv(SAMPLE_CV)
    merged = merge_candidate_parses(
        local,
        {
            "email": "incorrect@example.net",
            "current_title": "Staff Backend Engineer",
            "skills": ["Apache Kafka", "Python"],
            "years_of_experience": 7,
            "gender": "unsupported sensitive field",
        },
    )

    assert merged["email"] == "an.nguyen@example.com"
    assert merged["current_title"] == "Staff Backend Engineer"
    assert "email" in merged["parse_conflicts"]
    assert "gender" not in merged
    assert merged["review_recommended"] is True


def test_overlapping_roles_are_not_double_counted():
    parsed = parse_candidate_from_cv(
        """
        LE THI BINH
        Software Engineer
        WORK EXPERIENCE
        Lead Engineer | Company A
        2020 - Present
        Software Engineer | Company B
        2021 - 2023
        """
    )

    # The second role sits inside the first interval.
    assert parsed["years_of_experience"] == datetime.now().year - 2020
