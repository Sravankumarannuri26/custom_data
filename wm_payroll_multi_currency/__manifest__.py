# -*- coding:utf-8 -*-
{
    'name': "Odoo Payroll Multi Currency",
    'summary': """
    Odoo Payroll Multi Currency
    Odoo Payroll Multi Currency
    Payroll Accounting Multi Currency
    payslip multi murrency
    payroll multi murrency
    payslip secondary currency
    salary multi Currency
        """,
    'description': """ Odoo Payroll Multi Currency
    """,
    'category': 'Human Resources',
    'version': '1.0.3',
    'license': 'OPL-1',
    'author': "Waleed Mohsen",
    'support': 'mohsen.waleed@gmail.com',
    'currency': 'USD',
    'price': 49,
    'depends': ['hr_payroll', 'hr_payroll_account','account'],
    'data': [
       'views/hr_contract_view.xml',
       'views/hr_salary_attachment_views.xml',
       'views/hr_payslip_line_view.xml',
       'views/report_payslip_template.xml',
       'views/hr_payslip_views.xml',
       # 'views/hr_payroll_report_views.xml',
    ],
    'images': ['static/description/main_screenshot.png'],
    'installable': True,
    'auto_install': False,
    
}
