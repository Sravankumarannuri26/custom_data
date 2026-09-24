# -*- coding: utf-8 -*-

from odoo import api, models, _, fields
from odoo.exceptions import ValidationError
from datetime import datetime
import re
import phonenumbers
from odoo.tools.safe_eval import safe_eval, datetime as safe_eval_datetime, dateutil as safe_eval_dateutil
from num2words import num2words


# class HrPayslipEmployees(models.TransientModel):
#     _inherit = 'hr.payslip.employees'
#
#     @api.depends('structure_id', 'department_id', 'structure_type_id', 'job_id')
#     def _compute_employee_ids(self):
#         for wizard in self:
#             structure_type_id=''
#             if wizard.structure_id:
#                 structure_type_id = wizard.structure_id.type_id.id
#             elif wizard.structure_type_id:
#                 structure_type_id=wizard.structure_type_id.id
#
#             domain = wizard.get_employees_domain()
#             emp_objs=self.env['hr.employee'].search(domain)
#             employee_objs=[]
#             if structure_type_id:
#                 for emp_obj in emp_objs:
#                     if emp_obj.structure_type_id.id == structure_type_id:
#                         employee_objs.append(emp_obj.id)
#             else:
#                 for emp_obj in emp_objs:
#                     employee_objs.append(emp_obj.id)
#             wizard.employee_ids = employee_objs

# code changed  from contract to HrVersion, model changed from hr.contract to hr.version(sriman)
class HrVersionInherit(models.Model):
    _inherit = 'hr.version'

    aat_allowance = fields.Monetary('MI Allowance', copy=False)
    sub_total = fields.Monetary('Sub Total', copy=False)
    basic_salary_manual = fields.Monetary(string="Basic Salary Manual")
    hra_manual = fields.Monetary(string="HRA Manual")
    flexi_manual = fields.Monetary(string="Flexi Basket Manual")
    statutory_manual = fields.Monetary(string="Statutory Bonus Manual")
    gratuity_manual = fields.Monetary(string="Gratuity Manual")
    pf_manual = fields.Monetary(string="PF Manual")
    medical_manual=fields.Monetary(string="Medical Insurance Manual")
    # emp_code = fields.Char('Employee Code', copy=False)
    #
    #
    # @api.model_create_multi
    # def create(self, vals_list):
    #     for vals in vals_list:
    #         if 'emp_code' in vals and not vals.get('employee_id') and vals['emp_code'] != False:
    #             emp_code = vals['emp_code']
    #             employee = self.env['hr.employee'].search([('emp_code', '=', emp_code)], limit=1)
    #             if employee:
    #                 vals['employee_id'] = employee.id
    #             else:
    #                 raise ValidationError(_('Employee master not found. Employee ID: %s', emp_code))
    #     return super(HrContractInherit, self).create(vals_list)



class HrSalaryInherit(models.Model):
    _inherit = 'hr.salary.attachment'

    emp_code = fields.Char('Employee Code', copy=False)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'emp_code' in vals and not vals.get('employee_ids') and vals['emp_code'] != False:
                emp_code = vals['emp_code']
                employee = self.env['hr.employee'].search([('emp_code', '=', emp_code)], limit=1)
                if employee:
                    vals['employee_ids'] = employee.ids
                else:
                    raise ValidationError(_('Employee master not found. Employee ID: %s', emp_code))
        return super(HrSalaryInherit, self).create(vals_list)


class HrLeaveInherit(models.Model):
    _inherit = 'hr.leave'

    emp_code = fields.Char('Employee Code', copy=False)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'emp_code' in vals and not vals.get('employee_id') and vals['emp_code'] != False:
                emp_code = vals['emp_code']
                employee = self.env['hr.employee'].search([('emp_code', '=', emp_code)], limit=1)
                if employee:
                    vals['employee_id'] = employee.id
                else:
                    raise ValidationError(_('Employee master not found. Employee ID: %s', emp_code))
        return super(HrLeaveInherit, self).create(vals_list)


