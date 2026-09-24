import datetime
import json

from odoo import http
from odoo.http import request


class BirthdayTestController(http.Controller):

    @http.route('/techcarrot/api/employees/birthdays/test', type='http', auth='none', methods=['GET'], csrf=False)
    def test_birthday_notifications(self, test_date=None, **kwargs):
        target_date = datetime.date.today()
        if test_date:
            target_date = datetime.datetime.strptime(test_date, '%Y-%m-%d').date()

        employees = request.env['hr.employee'].sudo().search([('birthday', '!=', False)])
        matched = employees.filtered(
            lambda e: e.birthday.day == target_date.day and e.birthday.month == target_date.month
        )

        sent = []
        errors = []
        for emp in matched:
            try:
                emp._send_birthday_card_email()
                sent.append({'id': emp.id, 'name': emp.name})
            except Exception as exc:
                errors.append({'id': emp.id, 'name': emp.name, 'error': str(exc)})

        result = {
            'date_checked': str(target_date),
            'count': len(sent),
            'employees': sent,
            'errors': errors,
        }
        return request.make_response(
            json.dumps(result),
            headers=[('Content-Type', 'application/json')]
        )
