# -*- coding: utf-8 -*-
{
    'name': 'Portal User invite Email',
    'version': '19.0.1.0.0',
    'summary': 'Disable portal invitation email by overriding action_grant_access',
    'category': 'Tools',
    'author': 'Your Name',
    'depends': ['portal'],
    'data': ['data/invite_mail_template.xml'],
    'installable': True,
    'application': True,
    'auto_install': False,
}