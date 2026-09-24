# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name": "TechCarrot CRM Customization",
    "summary": "Development for TechCarrot",
    "category": "Sales",
    "version": "15.0.1",
    "sequence": 2,
    "author": "Ifensys",
    "website": "https://www.Ifensys.com",
    "depends": ['base', 'crm','contacts'],
    "data": ['security/ir.model.access.csv',
             'views/tec_deal_type_views.xml',
             'views/tec_crm_pipeline_views.xml',
             'views/tec_crm_industry_views.xml',
             'views/tec_ist_member_views.xml',
             'views/tec_lead_status_views.xml',],
    "application": True,
    "installable": True,
    "auto_install": False
}
