from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import date, timedelta
import logging

_logger = logging.getLogger(__name__)
# Compliance Task Stage Model
class ComplianceTaskStage(models.Model):
    _name = 'compliance.task.stage'
    _description = 'Compliance Task Stage'
    _order = 'sequence, id'
    _rec_name = 'name'

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    fold = fields.Boolean(string="Folded in Kanban")

    # Prevent duplicate stage names
    _sql_constraints = [
        ('unique_stage_name', 'unique(name)', 'Stage name must be unique!')
    ]

    @api.model
    def ensure_fixed_stages(self):
        # Ensure exactly 3 fixed stages exist
        fixed_stages = [
            {'name': 'In Progress', 'sequence': 1},
            {'name': 'Done', 'sequence': 2},
            {'name': 'Cancelled', 'sequence': 3},
        ]
        existing = self.search([('name', 'in', [s['name'] for s in fixed_stages])])
        existing_names = existing.mapped('name')
        for stage in fixed_stages:
            if stage['name'] not in existing_names:
                super(ComplianceTaskStage, self).create(stage)

    # Prevent creating, editing, or deleting stages dynamically
    @api.model_create_multi
    def create(self, vals_list):
        raise ValidationError("You cannot create new stages. Only 3 fixed stages are allowed.")

    def write(self, vals):
        raise ValidationError("You cannot edit task stages. Only 3 fixed stages are allowed.")

    def unlink(self):
        raise ValidationError("You cannot delete task stages. Only 3 fixed stages are allowed.")

