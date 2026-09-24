from odoo import models, fields, api, _
from odoo.exceptions import UserError
import re
import logging

_logger = logging.getLogger(__name__)


class HrEmployeeInherit(models.Model):
    _inherit = 'hr.employee'

    emp_code = fields.Char(
        string='Emp Code',
        copy=False,
        index=True,
        store=True,
        help="Unique employee code (e.g., P0001, TCIP0012, BC0005)"
    )

    employee_code = fields.Char(
        string='Employee Code',
        copy=False,
        index=True,
        #readonly=True,
        store=True,
        help="Unique employee code (e.g., P0001, TCIP0012, BC0005)"
    )

    line_manager_id = fields.Many2one('hr.employee', string='Line Manager', copy=False)
    # SELECTION FIELDS - Shown as dropdowns in Odoo UI
    engagement_location = fields.Selection(
        [
            ('onsite', 'Onsite'),
            ('offshore', 'Offshore'),
            ('near-shore', 'Nearshore'),
        ],
        string='Engagement Location',
        ondelete={'onsite': 'set null', 'offshore': 'set null', 'near-shore': 'set null'}
    )

    payroll_location = fields.Selection([
        ('dubai-onsite', 'Dubai- Onsite'),
        ('dubai-offshore', 'Dubai-Offshore'),
        ('tcip-india', 'TCIP India'),
    ], string='Payroll',
        ondelete={'dubai-onsite': 'set null', 'dubai-offshore': 'set null', 'tcip-india': 'set null'}
    )

    employment_type = fields.Selection([
        ('permanent', 'Permanent'),
        ('temporary', 'Temporary'),
        ('bootcamp', 'Bootcamp'),
        ('seconded', 'Seconded'),
        ('freelancer', 'Freelancer'),
    ], string='Employment Type',
        ondelete={'permanent': 'set null', 'temporary': 'set null', 'bootcamp': 'set null',
                  'seconded': 'set null', 'freelancer': 'set null'}
    )

    @api.model
    def create(self, vals):
        """Auto-normalize fields from SharePoint before saving"""
        vals = self._normalize_sharepoint_fields(vals)
        res = super(HrEmployeeInherit, self).create(vals)
        return res

    def write(self, vals):
        """Auto-normalize fields from SharePoint before updating"""
        vals = self._normalize_sharepoint_fields(vals)
        res = super(HrEmployeeInherit, self).write(vals)
        return res

    def _normalize_sharepoint_fields(self, vals):
        """
        Normalize SharePoint string values to match Odoo selection values.
        Accepts ANY string format (UPPERCASE, lowercase, underscores, hyphens, spaces)

        Examples:
        - "OFFSHORE" → "offshore"
        - "Dubai_Onsite" → "dubai-onsite"
        - "Tcip INDIA" → "tcip-india"
        - "PERMANENt" → "permanent"
        """
        # Normalize engagement_location
        if 'engagement_location' in vals and vals['engagement_location']:
            raw = str(vals['engagement_location']).lower().strip()
            clean = raw.replace('-', '').replace('_', '').replace(' ', '')

            if clean == 'onsite':
                vals['engagement_location'] = 'onsite'
            elif clean == 'offshore':
                vals['engagement_location'] = 'offshore'
            elif clean in ['nearshore', 'nearshore']:
                vals['engagement_location'] = 'near-shore'
            else:
                _logger.warning(f" Unknown engagement_location: '{vals['engagement_location']}' - setting to False")
                vals['engagement_location'] = False

        # Normalize payroll_location
        if 'payroll_location' in vals and vals['payroll_location']:
            raw = str(vals['payroll_location']).lower().strip()
            clean = raw.replace('_', '-').replace(' ', '-')

            if 'dubai' in clean and 'onsite' in clean:
                vals['payroll_location'] = 'dubai-onsite'
            elif 'dubai' in clean and 'offshore' in clean:
                vals['payroll_location'] = 'dubai-offshore'
            elif 'tcip' in clean or 'india' in clean:
                vals['payroll_location'] = 'tcip-india'
            else:
                _logger.warning(f" Unknown payroll_location: '{vals['payroll_location']}' - setting to False")
                vals['payroll_location'] = False

        # Normalize employment_type
        if 'employment_type' in vals and vals['employment_type']:
            raw = str(vals['employment_type']).lower().strip()

            valid_types = ['permanent', 'temporary', 'bootcamp', 'seconded', 'freelancer']

            if raw in valid_types:
                vals['employment_type'] = raw
            else:
                _logger.warning(f" Unknown employment_type: '{vals['employment_type']}' - setting to False")
                vals['employment_type'] = False

        return vals

    def action_open_code_generation_wizard(self):
        """Open wizard to generate employee code"""
        self.ensure_one()

        if self.emp_code:
            raise UserError(_(
                'Employee Code already exists: %s\n'
                'Cannot generate a new code for this employee.'
            ) % self.emp_code)

        return {
            'name': _('Generate Employee Code'),
            'type': 'ir.actions.act_window',
            'res_model': 'employee.code.generation.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_employee_id': self.id,
                'default_engagement_location': self.engagement_location,
                'default_payroll_location': self.payroll_location,
                'default_employment_type': self.employment_type,
            }
        }

    def action_generate_employee_code(self):
        """BACKWARD COMPATIBILITY - redirects to wizard"""
        _logger.warning("action_generate_employee_code is deprecated.")
        return self.action_open_code_generation_wizard()

    def action_bulk_generate_employee_codes(self):
        """Generate employee codes for all employees without codes"""
        employees_without_code = self.search([
            '|',
            ('emp_code', '=', False),
            ('emp_code', '=', '')
        ])

        if not employees_without_code:
            raise UserError(_('All employees already have employee codes!'))

        incomplete_employees = employees_without_code.filtered(
            lambda e: not e.engagement_location or not e.payroll_location or not e.employment_type
        )

        if incomplete_employees:
            raise UserError(_(
                'Cannot generate codes in bulk. Missing classification fields:\n\n%s'
            ) % '\n'.join(incomplete_employees.mapped('name')))

        generated_count = 0
        for employee in employees_without_code:
            new_code = employee._generate_next_employee_code()
            employee.write({'emp_code': new_code})
            generated_count += 1

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Generated %d employee codes!') % generated_count,
                'type': 'success',
                'sticky': True,
            }
        }

    def _generate_next_employee_code(self):
        """Generate employee code based on classification fields"""
        prefix = self._get_employee_code_prefix()
        if not prefix:
            prefix = 'EMP'

        all_employees = self.search([
            ('emp_code', '!=', False),
            ('emp_code', '=like', f'{prefix}%')
        ])

        existing_codes = [emp.emp_code for emp in all_employees if emp.emp_code]
        max_number = 0
        for code in existing_codes:
            match = re.match(rf'^{re.escape(prefix)}(\d+)$', code)
            if match:
                number = int(match.group(1))
                max_number = max(max_number, number)

        next_number = max_number + 1
        return f"{prefix}{next_number}"

    def _get_employee_code_prefix(self):
        """Determine prefix based on classification"""
        engagement = self.engagement_location
        payroll = self.payroll_location
        emp_type = self.employment_type

        if emp_type == 'seconded':
            return 'PT'
        if emp_type == 'freelancer':
            return 'TFL'
        if emp_type == 'bootcamp':
            if engagement in ['onsite', 'near-shore'] and payroll == 'dubai-onsite':
                return 'BC'
            elif engagement == 'offshore' and payroll == 'dubai-offshore':
                return 'BCO'
            elif engagement == 'offshore' and payroll == 'tcip-india':
                return 'BCI'
        if engagement == 'offshore' and payroll == 'tcip-india' and emp_type == 'permanent':
            return 'TCIP'
        if engagement == 'offshore' and payroll == 'dubai-offshore':
            if emp_type in ['permanent', 'temporary']:
                return 'T'
        if engagement in ['onsite', 'near-shore'] and payroll == 'dubai-onsite' and emp_type == 'permanent':
            return 'P'
        if engagement in ['onsite', 'near-shore'] and payroll == 'dubai-onsite' and emp_type == 'temporary':
            return 'T'

        return 'EMP'

    @api.constrains('emp_code')
    def _check_employee_code_unique(self):
        """Ensure employee code is unique"""
        for employee in self:
            if employee.emp_code:
                duplicate = self.search([
                    ('emp_code', '=', employee.emp_code),
                    ('id', '!=', employee.id)
                ], limit=1)
                if duplicate:
                    raise UserError(_(
                        'Employee Code "%s" already exists for employee: %s'
                    ) % (employee.emp_code, duplicate.name))
