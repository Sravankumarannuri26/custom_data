{
    'name': 'Portal Employee Sync',
    'version': '19.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Sync employees from external portal via API',
    'description': """
        Portal Employee Sync
        ====================
        - Create employees via REST API
        - API Key authentication
        - Auto-create departments
        - Track employee codes
        - Portal sync timestamps
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['base', 'hr'],
    'data': [
        'security/ir.model.access.csv',
        'views/portal_employee_views.xml',
        'views/inactive_employees.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}