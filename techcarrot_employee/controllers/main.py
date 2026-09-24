from odoo import http
from odoo.http import request
from odoo.addons.hr_payroll.controllers.main import HrPayroll
import io
import pikepdf
from datetime import datetime


class HrPayrollEncrypted(HrPayroll):

    @http.route(['/print/payslips'], type='http', auth='user')
    def get_payroll_report_print(self, list_ids='', **post):

        # Call original controller first
        response = super().get_payroll_report_print(
            list_ids=list_ids, **post
        )

        if not list_ids:
            return response

        ids = [int(s) for s in list_ids.split(',')]
        payslips = request.env['hr.payslip'].browse(ids)

        # If printing one payslip only (recommended)
        if len(payslips) == 1:
            employee = payslips.employee_id

            if employee.birthday:
                password = employee.birthday.strftime("%d%m%Y")

                pdf_stream = io.BytesIO(response.data)
                output_stream = io.BytesIO()

                with pikepdf.open(pdf_stream) as pdf:
                    pdf.save(
                        output_stream,
                        encryption=pikepdf.Encryption(
                            user=password,
                            owner=password,
                            R=4
                        )
                    )

                response.data = output_stream.getvalue()

        return response
