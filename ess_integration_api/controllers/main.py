import json
from odoo import http
from odoo.http import request

API_KEY = "dd7ef9db2080651a656e5a9dbfed5a03ef9616a7"


class EssIntegrationAPI(http.Controller):

    def _check_auth(self):
        auth_header = request.httprequest.headers.get('Authorization', '')
        token = auth_header.replace('Bearer ', '').strip()
        return token == API_KEY

    @http.route('/api/ess/leave_balance', type='http', auth='public', methods=['GET'], csrf=False)
    def get_leave_balance(self, **kwargs):
        if not self._check_auth():
            return request.make_response(
                json.dumps({'error': 'Unauthorized'}),
                headers={'Content-Type': 'application/json'}, status=401
            )

        email = kwargs.get('email')
        if not email:
            return request.make_response(
                json.dumps({'error': 'email parameter required'}),
                headers={'Content-Type': 'application/json'}, status=400
            )

        employee = request.env['hr.employee'].sudo().search([('work_email', '=', email)], limit=1)
        if not employee:
            return request.make_response(
                json.dumps({'error': 'Employee not found'}),
                headers={'Content-Type': 'application/json'}, status=404
            )

        leave_types = request.env['hr.leave.type'].with_context(
            employee_id=employee.id
        ).sudo().search([('active', '=', True)])

        balances = []
        for lt in leave_types:
            remaining = lt.with_context(employee_id=employee.id).virtual_remaining_leaves
            has_allocation = request.env['hr.leave.allocation'].sudo().search_count([
                ('employee_id', '=', employee.id),
                ('holiday_status_id', '=', lt.id),
                ('state', '=', 'validate'),
            ]) > 0
            if not has_allocation and remaining == 0:
                continue
            balances.append({'name': lt.name, 'remaining': remaining})

        leave_pending_count = request.env['hr.leave'].sudo().search_count([
            ('employee_id', '=', employee.id),
            ('state', 'in', ['confirm', 'validate1']),
        ])
        leave_approved_count = request.env['hr.leave'].sudo().search_count([
            ('employee_id', '=', employee.id),
            ('state', '=', 'validate'),
        ])
        leave_balance_days = round(sum(b['remaining'] for b in balances), 1)

        return request.make_response(json.dumps({
            'employee': employee.name,
            'balances': balances,
            'pending_count': leave_pending_count,
            'approved_count': leave_approved_count,
            'balance_days': leave_balance_days,
        }), headers={'Content-Type': 'application/json'})