# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.date_utils import start_of
from odoo.tools.misc import formatLang

from dateutil.relativedelta import relativedelta
from math import ceil

class HrSalaryAttachment(models.Model):
    _inherit = 'hr.salary.attachment'

    currency_id = fields.Many2one('res.currency', string='Currency', required=True, readonly=False, related=False,
                                  default=lambda self: self.env.company.currency_id)
    date_estimated_end = fields.Date(
        'Estimated End Date', help='Approximated end date.'
    )

    # @api.constrains('currency_id')
    # def _check_currency(self):
    #     if any(attachment.currency_id != attachment.employee_ids[0].contract_id.currency_id for attachment in self.filtered(lambda x: x.employee_count == 1)):
    #         raise ValidationError(_("Salary attachment currency not match employee current contract currency."))

    # sriman removed and commented 'no_end_date' and its codefrom depends as this is removed in odoo 19
    # @api.depends('state', 'total_amount', 'monthly_amount', 'date_start')
    # def _compute_estimated_end(self):
    #     for record in self:
    #         if record.state not in ['close', 'cancel'] and record.has_total_amount and record.monthly_amount:
    #             date_estimated_end = start_of(record.date_start + relativedelta(months=ceil(record.remaining_amount / record.monthly_amount)),'month')
    #             record.date_estimated_end = date_estimated_end  - relativedelta(days=1)
    #             date_end = start_of(record.date_start + relativedelta(months=ceil(record.remaining_amount / record.monthly_amount)),'month')
    #             record.date_end = date_end - relativedelta(days=1)
    #         else:
    #             record.date_estimated_end = False
    #             record.date_end = False
    #         # if record.no_end_date == True:
    #         #     record.date_estimated_end = False
    #         #     record.date_end = False

class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    def _get_worked_day_lines_values(self, domain=None):
        self.ensure_one()
        res = []
        hours_per_day = self._get_worked_day_lines_hours_per_day()
        work_hours = self.version_id.get_work_hours(self.date_from, self.date_to, domain=domain)
        work_hours_ordered = sorted(work_hours.items(), key=lambda x: x[1])
        biggest_work = work_hours_ordered[-1][0] if work_hours_ordered else 0
        add_days_rounding = 0
        for work_entry_type_id, hours in work_hours_ordered:
            work_entry_type = self.env['hr.work.entry.type'].browse(work_entry_type_id)
            days = round(hours / hours_per_day, 5) if hours_per_day else 0
            if work_entry_type_id == biggest_work:
                days += add_days_rounding
            day_rounded = self._round_days(work_entry_type, days)
            add_days_rounding += (days - day_rounded)
            # DO NOT LOAD ATTENDACE IN PAYROLL FORM
            # REQUIREMENT FROM MOSESS/DANIEL
            # if work_entry_type.code !='WORK100':
            attendance_line = {
                'sequence': work_entry_type.sequence,
                'work_entry_type_id': work_entry_type_id,
                'number_of_days': day_rounded,
                'number_of_hours': hours,
            }
            res.append(attendance_line)

        # Sort by Work Entry Type sequence
        work_entry_type = self.env['hr.work.entry.type']
        return sorted(res, key=lambda d: work_entry_type.browse(d['work_entry_type_id']).sequence)

    def _get_worked_day_lines(self, domain=None, check_out_of_contract=True):
        """
        :returns: a list of dict containing the worked days values that should be applied for the given payslip
        """
        res = []
        # fill only if the contract as a working schedule linked
        self.ensure_one()
        contract = self.version_id
        if contract.resource_calendar_id:
            res = self._get_worked_day_lines_values(domain=domain)
            if not check_out_of_contract:
                return res

            # If the contract doesn't cover the whole month, create
            # worked_days lines to adapt the wage accordingly
            out_days, out_hours = 0, 0
            reference_calendar = self._get_out_of_contract_calendar()
            if self.date_from < contract.date_start:
                start = fields.Datetime.to_datetime(self.date_from)
                stop = fields.Datetime.to_datetime(contract.date_start) + relativedelta(days=-1, hour=23, minute=59)
                out_time = reference_calendar.get_work_duration_data(start, stop, compute_leaves=False, domain=['|', ('work_entry_type_id', '=', False), ('work_entry_type_id.is_leave', '=', False)])
                out_days += out_time['days']
                out_hours += out_time['hours']
            if contract.date_end and contract.date_end < self.date_to:
                start = fields.Datetime.to_datetime(contract.date_end) + relativedelta(days=1)
                stop = fields.Datetime.to_datetime(self.date_to) + relativedelta(hour=23, minute=59)
                out_time = reference_calendar.get_work_duration_data(start, stop, compute_leaves=False, domain=['|', ('work_entry_type_id', '=', False), ('work_entry_type_id.is_leave', '=', False)])
                out_days += out_time['days']
                out_hours += out_time['hours']

            if out_days or out_hours:
                work_entry_type = self.env.ref('hr_work_entry.hr_work_entry_type_out_of_contract')
                if work_entry_type.code =='OUT':
                    #DO NOT LOOK FOR SATUREDAY AND SUNDAY FOR OUT OF CONTRACT
                    #REQUIREMENT FROM MOSESS/DANIEL
                    if self.date_from < contract.date_start:
                        start = fields.Datetime.to_datetime(self.date_from)
                        stop = fields.Datetime.to_datetime(contract.date_start) + relativedelta(days=-1, hour=23, minute=59)
                        out_days = (start-stop).days
                    if contract.date_end and contract.date_end < self.date_to:
                        start = fields.Datetime.to_datetime(contract.date_end) + relativedelta(days=1)
                        stop = fields.Datetime.to_datetime(self.date_to) + relativedelta(hour=23, minute=59)
                        out_days = (start - stop).days
                res.append({
                    'sequence': work_entry_type.sequence,
                    'work_entry_type_id': work_entry_type.id,
                    'number_of_days': abs(out_days),
                    'number_of_hours': abs(out_hours),
                })
        return res
