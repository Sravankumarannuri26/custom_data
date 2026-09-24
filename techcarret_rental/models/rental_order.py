# -*- coding: utf-8 -*-
import pytz
import calendar
from math import ceil
from dateutil.relativedelta import relativedelta
from setuptools.dist import sequence
from odoo import api, fields, models, _
from datetime import date, datetime, timedelta
from odoo.fields import Command
from odoo.tools import format_datetime, format_time, date_utils
from pytz import timezone, UTC
from odoo.tools import get_lang, SQL
from odoo.exceptions import ValidationError
from datetime import datetime
# from dateutil import relativedelta
import base64


class TecprojectType(models.Model):
    _name = 'tecproject.type'

    name = fields.Char('Name', copy=False, required=True)

    # _sql_constraints = [('unique_tecproject', 'unique (name)', 'Name must be unique.')]
    _name_unique = models.Constraint(
        'unique (name)',
        'Name must be unique.'
    )




class ProductTemplate(models.Model):
    _inherit = "product.template"

    employee_id = fields.Many2one('hr.employee', 'Employee')

    def write(self, vals):
        res = super(ProductTemplate, self).write(vals)
        if self.employee_id:
            self.employee_id.name = self.name
        return res

class Rentals(models.Model):
    _inherit = 'sale.order'


    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        company = self.env.company
        if company.r_analytic_plan_id:
            defaults['r_analytic_plan_id'] = company.r_analytic_plan_id.id
        if company.r_analytic_sub_plan_id:
            defaults['r_analytic_sub_plan_id'] = company.r_analytic_sub_plan_id.id
        if company.s_analytic_plan_id:
            defaults['s_analytic_plan_id'] = company.s_analytic_plan_id.id
        if company.s_analytic_sub_plan_id:
            defaults['s_analytic_sub_plan_id'] = company.s_analytic_sub_plan_id.id
        if company.ss_analytic_plan_id:
            defaults['ss_analytic_plan_id'] = company.ss_analytic_plan_id.id
        if company.ss_analytic_sub_plan_id:
            defaults['ss_analytic_sub_plan_id'] = company.ss_analytic_sub_plan_id.id

        user_tz = self.env.user.tz or self.env.context.get('tz')
        user_pytz = pytz.timezone(user_tz) if user_tz else pytz.utc
        now_dt = datetime.now().astimezone(user_pytz).replace(tzinfo=None)
        now_dt = now_dt.replace(hour=00, minute=00, second=1)
        now_dt = now_dt - relativedelta(hours=5)
        now_dt = now_dt - relativedelta(minutes=30)
        defaults['rental_start_date'] = now_dt

        now_dt = datetime.now().astimezone(user_pytz).replace(tzinfo=None)
        now_dt = now_dt.replace(hour=23, minute=59, second=59)
        now_dt = now_dt - relativedelta(hours=5)
        now_dt = now_dt - relativedelta(minutes=30)
        defaults['rental_return_date'] =now_dt
        if 'is_rental_order' in defaults:
            if defaults.get('is_rental_order') == True:
                defaults['journal_id'] = company.rental_journal_id.id
        if 'is_tec_subscription' in defaults:
            if defaults.get('is_tec_subscription') == True:
                defaults['journal_id'] = company.subscription_journal_id.id
        if 'is_rental_order' in defaults and 'is_tec_subscription' in defaults:
            if defaults.get('is_tec_subscription') == False and defaults.get('is_rental_order') == False:
                defaults['journal_id'] = company.sales_journal_id.id
        return defaults

    def _default_freequency(self):
        return self.env['sale.temporal.recurrence'].search([('unit', '=', 'month')], limit=1).id

    invoice_freequency = fields.Many2one('sale.temporal.recurrence', string='Invoicing Frequency', default=_default_freequency)
    rental_inv_line_ids = fields.One2many(
        comodel_name='rental.invoice.history',
        inverse_name='rental_sale_id',
        string="Rental History",
        copy=True, auto_join=True)
    rentalfirst_invoice_date = fields.Date(string='First Invoice Date', default=fields.Date.context_today)
    rentalnext_invoice_date = fields.Date(string='Next Invoice Date', copy=False)
    recurring_period_interval = fields.Selection([
        ('hour', 'Hours'),
        ('day', 'Days'),
        ('week', 'Weeks'),
        ('month', 'Months'),
        ('year', 'Years'),
    ], default='month')
    do_create_invoice_schedule = fields.Boolean(string="Dummy Compute", compute='_do_create_invoice_schedule')
    practice_id = fields.Many2one('employee.practice', 'Practice', copy=False)
    project_type_id = fields.Many2one('tecproject.type', 'Project type')
    project_code = fields.Char('Project Code', copy=False)
    is_tec_subscription = fields.Boolean("Is Subscription", default=False)
    r_analytic_plan_id = fields.Many2one('account.analytic.plan', 'Plan', readonly=False, domain="[('parent_id', '=', False)]")
    r_analytic_sub_plan_id = fields.Many2one('account.analytic.plan', 'Sub Plan', readonly=False, domain="[('parent_id', '=', r_analytic_plan_id)]")
    s_analytic_plan_id = fields.Many2one('account.analytic.plan', 'Plan', readonly=False, domain="[('parent_id', '=', False)]")
    s_analytic_sub_plan_id = fields.Many2one('account.analytic.plan', 'Sub Plan', readonly=False, domain="[('parent_id', '=', s_analytic_plan_id)]")
    ss_analytic_plan_id = fields.Many2one('account.analytic.plan', 'Plan', readonly=False, domain="[('parent_id', '=', False)]")
    ss_analytic_sub_plan_id = fields.Many2one('account.analytic.plan', 'Sub Plan', readonly=False, domain="[('parent_id', '=', ss_analytic_plan_id)]")
    has_recurring_line = fields.Boolean(compute='_compute_has_recurring_line')
    employee_id = fields.Many2one('hr.employee', 'Owner', copy=False)
    po_no = fields.Char('PO No', copy=False)
    # fields added by sriman
    x_studio_po_date=fields.Date("PO Date", copy=False)
    x_studio_so_period_1=fields.Char("SO Details", copy=False)


    #
    # _sql_constraints = [
    #     ('date_order_conditional_required',
    #      "CHECK((state = 'sale' AND date_order IS NOT NULL) OR state != 'sale')",
    #      "A confirmed sales order requires a confirmation date."),
    #     # ('so_po_no_unique', 'UNIQUE(po_no)', 'The PO No must be unique')
    # ]

    _date_order_required_on_sale = models.Constraint(
        "CHECK((state = 'sale' AND date_order IS NOT NULL) OR state != 'sale')",
        "A confirmed sales order requires a confirmation date."
    )


    @api.depends('order_line.price_unit')
    def _do_create_invoice_schedule(self):
        for order in self:
            # for order_line in order.order_line:
            #     if order_line.product_uom.name == 'Hours':
            #         order_line.product_uom_qty = order.duration_days * 8
            #     else:
            #         order_line.product_uom_qty = order.duration_days
            #     if order_line.product_id.product_pricing_ids:
            #         for product_pricing_id in order_line.product_id.product_pricing_ids:
            #             if order_line.product_uom.name == 'Hours' and product_pricing_id.recurrence_id.unit == 'hour':
            #                 order_line.price_unit= product_pricing_id.price
            #             elif order_line.product_uom.name == 'Days'and product_pricing_id.recurrence_id.unit == 'day':
            #                 order_line.price_unit=product_pricing_id.price
            #             elif order_line.product_uom.name == 'Week'and product_pricing_id.recurrence_id.unit == 'week':
            #                 order_line.price_unit=product_pricing_id.price
            #             elif order_line.product_uom.name == 'Months'and product_pricing_id.recurrence_id.unit == 'month':
            #                 order_line.price_unit=product_pricing_id.price
            #             elif order_line.product_uom.name == 'Years' and product_pricing_id.recurrence_id.unit == 'year':
            #                 order_line.price_unit=product_pricing_id.price
            #     else:
            #         if order_line.price_unit==0.00:
            #             order_line.price_unit = order_line.product_id.with_company(order_line.company_id.id).lst_price or 0.00
            order.do_create_invoice_schedule=True

    @api.depends('order_line', 'order_line.recurring_invoice')
    def _compute_has_recurring_line(self):
        recurring_product_orders = self.order_line.filtered(lambda l: l.product_id.recurring_invoice).order_id
        recurring_product_orders.has_recurring_line = True
        (self - recurring_product_orders).has_recurring_line = False

    @api.model_create_multi
    def create(self, vals_list):
        res = super(Rentals, self).create(vals_list)
        for so in res:
            tag_ids=[]
            for tag in so.tag_ids:
                tag_ids.append(tag.id)
            if so.is_subscription == True:
                tag_obj = self.env['crm.tag'].search([('name', '=', 'Subscription')], limit=1)
                if not tag_obj:
                    tag_obj = self.env['crm.tag'].create({'name': 'Subscription'})
                tag_ids.append(tag_obj.id)
            elif so.is_rental_order == True:
                tag_obj = self.env['crm.tag'].search([('name', '=', 'HR')], limit=1)
                if not tag_obj:
                    tag_obj = self.env['crm.tag'].create({'name': 'HR'})
                tag_ids.append(tag_obj.id)
            else:
                tag_obj = self.env['crm.tag'].search([('name', '=', 'Project')], limit=1)
                if not tag_obj:
                    tag_obj = self.env['crm.tag'].create({'name': 'Project'})
                tag_ids.append(tag_obj.id)
            if tag_ids:
                so.tag_ids = [(6, 0, tag_ids)]
        return res

    def write(self, vals):
        for line in self:
            tag_ids=[]
            is_subscription=False
            if 'is_subscription' in vals:
                if vals.get('is_subscription') == True:
                    is_subscription=True
            elif line.is_subscription == True:
                is_subscription=True
            if is_subscription == True:
                for tag in line.tag_ids:
                    if tag.name not in['Project', 'HR']:
                        tag_ids.append(tag.id)
                tag_obj = self.env['crm.tag'].search([('name', '=', 'Subscription')], limit=1)
                if not tag_obj:
                    tag_obj = self.env['crm.tag'].create({'name': 'Subscription'})
                tag_ids.append(tag_obj.id)
                if tag_ids:
                    vals.update({'tag_ids': [(6, 0, tag_ids)]})
        res = super(Rentals, self).write(vals)
        return res

    @api.onchange('partner_id')
    def _onchange_partner_payment_term_id(self):
        if self.partner_id:
            self.payment_term_id = self.partner_id.property_payment_term_id

    def _prepare_invoice(self):
        vals = super()._prepare_invoice()
        if self.payment_term_id:
            vals['invoice_payment_term_id'] = self.payment_term_id.id
        return vals


    @api.onchange('project_id')
    def _onchange_project_id(self):
        if self.project_id:
            self.project_code = self.project_id.project_code
            if self.project_id.project_code=='' or self.project_id.project_code==False:
                raise ValidationError(_("Project code not available. Please check the project details."))

    @api.depends('rental_start_date', 'rental_return_date')
    def _compute_duration(self):
        for order in self:
            order.remaining_hours = 0
            order.duration_days = 0
            # planned_days=0
            # if order.rental_start_date and order.rental_return_date:
            #     employee = ''
            #     for order_line in order.rental_inv_line_ids:
            #         if order_line.employee_id:
            #             if employee == '' or employee == order_line.employee_id.id:
            #                 if order_line.employee_id.resource_calendar_id:
            #                     employee = order_line.employee_id.id
            #     for order_line in order.rental_inv_line_ids:
            #         if employee == order_line.employee_id.id:
            #             planned_days = planned_days + order_line.planned_days
            #     if order.is_rental_order == True:
            #         if planned_days>0:
            #             order.duration_days = 0

    @api.onchange('rental_start_date')
    def _onchange_finvoice(self):
        start_date = self.rental_start_date + relativedelta(hours=8)
        if self.invoice_freequency:
            self.rentalfirst_invoice_date = start_date + relativedelta(months=1)
        else:
            if self.rental_start_date:
                self.rentalfirst_invoice_date = self.rental_start_date + relativedelta(months=1)

    @api.onchange('r_analytic_plan_id','s_analytic_plan_id','ss_analytic_plan_id')
    def _onchange_set_aa1(self):
        for sale in self:
            if sale.order_line:
                sale.r_analytic_sub_plan_id=''
                sale.s_analytic_sub_plan_id=''
                sale.ss_analytic_sub_plan_id=''
                for o_line in sale.order_line:
                    o_line.analytic_distribution=False

    @api.onchange('order_line','r_analytic_plan_id','r_analytic_sub_plan_id','s_analytic_plan_id','s_analytic_sub_plan_id','ss_analytic_plan_id','ss_analytic_sub_plan_id', 'project_id','project_code','project_type_id','practice_id')
    def _onchange_set_aa(self):
        for sale in self:
            for o_line in sale.order_line:
                if o_line.product_id:
                    aa_name=''
                    project_code = sale.project_code
                    if sale.project_id:
                        project_code = sale.project_id.project_code or sale.project_id.name
                    if sale.is_rental_order==True:
                        if o_line.product_id and project_code:
                            aa_name=o_line.product_id.name+'/'+project_code
                    elif sale.is_tec_subscription==True:
                        # PRJ/CLIENTCODE/LC/Practice/SO no.
                        if sale.partner_id and sale.partner_id.customer_code and sale.practice_id and sale.name:
                            aa_name="PRJ/"+str(sale.partner_id.customer_code)+"LC/"+sale.practice_id.name+"/"+sale.name
                    else:
                        # PRJ/CLIENTCODE/PROJECT TYPE/Practice/Project Code
                        if sale.partner_id and sale.partner_id.customer_code and sale.project_type_id and sale.practice_id and sale.name and project_code:
                            aa_name = "PRJ/"+str(sale.partner_id.customer_code)+"/"+str(sale.project_type_id.name)+"/"+str(sale.practice_id.name)+"/"+project_code
                    if aa_name !='':
                        analytic_plan_id=''
                        if sale.r_analytic_sub_plan_id and sale.is_rental_order==True:
                            analytic_plan_id=sale.r_analytic_sub_plan_id
                        elif sale.ss_analytic_sub_plan_id and sale.is_tec_subscription==True:
                            analytic_plan_id=sale.ss_analytic_sub_plan_id
                        elif sale.s_analytic_sub_plan_id:
                            analytic_plan_id=sale.s_analytic_sub_plan_id
                        if analytic_plan_id:
                            aa_objs = self.env['account.analytic.account'].search([('company_id', '=', sale.company_id.id),('plan_id', '=', analytic_plan_id.id),('name', '=', aa_name)], limit=1)
                            if not aa_objs:
                                aa_dict ={aa_objs.id: 100}
                                aa_objs = self.env['account.analytic.account'].create({
                                    'plan_id': analytic_plan_id.id,
                                    'name': aa_name,
                                    # 'company_id':sale.company_id.id,
                                    'partner_id': sale.partner_id.id,
                                })
                                if aa_objs:
                                    o_line.analytic_distribution=aa_dict
                            else:
                                aa_dict ={aa_objs.id: 100}
                                if o_line.analytic_distribution:
                                    for key, value in o_line.analytic_distribution.items():
                                        aa_dict.update({key:value})
                                o_line.analytic_distribution=aa_dict


    @api.onchange('rental_start_date','rental_return_date')
    def _onchange_rental_dates(self):
        if self.is_rental_order == True:
            for order in self:
                if order.rental_start_date.hour >=18 and order.rental_start_date.hour <= 23:
                    order.rental_start_date = order.rental_start_date + relativedelta(hours=8)
                if order.rental_return_date.hour >=18 and order.rental_return_date.hour <= 23:
                    order.rental_return_date = order.rental_return_date + relativedelta(hours=8)

    @api.onchange('invoice_freequency', 'rentalfirst_invoice_date','rental_start_date','rental_return_date','order_line')
    def _onchange_inv_freeqency(self):
        if self.is_rental_order == True:
            for order in self:
                for order_line in order.order_line:
                    if order_line.product_id.product_pricing_ids:
                        for product_pricing_id in order_line.product_id.product_pricing_ids:
                            if order_line.product_uom_id.name == 'Hours' and product_pricing_id.recurrence_id.unit == 'hour':
                                order_line.price_unit= product_pricing_id.price
                            elif order_line.product_uom_id.name == 'Days'and product_pricing_id.recurrence_id.unit == 'day':
                                order_line.price_unit=product_pricing_id.price
                            elif order_line.product_uom_id.name == 'Week'and product_pricing_id.recurrence_id.unit == 'week':
                                order_line.price_unit=product_pricing_id.price
                            elif order_line.product_uom_id.name == 'Months'and product_pricing_id.recurrence_id.unit == 'month':
                                order_line.price_unit=product_pricing_id.price
                            elif order_line.product_uom_id.name == 'Years' and product_pricing_id.recurrence_id.unit == 'year':
                                order_line.price_unit=product_pricing_id.price
                    else:
                        if order_line.price_unit == 0.00:
                            order_line.price_unit = order_line.product_id.with_company(order_line.company_id.id).lst_price or 0.00
                total_working_days=0
                no_working_days=0
                self.rental_inv_line_ids=[(6, 0, [])]
                datetime_min_time = datetime.min.time()
                datetime_max_time = datetime.min.time()
                if order.invoice_freequency.unit == 'hour':
                    order.recurring_period_interval = 'hour'
                elif order.invoice_freequency.unit == 'day':
                    order.recurring_period_interval = 'day'
                elif order.invoice_freequency.unit == 'week':
                    order.recurring_period_interval = 'week'
                elif order.invoice_freequency.unit == 'month':
                    order.recurring_period_interval = 'month'
                elif order.invoice_freequency.unit == 'year':
                    order.recurring_period_interval = 'year'
                if order.rental_start_date and order.rental_return_date and order.rentalfirst_invoice_date:
                    inv_dates=[]
                    for line in order.order_line:
                        if line.product_id and line.product_id.employee_id:
                            current = order.rental_start_date
                            next_inv_date = order.rentalfirst_invoice_date
                            so_line_worked_days = 0
                            first_inv_day = order.rentalfirst_invoice_date.day
                            while current <= order.rental_return_date:
                                month_start = current.replace(day=1)
                                next_month = month_start + relativedelta(months=1)
                                month_end = next_month - timedelta(days=1)
                                range_start = current
                                range_end_actual  = min(month_end, order.rental_return_date)
                                range_end = range_end_actual + timedelta(days=1)
                                current = range_end
                                planned_worked = 0
                                planned_data = 0
                                planned_worked = \
                                line.product_id.sudo().employee_id._get_work_days_data_batch(range_start, range_end, calendar=line.product_id.sudo().employee_id.resource_calendar_id) \
                                                        [line.product_id.sudo().employee_id.id]['days']

                                total_weekends = sum(
                                    1 for i in range((range_end - range_start).days + 1)
                                    if (range_start + timedelta(days=i)).weekday() >= 5
                                )
                                planned_worked-=total_weekends

                                if planned_worked > 0:
                                    uom = 'days'
                                    if line.product_uom_id.name == 'Days':
                                        planned_data = planned_worked
                                        uom = 'days'
                                    if line.product_uom_id.name == 'Hours':
                                        planned_data = planned_worked * 8
                                        uom = 'hours'
                                    if line.product_uom_id.name == 'Months' or line.product_uom_id.name == 'Month':
                                        tz = self.env.user.tz
                                        m_start = range_start
                                        r_end = range_end_actual.astimezone(timezone(tz)).date()
                                        difference = relativedelta(r_end, m_start)
                                        actualMonths = difference.months + (r_end.day - m_start.day) / 30
                                        # planned_data = actualMonths
                                        planned_data = 1.0
                                        uom = 'months'
                                    if line.product_uom_id.name == 'Units' :
                                        planned_data = 1.0
                                        uom = 'units'
                                    rental_month = str((range_start).month)
                                    inv_dates.append((0, 0, {
                                        'sale_state': order.state,
                                        'planned_days': planned_data,
                                        'partner_id': order.partner_id.id,
                                        'employee_id': line.product_id.sudo().employee_id.id,
                                        'rentalnext_invoice_date': next_inv_date,
                                        'rentalnext_invoice_date_time': next_inv_date,
                                        'uom': uom,
                                        'rental_month': rental_month,
                                        'so_line_id': line.id,
                                        'rental_start_date': range_start,
                                        'rental_return_date': range_end - timedelta(days=1)
                                    }))

                                    next_month_range_end = range_end.date() + relativedelta(months=1)
                                    if next_inv_date > range_end.date():
                                        if first_inv_day in [28, 29, 30, 31]:
                                            next_inv_date = next_inv_date
                                        elif next_month_range_end >= next_inv_date:
                                            next_inv_date = next_inv_date + relativedelta(months=1)
                                    elif next_inv_date <= range_end.date() and next_inv_date >= range_start.date():
                                        next_inv_date = next_inv_date + relativedelta(months=1)
                                    # Find date whether last day or not
                                    month_days = calendar.monthrange(next_inv_date.year, next_inv_date.month)[1]
                                    last_day = calendar.monthrange(order.rentalfirst_invoice_date.year, order.rentalfirst_invoice_date.month)[1]
                                    first_inv_month_end = order.rentalfirst_invoice_date.replace(day=last_day)
                                    if first_inv_month_end == order.rentalfirst_invoice_date:
                                        if month_days == 28:
                                            next_inv_date = next_inv_date.replace(day=28)
                                        elif month_days == 29:
                                            next_inv_date = next_inv_date.replace(day=29)
                                        elif month_days == 30:
                                            next_inv_date = next_inv_date.replace(day=30)
                                        elif month_days == 31:
                                            next_inv_date = next_inv_date.replace(day=31)

                                    elif first_inv_day in [28, 29, 30] and next_inv_date.month == 2:
                                        feb_last_day = calendar.monthrange(next_inv_date.year, next_inv_date.month)[1]
                                        next_inv_date = next_inv_date.replace(day=feb_last_day)
                                    else:
                                        next_inv_date = next_inv_date.replace(day=first_inv_day)
                                    # next_inv_date = next_inv_date + relativedelta(months=1)
                                    so_line_worked_days = so_line_worked_days + planned_worked
                            order.duration_days = so_line_worked_days
                    if inv_dates:
                        order.rental_inv_line_ids = inv_dates
                    employee = False
                    for sl_line in order.order_line:
                        if sl_line.manually_edited == True:
                            sl_line.product_uom_qty = sl_line.product_uom_qty
                            # sl_line.manually_edited = False
                        else:
                            if sl_line.product_uom_id.name == 'Hours':
                                sl_line.product_uom_qty = order.duration_days * 8
                            if sl_line.product_uom_id.name == 'Days':
                                sl_line.product_uom_qty = order.duration_days
                            if sl_line.product_uom_id.name == 'Months':
                                if not employee:
                                    month_employee = order.rental_inv_line_ids.filtered(lambda so_inv: so_inv.uom == 'months')
                                    employee = month_employee[0].sudo().employee_id
                                month_planned_data = 0
                                for rental_inv in order.rental_inv_line_ids:
                                    if employee == rental_inv.sudo().employee_id:
                                        month_planned_data = rental_inv.planned_days + month_planned_data
                                sl_line.product_uom_qty = month_planned_data


    def _confirmation_error_message(self):
        """ Return whether order can be confirmed or not if not then returm error message. """
        self.ensure_one()
        if self.state not in {'draft', 'sent'}:
            if self.is_rental_order == False:
                return _("Some orders are not in a state requiring confirmation.")
        if any(
                not line.display_type
                and not line.is_downpayment
                and not line.product_id
                for line in self.order_line
        ):
            return _("A line on these orders missing a product, you cannot confirm it.")

        return False

    def create_rental_invoice(self, rental_obj):
        invoice_line_ids=[]
        invoice_date=''
        for line in rental_obj.rental_sale_id.order_line:
            for rental_line in rental_obj.rental_sale_id.rental_inv_line_ids:
                if not invoice_date and rental_line.is_ready_to_invoice==True and rental_line.worked_days>0:
                    invoice_date = rental_line.rentalnext_invoice_date
                if not rental_line.inv_ref_id and rental_line.worked_days>0 and rental_line.is_selected:
                    if line.product_id.sudo().employee_id.id == rental_line.sudo().employee_id.id:
                        old_rental_objs = self.env['rental.invoice.history'].search(
                            [('rental_sale_id', '=', rental_obj.rental_sale_id.id),('employee_id', '=', rental_line.sudo().employee_id.id),
                             ('state', 'in', ['confirmed', 'done'])], limit=1, order='id desc')
                        if old_rental_objs:
                            old_inv_date = old_rental_objs.rentalnext_invoice_date
                        else:
                            old_inv_date = rental_obj.rental_sale_id.rental_start_date + relativedelta(hours=8)
                        upcoming_rental_objs = self.env['rental.invoice.history'].search(
                            [('rental_sale_id', '=', rental_obj.rental_sale_id.id),
                             ('employee_id', '=', rental_line.sudo().employee_id.id),
                             ('state', 'in', ['draft'])], limit=1)
                        if upcoming_rental_objs:
                            new_inv_date = upcoming_rental_objs.rentalnext_invoice_date
                        else:
                            new_inv_date = rental_obj.rental_sale_id.rental_return_date
                        distribution = line.env['account.analytic.distribution.model']._get_distribution({
                            "product_id": line.product_id.id,
                            "partner_id": line.order_id.partner_id.id,
                            "company_id": line.company_id.id,
                        })
                        analytic_distribution = distribution or line.analytic_distribution
                        if rental_obj.worked_days>0:
                            inv_line={
                                'product_id': line.product_id.id,
                                'product_uom_id':line.product_uom_id.id,
                                'name': line.product_id.name,
                                'quantity': rental_line.worked_days,
                                'price_unit': line.price_unit,
                                'tax_ids': line.tax_ids,
                                'discount': line.discount,
                                'sale_line_ids': [Command.link(line.id)],
                                'rental_start_date': rental_line.rental_start_date,
                                'rental_return_date': rental_line.rental_return_date,
                                'discount_fixed': line.discount_fixed
                            }
                            if analytic_distribution:
                                inv_line.update({'analytic_distribution':analytic_distribution})
                            invoice_line_ids.append((0, 0, inv_line))
                        # line.qty_delivered = line.qty_delivered + rental_line.worked_days
                        rental_line.is_ready_to_invoice=False
                        rental_line.state='done'
        if invoice_line_ids:
            inv_obj = self.env['account.move'].create({
                'move_type': 'out_invoice',
                'partner_id': rental_obj.rental_sale_id.partner_id.id,
                'invoice_date': invoice_date or fields.Date.today(),
                'ref': rental_obj.rental_sale_id.client_order_ref or "",
                'narration': rental_obj.rental_sale_id.note,
                'source_id': rental_obj.rental_sale_id.source_id.id,
                'team_id': rental_obj.rental_sale_id.team_id.id,
                'fiscal_position_id': (rental_obj.rental_sale_id.fiscal_position_id or rental_obj.rental_sale_id.fiscal_position_id._get_fiscal_position(rental_obj.rental_sale_id.partner_invoice_id)).id,
                'invoice_origin': rental_obj.rental_sale_id.name,
                'invoice_payment_term_id': rental_obj.rental_sale_id.payment_term_id.id,
                'invoice_user_id': rental_obj.rental_sale_id.user_id.id,
                'payment_reference': rental_obj.rental_sale_id.reference,
                'user_id': rental_obj.rental_sale_id.user_id.id,
                'currency_id': rental_obj.rental_sale_id.currency_id.id,
                'invoice_line_ids': invoice_line_ids
            })
            if inv_obj:
                for line in rental_obj.rental_sale_id.order_line:
                    for rental_line in rental_obj.rental_sale_id.rental_inv_line_ids:
                        if not rental_line.inv_ref_id and rental_line.worked_days > 0.00 and rental_line.is_selected:
                            if line.product_id.sudo().employee_id.id == rental_line.sudo().employee_id.id:
                                rental_line.inv_ref_id = inv_obj.id
                                rental_line.is_selected = False
                for inv_line in inv_obj.invoice_line_ids:
                    inv_line._compute_name()
                    for so_line in rental_obj.rental_sale_id.order_line:
                        if inv_line.product_id.id == so_line.product_id.id:
                            inv_ids=[inv_line.id]+so_line.invoice_lines.ids
                            so_line.invoice_lines = [(6, 0, inv_ids)]
                return inv_obj

    def _cron_create_rental_month_invoices(self, rental_invoice=''):
        """ Generate invoice """
        if rental_invoice:
            rental_objs = rental_invoice
        else:
            to_be_invoiced=[]
            user_tz = timezone(self.env.user.tz or 'UTC')
            now_dt = datetime.now().astimezone(user_tz).replace(tzinfo=None)
            r_invoice_day = self.env['ir.config_parameter'].sudo().get_param('techcarret_rental.r_invoice_day')
            search_date = date.today() + timedelta(days=int(r_invoice_day))
            rental_objs = self.env['rental.invoice.history'].search([('state', '=', 'draft')])
            for rental_obj in rental_objs:
                if rental_obj.rentalnext_invoice_date <= search_date:
                    if rental_obj.rental_sale_id.invoice_freequency.unit in ['hour']:
                        rentalnext_invoice_date_time  = pytz.utc.localize(rental_obj.rentalnext_invoice_date_time).astimezone(user_tz)
                        if rentalnext_invoice_date_time.date() < now_dt.date():
                            to_be_invoiced.append(rental_obj.id)
                        elif rentalnext_invoice_date_time.hour <= now_dt.hour:
                            to_be_invoiced.append(rental_obj.id)
                    else:
                        to_be_invoiced.append(rental_obj.id)
            if to_be_invoiced:
                rental_objs = self.env['rental.invoice.history'].search([('id', 'in', to_be_invoiced)])
        for rental_obj in rental_objs:
            if rental_obj.rental_sale_id.state=='sale':
                pending_month=[]
                for rh in rental_obj.rental_sale_id.rental_inv_line_ids:
                    if rh.state == 'draft':
                        m = rh.rentalnext_invoice_date.month
                        y = rh.rentalnext_invoice_date.year
                        str_m_y = str(m)+'_'+str(y)
                        pending_month.append(str_m_y)
                timesheet_months=[]
                if rental_obj.worked_days<=0:
                    old_rental_objs = self.env['rental.invoice.history'].search([('rental_sale_id','=',rental_obj.rental_sale_id.id),('id', '=', int(rental_obj.id-1)),('state','in',['confirmed','done'])], limit=1)
                    future_rental_objs = self.env['rental.invoice.history'].search([('rental_sale_id','=',rental_obj.rental_sale_id.id),('id', '=', int(rental_obj.id+1)),('state','in',['draft'])], limit=1)
                    if old_rental_objs:
                        start_date=(old_rental_objs.rentalnext_invoice_date).strftime('%Y-%m-%d 00:00:00')
                        if future_rental_objs:
                            end_date=datetime.strftime(future_rental_objs.rentalnext_invoice_date - timedelta(days=1), "%Y-%m-%d 23:59:59")
                        else:
                            end_date=datetime.strftime(rental_obj.rental_sale_id.rental_return_date, "%Y-%m-%d 23:59:59")
                    else:
                        start_date=(rental_obj.rental_sale_id.rental_start_date).strftime('%Y-%m-%d 00:00:00')
                        if future_rental_objs:
                            end_date=datetime.strftime(future_rental_objs.rentalnext_invoice_date - timedelta(days=1), "%Y-%m-%d 23:59:59")
                        else:
                            end_date=datetime.strftime(rental_obj.rental_sale_id.rental_return_date, "%Y-%m-%d 23:59:59")
                    delta =timedelta(days=1)
                    start_date = datetime.strptime(start_date, '%Y-%m-%d %H:%M:%S')
                    end_date = datetime.strptime(end_date, '%Y-%m-%d %H:%M:%S')
                    while start_date <= end_date:
                        m = start_date.month
                        y = start_date.year
                        str_m_y = str(m)+'_'+str(y)
                        if str_m_y not in timesheet_months and str_m_y in pending_month:
                            timesheet_months.append(str_m_y)
                        start_date += delta
                    if rental_obj.sudo().employee_id:
                        #CREATE RENTAL INVOICE
                        if rental_obj.worked_days>0:
                            self.create_rental_invoice(rental_obj)
                            rental_obj.state = 'done'
                            rental_obj.is_ready_to_invoice=False
                            if future_rental_objs:
                                future_rental_objs.is_ready_to_invoice=True
                                rental_obj.rental_sale_id.rentalnext_invoice_date = future_rental_objs.rentalnext_invoice_date
                else:
                    #CREATE RENTAL INVOICE
                    self.create_rental_invoice(rental_obj)
                    rental_obj.state = 'done'
                    rental_obj.is_ready_to_invoice=False
                    future_rental_objs = self.env['rental.invoice.history'].search([('rental_sale_id','=',rental_obj.rental_sale_id.id),('id', '=', int(rental_obj.id+1)),('state','in',['draft'])], limit=1)
                    if future_rental_objs:
                        future_rental_objs.is_ready_to_invoice=True
                        rental_obj.rental_sale_id.rentalnext_invoice_date = future_rental_objs.rentalnext_invoice_date

    def action_confirm(self):
        res = super(Rentals, self).action_confirm()
        for order in self:
            if order.is_rental_order == True:
                for rental_in in order.rental_inv_line_ids:
                    rental_in.state ='draft'
                # for o_line in so_line.order_line:
                    # if o_line.product_id and not o_line.product_id.employee_id:
                    #     raise UserError(_("Employee profile not mapped in product master"))
                for r_invoice in order.rental_inv_line_ids:
                    r_invoice.sale_state='sale'
            order.project_id.sale_order_id = order.id
            if not order.order_line:
                raise ValidationError(_("Please add atleast one line item in order lines."))
            if not order.is_rental_order and not order.is_subscription:
                order.project_id.reinvoiced_sale_order_id = order.id
                order.project_id.sale_line_id = order.order_line[0].id
                order.project_id.partner_id = order.partner_id.id
        return res

    def action_cancel(self):
        res = super(Rentals, self).action_cancel()
        for so_line in self:
            if so_line.is_rental_order == True:
                for r_invoice in so_line.rental_inv_line_ids:
                    r_invoice.sale_state='cancel'
                    r_invoice.state='cancel'
        return res

    def action_draft(self):
        res = super(Rentals, self).action_draft()
        for so_line in self:
            if so_line.is_rental_order == True:
                for line in so_line.order_line:
                    line.qty_delivered =0
                for r_invoice in so_line.rental_inv_line_ids:
                    r_invoice.sale_state='draft'
                    r_invoice.state='draft'
        return res

    # def _prepare_analytic_account_data(self, prefix=None):
    #     """ Prepare SO analytic account creation values.
    #
    #     :return: `account.analytic.account` creation values
    #     :rtype: dict
    #     """
    #     self.ensure_one()
    #     name = self.name
    #     if prefix:
    #         name = prefix + ": " + self.name
    #     project_plan, _other_plans = self.env['account.analytic.plan']._get_all_plans()
    #     return {
    #         'name': self.project_code,
    #         'code': self.client_order_ref,
    #         'company_id': self.company_id.id,
    #         'plan_id': project_plan.id,
    #         'partner_id': self.partner_id.id,
    #     }

    def action_quotation_send(self):
        res = super(Rentals, self).action_quotation_send()
        for order in self:
            pdf_content = \
            self.env['ir.actions.report']._render('techcarret_rental.action_generate_techcarrot_sale_report', self.ids)[0]
            pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')
            name = ''
            if self.state in ['draft', 'sent']:
                name = 'Quotation'
            if self.state == 'sale':
                name = 'Sale Order'
            attachment = self.env['ir.attachment'].create({
                'name': name + ' - ' + self.name,
                'type': 'binary',
                'datas': pdf_base64,
                'res_model': 'sale.order',
                'res_id': self.id,
                'mimetype': 'application/pdf'
            })
            if res.get('context'):
                res['context'].setdefault('default_attachment_ids', []).append(attachment.id)
        return res


