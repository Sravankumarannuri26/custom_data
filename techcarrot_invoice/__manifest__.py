# -*- coding: utf-8 -*-
{
    'name': 'Techcarret Invoice Templates',
    'summary': "Techcarret Invoice Templates",
    'description': "Techcarret Invoice Templates ",

    'author': 'Ifensys.',

    'category': 'Account',
    'version': '19.0.0.1.0',
    'depends': ['base', 'web', 'sale_management', 'stock', 'sale_renting', 'account', 'account_accountant', 'sale', 'techcarret_rental'],

    'data': [
        'security/ir.model.access.csv',
        'reports/invoice_report_template.xml',
        'reports/invoice_report_india.xml',
        'reports/payments_template.xml',
        'reports/payment_receipt.xml',
        'reports/invoice_ir_actions.xml',
        'reports/invoice_inherit.xml',
        'reports/statement_of_accounts.xml',
        'reports/po_report_india.xml',


        'data/server_action.xml',
        'views/res_bank_view.xml',
        # 'views/sale_order_view.xml',
        'views/account_move_view.xml',
        'wizard/inv_edit_prod_desc_view.xml',
    ],

    # 'license': "AGPL-1",

    'auto_install': False,
    'installable': True,


    # 'pre_init_hook': 'pre_init_check',
}
