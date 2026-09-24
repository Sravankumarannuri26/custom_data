# -*- coding:utf-8 -*-
{
    'name': "Payroll Accounting Multi Currency",

    'summary': """
        Payroll Accounting Multi Currency
        """,

    'description': """
        Payroll Accounting Multi Currency
        Payslip Multi Currency
        Payroll Multi Currency
    """,

    'author': "CorTex IT Solutions Ltd.",
    'website': "http://www.cortexsolutions.net",
    'category': 'Human Resources',
    'version': '1.2.1',
    'license': 'OPL-1',
    'currency': 'EUR',
    'price': 150,
    'depends': ['hr_payroll', 'hr_payroll_account','account'],
    'data': [
        'views/hr_contract_view.xml',
        'views/hr_payslip_line_view.xml',
        'views/report_payslip_template.xml',
    ],
    'images': ['static/description/main_screenshot.png'],
    'installable': True,
    'auto_install': False,
}
