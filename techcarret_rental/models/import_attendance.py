# -*- coding: utf-8 -*-
import xlrd
import logging
import tempfile
import binascii
from datetime import date, datetime, timedelta
from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

try:
	import xlwt
except ImportError:
	_logger.debug('Cannot `import xlwt`.')
try:
	import cStringIO
except ImportError:
	_logger.debug('Cannot `import cStringIO`.')
try:
	import base64
except ImportError:
	_logger.debug('Cannot `import base64`.')


class ImportAttendance(models.Model):
	_name = 'import.attendance'
	_description = 'Import Attendance'
	_inherit = ['portal.mixin', 'product.catalog.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
	_order = 'id desc'
	_rec_name ='date'


	def _get_year_selection(self):
		current_year = datetime.now().year
		return [(str(i), i) for i in range(1990, current_year + 8)]

	file_type = fields.Selection([('XLS', 'XLS File')],string='File Type', default='XLS')
	file = fields.Binary(string="Upload File", required=True)
	month = fields.Integer("Month")
	date= fields.Datetime("Imported On", default=fields.Datetime.now)
	year = fields.Selection(selection='_get_year_selection', string='Year')
	no_employee = fields.Integer('NO. Employees', compute='get_num_employee')
	state = fields.Selection([("draft", "New"), ("validate", "Validated"), ("imported", "Imported")], required=True, default="draft", tracking=1)
	attendance_data_ids = fields.One2many('import.attendance.line', 'import_attendance_id', string='Stock Data')

	def get_eployee(self, emp_code):
		emp_obj = self.env['hr.employee'].sudo().search([('emp_code', '=', str(emp_code))], limit=1)
		if emp_obj:
			return emp_obj
		else:
			raise UserError(_('Employee master not found. Employee ID: %s', emp_code))

	def get_project(self, code, employee):
		project_obj = self.env['project.project'].sudo().search([('project_code', '=', str(code))], limit=1)
		if project_obj:
			so_objs = self.env['sale.order'].sudo().search([('is_rental_order','=',True),('project_id', '=', project_obj.id)])
			if so_objs:
				is_so_available = False
				for so_obj in so_objs:
					if so_obj.state != 'sale':
						continue
					for line in so_obj.order_line:
						employee_id = getattr(line.product_id.employee_id, 'id', None)
						if employee_id and employee_id == employee.id:
							is_so_available = True
							return so_obj
				if is_so_available == False:
					raise UserError(_('Employee code is not found in this project: %s, Employee: %s', code, employee.emp_code))
			else:
				raise UserError(_('Project is not assigned to any of rental order: %s', code))
		else:
			raise UserError(_('Project code is not found: %s', code))

	def import_attendance(self):
		for line in self.attendance_data_ids:
			m = line.month
			y = line.year
			so_inv_line_objs = self.env['rental.invoice.history'].search([('rental_sale_id','=', line.sale_id.id),('state','=','draft'),('employee_id', '=', line.employee_id.id)])
			if so_inv_line_objs:
				for so_inv_line_obj in so_inv_line_objs:
					# hm = so_inv_line_obj.rentalnext_invoice_date.month
					hm = so_inv_line_obj.rental_month
					hy = so_inv_line_obj.rentalnext_invoice_date.year
					if hm<str(m) and so_inv_line_obj.worked_days==0:
						so_inv_line_obj.state = 'done'
					if str(m) == hm and y == str(hy):
						if so_inv_line_obj.uom == line.uom:
							worked_qty = line.worked_qty
						else:
							if so_inv_line_obj.uom == 'days' and line.uom=='hours':
								worked_qty = line.worked_qty/8
							else:
								worked_qty = line.worked_qty * 8
						so_inv_line_obj.worked_days = so_inv_line_obj.worked_days + worked_qty
						line.history_line_id=so_inv_line_obj.id
						so_inv_line_obj.is_ready_to_invoice=True
			line.state='imported'
		self.state = 'imported'

	def rollback_data(self):
		for line in self.attendance_data_ids:
			workentry_obj = self.env['employee.workentry'].sudo().search([('import_id', '=', line.id)])
			if workentry_obj:
				workentry_obj.unlink()
			if not line.history_line_id.inv_ref_id:
				so_inv_line_objs = self.env['rental.invoice.history'].search([('rental_sale_id','=', line.sale_id.id),('id', '<', line.history_line_id.id)])
				if so_inv_line_objs:
					for so_inv_line_obj in so_inv_line_objs:
						if so_inv_line_obj.worked_days ==0:
							so_inv_line_obj.state = 'draft'
				line.history_line_id.worked_days= 0
				line.history_line_id.state='draft'
				line.history_line_id=''
				line.state='draft'
			else:
				raise ValidationError(_("Can not roll back the invoiced data!"))
		self.state = 'draft'

	def get_num_employee(self):
		for imp_record in self:
			no_employee=[]
			for line in imp_record.attendance_data_ids:
				if line.employee_id:
					if line.employee_id.id not in no_employee:
						no_employee.append(line.employee_id.id)
			imp_record.no_employee=len(no_employee)

	def validate_data(self):
		for line in self.attendance_data_ids:
			employee_obj = self.get_eployee(line.emp_code)
			if employee_obj.id:
				line.employee_id = employee_obj.id
			so_obj = self.get_project(line.rental_order, employee_obj)
			if so_obj:
				line.sale_id = so_obj.id
			emp_attendace_objs = self.env['import.attendance.line'].search([
				('employee_id', '=', line.employee_id.id),
				('month', '=', int(line.month)),
				('state', '=', 'imported'),
				('year', '=', str(line.year)),
				('sale_id', '=', line.sale_id.id)
			])
			if emp_attendace_objs:
				raise UserError(_('Employee timesheet already imported. Employee %s', line.employee_id.emp_code))

		for line in self.attendance_data_ids:
			m = line.month
			y = line.year
			so_inv_line_objs = self.env['rental.invoice.history'].search([('rental_sale_id','=', line.sale_id.id),('state','=','draft'),('employee_id', '=', line.employee_id.id)])
			if so_inv_line_objs:
				is_data_available=False
				for so_inv_line_obj in so_inv_line_objs:
					hm = so_inv_line_obj.rental_month
					hy = so_inv_line_obj.rentalnext_invoice_date.year
					if str(m) == hm and y == str(hy):
						is_data_available = True
				if is_data_available == False:
					raise UserError(_('Rental not available. Project %s Employee %s',  line.sale_id.project_code, line.employee_id.emp_code))
		self.state='validate'

	@api.onchange('file')
	def get_attendance(self):
		values=[]
		self.attendance_data_ids = [(6, 0, [])]
		no_employee=[]
		if self.file and not self.attendance_data_ids:
			try:
				file = tempfile.NamedTemporaryFile(delete= False,suffix=".xlsx")
				file.write(binascii.a2b_base64(self.file))
				file.seek(0)
				workbook = xlrd.open_workbook(file.name)
				sheet = workbook.sheet_by_index(0)
			except Exception as e:
				raise ValidationError(_('Please Select Valid File Format!. Error %s', e))
			month=''
			year=''
			for row_no in range(sheet.nrows):
				line = list(map(lambda row:isinstance(row.value, bytes) and row.value.encode('utf-8') or str(row.value), sheet.row(row_no)))
				if line:
					if row_no == 0:
						if '.' in line[1]:
							month = line[1].split('.')[0]
							self.month = month
						else:
							month = str(line[1])
							self.month = month
						if '.' in line[3]:
							year = line[3].split('.')[0]
							self.year = year
						else:
							year=str(line[3])
							self.year = year
					if row_no>=2:
						if '.' in line[1]:
							project_code = line[1].split('.')[0]
						else:
							project_code = str(line[1])
						if '.' in line[0]:
							emp_code = line[0].split('.')[0]
						else:
							emp_code = str(line[0])
						if line[3] == 'Hours':
							uom='hours'
						elif line[3] == 'Months':
							uom='months'
						else:
							uom = 'days'
						values.append((0, 0, {
									'month': int(month),
									'year': str(year),
									'worked_qty': int(float(line[2])),
									'uom':uom,
									'rental_order':project_code,
									'emp_code':emp_code
									}))
			if values:
				self.attendance_data_ids= values
				self.no_employee=len(no_employee)

	def unlink(self):
		for rec in self:
			if rec.state == 'imported':
				raise UserError(_('Imported data can not be deleted.'))
		return super(ImportAttendance, self).unlink()

class ImportStockLine(models.Model):
	_name = 'import.attendance.line'
	_description = 'Import Stock Line'

	def _get_year_selection(self):
		current_year = datetime.now().year
		return [(str(i), i) for i in range(1990, current_year + 8)]

	import_attendance_id = fields.Many2one("import.attendance", 'Stock Data', required=True, ondelete='cascade', index=True, copy=False)
	employee_id = fields.Many2one('hr.employee', string="Employee")
	emp_code = fields.Char("Employee Code")
	worked_qty = fields.Integer("Worked QTY")
	month = fields.Integer("Month")
	year = fields.Selection(selection='_get_year_selection', string='Year')
	state = fields.Selection([("draft", "New"), ("imported", "Imported")], required=True, default="draft")
	uom = fields.Selection([("hours", "Hours"), ("days", "Days"), ("months", "Months")], string="UOM", required=True, default="days")
	rental_order = fields.Char('Project', copy=False)
	sale_id = fields.Many2one('sale.order', 'Rental Order', copy=False)
	history_line_id = fields.Many2one('rental.invoice.history', copy=False)
	is_consolidated = fields.Boolean('Is Consolidated', defualt=False)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
