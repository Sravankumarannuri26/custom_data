import json
import base64
import urllib.parse
from datetime import timedelta
from odoo import http, fields
from odoo.http import request
from odoo.exceptions import ValidationError
import pytz

API_KEY = "dd7ef9db2080651a656e5a9dbfed5a03ef9616a7"


class LeaveManagementAPI(http.Controller):

    def _check_auth(self):
        auth_header = request.httprequest.headers.get('Authorization', '')
        token = auth_header.replace('Bearer ', '').strip()
        return token == API_KEY

    def _unauthorized(self):
        return request.make_response(
            json.dumps({'error': 'Unauthorized'}),
            headers={'Content-Type': 'application/json'}, status=401
        )

    def _get_employee(self, email):
        return request.env['hr.employee'].sudo().search([('work_email', '=', email)], limit=1)

    # ---------- balance helpers ----------

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
        company = request.env.company.sudo()
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

    # ---------- GET /api/ess/leaves ----------

    @http.route('/api/ess/leaves', type='http', auth='public', methods=['GET'], csrf=False)
    def get_leaves(self, **kwargs):
        if not self._check_auth():
            return self._unauthorized()

        email = kwargs.get('email')
        employee = self._get_employee(email)
        if not employee:
            return request.make_response(json.dumps({'error': 'Employee not found'}),
                                         headers={'Content-Type': 'application/json'}, status=404)

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

        selectable_types = leave_types.filtered(_selectable)
        leave_types_out = [{
            'id': lt.id, 'name': lt.name,
            'request_unit': lt.request_unit,
            'support_document': bool(getattr(lt, 'support_document', False)),
        } for lt in selectable_types]

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
            'date_from': lv.date_from.strftime('%Y-%m-%d') if lv.date_from else None,
            'date_to': lv.date_to.strftime('%Y-%m-%d') if lv.date_to else None,
            'number_of_days': lv.number_of_days,
            'state': lv.state,
            'create_date': lv.create_date.strftime('%Y-%m-%d') if lv.create_date else None,
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
        if employee.line_manager_id and employee.line_manager_id.user_id:
            lm = employee.line_manager_id.user_id
            line_manager = {'name': lm.name, 'email': lm.email}

        return request.make_response(json.dumps({
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
        }), headers={'Content-Type': 'application/json'})

    # ---------- POST /api/ess/leaves/submit ----------

    @http.route('/api/ess/leaves/submit', type='http', auth='public', methods=['POST'], csrf=False)
    def submit_leave(self, **post):
        if not self._check_auth():
            return self._unauthorized()

        email = post.get('email')
        employee = self._get_employee(email)
        if not employee:
            return request.make_response(json.dumps({'success': False, 'error': 'Employee not found'}),
                                         headers={'Content-Type': 'application/json'}, status=404)

        approval_required = employee.company_id.leave_approval_required
        if approval_required and not employee.line_manager_id:
            return request.make_response(json.dumps({
                'success': False,
                'error': "You cannot apply for leave because no line manager is assigned. Please contact HR."
            }), headers={'Content-Type': 'application/json'})

        leave_type_id = post.get('leave_type_id')
        date_from_str = post.get('date_from')
        date_to_str = post.get('date_to')
        reason = (post.get('reason') or '').strip()
        is_half_day = post.get('is_half_day') == '1'
        from_period = post.get('request_date_from_period') or 'am'
        to_period = post.get('request_date_to_period') or 'pm'

        if not leave_type_id or not date_from_str or not date_to_str:
            return request.make_response(json.dumps({'success': False, 'error': 'Please fill all required fields'}),
                                         headers={'Content-Type': 'application/json'})

        try:
            date_from_obj = fields.Date.from_string(date_from_str)
            date_to_obj = fields.Date.from_string(date_to_str)
            if date_to_obj < date_from_obj:
                return request.make_response(json.dumps({'success': False, 'error': 'End date cannot be before start date'}),
                                             headers={'Content-Type': 'application/json'})

            overlapping = request.env['hr.leave'].sudo().search([
                ('employee_id', '=', employee.id),
                ('state', 'not in', ['refuse', 'draft', 'cancel']),
                ('date_from', '<=', fields.Datetime.from_string(str(date_to_obj) + ' 23:59:59')),
                ('date_to', '>=', fields.Datetime.from_string(str(date_from_obj) + ' 00:00:00')),
            ], limit=1)
            if overlapping:
                overlap_from = overlapping.date_from.strftime('%d %b %Y') if overlapping.date_from else ''
                overlap_to = overlapping.date_to.strftime('%d %b %Y') if overlapping.date_to else ''
                return request.make_response(json.dumps({
                    'success': False,
                    'error': f"You already have a leave request from {overlap_from} to {overlap_to}. Overlapping dates are not allowed."
                }), headers={'Content-Type': 'application/json'})
        except Exception as e:
            return request.make_response(json.dumps({'success': False, 'error': 'Invalid date format'}),
                                         headers={'Content-Type': 'application/json'})

        try:
            leave_type_id_int = int(leave_type_id)
            leave_type = request.env['hr.leave.type'].sudo().browse(leave_type_id_int)
            if not leave_type.exists():
                return request.make_response(json.dumps({'success': False, 'error': 'Invalid leave type selected'}),
                                             headers={'Content-Type': 'application/json'})
        except Exception:
            return request.make_response(json.dumps({'success': False, 'error': 'Invalid leave type'}),
                                         headers={'Content-Type': 'application/json'})

        attachment = request.httprequest.files.get('leave_attachment')
        has_file = bool(attachment and attachment.filename)
        requires_doc = getattr(leave_type, 'support_document', False)
        if requires_doc and not has_file:
            return request.make_response(json.dumps({
                'success': False, 'error': 'A supporting document is required for this leave type.'
            }), headers={'Content-Type': 'application/json'})

        if attachment and attachment.filename:
            allowed_exts = ('.pdf', '.doc', '.docx', '.png', '.jpg', '.jpeg', '.xlsx', '.txt')
            if not attachment.filename.lower().endswith(allowed_exts):
                return request.make_response(json.dumps({
                    'success': False, 'error': 'Invalid file type. Allowed: PDF, DOC, DOCX, PNG, JPG, JPEG, XLSX, TXT.'
                }), headers={'Content-Type': 'application/json'})
            attachment.seek(0, 2)
            file_size = attachment.tell()
            attachment.seek(0)
            if file_size > 10 * 1024 * 1024:
                return request.make_response(json.dumps({
                    'success': False, 'error': 'File is too large. Maximum allowed size is 10MB.'
                }), headers={'Content-Type': 'application/json'})

        if getattr(leave_type, 'x_is_frozen', False):
            unlocked = request.env['hr.leave.allocation'].sudo().search_count([
                ('employee_id', '=', employee.id), ('holiday_status_id', '=', leave_type.id),
                ('state', '=', 'validate'), ('x_frozen_unlocked', '=', True),
            ])
            if not unlocked:
                return request.make_response(json.dumps({
                    'success': False, 'error': 'This leave type is currently locked. Please contact HR to request access.'
                }), headers={'Content-Type': 'application/json'})

        try:
            requested_days = self._ess_count_workdays(date_from_obj, date_to_obj)
            if is_half_day and requested_days == 1:
                requested_days = 0.5
            current_balance = self._ess_leave_balance_for(employee, leave_type)
            allowed_excess = leave_type.max_allowed_negative if leave_type.allows_negative else 0
            if current_balance - requested_days < -allowed_excess:
                return request.make_response(json.dumps({
                    'success': False,
                    'error': 'You do not have enough leave balance for this request. Please reach out to HR for support.'
                }), headers={'Content-Type': 'application/json'})
        except Exception:
            return request.make_response(json.dumps({
                'success': False, 'error': 'Could not verify your leave balance. Please reach out to HR for support.'
            }), headers={'Content-Type': 'application/json'})

        backup_type = (post.get('backup_type') or '').strip()
        backup_employee_id = post.get('backup_employee_id')
        backup_name = (post.get('backup_name') or '').strip()
        backup_email = (post.get('backup_email') or '').strip()
        backup_required = date_to_obj > fields.Date.today()

        if backup_required:
            if backup_type == 'internal' and not backup_employee_id:
                return request.make_response(json.dumps({
                    'success': False, 'error': 'Please select a backup person for this future-dated leave.'
                }), headers={'Content-Type': 'application/json'})
            elif backup_type == 'external' and (not backup_name or not backup_email):
                return request.make_response(json.dumps({
                    'success': False, 'error': 'Please provide both the name and email of your external backup.'
                }), headers={'Content-Type': 'application/json'})
            elif backup_type not in ('internal', 'external'):
                return request.make_response(json.dumps({
                    'success': False, 'error': 'Please nominate a backup person for this future-dated leave.'
                }), headers={'Content-Type': 'application/json'})

        try:
            leave_vals = {
                'employee_id': employee.id,
                'holiday_status_id': leave_type_id_int,
                'request_date_from': date_from_obj,
                'request_date_to': date_to_obj,
                'name': reason or '/',
            }
            if leave_type.request_unit == 'half_day':
                leave_vals['request_date_from_period'] = from_period
                leave_vals['request_date_to_period'] = to_period
            leave = request.env['hr.leave'].sudo().create(leave_vals)

            if backup_required and backup_type:
                backup_vals = {'x_backup_type': backup_type}
                if backup_type == 'internal' and backup_employee_id:
                    backup_vals['x_backup_employee_id'] = int(backup_employee_id)
                elif backup_type == 'external':
                    backup_vals['x_backup_name'] = backup_name
                    backup_vals['x_backup_email'] = backup_email
                leave.sudo().write(backup_vals)

            if attachment and attachment.filename:
                attachment.seek(0)
                attachment_content = attachment.read()
                if len(attachment_content) <= 10 * 1024 * 1024:
                    request.env['ir.attachment'].sudo().create({
                        'name': attachment.filename, 'type': 'binary',
                        'datas': base64.b64encode(attachment_content),
                        'res_model': 'hr.leave', 'res_id': leave.id,
                        'mimetype': attachment.mimetype,
                    })

            if not approval_required:
                try:
                    leave_company = employee.company_id
                    leave.sudo().with_company(leave_company).with_context(
                        allowed_company_ids=[leave_company.id],
                        _ess_approved_sent=True, _ess_negative_hr_sent=True,
                    ).action_approve()
                except Exception:
                    request.env.cr.rollback()
                    return request.make_response(json.dumps({
                        'success': False, 'error': 'Could not process your leave. Please reach out to HR for support.'
                    }), headers={'Content-Type': 'application/json'})

            try:
                recipients = self._ess_leave_notify_recipients(employee)
                if recipients:
                    template = request.env.ref('leave_management_api.email_template_leave_applied_notification', raise_if_not_found=False)
                    if template:
                        base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
                        template.with_context(base_url=base_url).sudo().send_mail(
                            leave.id, force_send=True, email_values={'email_to': ','.join(recipients)}
                        )
            except Exception as mail_err:
                pass

            try:
                if (leave.x_backup_type == 'internal' and leave.x_backup_employee_id
                        and leave.x_backup_employee_id.work_email):
                    bk_template = request.env.ref('leave_management_api.email_template_leave_backup_notification', raise_if_not_found=False)
                    if bk_template:
                        base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
                        bk_template.with_context(base_url=base_url).sudo().send_mail(
                            leave.id, force_send=True,
                            email_values={'email_to': leave.x_backup_employee_id.work_email}
                        )
            except Exception:
                pass

            return request.make_response(json.dumps({
                'success': True, 'leave_id': leave.id,
                'auto_approved': not approval_required,
            }), headers={'Content-Type': 'application/json'})

        except ValidationError as ve:
            request.env.cr.rollback()
            return request.make_response(json.dumps({'success': False, 'error': str(ve)}),
                                         headers={'Content-Type': 'application/json'})
        except Exception as e:
            request.env.cr.rollback()
            return request.make_response(json.dumps({'success': False, 'error': 'Failed to submit leave. Please try again.'}),
                                         headers={'Content-Type': 'application/json'})