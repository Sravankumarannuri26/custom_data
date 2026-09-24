from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    emp_code = fields.Char(
        string='Employee Code',
        help='Code from portal',
        copy=False,
        index=True
    )

    portal_sync_date = fields.Datetime(
        string='Last Portal Sync',
        readonly=True
    )

   # @api.model
   # def create(self, vals):
   #     employee = super(HrEmployee, self).create(vals)
   #     _logger.info(f" Created: {employee.name}")
   #     return employee
