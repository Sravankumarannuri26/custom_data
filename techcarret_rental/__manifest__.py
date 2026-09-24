# -*- coding: utf-8 -*-
{
    'name': 'Techcarret Rental Orders',
    'summary': "Techcarret Rental Orders",
    'description': "Techcarret Rental Orders",
    'author': 'Ifensys',
    'category': 'Sales',
    'version': '19.1',
    'depends': ['product', 'sale_management', 'sale', 'stock', 'sale_renting', 'sale_project', 'hr', 'hr_payroll', 'hr_work_entry', 'account', 'analytic', 'sale_subscription', 'sale_stock_renting',
                'techcarrot_employee', 'techcarrot_contacts', 'sale_project', 'purchase', 'sale_fixed_discount'],
    'data': [
        'security/ir.model.access.csv',
        'security/rental_security.xml',
        'views/sequence_view.xml',
        'report/sale_ir_actions.xml',
        'report/sale_report_template.xml',
        'report/po_ir_actions.xml',
        'report/po_report_template.xml',
        'views/tec_project_type_views.xml',
        'views/res_config_settings_views.xml',
        'views/rental_order_view.xml',
        'views/employee_view.xml',
        'views/import_attendance_view.xml',
        # 'views/project_milestone_view.xml',
        'views/cron_view.xml',
        'views/purchase_view.xml',
        'wizard/edit_prod_desc_view.xml',
        'views/menu_view.xml'
    ],

    'assets': {
        'web.assets_backend': [
            # 'techcarret_rental/static/src/css/widget.css',
            # 'techcarret_rental/static/src/xml/one2many_delete_templates.xml',
            # 'techcarret_rental/static/src/xml/hide_view_button.xml',
            # 'techcarret_rental/static/src/js/list_renderer.js',
        ],
    },
    'auto_install': False,
    'installable': True,
}
