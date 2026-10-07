import hmac
import io
import json
import logging
from calendar import monthrange
from datetime import date
from urllib.parse import quote

from odoo import SUPERUSER_ID, http
from odoo.http import request

_logger = logging.getLogger(__name__)

PAID_STATES = ['paid']
ACCESS_GROUP = 'payslip_api.group_payslip_access'
REPORT_XMLIDS = [
    'hr_payroll.action_report_payslip',
    'hr_payroll.payslip_report',
    'hr_payroll.report_payslip',
    'hr_payroll.report_payslip_details',
]


class PayslipAPI(http.Controller):

    # ---------------- helpers ----------------

    def _check_auth(self):
        key = request.env['ir.config_parameter'].sudo().get_param('ess_integration.payslip_api_key') or ''
        token = request.httprequest.headers.get('Authorization', '').replace('Bearer ', '', 1).strip()
        return bool(key) and hmac.compare_digest(token.encode(), key.encode())

    def _json(self, payload, status=200):
        return request.make_response(
            json.dumps(payload), headers={'Content-Type': 'application/json'}, status=status)

    def _get_employee(self, email):
        return request.env['hr.employee'].sudo().search([('work_email', '=', email)], limit=1)

    def _admin(self, rec):
        # Payroll data and reports can depend on the current user's groups,
        # so read them as the superuser, not as the public user.
        return rec.with_user(SUPERUSER_ID)

    def _has_access(self, employee):
        """Same rule as the old portal: the employee's user must be in the Payslip Access group."""
        user = employee.user_id
        return bool(user) and user.sudo().has_group(ACCESS_GROUP)

    def _period(self, slip):
        return slip.date_from.strftime('%B %Y') if slip and slip.date_from else 'N/A'

    def _entry(self, require_access=True):
        """Returns (employee, error_response)."""
        if not self._check_auth():
            return None, self._json({'error': 'Unauthorized'}, 401)
        employee = self._get_employee(request.params.get('email'))
        if not employee:
            return None, self._json({'error': 'Employee not found'}, 404)
        if require_access and not self._has_access(employee):
            return None, self._json(
                {'error': 'Payslips are not enabled for your account.', 'code': 'no_access'}, 403)
        return employee, None

    def _own_paid_slip(self, payslip_id, employee):
        slip = self._admin(request.env['hr.payslip']).browse(payslip_id)
        if (not slip.exists() or slip.employee_id.id != employee.id
                or slip.state not in PAID_STATES):
            return None
        return slip

    # ---------------- GET /api/ess/payslips/summary ----------------

    @http.route('/api/ess/payslips/summary', type='http', auth='public', methods=['GET'], csrf=False)
    def payslip_summary(self, **kw):
        employee, err = self._entry(require_access=False)
        if err:
            return err
        if not self._has_access(employee):
            return self._json({'has_access': False})
        Slip = self._admin(request.env['hr.payslip'])
        domain = [('employee_id', '=', employee.id), ('state', 'in', PAID_STATES)]
        latest = Slip.search(domain, order='date_from desc', limit=1)
        return self._json({
            'has_access': True,
            'payslips_count': Slip.search_count(domain),
            'latest_period': self._period(latest) if latest else None,
        })

    # ---------------- GET /api/ess/payslips ----------------

    @http.route('/api/ess/payslips', type='http', auth='public', methods=['GET'], csrf=False)
    def payslip_list(self, **kw):
        employee, err = self._entry()
        if err:
            return err
        Slip = self._admin(request.env['hr.payslip'])
        base = [('employee_id', '=', employee.id), ('state', 'in', PAID_STATES)]
        domain = list(base)

        month, year = kw.get('month'), kw.get('year')
        if month and year:
            try:
                m, y = int(month), int(year)
                domain += [('date_from', '>=', date(y, m, 1)),
                           ('date_to', '<=', date(y, m, monthrange(y, m)[1]))]
            except (ValueError, TypeError):
                _logger.warning("Payslip filter ignored: month=%s year=%s", month, year)

        slips = Slip.search(domain, order='date_from desc, date_to desc')

        earliest = Slip.search(base, order='date_from asc', limit=1)
        this_year = date.today().year
        first_year = earliest.date_from.year if earliest and earliest.date_from else this_year
        years = list(range(min(first_year, this_year), this_year + 1))

        _logger.info("ESS payslip: %s listed payslips (%s results)", employee.work_email, len(slips))
        return self._json({
            'years': years,
            'payslips': [{
                'id': s.id,
                'employee_name': s.employee_id.name,
                'date_from': s.date_from.strftime('%Y-%m-%d') if s.date_from else None,
                'date_to': s.date_to.strftime('%Y-%m-%d') if s.date_to else None,
                'state': s.state,
            } for s in slips],
        })

    # ---------------- GET /api/ess/payslips/<id>/pdf ----------------

    @http.route('/api/ess/payslips/<int:payslip_id>/pdf', type='http', auth='public', methods=['GET'], csrf=False)
    def payslip_pdf(self, payslip_id, **kw):
        employee, err = self._entry()
        if err:
            return err
        slip = self._own_paid_slip(payslip_id, employee)
        if not slip:
            return self._json({'error': 'Payslip not found', 'code': 'access_denied'}, 404)

        report = None
        for xmlid in REPORT_XMLIDS:
            report = request.env.ref(xmlid, raise_if_not_found=False)
            if report:
                break
        if not report:
            report = request.env['ir.actions.report'].sudo().search(
                [('model', '=', 'hr.payslip'), ('report_type', '=', 'qweb-pdf')], limit=1)
        if not report:
            return self._json({'error': 'Payslip report template not found.', 'code': 'report_not_found'}, 500)

        try:
            report = report.with_user(SUPERUSER_ID)
            pdf, _fmt = report._render_qweb_pdf(report.report_name, slip.ids)
        except Exception:
            _logger.exception("ESS payslip: render failed for payslip %s", payslip_id)
            return self._json({'error': 'Could not generate the payslip.', 'code': 'render_failed'}, 500)

        if not pdf:
            return self._json({'error': 'Generated payslip is empty.', 'code': 'empty_pdf'}, 500)

        # Password = employee's birthday (DDMMYYYY), applied here on Odoo.sh.
        # Old behaviour: if it can't be applied, the plain PDF is still sent.
        require_protection = (request.env['ir.config_parameter'].sudo()
                              .get_param('ess_integration.payslip_require_protection') or ''
                              ).lower() in ('1', 'true', 'yes')
        protected = None
        birthday = slip.employee_id.birthday
        if birthday:
            try:
                import pikepdf
                password = birthday.strftime('%d%m%Y')
                out = io.BytesIO()
                with pikepdf.open(io.BytesIO(pdf)) as doc:
                    doc.save(out, encryption=pikepdf.Encryption(user=password, owner=password, R=4))
                protected = out.getvalue()
            except Exception:
                _logger.exception("ESS payslip: encryption failed for payslip %s", payslip_id)

        if protected is None:
            if require_protection:
                return self._json({'error': 'This payslip cannot be protected right now.',
                                   'code': 'protect_failed'}, 422)
            _logger.warning("ESS payslip: payslip %s sent WITHOUT a password "
                            "(no birthday on file, or encryption failed)", payslip_id)
            protected = pdf

        filename = "%s - %s.pdf" % (slip.employee_id.name, self._period(slip))
        _logger.info("ESS payslip: %s downloaded payslip %s", employee.work_email, slip.id)
        return request.make_response(protected, headers=[
            ('Content-Type', 'application/pdf'),
            ('Content-Length', str(len(protected))),
            ('X-Filename', quote(filename)),
        ])