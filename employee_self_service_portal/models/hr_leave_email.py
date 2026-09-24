from odoo import models, fields
from datetime import timedelta
import logging
from math import ceil
from odoo.tools import float_round
from pytz import utc

_logger = logging.getLogger(__name__)


class HrLeaveESS(models.Model):
    _inherit = 'hr.leave'

    state = fields.Selection(tracking=False)

    def _weekend_attendance_hours(self, calendar, date_from, date_to):
        if not calendar:
            return 0.0
        if not date_from.tzinfo:
            date_from = date_from.replace(tzinfo=utc)
        if not date_to.tzinfo:
            date_to = date_to.replace(tzinfo=utc)
        intervals = calendar._attendance_intervals_batch(
            date_from, date_to,
            domain=[('dayofweek', 'in', ('5', '6'))],
        )[False]
        return sum((stop - start).total_seconds() / 3600 for start, stop, meta in intervals)

    def _get_durations(self, check_leave_type=True, resource_calendar=None):
        result = super()._get_durations(
            check_leave_type=check_leave_type,
            resource_calendar=resource_calendar,
        )

        if not check_leave_type:
            return result

        for leave in self:
            if leave.id not in result:
                continue

            days, hours = result[leave.id]
            if not leave.date_from or not leave.date_to or not days:
                continue

            calendar = resource_calendar or leave.resource_calendar_id
            if not calendar:
                continue

            weekend_attendances = calendar.attendance_ids.filtered(
                lambda a: a.dayofweek in ('5', '6') and a.hour_to > a.hour_from
            )
            if not weekend_attendances:
                continue

            weekend_hours = self._weekend_attendance_hours(
                calendar, leave.date_from, leave.date_to
            )
            if not weekend_hours:
                continue

            hours_per_day = calendar.hours_per_day or (hours / days if days else 8.0)
            new_hours = max(hours - weekend_hours, 0.0)
            new_days = new_hours / hours_per_day if hours_per_day else 0.0

            if leave.leave_type_request_unit == 'day':
                new_days = ceil(new_days) if new_days else 0.0
            elif leave.request_unit_half and calendar.duration_based:
                new_days = float_round(new_days, precision_rounding=0.5)

            result[leave.id] = (new_days, new_hours)

        return result
    
    def _track_subtype(self, init_values):
        return False

    def activity_update(self):
        return super(HrLeaveESS, self.with_context(mail_dont_send=True)).activity_update()

    def message_post(self, **kwargs):
        body = kwargs.get('body') or ''
        if isinstance(body, str) and (
            'has been accepted' in body or 'has been refused' in body
        ):
            kwargs.pop('partner_ids', None)
            kwargs['mail_auto_delete'] = True
            self = self.with_context(
                mail_create_nosubscribe=True,
                mail_dont_send=True,
                mail_notify_force_send=False,
            )
        return super(HrLeaveESS, self).message_post(**kwargs)

    def _notify_manager(self):
        return

    def _ess_send_mail(self, template_xmlid, email_to, email_cc=None):
        if not email_to:
            return
        template = self.env.ref(template_xmlid, raise_if_not_found=False)
        if not template:
            return
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        cc = [e for e in (email_cc or []) if e]
        for leave in self:
            vals = {'email_to': email_to}
            if cc:
                vals['email_cc'] = ','.join(cc)
            template.with_context(base_url=base_url, mail_dont_send=False).sudo().send_mail(
                leave.id, force_send=True, email_values=vals
            )

    def action_approve(self, check_state=True):
        res = super().action_approve(check_state=check_state)
        for leave in self:
            if leave.state != 'validate':
                continue
            creator_user = leave.create_uid
            employee_user = leave.employee_id.user_id
            on_behalf = bool(
                employee_user and creator_user and employee_user.id != creator_user.id
            )

            if on_behalf:
                hr_dept = leave.env.company.leave_hr_department_email
                recipients = []
                for e in (leave.employee_id.work_email, hr_dept):
                    e = (e or '').strip()
                    if e and e.lower() not in [r.lower() for r in recipients]:
                        recipients.append(e)
                if recipients:
                    leave._ess_send_mail(
                        'employee_self_service_portal.email_template_leave_on_behalf',
                        ','.join(recipients),
                    )
            else:

                if not leave.env.context.get('_ess_approved_sent') and leave.employee_id.work_email:
                    leave._ess_send_mail(
                        'employee_self_service_portal.email_template_leave_approved',
                        leave.employee_id.work_email,
                    )
        return res

    def _ess_full_recipients(self):

        self.ensure_one()

        company = self.env.company
        emp = self.employee_id
        candidates = [
            emp.work_email,
            company.leave_hr_department_email,
            emp.line_manager_id.work_email if emp.line_manager_id else None,
            emp.parent_id.work_email if emp.parent_id else None,  # account manager
            company.leave_hr_manager_id.work_email if company.leave_hr_manager_id else None,
            company.leave_delivery_head_id.work_email if company.leave_delivery_head_id else None,
        ]
        if self.x_backup_type == 'internal' and self.x_backup_employee_id:
            candidates.append(self.x_backup_employee_id.work_email)


        seen, result = set(), []
        for e in candidates:
            e = (e or '').strip()
            if e and e.lower() not in seen:
                seen.add(e.lower())
                result.append(e)
        return result

    def action_refuse(self):
        res = super().action_refuse()
        for leave in self:
            recipients = leave._ess_full_recipients()
            if recipients:
                tmpl = leave.env.ref(
                    'employee_self_service_portal.email_template_leave_cancelled_hr',
                    raise_if_not_found=False
                )
                if tmpl:
                    base_url = leave.env['ir.config_parameter'].sudo().get_param('web.base.url')
                    tmpl.with_context(base_url=base_url).sudo().send_mail(
                        leave.id, force_send=True,
                        email_values={'email_to': ','.join(recipients)}
                    )
        return res


class HrLeaveAllocationESS(models.Model):
    _inherit = 'hr.leave.allocation'

    def message_post(self, **kwargs):
        kwargs['mail_auto_delete'] = True
        self = self.with_context(
            mail_create_nosubscribe=True,
            mail_dont_send=True,
            mail_notify_force_send=False,
        )
        return super().message_post(**kwargs)

    def activity_update(self):
        return super(HrLeaveAllocationESS,
                     self.with_context(mail_dont_send=True)).activity_update()