class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    emp_code = fields.Char('Employee Code', copy=False)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'emp_code' in vals and not vals.get('employee_id') and vals['emp_code'] != False:
                emp_code = vals['emp_code']
                employee = self.env['hr.employee'].search([('emp_code', '=', emp_code)], limit=1)
                if employee:
                    vals['employee_id'] = employee.id
                else:
                    raise ValidationError(_('Employee master not found. Employee ID: %s', emp_code))
        return super(HrAttendance, self).create(vals_list)


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'
    # _order = 'number desc'
    
    def get_amount_in_words(self,amount):
        whole = int(amount)
        decimal = int(round((amount - whole) * 100))
     
        currency_code = self.employee_id.currency_id.name or ''
     
        words = ""
     
     
        if whole:
    
            words += num2words(whole, lang='en_IN')
    
            words = words.replace(',', '')
    
            words = words.replace('-', ' ')
    
            words = words.capitalize()
     
     
        if decimal:
    
            decimal_words = num2words(decimal, lang='en_IN')
    
            decimal_words = decimal_words.replace(',', '')
    
            decimal_words = decimal_words.replace('-', ' ')
    
            decimal_words = decimal_words.lower()
     
            if words:
    
                words += f" decimal {decimal_words}"
    
            else:
    
                words = f"zero decimal {decimal_words}"
     
        if not words:
    
            words = "zero"
     
        return f"{currency_code} {words.title()} only"
 

    def _prepare_line_values(self, line, account_id, date, debit, credit):
        # if not self.company_id.batch_payroll_move_lines and line.code == "NET":
        #     partner = self.employee_id.work_contact_id
        # else:
        #     partner = line.partner_id
        partner = self.employee_id.work_contact_id
        product = self.env['product.product'].sudo().search([('employee_id', '=', self.employee_id.id)], limit=1)
        return {
            'name': line.name if line.salary_rule_id.split_move_lines else line.salary_rule_id.name,
            'partner_id': partner.id,
            'product_id': product.id,
            'emp_code': self.employee_id.emp_code,
            'account_id': account_id,
            'journal_id': line.slip_id.struct_id.journal_id.id,
            'date': date,
            'debit': debit,
            'credit': credit,
            'analytic_distribution': False,
            'tax_tag_ids': line.debit_tag_ids.ids if account_id == line.salary_rule_id.account_debit.id else line.credit_tag_ids.ids,
        }
        # 'analytic_distribution': (line.salary_rule_id.analytic_account_id and {line.salary_rule_id.analytic_account_id.id: 100}) or
        #                              (line.slip_id.contract_id.analytic_account_id.id and {line.slip_id.contract_id.analytic_account_id.id: 100}),


    def _get_report_name(self):
        formated_date_cache = {}
        report_name = ''
        for slip in self.filtered(lambda p: p.employee_id and p.date_from and p.date_to):
            lang = slip.employee_id.lang or self.env.user.lang
            context = {'lang': lang}
            payslip_name = slip.struct_id.payslip_name or _('Salary Slip')
            del context

            report_name = '%(employee_name)s - %(dates)s' % {
                'employee_name': slip.employee_id.legal_name,
                'dates': slip._get_period_name(formated_date_cache),
            }
        return report_name


    def action_payslip_draft(self):
        res = super(HrPayslip, self).action_payslip_draft()
        work_entries = self.env['hr.work.entry'].search([
                            ('employee_id', '=', self.employee_id.id),
                            ('date_start', '>=', self.date_from),
                            ('date_stop', '<=', self.date_to),
                            ('state', '=', 'validated'),
                        ])
        work_entries.sudo().write({'state': 'draft'})
        return res

    @api.model
    def _cron_generate_pdf(self, batch_size=False):
        payslips = self.search([
            ('state', 'in', ['done', 'paid']),
            ('queued_for_pdf', '=', True),
        ])
        if payslips:
            BATCH_SIZE = batch_size or 50
            payslips_batch = payslips[:BATCH_SIZE]
            payslips_batch._generate_pdf()
            payslips_batch.write({'queued_for_pdf': False})
            # if necessary, retrigger the cron to generate more pdfs
            # if len(payslips) > BATCH_SIZE:
            #     self.env.ref('hr_payroll.ir_cron_generate_payslip_pdfs')._trigger()
            #     return True

        lines = self.env['hr.payroll.employee.declaration'].search([('pdf_to_generate', '=', True)])
        if lines:
            BATCH_SIZE = batch_size or 30
            lines_batch = lines[:BATCH_SIZE]
            # lines_batch._generate_pdf()
            lines_batch.write({'pdf_to_generate': False})
            # if necessary, retrigger the cron to generate more pdfs
            # if len(lines) > BATCH_SIZE:
            #     self.env.ref('hr_payroll.ir_cron_generate_payslip_pdfs')._trigger()
            #     return True
        return False

    def _generate_pdf(self):
        mapped_reports = self._get_pdf_reports()
        attachments_vals_list = []
        generic_name = _("Payslip")
        template = self._get_email_template()
        for report, payslips in mapped_reports.items():
            for payslip in payslips:
                pdf_content, dummy = self.env['ir.actions.report'].sudo().with_context(lang=payslip.employee_id.lang or self.env.lang)._render_qweb_pdf(report, payslip.id)
                if report.print_report_name:
                    pdf_name = safe_eval(report.print_report_name, {'object': payslip})
                else:
                    pdf_name = generic_name
                attachments_vals_list.append({
                    'name': pdf_name,
                    'type': 'binary',
                    'raw': pdf_content,
                    'res_model': payslip._name,
                    'res_id': payslip.id
                })
                # Send email to employees
                # if template:
                #     template.send_mail(payslip.id)
        self.env['ir.attachment'].sudo().create(attachments_vals_list)


class HrPayslipRun(models.Model):
    _inherit = 'hr.payslip.run'


    def action_draft(self):
        res = super(HrPayslipRun, self).action_draft()
        for payslip in self.slip_ids:
            work_entries = self.env['hr.work.entry'].search([
                                ('employee_id', '=', payslip.employee_id.id),
                                ('date_start', '>=', payslip.date_from),
                                ('date_stop', '<=', payslip.date_to),
                                ('state', '=', 'validated'),
                            ])
            work_entries.sudo().write({'state': 'draft'})
        return res




