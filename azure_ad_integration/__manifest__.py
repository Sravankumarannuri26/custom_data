{
    'name': 'Azure AD Email Auto Creation',
    'version': '1.0.1',
    'depends': ['hr'],
    'data': [
        'security/ir.model.access.csv',
        'views/hr_department_views.xml',
        'views/azure_license_views.xml',
        'views/hr_employee_views.xml',
        'views/employee_code_auto_generate.xml',
        'views/employee_code_wizard_views.xml',
    ],
    'installable': True,
}
