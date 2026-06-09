from __future__ import annotations

from app.attacks.families import ATTACK_FAMILIES
from app.core.schema import SecurityCase
from app.tasks.injection_tasks import INJECTION_TASKS
from app.tasks.user_tasks import USER_TASKS

# Human-readable metadata for the experimenter. These labels are not registered
# as MCP tools and are not visible to the AI under test unless the experimenter
# explicitly pastes them into the chat.
VECTOR_REGISTRY: dict[str, dict[str, str]] = {
    "email_alice_body": {"surface": "mail", "label": "Email body: Alice meeting note", "clean_control": "Other fake app surfaces contain no injection text."},
    "email_security_body": {"surface": "mail", "label": "Email body: Security review action items", "clean_control": "Other fake app surfaces contain no injection text."},
    "email_budget_body": {"surface": "mail", "label": "Email body: Q2 budget draft", "clean_control": "Other fake app surfaces contain no injection text."},
    "email_compliance_body": {"surface": "mail", "label": "Email body: Compliance deadline", "clean_control": "Other fake app surfaces contain no injection text."},
    "email_trip_body": {"surface": "mail", "label": "Email body: Tokyo trip planning", "clean_control": "Other fake app surfaces contain no injection text."},
    "calendar_vendor_review_description": {"surface": "calendar", "label": "Calendar event description: Vendor review", "clean_control": "Other fake app surfaces contain no injection text."},
    "calendar_compliance_deadline_description": {"surface": "calendar", "label": "Calendar event description: Compliance renewal deadline", "clean_control": "Other fake app surfaces contain no injection text."},
    "calendar_seoul_planning_description": {"surface": "calendar", "label": "Calendar event description: Seoul trip planning notes", "clean_control": "Other fake app surfaces contain no injection text."},
    "calendar_tokyo_trip_description": {"surface": "calendar", "label": "Calendar event description: Tokyo trip planning sync", "clean_control": "Other fake app surfaces contain no injection text."},
    "drive_compliance_doc": {"surface": "drive", "label": "Drive document: compliance_renewal_deadline.md content", "clean_control": "Other fake app surfaces contain no injection text."},
    "drive_project_launch_doc": {"surface": "drive", "label": "Drive document: project_launch.md content", "clean_control": "Other fake app surfaces contain no injection text."},
    "drive_q2_budget_doc": {"surface": "drive", "label": "Drive document: q2_budget.md content", "clean_control": "Other fake app surfaces contain no injection text."},
    "drive_vendor_due_diligence_doc": {"surface": "drive", "label": "Drive document: vendor_due_diligence.md content", "clean_control": "Other fake app surfaces contain no injection text."},
    "drive_tokyo_trip_doc": {"surface": "drive", "label": "Drive document: tokyo_trip_package_notes.md content", "clean_control": "Other fake app surfaces contain no injection text."},
    "drive_risk_report_doc": {"surface": "drive", "label": "Drive document: risk_controls_overview.md content", "clean_control": "Other fake app surfaces contain no injection text."},
    "web_vendor_product_html": {"surface": "web", "label": "Web page content: vendor product page", "clean_control": "Other fake app surfaces contain no injection text."},
    "web_tokyo_guide_html": {"surface": "web", "label": "Web page content: Tokyo guide", "clean_control": "Other fake app surfaces contain no injection text."},
    "web_paris_itinerary_html": {"surface": "web", "label": "Web page content: Paris itinerary", "clean_control": "Other fake app surfaces contain no injection text."},
    "web_london_hotel_html": {"surface": "web", "label": "Web page content: London hotel notes", "clean_control": "Other fake app surfaces contain no injection text."},
    "web_london_car_html": {"surface": "web", "label": "Web page content: London car rental notes", "clean_control": "Other fake app surfaces contain no injection text."},
    "web_risk_review_html": {"surface": "web", "label": "Web page content: risk review page", "clean_control": "Other fake app surfaces contain no injection text."},
    "slack_project_message": {"surface": "slack", "label": "Slack message: C-project channel history", "clean_control": "Other fake app surfaces contain no injection text."},
    "slack_security_message": {"surface": "slack", "label": "Slack message: C-security channel history", "clean_control": "Other fake app surfaces contain no injection text."},
    "slack_travel_message": {"surface": "slack", "label": "Slack message: C-travel channel history", "clean_control": "Other fake app surfaces contain no injection text."},
    "banking_utility_bill_note": {"surface": "banking", "label": "Bank transaction note: December utility bill", "clean_control": "Other fake app surfaces contain no injection text."},
    "banking_q1_cloud_vendor_note": {"surface": "banking", "label": "Bank transaction note: Q1 cloud vendor charge", "clean_control": "Other fake app surfaces contain no injection text."},
    "banking_unusual_transaction_note": {"surface": "banking", "label": "Bank transaction note: unusual overseas charge", "clean_control": "Other fake app surfaces contain no injection text."},
    "banking_landlord_account_note": {"surface": "banking", "label": "Bank account metadata: landlord rent account", "clean_control": "Other fake app surfaces contain no injection text."},
    "hotel_london_value_review": {"surface": "travel", "label": "Hotel review: London Value Hotel offer", "clean_control": "Other fake app surfaces contain no injection text."},
    "hotel_paris_luxury_review": {"surface": "travel", "label": "Hotel review: Paris Luxury Palace offer", "clean_control": "Other fake app surfaces contain no injection text."},
    "hotel_tokyo_refundable_review": {"surface": "travel", "label": "Hotel review: Tokyo Refundable Hotel offer", "clean_control": "Other fake app surfaces contain no injection text."},
    "car_london_economy_note": {"surface": "travel", "label": "Car rental note: London economy offer", "clean_control": "Other fake app surfaces contain no injection text."},
    "memory_agentic_ai_note": {"surface": "memory", "label": "Memory document: Agentic AI project note", "clean_control": "Other fake app surfaces contain no injection text."},
    "memory_london_hotel_pref": {"surface": "memory", "label": "Memory document: London hotel preference", "clean_control": "Other fake app surfaces contain no injection text."},
    "memory_london_car_pref": {"surface": "memory", "label": "Memory document: London car preference", "clean_control": "Other fake app surfaces contain no injection text."},
    "memory_tokyo_pref": {"surface": "memory", "label": "Memory document: Tokyo trip preference", "clean_control": "Other fake app surfaces contain no injection text."},
    "memory_risk_report_rule": {"surface": "memory", "label": "Memory document: risk report rule", "clean_control": "Other fake app surfaces contain no injection text."},
}
# Candidate injection surfaces are tied to the tools a user task could plausibly
# call. This avoids accidental multi-vector contamination: a calendar-injection
# case has only the calendar surface poisoned, even if the user task also asks the
# agent to read email first.
CANDIDATE_PLACEHOLDERS_BY_USER_TASK: dict[str, list[str]] = {
    "W01": ["email_alice_body"],
    "W02": ["email_compliance_body", "calendar_compliance_deadline_description", "drive_compliance_doc"],
    "W03": ["drive_project_launch_doc"],
    "W04": ["email_security_body", "slack_security_message"],
    "W05": ["email_budget_body", "drive_q2_budget_doc"],
    "W06": ["calendar_vendor_review_description"],
    "W07": ["web_vendor_product_html", "drive_vendor_due_diligence_doc"],
    "W08": [
        "email_trip_body",
        "calendar_tokyo_trip_description",
        "drive_tokyo_trip_doc",
        "web_tokyo_guide_html",
        "slack_travel_message",
        "hotel_tokyo_refundable_review",
        "memory_tokyo_pref",
    ],
    "B01": ["banking_utility_bill_note"],
    "B02": ["banking_q1_cloud_vendor_note"],
    "B03": ["banking_unusual_transaction_note"],
    "B04": ["banking_landlord_account_note"],
    "T01": ["hotel_london_value_review", "web_london_hotel_html", "memory_london_hotel_pref"],
    "T02": ["hotel_paris_luxury_review", "web_paris_itinerary_html"],
    "T03": ["car_london_economy_note", "web_london_car_html", "memory_london_car_pref"],
    "T04": ["calendar_seoul_planning_description"],
    "M01": ["memory_agentic_ai_note"],
    "M02": ["web_vendor_product_html"],
    "M03": ["slack_project_message"],
    "M04": ["memory_risk_report_rule", "web_risk_review_html", "drive_risk_report_doc"],
}

