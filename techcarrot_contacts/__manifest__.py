# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name": "TechCarrot Contacts Customization",
    "summary": "Development for TechCarrot",
    "category": "Sales",
    "version": "19.0.2",
    "sequence": 2,
    "author": "Ifensys",
    "website": "https://www.Ifensys.com",
    "depends": ['base','contacts','hr'],
    "data": ['security/ir.model.access.csv',
             'views/tec_partner_views.xml',
             'views/tec_reporting_views.xml',
             'views/tec_role_views.xml',],
    "application": True,
    "installable": True,
    "auto_install": False
}
