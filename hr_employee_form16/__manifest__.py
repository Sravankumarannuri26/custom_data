{
    'name': 'Employee Form 16 (India)',
    'version': '19.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Upload and manage Form 16 PDFs per employee per financial year',
    'depends': ['hr', 'l10n_in'],
    'data': [
        'security/ir.model.access.csv',
        'views/hr_employee_views.xml',
        'views/form16_bulk_import_views.xml',
    ],
    'installable': True,
    'license': 'LGPL-3',
}