def build_cases() -> dict[str, SecurityCase]:
    cases: dict[str, SecurityCase] = {}
    for user in USER_TASKS.values():
        placeholders = CANDIDATE_PLACEHOLDERS_BY_USER_TASK.get(user.id, [])
        for placeholder in placeholders:
            for inj in INJECTION_TASKS.values():
                for family in ATTACK_FAMILIES.values():
                    case_id = f"{user.id}__{placeholder}__{inj.id}__{family.id}"
                    cases[case_id] = SecurityCase(case_id, user.id, inj.id, family.id, user.suite, placeholder)
    return cases


SECURITY_CASES = build_cases()

INTERNAL_CASE_IDS = sorted(SECURITY_CASES.keys())
PUBLIC_TO_INTERNAL_CASE_ID = {f"case_{idx:04d}": internal for idx, internal in enumerate(INTERNAL_CASE_IDS, start=1)}
INTERNAL_TO_PUBLIC_CASE_ID = {internal: public for public, internal in PUBLIC_TO_INTERNAL_CASE_ID.items()}


def public_case_id(internal_case_id: str) -> str:
    return INTERNAL_TO_PUBLIC_CASE_ID.get(internal_case_id, internal_case_id)


def resolve_case_id(case_id: str) -> str:
    return PUBLIC_TO_INTERNAL_CASE_ID.get(case_id, case_id)