class RentalOrdersLine(models.Model):
    _inherit = 'sale.order.line'

    # qty_delivered = fields.Float(
    #     string="Delivery Quantity",
    #     compute='_compute_qty_delivered',
    #     default=0.0,
    #     digits='Product Unit of Measure',
    #     store=True, readonly=False, copy=False)
    start_date = fields.Datetime()
    return_date = fields.Datetime()
    manually_edited = fields.Boolean('Manually Edited', default=False)

    # def write(self, vals):
    #     res = super(RentalOrdersLine, self).write(vals)
    #     print('SWIRTTRTTRRRRRRRRRRRRR_______________',self)
    #     self.manually_edited = False
    #     return res

    # code changed by sriman 'product_uom' to 'product_uom_id' as product_uom is not available in odoo19. entire code it is changes
    @api.depends('product_id', 'product_uom_id', 'product_uom_qty')
    def _compute_discount(self):
        discount_enabled = self.env['product.pricelist.item']._is_discount_feature_enabled()
        for line in self:
            if not line.product_id or line.display_type:
                line.discount = 0.0
            if not (line.order_id.pricelist_id and discount_enabled):
                continue
            # line.discount = 0.0
            if not line.pricelist_item_id._show_discount():
                # No pricelist rule was found for the product
                # therefore, the pricelist didn't apply any discount/change
                # to the existing sales price.
                continue
            line = line.with_company(line.company_id)
            pricelist_price = line._get_pricelist_price()
            base_price = line._get_pricelist_price_before_discount()

            if base_price != 0:  # Avoid division by zero
                discount = (base_price - pricelist_price) / base_price * 100
                if (discount > 0 and base_price > 0) or (discount < 0 and base_price < 0):
                    # only show negative discounts if price is negative
                    # otherwise it's a surcharge which shouldn't be shown to the customer
                    line.discount = discount

    @api.onchange('product_uom_qty')
    def _onchange_product_uom_qty(self):
        for order in self:
            if order.order_id and order.order_id.is_rental_order == True:
                if order.product_id and order.product_uom_qty>0.00:
                    # order.manually_edited = False
                    if order.product_uom_id.name == 'Hours':
                        hours_qty = order.order_id.duration_days * 8
                        if order.product_uom_qty != hours_qty:
                            order.manually_edited = True
                    elif order.product_uom_id.name == 'Days':
                        days_qty = order.order_id.duration_days
                        if order.product_uom_qty != days_qty:
                            order.manually_edited = True
                    elif order.product_uom_id.name == 'Months':
                        tz = self.env.user.tz
                        m_start = order.order_id.rental_start_date + relativedelta(hours=7)
                        r_end = order.order_id.rental_return_date.astimezone(timezone(tz)).date()
                        difference = relativedelta(r_end, m_start)
                        month_qty = difference.months + (r_end.day - m_start.day) / 30
                        # if order.product_uom_qty != month_qty:
                        order.manually_edited = True

    @api.onchange('product_uom_id')
    def _onchange_product_uom_manual(self):
        for order in self:
            if order.order_id and order.order_id.is_rental_order == True:
                order.manually_edited = False

    # @api.depends(
    #     'qty_delivered_method',
    #     'analytic_line_ids.so_line',
    #     'analytic_line_ids.unit_amount',
    #     'analytic_line_ids.product_uom_id')
    # def _compute_qty_delivered(self):
    #     """ This method compute the delivered quantity of the SO lines: it covers the case provide by sale module, aka
    #         expense/vendor bills (sum of unit_amount of AAL), and manual case.
    #         This method should be overridden to provide other way to automatically compute delivered qty. Overrides should
    #         take their concerned so lines, compute and set the `qty_delivered` field, and call super with the remaining
    #         records.
    #     """
    #     # compute for analytic lines
    #     for line in self:
    #         if line.order_id.is_rental_order == False:
    #             lines_by_analytic = self.filtered(lambda sol: sol.qty_delivered_method == 'analytic')
    #             mapping = lines_by_analytic._get_delivered_quantity_by_analytic([('amount', '<=', 0.0)])
    #             for so_line in lines_by_analytic:
    #                 so_line.qty_delivered = mapping.get(so_line.id or so_line._origin.id, 0.0)

    @api.depends('qty_delivered_method', 'product_uom_qty', 'reached_milestones_ids.quantity_percentage')
    def _compute_qty_delivered(self):
        lines_by_milestones = self.filtered(lambda sol: sol.qty_delivered_method == 'milestones')
        super(RentalOrdersLine, self - lines_by_milestones)._compute_qty_delivered()

        if not lines_by_milestones:
            return

        project_milestone_read_group = self.env['project.milestone']._read_group(
            [('sale_line_id', 'in', lines_by_milestones.ids), ('is_reached', '=', True)],
            ['sale_line_id'],
            ['quantity_percentage:sum'],
        )
        reached_milestones_per_sol = {sale_line.id: percentage_sum for sale_line, percentage_sum in
                                      project_milestone_read_group}
        for line in lines_by_milestones:
            sol_id = line.id or line._origin.id
            qty_delivered = reached_milestones_per_sol.get(sol_id, 0.0) * line.product_uom_qty
            line.qty_delivered = line.product_uom_id._compute_quantity(qty_delivered, line.product_uom_id)


