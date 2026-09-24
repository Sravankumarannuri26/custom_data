from odoo import models, api


class HrEmployeeInheritUniqueEmail(models.Model):
    _inherit = 'hr.employee'

    @api.constrains('work_email')
    def _check_work_email(self):
        """Override to remove unique email constraint — allow same email on archived employees"""
        pass