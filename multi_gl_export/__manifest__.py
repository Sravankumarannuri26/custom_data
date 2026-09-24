# -*- coding: utf-8 -*-
{
    'name': 'Multi General Ledger Export',
    'version': '1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Export multiple General Ledger accounts using comma-separated search And also Project Code and Name Field added to the General Ledger Report',
    'depends': ['account_reports'],
    'data': [
        'security/ir.model.access.csv',
        'data/general_ledger_data.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'multi_gl_export/static/src/js/account_report_search_bar.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}