def _get_rental_order_line_description(self):
        tz = self._get_tz()
        if self.order_id.is_rental_order == True:
            start_date = self.order_id.rental_start_date + relativedelta(hours=2)
            return_date = self.order_id.rental_return_date
            start_date = start_date.replace(tzinfo=UTC).astimezone(timezone(tz)).date()
            return_date = return_date.replace(tzinfo=UTC).astimezone(timezone(tz)).date()
            start_date = start_date.strftime(get_lang(self.env).date_format)
            return_date = return_date.strftime(get_lang(self.env).date_format)
            # s_date = start_date.strftime("%m-%d-%Y")
            # r_date = return_date.strftime("%m-%d-%Y")
            return _(
                " ", from_date=start_date, to_date=return_date
            )
        else:
            start_date = self.order_id.rental_start_date
            return_date = self.order_id.rental_return_date
            env = self.with_context(use_babel=True).env
            if start_date and return_date \
                    and start_date.replace(tzinfo=UTC).astimezone(timezone(tz)).date() \
                    == return_date.replace(tzinfo=UTC).astimezone(timezone(tz)).date():
                # If return day is the same as pickup day, don't display return_date Y/M/D in description.
                return_date_part = format_time(env, return_date, tz=tz, time_format=False)
            else:
                return_date_part = format_datetime(env, return_date, tz=tz, dt_format=False)
            start_date_part = format_datetime(env, start_date, tz=tz, dt_format=False)
            return _(
                "\n%(from_date)s to %(to_date)s", from_date=start_date_part, to_date=return_date_part
            )

