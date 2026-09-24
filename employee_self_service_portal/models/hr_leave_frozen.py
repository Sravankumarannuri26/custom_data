from odoo import models, fields, api
import logging
_logger = logging.getLogger(__name__)


class HrLeaveTypeFrozen(models.Model):
    _inherit = 'hr.leave.type'

    x_is_frozen = fields.Boolean(
        string="Frozen Leave",
        compute='_compute_is_frozen',
        store=True,
    )

    @api.depends('name')
    def _compute_is_frozen(self):
        for lt in self:
            lt.x_is_frozen = (lt.name or '').strip().lower() == 'frozen leave'


class HrLeaveAllocationFrozen(models.Model):
    _inherit = 'hr.leave.allocation'

    x_frozen_unlocked = fields.Boolean(
        string="Unlock Frozen Leave",
        help="When enabled, the employee can apply for this frozen leave type."
    )
    x_type_is_frozen = fields.Boolean(
        related='holiday_status_id.x_is_frozen',
        string="Is Frozen Type",
        store=False,
    )


class HrLeaveBackup(models.Model):
    _inherit = 'hr.leave'

    x_backup_type = fields.Selection(
        [('internal', 'Within TechCarrot'),
         ('external', 'Outside TechCarrot')],
        string="Backup Type",
    )

    x_backup_employee_id = fields.Many2one(
        'hr.employee',
        string="Backup Person (Internal)",
    )

    x_backup_name = fields.Char(string="Backup Person Name")
    x_backup_email = fields.Char(string="Backup Person Email")

    x_backup_display = fields.Char(
        string="Backup Person",
        compute='_compute_x_backup_display',
    )

    @api.depends('x_backup_type', 'x_backup_employee_id', 'x_backup_name')
    def _compute_x_backup_display(self):
        for leave in self:
            if leave.x_backup_type == 'internal' and leave.x_backup_employee_id:
                leave.x_backup_display = f"{leave.x_backup_employee_id.name} (Internal)"
            elif leave.x_backup_type == 'external' and leave.x_backup_name:
                leave.x_backup_display = f"{leave.x_backup_name} (External)"
            else:
                leave.x_backup_display = "—"