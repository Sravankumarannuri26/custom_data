# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class HrPayslipEmployees(models.TransientModel):
    _inherit = 'hr.payslip.employees'

    @api.depends('structure_id', 'department_id', 'structure_type_id', 'job_id')
    def _compute_employee_ids(self):
        for wizard in self:
            structure_type_id=''
            if wizard.structure_id:
                structure_type_id = wizard.structure_id.type_id.id
            elif wizard.structure_type_id:
                structure_type_id=wizard.structure_type_id.id

            domain = wizard.get_employees_domain()
            emp_objs=self.env['hr.employee'].search(domain)
            employee_objs=[]
            if structure_type_id:
                for emp_obj in emp_objs:
                    if emp_obj.structure_type_id.id == structure_type_id:
                        employee_objs.append(emp_obj.id)
            else:
                for emp_obj in emp_objs:
                    employee_objs.append(emp_obj.id)
            wizard.employee_ids = employee_objs

# 
# 
# class HrPaysliprun(models.Model):
#     _inherit = 'hr.payslip.run'
# 
#     def _are_payslips_ready(self):
#         to_process = self.env["hr.payroll"]
#         # self.env.cr.commit()
#         for slip in self.mapped('slip_ids'):
#             if slip.state in ['done'] and not slip.entry_id:
#                 print('ENTTTTTTTT=====',slip.entry_id)
#                 to_process += slip
#         return all(to_process)

