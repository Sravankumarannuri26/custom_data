import json
from odoo import http
from odoo.http import request

API_KEY = "dd7ef9db2080651a656e5a9dbfed5a03ef9616a7"  # move to a config param later


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
                headers={'Content-Type': 'application/json'},
                status=401
            )

        email = kwargs.get('email')
        if not email:
            return request.make_response(
                json.dumps({'error': 'email parameter required'}),
                headers={'Content-Type': 'application/json'},
                status=400
            )

        employee = request.env['hr.employee'].sudo().search([('work_email', '=', email)], limit=1)
        if not employee:
            return request.make_response(
                json.dumps({'error': 'Employee not found'}),
                headers={'Content-Type': 'application/json'},
                status=404
            )

        leave_types = request.env['hr.leave.type'].sudo().search([])
        balances = []
        for lt in leave_types:
            balances.append({
                'name': lt.name,
                'remaining': lt.with_context(employee_id=employee.id).virtual_remaining_leaves,
            })

        return request.make_response(
            json.dumps({'employee': employee.name, 'balances': balances}),
            headers={'Content-Type': 'application/json'}
        )

    @http.route('/api/ess/apply_leave', type='http', auth='public', methods=['POST'], csrf=False)
    def apply_leave(self, **kwargs):
        if not self._check_auth():
            return request.make_response(
                json.dumps({'error': 'Unauthorized'}),
                headers={'Content-Type': 'application/json'}, status=401
            )

        email = kwargs.get('email')
        leave_type_name = kwargs.get('leave_type', 'Annual Leave')
        date_from = kwargs.get('date_from')
        date_to = kwargs.get('date_to')

        employee = request.env['hr.employee'].sudo().search([('work_email', '=', email)], limit=1)
        if not employee:
            return request.make_response(json.dumps({'error': 'Employee not found'}),
                                         headers={'Content-Type': 'application/json'}, status=404)

        leave_type = request.env['hr.leave.type'].sudo().search([('name', '=', leave_type_name)], limit=1)
        if not leave_type:
            return request.make_response(json.dumps({'error': 'Leave type not found'}),
                                         headers={'Content-Type': 'application/json'}, status=404)

        leave = request.env['hr.leave'].sudo().create({
            'employee_id': employee.id,
            'holiday_status_id': leave_type.id,
            'request_date_from': date_from,
            'request_date_to': date_to,
            'name': 'Applied via ESS Community test',
        })

        return request.make_response(
            json.dumps({'success': True, 'leave_id': leave.id, 'state': leave.state}),
            headers={'Content-Type': 'application/json'}
        )