# Compliance Task Model
class ComplianceTask(models.Model):
    _name = 'compliance.task'
    _description = 'Compliance Task'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Basic Task Fields
    name = fields.Char(string="Compliance Name", required=True)
    compliance_project_id = fields.Many2one(
        'compliance.project',
        string="Compliance Project",
        required=True,
        ondelete='restrict'
    )
    location_id = fields.Many2one(
        'compliance.location.master',
        string="Location",
        required=True,
        ondelete='restrict'
    )
    company_id = fields.Many2one(
        'compliance.company.master',
        string="Company",
        required=True,
        ondelete='restrict'
    )
    manager_id = fields.Many2one(
        'res.users',
        string="Manager",
        required=True,
        ondelete='restrict'
    )
    assignee_ids = fields.Many2many(
        'res.users',
        string="Assignees",
        required=True,
        ondelete='restrict'
    )
    reporting_status = fields.Selection([
        ('on_time', 'Complied on time'),
        ('late', 'Complied after due'),
        ('overdue', 'Overdue'),
        ('in_progress', 'In Progress'),
    ])
    complied_on = fields.Date()
    due_on = fields.Date(required=True)
    legend = fields.Selection([
        ('on_time', 'On Time'),
        ('late', 'Late'),
        ('pending', 'Pending'),
    ])
    active = fields.Boolean(default=True)
    is_favorite = fields.Boolean(default=False)

    stage_id = fields.Many2one(
        'compliance.task.stage',
        string='Stage',
        tracking=True,
        index=True,
        ondelete='restrict',
        group_expand='_read_group_stage_ids',
        default=lambda self: self._get_default_stage_id()
    )

    compliance_month = fields.Selection(
        [
            ('january', 'January'),
            ('february', 'February'),
            ('march', 'March'),
            ('april', 'April'),
            ('may', 'May'),
            ('june', 'June'),
            ('july', 'July'),
            ('august', 'August'),
            ('september', 'September'),
            ('october', 'October'),
            ('november', 'November'),
            ('december', 'December'),
        ],
        string="Compliance Month",
        required=True 
    )
    remarks=fields.Text(string="Remarks")

    kanban_state = fields.Selection([
        ('normal', 'In Progress'),
        ('done', 'Ready'),
        ('blocked', 'Blocked'),
    ], default='normal', tracking=True)

    color = fields.Integer(string='Color Index')
    attachment_count = fields.Integer(compute='_compute_attachment_count', string='Attachment Count')

    # Kanban Helpers
    def _read_group_stage_ids(self, stages=None, domain=None, order=None):
        # Ensure fixed stages exist and return them for Kanban grouping.
        self.env['compliance.task.stage'].ensure_fixed_stages()
        return self.env['compliance.task.stage'].search([], order='sequence, id')

    @api.model
    def _get_default_stage_id(self):
        # Ensure the 3 fixed stages exist
        self.env['compliance.task.stage'].ensure_fixed_stages()

        # Assign 'In Progress' stage by default on task creation.
        stage = self.env['compliance.task.stage'].search([('name', '=', 'In Progress')], limit=1)
        return stage.id if stage else False

    # Create / Update Logic
    @api.model_create_multi
    def create(self, vals_list):
        # Ensure the 3 fixed stages exist
        self.env['compliance.task.stage'].ensure_fixed_stages()

        # Get the default "In Progress" stage
        default_stage = self.env['compliance.task.stage'].search([('name', '=', 'In Progress')], limit=1)

        for vals in vals_list:
            if not vals.get('stage_id') and default_stage:
                vals['stage_id'] = default_stage.id

        records = super(ComplianceTask, self).create(vals_list)
        records._apply_compliance_logic()
        return records

    def write(self, vals):
        # Enforce validation when marking task as Done and re-evaluate compliance logic when relevant fields change.
        if 'stage_id' in vals:
            done_stage = self.env['compliance.task.stage'].search([('name', '=', 'Done')], limit=1)
            if done_stage and vals['stage_id'] == done_stage.id:
                for task in self:
                    if not task.complied_on:
                        raise ValidationError("Please enter the Complied On date before marking the task as Done.")
        res = super().write(vals)
        if any(key in vals for key in ['stage_id', 'due_on', 'complied_on']):
            self._apply_compliance_logic()
        return res

    # CRON: Consolidated Email Reminders
    @api.model
    def cron_send_consolidated_task_reminders(self):

        today = fields.Date.today()
        trigger_days = {7, 5, 2, -2, -5, -7}

        # Fetch all relevant tasks
        tasks = self.search([
            ('reporting_status', 'in', ['overdue', 'in_progress']),
            ('active', '=', True),
            ('due_on', '!=', False),
            ('assignee_ids', '!=', False),
        ])
        _logger.info("Found %d eligible compliance tasks", len(tasks))
        if not tasks:
            _logger.info("No tasks found, cron exiting")
            return

        # Group tasks by user
        user_task_map = {}
        for task in tasks:
            for user in task.assignee_ids:
                user_task_map.setdefault(user, self.env['compliance.task'])
                user_task_map[user] |= task
        _logger.info("Grouped tasks for %d users", len(user_task_map))

        # Load email template
        template = self.env.ref(
            'compliance_tracker.email_template_compliance_reminder_assignee',
            raise_if_not_found=False
        )
        if not template:
            _logger.error("Consolidated reminder email template NOT FOUND")
            return

        # Process each user
        for user, user_tasks in user_task_map.items():
            # _logger.info("Preparing email input for user: %s <%s>", user.name, user.email)

            # Check for trigger tasks
            trigger_tasks = user_tasks.filtered(lambda t: (t.due_on - today).days in trigger_days)
            if not trigger_tasks:
                # _logger.info(" Skipping %s — no trigger-day tasks", user.email)
                continue

            task_lines = []
            for task in trigger_tasks:
                task_lines.append({
                    'name': task.name,
                    'project': task.compliance_project_id.name or '-',
                    'due_on': task.due_on.strftime('%d-%m-%Y'),
                    'status': dict(task._fields['reporting_status'].selection).get(task.reporting_status, task.reporting_status),
                    'days_remaining': (task.due_on - today).days,
                })

            ctx = {
                'assignee_name': user.name,
                'tasks': task_lines,
                'today': today,
            }

            res_id = trigger_tasks[0].id

            # Send email

            template.with_context(ctx).send_mail(
                res_id,
                force_send=True,
                email_values={
                    'email_to': user.email,
                }
            )

            # _logger.info("Email SENT to %s <%s>", user.name, user.email)


        # Manager escalation (overdue tasks only)

        # _logger.info("Processing manager escalations")

        manager_task_map = {}

        # Collect overdue tasks grouped by manager
        for task in tasks.filtered(lambda t: t.due_on and t.due_on < today and (t.due_on - today).days in trigger_days):
            manager = task.manager_id
            if not manager or not manager.email:
                # _logger.info("Skipping task %s — no manager or manager email", task.name)
                continue

            manager_task_map.setdefault(manager, self.env['compliance.task'])
            manager_task_map[manager] |= task

        if not manager_task_map:
            _logger.info("No overdue tasks for managers")
            return

        template_manager = self.env.ref(
            'compliance_tracker.email_template_compliance_reminder_manager',
            raise_if_not_found=False
        )
        if not template_manager:
            _logger.error("Manager reminder email template NOT FOUND")
            return

        # Send emails manager-wise
        for manager, manager_tasks in manager_task_map.items():
            # _logger.info("Preparing manager escalation email for: %s <%s>", manager.name, manager.email)
            task_lines = []
            for task in manager_tasks:
                task_lines.append({
                    'name': task.name,
                    'project': task.compliance_project_id.name or '-',
                    'assignees': ", ".join(task.assignee_ids.mapped('name')),
                    'due_on': task.due_on.strftime('%d-%m-%Y'),
                    'days_overdue': (today - task.due_on).days,
                })
            # Context passed directly to template
            ctx = {
                'manager_name': manager.name,
                'tasks': task_lines,
                'today': today,
            }

            res_id = manager_tasks[0].id  # must belong to template model

            # Let Odoo render & send
            template_manager.with_context(ctx).send_mail(
                res_id,
                force_send=True,
                email_values={'email_to': manager.email}
            )


    # Compliance Status Calculation
    def _apply_compliance_logic(self):
        # Determines legend & reporting status based on due date and complied date.
        today = date.today()
        for task in self:
            vals = {}
            if task.complied_on:
                if task.complied_on > task.due_on:
                    vals.update({'legend': 'late', 'reporting_status': 'late'})
                else:
                    vals.update({'legend': 'on_time', 'reporting_status': 'on_time'})
            elif task.due_on < today:
                vals.update({'legend': 'pending', 'reporting_status': 'overdue'})
            else:
                vals.update({'legend': 'pending', 'reporting_status': 'in_progress'})
            if vals:
                super(ComplianceTask, task).write(vals)

    # Attachment Counter
    def _compute_attachment_count(self):
        for record in self:
            record.attachment_count = self.env['ir.attachment'].search_count([
                ('res_model', '=', self._name),
                ('res_id', '=', record.id)
            ])