@api.depends('product_id', 'linked_line_id', 'linked_line_ids')
def _compute_name(self):
    for line in self:
        if not line.product_id and not line.is_downpayment:
            continue

        lang = line.order_id._get_lang()
        if lang != self.env.lang:
            line = line.with_context(lang=lang)

        if line.product_id and line.order_id.is_rental_order:
            if line.name:
                line.name = line.name
            else:
                line.name = " "
            continue
        elif line.product_id:
            line.name = line._get_sale_order_line_multiline_description_sale()
            continue

        if line.is_downpayment:
            line.name = line._get_downpayment_description()



    # def _timesheet_create_project_prepare_values(self):
    #     """Generate project values"""
    #     # create the project or duplicate one
    #     return {
    #         'name': self.order_id.project_code,
    #         'partner_id': self.order_id.partner_id.id,
    #         'sale_line_id': self.id,
    #         'active': True,
    #         'company_id': self.company_id.id,
    #         'allow_billable': True,
    #         'date_start': self.order_id.rental_start_date,
    #         'date': self.order_id.rental_return_date,
    #         'user_id': self.product_id.project_template_id.user_id.id,
    #     }

    # def _timesheet_service_generation(self):
    #     """ For service lines, create the task or the project. If already exists, it simply links
    #         the existing one to the line.
    #         Note: If the SO was confirmed, cancelled, set to draft then confirmed, avoid creating a
    #         new project/task. This explains the searches on 'sale_line_id' on project/task. This also
    #         implied if so line of generated task has been modified, we may regenerate it.
    #     """
    #     so_line_task_global_project = self._get_so_lines_task_global_project()
    #     products_no_project = so_line_task_global_project.filtered(
    #         lambda sol: not (sol.product_id.project_id or sol.order_id.project_id)
    #     ).product_id
    #     if products_no_project:
    #         raise UserError(_(
    #             "A project must be defined on the quotation or on the form of products creating a task on order.\n"
    #             "The following products need a project in which to put their task: %(product_names)s",
    #             product_names=format_list(self.env, products_no_project.mapped('name')),
    #         ))
    #     so_line_new_project = self._get_so_lines_new_project()
    #
    #     # search so lines from SO of current so lines having their project generated, in order to check if the current one can
    #     # create its own project, or reuse the one of its order.
    #     map_so_project = {}
    #     if so_line_new_project:
    #         order_ids = self.mapped('order_id').ids
    #         so_lines_with_project = self.search([('order_id', 'in', order_ids), ('project_id', '!=', False), ('product_id.service_tracking', 'in', ['project_only', 'task_in_project']), ('product_id.project_template_id', '=', False)])
    #         map_so_project = {sol.order_id.id: sol.project_id for sol in so_lines_with_project}
    #         so_lines_with_project_templates = self.search([('order_id', 'in', order_ids), ('project_id', '!=', False), ('product_id.service_tracking', 'in', ['project_only', 'task_in_project']), ('product_id.project_template_id', '!=', False)])
    #         map_so_project_templates = {(sol.order_id.id, sol.product_id.project_template_id.id): sol.project_id for sol in so_lines_with_project_templates}
    #
    #     # search the global project of current SO lines, in which create their task
    #     map_sol_project = {}
    #     if so_line_task_global_project:
    #         map_sol_project = {sol.id: sol.product_id.with_company(sol.company_id).project_id for sol in so_line_task_global_project}
    #
    #     def _can_create_project(sol):
    #         if not sol.project_id:
    #             if sol.product_id.project_template_id:
    #                 return (sol.order_id.id, sol.product_id.project_template_id.id) not in map_so_project_templates
    #             elif sol.order_id.id not in map_so_project:
    #                 return True
    #         return False
    #
    #     # task_global_project: create task in global project
    #     # for so_line in so_line_task_global_project:
    #     #     if not so_line.task_id:
    #     #         project = map_sol_project.get(so_line.id) or so_line.order_id.project_id
    #     #         if project and so_line.product_uom_qty > 0:
    #     #             so_line._timesheet_create_task(project)
    #
    #     # project_only, task_in_project: create a new project, based or not on a template (1 per SO). May be create a task too.
    #     # if 'task_in_project' and project_id configured on SO, use that one instead
    #     for so_line in so_line_new_project:
    #         project = False
    #         if so_line.product_id.service_tracking in ['project_only', 'task_in_project']:
    #             project = so_line.project_id
    #         if not project and _can_create_project(so_line):
    #             # project = so_line._timesheet_create_project()
    #             if so_line.product_id.project_template_id:
    #                 map_so_project_templates[(so_line.order_id.id, so_line.product_id.project_template_id.id)] = project
    #             else:
    #                 map_so_project[so_line.order_id.id] = project
    #         elif not project:
    #             # Attach subsequent SO lines to the created project
    #             so_line.project_id = (
    #                 map_so_project_templates.get((so_line.order_id.id, so_line.product_id.project_template_id.id))
    #                 or map_so_project.get(so_line.order_id.id)
    #             )
    #         if so_line.product_id.service_tracking == 'task_in_project':
    #             if not project:
    #                 if so_line.product_id.project_template_id:
    #                     project = map_so_project_templates[(so_line.order_id.id, so_line.product_id.project_template_id.id)]
    #                 else:
    #                     project = map_so_project[so_line.order_id.id]
    #             # if not so_line.task_id:
    #             #     so_line._timesheet_create_task(project=project)
    #         # so_line._handle_milestones(project)
    #
    #     # If the SO generates projects or create task in project on confirmation and the project of the SO is not set, set it to the project with the lowest sequence
    #     so_lines = so_line_task_global_project + so_line_new_project
    #     so = so_lines.order_id
    #     sol_projects = so_lines.project_id | so_lines.task_id.project_id
    #     if not so.project_id and sol_projects:
    #         so.project_id = sol_projects.sorted('sequence')[0]

    @api.onchange('product_id')
    def _onchange_rent_product(self):
        for order in self:
            order.start_date = order.order_id.rental_start_date
            order.return_date = order.order_id.rental_return_date
            # order.order_id._onchange_inv_freeqency()
            if order.order_id.is_rental_order == True:
                # if order.product_id and not order.product_id.employee_id:
                #     raise UserError(_("Employee profile not mapped in product master"))
                # if order.product_id.employee_id.work_log_ids:
                #     for line in order.product_id.employee_id.work_log_ids:
                #         if line.state == 'active':
                #             raise UserError(_("Employee is not available for rental."))
                if order.order_id.duration_days>0 and order.product_uom_qty<=1:
                    if order.product_uom_id.name == 'Hours':
                        order.product_uom_qty = order.order_id.duration_days * 8
                    elif order.product_uom_id.name == 'Months':
                        months = (order.order_id.rental_return_date.year - order.order_id.rental_start_date.year) * 12 + (
                                             order.order_id.rental_return_date.month - order.order_id.rental_start_date.month)
                        order.product_uom_qty = months
                    else:
                        order.product_uom_qty = order.order_id.duration_days

    @api.onchange('product_id', 'product_uom_id', 'product_uom_qty')
    def _onchange_rentalproduct(self):
        for order in self:
            if order.order_id.is_rental_order == True:
                if order.product_id.product_pricing_ids:
                    for product_pricing_id in order.product_id.product_pricing_ids:
                        if order.product_uom_id.name == 'Hours' and product_pricing_id.recurrence_id.unit == 'hour':
                            order.price_unit= product_pricing_id.price
                        elif order.product_uom_id.name == 'Days'and product_pricing_id.recurrence_id.unit == 'day':
                            order.price_unit=product_pricing_id.price
                        elif order.product_uom_id.name == 'Week'and product_pricing_id.recurrence_id.unit == 'week':
                            order.price_unit=product_pricing_id.price
                        elif order.product_uom_id.name == 'Months'and product_pricing_id.recurrence_id.unit == 'month':
                            order.price_unit=product_pricing_id.price
                        elif order.product_uom_id.name == 'Years' and product_pricing_id.recurrence_id.unit == 'year':
                            order.price_unit=product_pricing_id.price
                else:
                    if order.price_unit == 0.00:
                        order.price_unit = order.product_id.with_company(order.company_id.id).lst_price

    def action_replace_product_desc(self):
        return {
            'name': _('Enter Product Desc'),
            'type': 'ir.actions.act_window',
            'res_model': 'edit.product.desc',
            'view_mode': 'form',
            # 'context': {'default_demand_quantity': self.product_uom_qty},
            'target': 'new',
        }

