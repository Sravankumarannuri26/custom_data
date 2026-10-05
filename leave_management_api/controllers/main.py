import json
import re
import base64
import logging
from datetime import timedelta
import pytz
from markupsafe import Markup
from odoo import SUPERUSER_ID, http, fields
from odoo.http import request
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

API_KEY = "dd7ef9db2080651a656e5a9dbfed5a03ef9616a7"


class LeaveManagementAPI(http.Controller):

    # ------------------------------------------------------------------
    # generic helpers
    # ------------------------------------------------------------------

    def _check_auth(self):
        auth_header = request.httprequest.headers.get('Authorization', '')
        token = auth_header.replace('Bearer ', '').strip()
        return token == API_KEY

    def _json(self, payload, status=200):
        return request.make_response(
            json.dumps(payload),
            headers={'Content-Type': 'application/json'},
            status=status,
        )

    def _unauthorized(self):
        return self._json({'error': 'Unauthorized'}, 401)

    def _get_employee(self, email):
        return request.env['hr.employee'].sudo().search([('work_email', '=', email)], limit=1)

    # ------------------------------------------------------------------
    # service-user helpers (all writes run as the integration user)
    # ------------------------------------------------------------------

    def _service_user(self):
        uid = int(request.env['ir.config_parameter'].sudo().get_param('ess_integration.service_user_id') or 0)
        user = request.env['res.users'].sudo().browse(uid)
        return user if user.exists() else None

    def _as_service(self, rec):
        user = self._service_user()
        if not user:
            _logger.warning("ess_integration.service_user_id is not set; falling back to plain sudo")
            return rec.sudo()
        return rec.with_user(user).sudo()

    def _audit_note(self, leave, text, employee, extra=None):
        body = Markup("%s <b>%s</b> (%s)") % (text, employee.name or '', employee.work_email or '')
        if extra:
            body += Markup("<br/>Reason: %s") % extra
        self._as_service(leave).message_post(body=body, subtype_xmlid='mail.mt_note')

    # ------------------------------------------------------------------
    # friendly errors
    # ------------------------------------------------------------------

    def _friendly_leave_error(self, raw):
        raw_l = (raw or '').lower()
        if 'no valid allocation' in raw_l:
            return ("You don't have enough leave balance for this request. "
                    "Please check your available days or contact HR.")
        if 'overlap' in raw_l or 'already' in raw_l:
            return ("This request overlaps with an existing leave. "
                    "Please choose different dates.")
        if 'duration' in raw_l:
            return "The selected dates don't include any valid working days."
        return raw

    def _friendly_cancel_error(self, raw):
        raw_l = (raw or '').lower()
        if 'past' in raw_l or 'in the past' in raw_l:
            return ("You can't cancel a leave request whose dates are in the past. "
                    "Please contact HR if something needs to be corrected.")
        if 'delete' in raw_l or 'unlink' in raw_l:
            return ("This leave request can't be cancelled directly. "
                    "Please contact HR for help.")
        return "Couldn't cancel this leave request. Please try again or contact HR."

    # ------------------------------------------------------------------
    # balance helpers
    # ------------------------------------------------------------------

    def _ess_net_balance(self, employee, leave_type):
        Alloc = request.env['hr.leave.allocation'].sudo()
        Leave = request.env['hr.leave'].sudo()
        allocated = sum(Alloc.search([
            ('employee_id', '=', employee.id), ('holiday_status_id', '=', leave_type.id),
            ('state', '=', 'validate'),
        ]).mapped('number_of_days'))
        committed = sum(Leave.search([
            ('employee_id', '=', employee.id), ('holiday_status_id', '=', leave_type.id),
            ('state', 'not in', ['draft', 'refuse', 'cancel']),
        ]).mapped('number_of_days'))
        return allocated - committed

    def _get_leave_balances(self, employee):
        leave_types = request.env['hr.leave.type'].with_context(
            employee_id=employee.id
        ).sudo().search([('active', '=', True)])

        unlocked_ids = request.env['hr.leave.allocation'].sudo().search([
            ('employee_id', '=', employee.id), ('state', '=', 'validate'),
            ('x_frozen_unlocked', '=', True), ('holiday_status_id.x_is_frozen', '=', True),
        ]).mapped('holiday_status_id').ids

        balances = []
        for idx, lt in enumerate(leave_types):
            used = lt.leaves_taken
            is_accrual = request.env['hr.leave.allocation'].sudo().search_count([
                ('employee_id', '=', employee.id), ('holiday_status_id', '=', lt.id),
                ('state', '=', 'validate'), ('allocation_type', '=', 'accrual'),
            ]) > 0
            remaining = self._ess_net_balance(employee, lt) if is_accrual else lt.virtual_remaining_leaves
            has_allocation = request.env['hr.leave.allocation'].sudo().search_count([
                ('employee_id', '=', employee.id), ('holiday_status_id', '=', lt.id), ('state', '=', 'validate'),
            ]) > 0
            if not (has_allocation or used > 0 or remaining != 0):
                continue
            balances.append({
                'id': lt.id, 'name': lt.name, 'max_days': lt.max_leaves, 'used': used,
                'remaining': remaining, 'allows_negative': getattr(lt, 'allows_negative', False),
                'color_slot': lt.color if lt.color else idx,
                'is_frozen': getattr(lt, 'x_is_frozen', False),
                'is_unlocked': lt.id in unlocked_ids,
            })
        return balances

    @http.route('/api/ess/leave_summary', type='http', auth='public', methods=['GET'], csrf=False)
    def get_leave_summary(self, **kwargs):
        if not self._check_auth():
            return self._unauthorized()

        employee = self._get_employee(kwargs.get('email'))
        if not employee:
            return self._json({'error': 'Employee not found'}, 404)

        balances = self._get_leave_balances(employee)
        Leave = request.env['hr.leave'].sudo()
        return self._json({
            'employee': employee.name,
            'pending_count': Leave.search_count([
                ('employee_id', '=', employee.id), ('state', 'in', ['confirm', 'validate1'])]),
            'approved_count': Leave.search_count([
                ('employee_id', '=', employee.id), ('state', '=', 'validate')]),
            # same rule as the old dashboard: Annual Leave only
            'balance_days': round(sum(
                b['remaining'] for b in balances if 'annual' in b['name'].lower()
            ), 1),
        })

    def _ess_leave_balance_for(self, employee, leave_type):
        is_accrual = request.env['hr.leave.allocation'].sudo().search_count([
            ('employee_id', '=', employee.id), ('holiday_status_id', '=', leave_type.id),
            ('state', '=', 'validate'), ('allocation_type', '=', 'accrual'),
        ]) > 0
        if is_accrual:
            return self._ess_net_balance(employee, leave_type)
        return leave_type.with_context(employee_id=employee.id).sudo().virtual_remaining_leaves

    def _ess_count_workdays(self, date_from, date_to):
        if not date_from or not date_to or date_to < date_from:
            return 0
        days = 0
        cur = date_from
        while cur <= date_to:
            if cur.weekday() < 5:
                days += 1
            cur += timedelta(days=1)
        return days

    def _ess_leave_notify_recipients(self, employee):
        company = employee.company_id.sudo()
        emp = employee.sudo()
        candidates = [
            emp.work_email, company.leave_hr_department_email,
            emp.line_manager_id.work_email if emp.line_manager_id else None,
            emp.parent_id.work_email if emp.parent_id else None,
            company.leave_hr_manager_id.work_email if company.leave_hr_manager_id else None,
            company.leave_delivery_head_id.work_email if company.leave_delivery_head_id else None,
        ]
        seen, result = set(), []
        for email in candidates:
            e = (email or '').strip()
            if e and e.lower() not in seen:
                seen.add(e.lower())
                result.append(e)
        return result

    # ------------------------------------------------------------------
    # GET /api/ess/leaves
    # ------------------------------------------------------------------

    @http.route('/api/ess/leaves', type='http', auth='public', methods=['GET'], csrf=False)
    def get_leaves(self, **kwargs):
        if not self._check_auth():
            return self._unauthorized()

        employee = self._get_employee(kwargs.get('email'))
        if not employee:
            return self._json({'error': 'Employee not found'}, 404)

        balances = self._get_leave_balances(employee)

        leave_types = request.env['hr.leave.type'].with_context(
            employee_id=employee.id
        ).sudo().search([('active', '=', True)])
        unlocked_ids = request.env['hr.leave.allocation'].sudo().search([
            ('employee_id', '=', employee.id), ('state', '=', 'validate'),
            ('x_frozen_unlocked', '=', True), ('holiday_status_id.x_is_frozen', '=', True),
        ]).mapped('holiday_status_id').ids

        def _selectable(lt):
            if lt.max_leaves <= 0:
                return False
            if getattr(lt, 'x_is_frozen', False) and lt.id not in unlocked_ids:
                return False
            return True

        leave_types_out = [{
            'id': lt.id, 'name': lt.name,
            'request_unit': lt.request_unit,
            'support_document': bool(getattr(lt, 'support_document', False)),
        } for lt in leave_types.filtered(_selectable)]

        filterby = kwargs.get('filterby', 'all')
        sortby = kwargs.get('sortby', 'date')
        page = max(int(kwargs.get('page', 1) or 1), 1)
        per_page = 5

        sort_map = {'date': 'date_from desc', 'state': 'state', 'type': 'holiday_status_id'}
        filter_map = {
            'all': [], 'pending': [('state', 'in', ['draft', 'confirm', 'validate1'])],
            'approved': [('state', '=', 'validate')], 'rejected': [('state', '=', 'refuse')],
            'cancelled': [('state', '=', 'cancel')],
        }
        order = sort_map.get(sortby, 'date_from desc')
        domain = [('employee_id', '=', employee.id)] + filter_map.get(filterby, [])

        Leave = request.env['hr.leave'].sudo()
        total_count = Leave.search_count(domain)
        total_pages = (total_count + per_page - 1) // per_page
        if total_pages and page > total_pages:
            page = total_pages
        offset = (page - 1) * per_page
        leave_requests = Leave.search(domain, order=order, limit=per_page, offset=offset)

        requests_out = [{
            'id': lv.id,
            'leave_type': lv.holiday_status_id.name,
            'date_from': lv.date_from.strftime('%d/%m/%Y') if lv.date_from else None,
            'date_to': lv.date_to.strftime('%d/%m/%Y') if lv.date_to else None,
            'number_of_days': lv.number_of_days,
            'state': lv.state,
            'create_date': lv.create_date.strftime('%d/%m/%Y') if lv.create_date else None,
        } for lv in leave_requests]

        all_active = Leave.search([
            ('employee_id', '=', employee.id), ('state', 'not in', ['refuse', 'cancel']),
        ])
        active_ranges = [{
            'from': lv.date_from.strftime('%Y-%m-%d') if lv.date_from else None,
            'to': lv.date_to.strftime('%Y-%m-%d') if lv.date_to else None,
        } for lv in all_active]

        backup_employees = request.env['hr.employee'].sudo().search([
            ('id', '!=', employee.id), ('active', '=', True),
        ], order='name')
        backup_out = [{'id': e.id, 'name': e.name} for e in backup_employees]

        holiday_recs = request.env['resource.calendar.leaves'].sudo().search([('resource_id', '=', False)])
        holiday_map = {}
        user_tz = pytz.timezone(employee.user_id.tz or 'UTC') if employee.user_id else pytz.UTC
        for h in holiday_recs:
            if not h.date_from:
                continue
            start = h.date_from
            end = h.date_to or h.date_from
            total_days = max(int(round((end - start).total_seconds() / 86400)), 1)
            for i in range(total_days):
                slice_mid = start + timedelta(days=i, hours=12)
                local_mid = pytz.utc.localize(slice_mid).astimezone(user_tz)
                holiday_map[local_mid.date().strftime('%Y-%m-%d')] = h.name or 'Public Holiday'

        line_manager = None
        lm_emp = employee.line_manager_id
        if lm_emp and lm_emp.user_id:
            lm = lm_emp.user_id
            line_manager = {
                'name': lm.name,
                'email': lm.email or '',
                'phone': lm.partner_id.phone or '',
                'job_title': lm_emp.job_id.name if lm_emp.job_id else '',
            }

        return self._json({
            'employee': employee.name,
            'balances': balances,
            'leave_types': leave_types_out,
            'leave_requests': requests_out,
            'page': page, 'total_pages': total_pages, 'total_count': total_count,
            'filterby': filterby, 'sortby': sortby,
            'active_leave_ranges': active_ranges,
            'backup_employees': backup_out,
            'holiday_map': holiday_map,
            'line_manager': line_manager,
            'approval_required': employee.company_id.leave_approval_required,
        })

    # ------------------------------------------------------------------
    # POST /api/ess/leaves/submit
    # ------------------------------------------------------------------

    @http.route('/api/ess/leaves/submit', type='http', auth='public', methods=['POST'], csrf=False)
    def submit_leave(self, **post):
        if not self._check_auth():
            return self._unauthorized()

        employee = self._get_employee(post.get('email'))
        if not employee:
            return self._json({'success': False, 'error': 'Employee not found'}, 404)

        approval_required = employee.company_id.leave_approval_required
        if approval_required and not employee.line_manager_id:
            return self._json({
                'success': False,
                'error': "You cannot apply for leave because no line manager is assigned. Please contact HR.",
            })

        leave_type_id = post.get('leave_type_id')
        date_from_str = post.get('date_from')
        date_to_str = post.get('date_to')
        reason = (post.get('reason') or '').strip()
        is_half_day = post.get('is_half_day') == '1'
        from_period = post.get('request_date_from_period') or 'am'
        to_period = post.get('request_date_to_period') or 'pm'

        if not leave_type_id or not date_from_str or not date_to_str:
            return self._json({'success': False, 'error': 'Please fill all required fields'})

        try:
            date_from_obj = fields.Date.from_string(date_from_str)
            date_to_obj = fields.Date.from_string(date_to_str)
            if date_to_obj < date_from_obj:
                return self._json({'success': False, 'error': 'End date cannot be before start date'})

            overlapping = request.env['hr.leave'].sudo().search([
                ('employee_id', '=', employee.id),
                ('state', 'not in', ['refuse', 'draft', 'cancel']),
                ('date_from', '<=', fields.Datetime.from_string(str(date_to_obj) + ' 23:59:59')),
                ('date_to', '>=', fields.Datetime.from_string(str(date_from_obj) + ' 00:00:00')),
            ], limit=1)
            if overlapping:
                overlap_from = overlapping.date_from.strftime('%d %b %Y') if overlapping.date_from else ''
                overlap_to = overlapping.date_to.strftime('%d %b %Y') if overlapping.date_to else ''
                return self._json({
                    'success': False,
                    'error': f"You already have a leave request from {overlap_from} to {overlap_to}. Overlapping dates are not allowed.",
                })
        except Exception:
            return self._json({'success': False, 'error': 'Invalid date format'})

        try:
            leave_type_id_int = int(leave_type_id)
            leave_type = request.env['hr.leave.type'].sudo().browse(leave_type_id_int)
            if not leave_type.exists():
                return self._json({'success': False, 'error': 'Invalid leave type selected'})
        except Exception:
            return self._json({'success': False, 'error': 'Invalid leave type'})

        attachment = request.httprequest.files.get('leave_attachment')
        has_file = bool(attachment and attachment.filename)
        if getattr(leave_type, 'support_document', False) and not has_file:
            return self._json({'success': False, 'error': 'A supporting document is required for this leave type.'})

        if has_file:
            allowed_exts = ('.pdf', '.doc', '.docx', '.png', '.jpg', '.jpeg', '.xlsx', '.txt')
            if not attachment.filename.lower().endswith(allowed_exts):
                return self._json({
                    'success': False,
                    'error': 'Invalid file type. Allowed: PDF, DOC, DOCX, PNG, JPG, JPEG, XLSX, TXT.',
                })
            attachment.seek(0, 2)
            file_size = attachment.tell()
            attachment.seek(0)
            if file_size > 10 * 1024 * 1024:
                return self._json({'success': False, 'error': 'File is too large. Maximum allowed size is 10MB.'})

        if getattr(leave_type, 'x_is_frozen', False):
            unlocked = request.env['hr.leave.allocation'].sudo().search_count([
                ('employee_id', '=', employee.id), ('holiday_status_id', '=', leave_type.id),
                ('state', '=', 'validate'), ('x_frozen_unlocked', '=', True),
            ])
            if not unlocked:
                return self._json({
                    'success': False,
                    'error': 'This leave type is currently locked. Please contact HR to request access.',
                })

        try:
            requested_days = self._ess_count_workdays(date_from_obj, date_to_obj)
            if is_half_day and requested_days == 1:
                requested_days = 0.5
            current_balance = self._ess_leave_balance_for(employee, leave_type)
            allowed_excess = leave_type.max_allowed_negative if leave_type.allows_negative else 0
            if current_balance - requested_days < -allowed_excess:
                return self._json({
                    'success': False,
                    'error': 'You do not have enough leave balance for this request. Please reach out to HR for support.',
                })
        except Exception:
            return self._json({
                'success': False,
                'error': 'Could not verify your leave balance. Please reach out to HR for support.',
            })

        backup_type = (post.get('backup_type') or '').strip()
        backup_employee_id = post.get('backup_employee_id')
        backup_name = (post.get('backup_name') or '').strip()
        backup_email = (post.get('backup_email') or '').strip()
        backup_required = date_to_obj > fields.Date.today()

        if backup_required:
            if backup_type == 'internal':
                if not backup_employee_id:
                    return self._json({'success': False, 'error': 'Please select a backup person for this future-dated leave.'})
            elif backup_type == 'external':
                if not backup_name or not backup_email:
                    return self._json({'success': False, 'error': 'Please provide both the name and email of your external backup.'})
                if not re.match(r"^[A-Za-z .'\-]{2,100}$", backup_name):
                    return self._json({
                        'success': False,
                        'error': 'Backup person name can only contain letters, spaces, hyphens, apostrophes, and periods (2-100 characters).',
                    })
                if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", backup_email):
                    return self._json({'success': False, 'error': 'Please enter a valid email address for the external backup.'})
            else:
                return self._json({'success': False, 'error': 'Please nominate a backup person for this future-dated leave.'})

        try:
            leave_vals = {
                'employee_id': employee.id,
                'holiday_status_id': leave_type_id_int,
                'request_date_from': date_from_obj,
                'request_date_to': date_to_obj,
                'name': reason or '/',
                'x_ess_applicant_id': employee.id,
            }
            if leave_type.request_unit == 'half_day':
                leave_vals['request_date_from_period'] = from_period
                leave_vals['request_date_to_period'] = to_period

            leave = self._as_service(request.env['hr.leave']).create(leave_vals)
            self._audit_note(leave, "Applied via ESS Portal by", employee)

            if backup_required and backup_type:
                backup_vals = {'x_backup_type': backup_type}
                if backup_type == 'internal' and backup_employee_id:
                    backup_vals['x_backup_employee_id'] = int(backup_employee_id)
                elif backup_type == 'external':
                    backup_vals['x_backup_name'] = backup_name
                    backup_vals['x_backup_email'] = backup_email
                leave.write(backup_vals)

            if has_file:
                attachment.seek(0)
                content = attachment.read()
                if len(content) <= 10 * 1024 * 1024:
                    self._as_service(request.env['ir.attachment']).create({
                        'name': attachment.filename, 'type': 'binary',
                        'datas': base64.b64encode(content),
                        'res_model': 'hr.leave', 'res_id': leave.id,
                        'mimetype': attachment.mimetype,
                    })

            if not approval_required:
                try:
                    leave_company = employee.company_id
                    leave.with_company(leave_company).with_context(
                        allowed_company_ids=[leave_company.id],
                        _ess_approved_sent=True, _ess_negative_hr_sent=True,
                    ).action_approve()
                except Exception:
                    request.env.cr.rollback()
                    return self._json({
                        'success': False,
                        'error': 'Could not process your leave. Please reach out to HR for support.',
                    })

            try:
                recipients = self._ess_leave_notify_recipients(employee)
                if recipients:
                    template = request.env.ref('leave_management_api.email_template_leave_applied_notification', raise_if_not_found=False)
                    if template:
                        base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
                        self._as_service(template).with_context(base_url=base_url).send_mail(
                            leave.id, force_send=True, email_values={'email_to': ','.join(recipients)}
                        )
            except Exception:
                _logger.exception("ESS Leave: applied notification failed for leave %s", leave.id)

            try:
                if (leave.x_backup_type == 'internal' and leave.x_backup_employee_id
                        and leave.x_backup_employee_id.work_email):
                    bk_template = request.env.ref('leave_management_api.email_template_leave_backup_notification', raise_if_not_found=False)
                    if bk_template:
                        base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
                        self._as_service(bk_template).with_context(base_url=base_url).send_mail(
                            leave.id, force_send=True,
                            email_values={'email_to': leave.x_backup_employee_id.work_email}
                        )
            except Exception:
                _logger.exception("ESS Leave: backup notification failed for leave %s", leave.id)

            return self._json({'success': True, 'leave_id': leave.id, 'auto_approved': not approval_required})

        except ValidationError as ve:
            request.env.cr.rollback()
            raw_msg = ve.args[0] if ve.args else str(ve)
            return self._json({'success': False, 'error': self._friendly_leave_error(raw_msg)})
        except Exception:
            _logger.exception("ESS Leave submit failed for %s", employee.name)
            request.env.cr.rollback()
            return self._json({'success': False, 'error': 'Failed to submit leave. Please try again.'})

    # ------------------------------------------------------------------
    # GET /api/ess/leaves/<id>
    # ------------------------------------------------------------------

    @http.route('/api/ess/leaves/<int:leave_id>', type='http', auth='public', methods=['GET'], csrf=False)
    def get_leave_detail(self, leave_id, **kwargs):
        if not self._check_auth():
            return self._unauthorized()

        employee = self._get_employee(kwargs.get('email'))
        if not employee:
            return self._json({'error': 'Employee not found'}, 404)

        leave = request.env['hr.leave'].sudo().search([
            ('id', '=', leave_id), ('employee_id', '=', employee.id),
        ], limit=1)
        if not leave:
            return self._json({'error': 'Leave request not found'}, 404)

        state_map = {
            'draft': 'Draft', 'confirm': 'Pending Approval', 'validate1': 'Pending Approval',
            'validate': 'Approved', 'refuse': 'Rejected',
        }
        state_label = state_map.get(leave.state, 'Unknown')

        attachments = request.env['ir.attachment'].sudo().search([
            ('res_model', '=', 'hr.leave'), ('res_id', '=', leave.id),
        ])
        attachments_out = []
        for att in attachments:
            if not att.access_token:
                att.generate_access_token()
            attachments_out.append({'id': att.id, 'name': att.name, 'access_token': att.access_token})

        line_manager = None
        if employee.line_manager_id and employee.line_manager_id.user_id:
            lm = employee.line_manager_id.user_id
            line_manager = {'name': lm.name, 'email': lm.email}

        can_cancel = bool(
            leave.state in ('draft', 'confirm', 'validate1', 'validate')
            and leave.request_date_from and leave.request_date_from > fields.Date.today()
        )

        day_period = None
        if (leave.request_unit_half and leave.date_from and leave.date_to
                and leave.date_from.date() == leave.date_to.date()):
            if leave.request_date_from_period == leave.request_date_to_period:
                day_period = 'Morning' if leave.request_date_from_period == 'am' else 'Afternoon'
            else:
                day_period = 'Full Day'

        # 'name' is masked for non-HR users; read it as superuser
        reason_raw = request.env['hr.leave'].with_user(SUPERUSER_ID).sudo().browse(leave.id).read(['name'])
        reason_value = reason_raw[0]['name'] if reason_raw else None

        return self._json({
            'id': leave.id,
            'leave_type': leave.holiday_status_id.name,
            'number_of_days': leave.number_of_days,
            'date_from': leave.date_from.strftime('%d %B %Y') if leave.date_from else None,
            'date_to': leave.date_to.strftime('%d %B %Y') if leave.date_to else None,
            'create_date': leave.create_date.strftime('%d %B %Y, %H:%M') if leave.create_date else None,
            'reason': reason_value if reason_value and reason_value != '/' else None,
            'state': leave.state,
            'state_label': state_label,
            'day_period': day_period,
            'employee_name': employee.name,
            'attachments': attachments_out,
            'line_manager': line_manager,
            'can_cancel': can_cancel,
            'refuse_reason': getattr(leave, 'reason_refusal', None) or getattr(leave, 'refuse_reason', None) or None,
        })

    # ------------------------------------------------------------------
    # POST /api/ess/leaves/<id>/cancel
    # ------------------------------------------------------------------

    @http.route('/api/ess/leaves/<int:leave_id>/cancel', type='http', auth='public', methods=['POST'], csrf=False)
    def cancel_leave(self, leave_id, **post):
        if not self._check_auth():
            return self._unauthorized()

        employee = self._get_employee(post.get('email'))
        if not employee:
            return self._json({'success': False, 'error': 'Employee not found'}, 404)

        leave = request.env['hr.leave'].sudo().search([
            ('id', '=', leave_id), ('employee_id', '=', employee.id),
        ], limit=1)
        if not leave:
            return self._json({'success': False, 'error': 'Leave request not found'}, 404)

        if leave.state in ('cancel', 'refuse'):
            return self._json({'success': False, 'error': 'This leave is already cancelled.'})

        start_date = leave.request_date_from or (leave.date_from.date() if leave.date_from else None)
        if not start_date or start_date <= fields.Date.today():
            return self._json({
                'success': False,
                'error': 'This leave can no longer be cancelled because it has already started or is in the past. Please contact HR.',
            })

        try:
            self._as_service(leave).with_context(_ess_selfcancel=True)._action_user_cancel('Cancelled by employee via portal')
            self._audit_note(leave, "Cancelled via ESS Portal by", employee)

            try:
                recipients = []
                for e in (employee.company_id.leave_hr_department_email, employee.work_email):
                    e = (e or '').strip()
                    if e and e not in recipients:
                        recipients.append(e)
                if recipients:
                    tmpl = request.env.ref('leave_management_api.email_template_leave_cancelled_self', raise_if_not_found=False)
                    if tmpl:
                        base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
                        self._as_service(tmpl).with_context(base_url=base_url).send_mail(
                            leave.id, force_send=True, email_values={'email_to': ','.join(recipients)}
                        )
            except Exception:
                _logger.exception("ESS Cancel: email failed for leave %s", leave.id)

            return self._json({'success': True})

        except Exception as e:
            request.env.cr.rollback()
            return self._json({'success': False, 'error': self._friendly_cancel_error(str(e))})

    # ------------------------------------------------------------------
    # POST /api/ess/leaves/<id>/remind
    # ------------------------------------------------------------------

    @http.route('/api/ess/leaves/<int:leave_id>/remind', type='http', auth='public', methods=['POST'], csrf=False)
    def remind_leave(self, leave_id, **post):
        if not self._check_auth():
            return self._unauthorized()

        employee = self._get_employee(post.get('email'))
        if not employee:
            return self._json({'success': False, 'error': 'Employee not found'}, 404)

        leave = request.env['hr.leave'].sudo().search([
            ('id', '=', leave_id), ('employee_id', '=', employee.id),
        ], limit=1)
        if not leave:
            return self._json({'success': False, 'error': 'Leave request not found'}, 404)

        if leave.state not in ('confirm', 'validate1'):
            return self._json({'success': False, 'error': 'Reminder can only be sent for pending leaves'})

        try:
            template = request.env.ref('leave_management_api.email_template_leave_reminder', raise_if_not_found=False)
            manager_email = employee.line_manager_id.work_email if employee.line_manager_id else False
            if template and manager_email:
                self._as_service(template).send_mail(
                    leave.id, force_send=True, email_values={'email_to': manager_email}
                )
                self._audit_note(leave, "Reminder sent via ESS Portal by", employee)
            return self._json({'success': True})
        except Exception:
            _logger.exception("ESS Remind failed for leave %s", leave.id)
            return self._json({'success': False, 'error': 'Failed to send reminder. Please try again.'})

    # ------------------------------------------------------------------
    # manager approvals
    # ------------------------------------------------------------------

    def _is_line_manager(self, employee):
        if not employee.user_id:
            return False
        return request.env['hr.employee'].sudo().search_count([
            ('line_manager_id.user_id', '=', employee.user_id.id),
        ]) > 0

    def _get_approvable_leave(self, leave_id, manager_employee):
        leave = request.env['hr.leave'].sudo().browse(int(leave_id))
        if not leave.exists():
            return False
        mgr_user = leave.employee_id.line_manager_id.user_id
        if not mgr_user or not manager_employee.user_id or mgr_user.id != manager_employee.user_id.id:
            return False
        return leave

    @http.route('/api/ess/approvals/summary', type='http', auth='public', methods=['GET'], csrf=False)
    def get_approvals_summary(self, **kwargs):
        if not self._check_auth():
            return self._unauthorized()

        employee = self._get_employee(kwargs.get('email'))
        if not employee:
            return self._json({'error': 'Employee not found'}, 404)

        if not self._is_line_manager(employee):
            return self._json({'is_line_manager': False})

        base = [('employee_id.line_manager_id.user_id', '=', employee.user_id.id)]
        Leave = request.env['hr.leave'].sudo()
        return self._json({
            'is_line_manager': True,
            'pending_count': Leave.search_count(base + [('state', '=', 'confirm')]),
            'approved_count': Leave.search_count(base + [('state', 'in', ['validate1', 'validate'])]),
            'rejected_count': Leave.search_count(base + [('state', '=', 'refuse')]),
        })

    @http.route('/api/ess/approvals', type='http', auth='public', methods=['GET'], csrf=False)
    def get_approvals(self, **kwargs):
        if not self._check_auth():
            return self._unauthorized()

        employee = self._get_employee(kwargs.get('email'))
        if not employee:
            return self._json({'error': 'Employee not found'}, 404)

        if not self._is_line_manager(employee):
            return self._json({'error': 'Not a line manager'}, 403)

        filterby = kwargs.get('filterby', 'pending')
        filter_map = {
            'pending': [('state', '=', 'confirm')],
            'approved': [('state', 'in', ['validate1', 'validate'])],
            'rejected': [('state', '=', 'refuse')],
        }
        domain = [
            ('employee_id.line_manager_id.user_id', '=', employee.user_id.id),
        ] + filter_map.get(filterby, filter_map['pending'])

        leaves = request.env['hr.leave'].sudo().search(domain, order='write_date desc')
        return self._json({
            'is_line_manager': True,
            'filterby': filterby,
            'leaves': [{
                'id': lv.id,
                'employee_name': lv.employee_id.name,
                'leave_type': lv.holiday_status_id.name,
                'date_from': lv.request_date_from.strftime('%d/%m/%Y') if lv.request_date_from else None,
                'date_to': lv.request_date_to.strftime('%d/%m/%Y') if lv.request_date_to else None,
                'number_of_days': lv.number_of_days,
                'state': lv.state,
            } for lv in leaves],
        })

    @http.route('/api/ess/approvals/<int:leave_id>/approve', type='http', auth='public', methods=['POST'], csrf=False)
    def approve_leave(self, leave_id, **post):
        if not self._check_auth():
            return self._unauthorized()

        manager = self._get_employee(post.get('email'))
        if not manager:
            return self._json({'success': False, 'error': 'Employee not found'}, 404)
        if not self._is_line_manager(manager):
            return self._json({'success': False, 'error': 'Not authorized'}, 403)

        leave = self._get_approvable_leave(leave_id, manager)
        if not leave:
            return self._json({'success': False, 'error': 'You are not authorised to act on this request.'})
        if leave.state not in ('confirm', 'validate1'):
            return self._json({'success': False, 'error': 'This request is no longer pending.'})

        try:
            leave_company = leave.employee_id.company_id
            self._as_service(leave).with_company(leave_company).with_context(
                allowed_company_ids=[leave_company.id]
            ).action_approve()
            self._audit_note(leave, "Approved via ESS Portal by line manager", manager)
            return self._json({'success': True})
        except Exception:
            _logger.exception("ESS approve failed for leave %s", leave_id)
            request.env.cr.rollback()
            return self._json({'success': False, 'error': 'Could not approve this request. Please try again or contact HR.'})

    @http.route('/api/ess/approvals/<int:leave_id>/reject', type='http', auth='public', methods=['POST'], csrf=False)
    def reject_leave(self, leave_id, **post):
        if not self._check_auth():
            return self._unauthorized()

        manager = self._get_employee(post.get('email'))
        if not manager:
            return self._json({'success': False, 'error': 'Employee not found'}, 404)
        if not self._is_line_manager(manager):
            return self._json({'success': False, 'error': 'Not authorized'}, 403)

        leave = self._get_approvable_leave(leave_id, manager)
        if not leave:
            return self._json({'success': False, 'error': 'You are not authorised to act on this request.'})
        if leave.state not in ('confirm', 'validate1'):
            return self._json({'success': False, 'error': 'This request is no longer pending.'})

        reason = (post.get('reject_reason') or '').strip()

        try:
            self._as_service(leave).action_refuse()
            self._audit_note(leave, "Rejected via ESS Portal by line manager", manager, extra=reason or None)
            return self._json({'success': True})
        except Exception:
            _logger.exception("ESS reject failed for leave %s", leave_id)
            request.env.cr.rollback()
            return self._json({'success': False, 'error': 'Could not reject this request. Please try again or contact HR.'})