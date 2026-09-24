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