class RentalInvoiceHistory(models.Model):
    _name = 'rental.invoice.history'

    rental_sale_id = fields.Many2one(
        comodel_name='sale.order',
        string="Rental Order",
        required=True, ondelete='cascade', index=True, copy=False)
    so_line_id = fields.Many2one(comodel_name='sale.order.line', string="Rental Order Line")
    is_ready_to_invoice = fields.Boolean('Can be invoiced?', default=False, copy=False)
    partner_id = fields.Many2one('res.partner', string="Customer")
    rentalnext_invoice_date = fields.Date(string='Next Invoice Date')
    rentalnext_invoice_date_time = fields.Datetime(string='Next Invoice Date')
    employee_id = fields.Many2one('hr.employee', string='Employee')
    inv_ref_id = fields.Many2one('account.move', 'Invoice Ref#')
    invoice_state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('posted', 'Posted'),
            ('cancel', 'Cancelled'),
        ],
        related='inv_ref_id.state',
        string='Status',
    )
    sale_state = fields.Selection([('draft', "Quotation"),
                              ('sent', "Quotation Sent"),
                              ('sale', "Sales Order"),
                              ('cancel', "Cancelled"),], default='draft')
    state = fields.Selection([('draft', 'Draft'), ('done', 'Invoiced'),('confirmed','Confirmed'),('cancel','Cancel')], default='draft')
    uom = fields.Selection([("hours", "Hours"), ("days", "Days"), ("months", "Months"),("units","Units")], string="UOM", required=True, default="days")
    rental_month = fields.Selection([
        ("1", "January"),
        ("2", "February"),
        ("3", "March"),
        ("4", "April"),
        ("5", "May"),
        ("6", "June"),
        ("7", "July"),
        ("8", "August"),
        ("9", "September"),
        ("10", "October"),
        ("11", "November"),
        ("12", "December"),
    ], string="Rental Month", default="1")
    work_entry_ids = fields.Many2many('hr.work.entry', string='Work Entries')
    planned_days = fields.Float("Planned QTY", default=1.0)
    worked_days = fields.Float("Worked QTY")
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    is_selected = fields.Boolean("Select")
    rental_start_date = fields.Datetime('Rental Start Date')
    rental_return_date = fields.Datetime('Rental Return Date')

    def create_invoice(self):
        for line in self:
            line.rental_sale_id._cron_create_rental_month_invoices(line)

    # @api.onchange('worked_days')
    # def _onchange_worked_days(self):
    #     self.is_ready_to_invoice=False
    #     if self.worked_days > self.planned_days:
    #         raise ValidationError("Worked Quantity cannot be greater than the Planned Quantity.")
    #     if self.worked_days>0.0:
    #         self.is_ready_to_invoice=True

    @api.onchange('planned_days')
    def _onchage_planned_days(self):
        if self.planned_days == 0:
            raise ValidationError("Planned Quantity cannot be zero.")

    def create_invoice_button_reset(self):
        if self.state == 'done' and not self.inv_ref_id:
            self.state = 'draft'
            self.is_ready_to_invoice = True

