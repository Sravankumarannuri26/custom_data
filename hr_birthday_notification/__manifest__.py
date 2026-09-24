{
    'name': 'HR Birthday Notification',
    'version': '19.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Daily birthday card email notifications to HR',
    'description': """
Sends an automated birthday card email to the HR Reviewer group each day
for employees whose birthday (day + month) matches today's date.
    """,
    'author': 'TechCarrot',
    'depends': ['hr'],
    'data': [
        'data/ir_cron.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
