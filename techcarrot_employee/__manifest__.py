# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name": "TechCarrot Employee Customization",
    "summary": "Development for TechCarrot",
    "category": "Sales",
    "version": "19.0.1",
    "sequence": 2,
    "author": "Ifensys",
    "website": "https://www.Ifensys.com",
    "depends": ['base', 'hr','hr_payroll','hr_attendance','hr_appraisal','contacts',
                'l10n_ae_hr_payroll',
                'hr_expense', 'web'],
    "data": [
            'security/ir.model.access.csv',
            'report/payslip_report_template.xml',
            'views/tec_employee_views.xml',
             'views/tec_employee_relationship_views.xml',
             'views/tec_employment_status_views.xml',
             'views/tec_language_master_views.xml',
             'views/tec_exit_type_views.xml',
             'views/tec_exit_reason_views.xml',
             'views/tec_religion_views.xml',
             'views/tec_employee_practice_views.xml',
             'views/tec_sub_practice_views.xml',
             'views/tec_contract_view.xml',
             'views/tec_expense_view.xml',
             'views/tec_employee_category_views.xml',
             ],
    "application": True,
    "installable": True,
    "auto_install": False
}
