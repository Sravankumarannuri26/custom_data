# -*- coding: utf-8 -*-
{
    'name': 'AR Aging Details by Invoice Due Date - XLSX Export',
    'version': '19.0.1.0.0',
    'summary': 'Wizard to export flattened, invoice-level AR aging details to XLSX',
    'description': """
Exports open customer receivable lines (invoices / credit memos) as a flat,
invoice-level list with due date, age, status, credit terms and balances -
matching a fixed 12-column layout:

date, status, entity, age, due_date, transaction_number/Invoice #,
Credit Period (example), customer_name, currency_code, balance, amount,
exchange_rate

Access: Accounting > Reporting > Partner Reports > AR Aging Details Export
""",
    'category': 'Accounting/Accounting',
    'author': 'Sriman',
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/ar_aging_details_wizard_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