class ProjectProject(models.Model):
    _inherit = 'project.project'

    allow_billable = fields.Boolean("Billable", default=True)
    project_code = fields.Char('Project Code', copy=False)

    def unlinkaa(self):
        # Delete the empty related analytic account
        analytic_accounts_to_delete = self.env['account.analytic.account']
        for project in self:
            if project.account_id:
                analytic_accounts_to_delete |= project.account_id
        analytic_accounts_to_delete.unlink()
        return True

    @api.model_create_multi
    def create(self, vals):
        # if 'name' in vals and self.search([('name', '=', vals['name'])]):
        #     raise ValidationError(_('Name must be unique.'))
        for create_val in vals:
            if 'project_code' in create_val and self.search([('project_code', 'ilike', create_val['project_code'])]):
                raise ValidationError(_('Project code must be unique.'))
        return super().create(vals)

    # def write(self, vals):
    #     # if 'name' in vals:
    #     #     for record in self:
    #     #         existing = self.search([('name', '=', vals['name']), ('id', '!=', record.id)])
    #     #         if existing:
    #     #             raise ValidationError(_('Name must be unique.'))
    #     if 'project_code' in vals:
    #         for record in self:
    #             existing = self.search([('project_code', 'ilike', vals['project_code']), ('id', '!=', record.id)])
    #             if existing:
    #                 raise ValidationError(_('Project code must be unique.'))
    #     res = super(ProjectProject, self).write(vals) if vals else True
    #     for line in self:
    #         line.unlinkaa()
    #     return res

    # @api.constrains('sale_line_id')
    # def _check_sale_line_type(self):
    #     for project in self.filtered(lambda project: project.sale_line_id):
    #         break
    #         # if not project.sale_line_id.is_service:
            #     raise ValidationError(
            #         _("You cannot link a billable project to a sales order item that is not a service."))
            # if project.sale_line_id.is_expense:
            #     raise ValidationError(
            #         _("You cannot link a billable project to a sales order item that comes from an expense or a vendor bill."))
