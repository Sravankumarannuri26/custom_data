{
    'name': 'Staging Database Sanitizer',
    'version': '19.0.1.0.0',
    'category': 'Technical',
    'summary': 'Automatically sanitize staging databases after restore',
    'description': """
        Staging Database Sanitizer
        ==========================

        Automatically sanitizes data when installed on a staging database:
        - Deletes sign documents, payslips, attachments, mail tracking
        - Updates employee salary data
        - Removes specific GL code series

        Runs automatically on module installation if database.is_neutralized = true
    """,
    'depends': ['base', 'hr', 'account'],
    'data': [
        'security/ir.model.access.csv',
    ],
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}