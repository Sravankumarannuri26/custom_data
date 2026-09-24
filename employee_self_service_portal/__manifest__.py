# __manifest__.py
{
    "name": "Employee Self Service Portal MLR",
    "version": "19.1.7",
    "depends": ["portal", "hr", "hr_attendance", "hr_payroll", "hr_holidays", "hr_expense", "techcarrot_crm_mlr","base_setup"],
    "category": "Human Resources",
    "author": "Lovaraju Mylapalli",
    "website": "https://www.mlr.com",
    "description": """
        Employee Self Service Portal
        =================================
        This module provides a portal for employees to manage their personal information, attendance, and other HR-related tasks. this is techcarrot customized
    """,
    "images": ["static/description/banner.png"],
    "summary": "Allow employees to access and manage their information via portal access.",
    "data": [
        "security/portal_access_groups.xml",        # Must be loaded first to create groups
        "security/ir.model.access.csv",
        "security/portal_employee_security.xml",
        "data/portal_data.xml",
        "data/attendance_cron.xml",               # Auto-checkout cron job
        "data/leave_email_templates.xml",
        # "data/expense_categories.xml",            # Default expense categories
        "views/menu.xml",
        "views/portal_layout.xml",
        "views/portal_ess_dashboard.xml",
        "views/portal_ess_dashboard_enhanced.xml",
        "views/Employee_details/portal_employee_templates.xml",
        "views/Employee_details/portal_attendance_templates.xml",
        "views/Employee_details/employee_form_view.xml",
        "views/Employee_details/portal_employee_edit_templates.xml",

        # ── Employee Profile ──
        # BASE MUST BE FIRST — all profile tabs call t-call="...portal_employee_profile_base"
        "views/Employee_details/portal_employee_profile_base.xml",         # ← MOVED TO TOP
        "views/Employee_details/portal_employee_profile_personal.xml",
        "views/Employee_details/portal_employee_profile_experience.xml",
        "views/Employee_details/portal_employee_profile_certification.xml",
        "views/Employee_details/portal_employee_profile_bank.xml",

        "views/Employee_details/portal_employee_crm.xml",
        "views/Employee_details/portal_employee_crm_enhanced.xml",
        "views/Employee_details/portal_employee_crm_create.xml",
        "views/Employee_details/portal_employee_crm_edit.xml",
        "views/Employee_details/portal_employee_crm_activity_edit.xml",
        "views/Employee_details/portal_employee_crm_activity_modal.xml",
        "views/Employee_details/portal_employee_crm_notes_modal.xml",
        "views/Employee_details/portal_expense_templates.xml",
        "views/Employee_details/portal_expense_submit.xml",
        "views/Employee_details/portal_payslip_templates.xml",
        "views/Employee_details/portal_payslip_view.xml",
        "views/Employee_details/portal_form16_template.xml",
        "views/portal_ess_ticket_form.xml",
        "views/portal_ess_leave_management.xml",
        'views/res_config_settings_views.xml', 
        'views/hr_leave_frozen_views.xml',
        'views/portal_contacts.xml',

        # "views/Employee_details/inherit_template.xml",
        # "views/Employee_details/portal_employee_profile_payroll.xml",
        # "views/Employee_details/profile_photo_upload.xml",
    ],
    "installable": True,
    "application": True,
    "license": "LGPL-3"
}