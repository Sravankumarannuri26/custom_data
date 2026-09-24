from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import date
import logging

_logger = logging.getLogger(__name__)


class ComplianceProjectStage(models.Model):
    _name = 'compliance.project.stage'
    _description = 'Compliance Project Stage'
    _order = 'sequence, id'

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    fold = fields.Boolean(string="Folded in Kanban")

    _sql_constraints = [
        ('unique_project_stage_name', 'unique(name)', 'Project stage name must be unique!')
    ]

    @api.model
    def _init_default_stages(self):
        # 3 fixed stages
        stages = [
            {'name': 'In Progress', 'sequence': 1},
            {'name': 'Completed', 'sequence': 2},
            {'name': 'Cancelled', 'sequence': 3},
        ]

        for stage in stages:
            if not self.search([('name', '=', stage['name'])], limit=1):
                super().create(stage)
    # Prevent creating, editing, or deleting stages dynamically
    def create(self, vals):
        raise ValidationError("Project stages are fixed and cannot be created.")

    def write(self, vals):
        raise ValidationError("Project stages are fixed and cannot be modified.")

    def unlink(self):
        raise ValidationError("Project stages are fixed and cannot be deleted.")

# Compliance Project Model
class ComplianceProject(models.Model):
    _name = 'compliance.project'
    _description = 'Compliance Project'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Basic Project Fields
    name = fields.Char(string="Project Name", required=True)
    kanban_color = fields.Integer(string="Color Index", default=0)
    year = fields.Char(string="Year")

    tag_ids = fields.Many2many('compliance.project.tag', string="Tags")
    is_favorite = fields.Boolean(string="Favorite")

    stage_id = fields.Many2one(
        'compliance.project.stage',
        string='Stage',
        tracking=True,
        index=True,
        ondelete='restrict',
        default=lambda self: self._get_default_stage_id(),
        group_expand='_read_group_stage_ids',
    )

    task_ids = fields.One2many(
        'compliance.task',
        'compliance_project_id',
        string="Compliance Tasks"
    )

    open_task_count = fields.Integer(
        compute="_compute_task_counts",
        string="Open Tasks",
        store=False
    )
    closed_task_count = fields.Integer(
        compute="_compute_task_counts",
        string="Closed Tasks",
        store=False
    )

    assignee_ids = fields.Many2many('res.users', string="Assignees")

    @api.depends('task_ids.legend')
    def _compute_task_counts(self):
        # Computes number of open and closed tasks for each project.
        for project in self:
            project.open_task_count = len(
                project.task_ids.filtered(lambda t: t.legend == 'pending')
            )
            project.closed_task_count = len(
                project.task_ids.filtered(lambda t: t.legend in ('on_time', 'late'))
            )

    @api.model
    def _read_group_stage_ids(self, stages, domain, order=None, **kwargs):
        # Ensures all stages are shown in Kanban view even if empty.]
        return self.env['compliance.project.stage'].search(
            [],
            order=order or 'sequence, id'
        )

    @api.model
    def _get_default_stage_id(self):
        # Assign 'In Progress' stage by default on project creation.
        self.env['compliance.project.stage']._init_default_stages()
        return self.env['compliance.project.stage'].search(
            [], order='sequence, id', limit=1
        )

    @api.model_create_multi
    def create(self, vals_list):
        # Automatically assigns default stage when creating projects.
        self.env['compliance.project.stage']._init_default_stages()
        default_stage = self._get_default_stage_id()
        for vals in vals_list:
            if not vals.get('stage_id'):
                vals['stage_id'] = default_stage.id
        return super().create(vals_list)

    def write(self, vals):
        # Prevents marking a project as 'Completed' if there are still pending compliance tasks.
        if 'stage_id' in vals:
            completed_stage = self.env['compliance.project.stage'].search(
                [('name', '=', 'Completed')], limit=1
            )
            if completed_stage and vals['stage_id'] == completed_stage.id:
                for project in self:
                    if project.task_ids.filtered(lambda t: t.legend == 'pending'):
                        raise ValidationError(
                            "You cannot mark the project as Completed while there are open tasks."
                        )
        return super().write(vals)


