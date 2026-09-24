from odoo import api, fields, models, _
from odoo.osv import expression
from odoo.exceptions import ValidationError


class AccountMove(models.Model):
    _inherit = "account.move"

    doc_no = fields.Char('Doc No#')
    cust_inv_date = fields.Date('Customer INV Date')
    project_id = fields.Many2one('project.project', string='Project')

    def vat_report(self):
        tax_id = self.env['account.tax'].search([
            ('name', '=', '5%  Tax Included'),
            ('type_tax_use', '=', 'purchase'),
        ], limit=1).id

        old_base_tag = self.env['account.account.tag'].search([('name', '=', '1(b)B'), ('applicability', '=', 'taxes')],
                                                              limit=1).id
        old_tax_tag = self.env['account.account.tag'].search([('name', '=', '1(b)T'), ('applicability', '=', 'taxes')],
                                                             limit=1).id
        new_base_tag = self.env['account.account.tag'].search([('name', '=', '9B'), ('applicability', '=', 'taxes')],
                                                              limit=1).id
        new_tax_tag = self.env['account.account.tag'].search([('name', '=', '9T'), ('applicability', '=', 'taxes')],
                                                             limit=1).id

        base_lines = self.env['account.move.line'].search([
            ('tax_ids', 'in', tax_id),
            ('tax_tag_ids', 'in', old_base_tag),
            ('parent_state', '=', 'posted'),
        ])
        tax_lines = self.env['account.move.line'].search([
            ('tax_line_id', '=', tax_id),
            ('tax_tag_ids', 'in', old_tax_tag),
            ('parent_state', '=', 'posted'),
        ])

        base_lines.write({'tax_tag_ids': [(3, old_base_tag), (4, new_base_tag)]})
        tax_lines.write({'tax_tag_ids': [(3, old_tax_tag), (4, new_tax_tag)]})
    
    @api.onchange('project_id')
    def _onchange_project_id(self):
        """When project is selected on invoice, update all line project codes"""
        if self.project_id and self.project_id.project_code:
            for line in self.invoice_line_ids:
                if not line.project_code:
                    line.project_code = self.project_id.project_code
    def get_extra_print_items(self):
        print_items = []
        posted_moves = self.filtered(lambda move: move.state == 'posted')

        can_export_xml = any(
            (
                    move.ubl_cii_xml_id
                    or (
                            move.commercial_partner_id
                            and (
                                    (edi_format := move.commercial_partner_id.with_company(
                                        move.company_id)._get_ubl_cii_edi_format())
                                    and move._need_ubl_cii_xml(edi_format)
                            )
                    )
            )
            for move in posted_moves
        )

        if can_export_xml:
            print_items.append({
                'key': 'download_ubl',
                'description': _('Export XML'),
                **posted_moves.action_invoice_download_ubl(),
            })
        return print_items


    
    def action_update_project_codes(self):
        """Update all invoice lines with the selected project code"""
        self.ensure_one()
        if not self.project_id or not self.project_id.project_code:
            raise ValidationError(_("Please select a project with a valid project code first."))
        
        for line in self.invoice_line_ids:
            line.project_code = self.project_id.project_code
            
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('All invoice lines updated with project code: %s') % self.project_id.project_code,
                'type': 'success',
                'sticky': False,
            }
        }
    
    @api.model
    def create(self, vals):
        """Override create to handle auto-filling project codes when invoice is created"""
        move = super(AccountMove, self).create(vals)
    
        for rec in move:
            # Check if this is created from a sale order with a project
            if rec.move_type == 'out_invoice' and rec.invoice_origin:
                # Try to find related sale order
                sale_orders = self.env['sale.order'].search([('name', '=', rec.invoice_origin)])
                if sale_orders and sale_orders[0].project_id:
                    project_code = sale_orders[0].project_id.project_code
                    if project_code:
                        # Set the invoice project
                        rec.project_id = sale_orders[0].project_id.id
                        # Update all lines without project code
                        for line in rec.invoice_line_ids.filtered(lambda l: not l.project_code):
                            line.project_code = project_code
        
        return move
    
    @api.depends('company_id', 'invoice_filter_type_domain')
    def _compute_suitable_journal_ids(self):
        for m in self:
            journal_type = m.invoice_filter_type_domain or 'general'
            company = m.company_id or self.env.company
            m.suitable_journal_ids = self.env['account.journal'].search([
                *self.env['account.journal']._check_company_domain(company),
                # ('type', '=', journal_type),
            ])

    def _get_partner_shipping_id(self):
        partner_shipping_id = False
        if self.is_invoice(include_receipts=True):
            addr = self.partner_id.address_get(['delivery'])
            partner_shipping_id = addr and addr.get('delivery')
            if partner_shipping_id:
                partner_shipping_id = self.env['res.partner'].browse(partner_shipping_id)
            else:
                partner_shipping_id = False
        else:
            partner_shipping_id = False
        return partner_shipping_id



class AccountMoveSend(models.AbstractModel):
    _inherit = 'account.move.send'

    @api.model
    def _get_default_pdf_report_id(self, move):
        return self.env.ref('techcarrot_invoice.action_generate_techcarrot_invoice_report')

    @api.model
    def _get_default_mail_attachments_widget(self, move, mail_template, extra_edis=None, pdf_report=None):
        # \
        # + self._get_placeholder_mail_template_dynamic_attachments_data(move, mail_template, pdf_report=pdf_report) \
        # + self._get_invoice_extra_attachments_data(move) \
        # + self._get_mail_template_attachments_data(mail_template)
        return self._get_placeholder_mail_attachments_data(move, extra_edis=extra_edis)


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @api.model
    def _project_code_get(self):
        # Using phonenumbers library to get all country calling codes
        company = self.env.company
        project_codes = []
        project_ids = self.env['project.project'].search(['|', ('company_id', '=', company.id),
                                                            ('company_id', '=', False)])
        for project_id in project_ids:
            if project_id.project_code:
                str_project_code = (f"{project_id.project_code}", f"{project_id.project_code}")
                if str_project_code not in project_codes:
                    project_codes.append(str_project_code)
        return project_codes

    project_code = fields.Selection(selection=_project_code_get, string='Project Code', copy=False)
    employee_id = fields.Many2one('hr.employee', string="Employee")
    emp_code = fields.Char('Employee Code', copy=False)
    project_id = fields.Many2one('project.project', string='Project', compute='_compute_project_id', store=False, readonly=True)
    
    @api.depends('project_code')
    def _compute_project_id(self):
        """Compute the related project based on project code"""
        for line in self:
            if line.project_code:
                project = self.env['project.project'].search([('project_code', '=', line.project_code)], limit=1)
                line.project_id = project.id if project else False
            else:
                line.project_id = False

    # @api.model
    # def default_get(self, fields_list):
    #     defaults = super().default_get(fields_list)
    #     return defaults

    @api.model_create_multi
    def create(self, vals):
        for val in vals:
            if 'emp_code' in val and not val.get('product_id') and val['emp_code'] != False:
                emp_code = val['emp_code']

                # query = """
                #             SELECT p.id from product_template p,hr_employee e where e.emp_code =%s and p.employee_id=e.id;
                #         """
                #
                # self.env.cr.execute(query, (emp_code))
                # emp_product = self.env.cr.fetchall()

                employee = self.env['hr.employee'].sudo().search([('emp_code', '=', str(emp_code))], limit=1)
                if employee:
                    emp_product = self.env['product.product'].sudo().search([('employee_id', '=', employee.id)], limit=1)
                    if emp_product:
                        val['product_id'] = emp_product.id
                #     else:
                #         raise ValidationError(_('Employee master not found. Employee ID: %s', emp_code))
                # else:
                #     raise ValidationError(_('Employee master not found. Employee ID: %s', emp_code))

        res = super(AccountMoveLine, self).create(vals)

        # Set project code automatically from linked sale order
        for line in res:
            if line.sale_line_ids and not line.project_code:
                sale_line = line.sale_line_ids[0]
                if sale_line.order_id.project_id and sale_line.order_id.project_id.project_code:
                    line.project_code = sale_line.order_id.project_id.project_code

        return res


    # //////////////////////////////////////////////

    # domain_project_ids = fields.Many2many('project.project', compute='_compute_project_ids')

    # @api.depends('account_id')
    # def _compute_project_ids(self):
    #     for rec in self:
    #         domain = [('stage_id.name', 'not in', ['To Do', 'Cancelled'])]
    #         domain_project_ids = self.env['project.project'].search(domain)
    #         rec.domain_project_ids = domain_project_ids.ids

    def _check_qty_whole_fraction(self):
        qty = self.quantity
        frac_qty = str(self.quantity).split('.')[1]
        frac_qty = int(frac_qty)
        if frac_qty == 0:
            qty = "{:,.2f}".format(self.quantity)
        else:
            digits = f"{self.quantity:.6f}"
            if '.' in digits:
                qty = digits.rstrip('0').rstrip('.')
        return qty
        
    @api.onchange('sale_line_ids', 'move_id')
    def _onchange_sale_line_ids(self):
        """Update project code when sale lines change or when invoice is created from a sale order"""
        for line in self:
            if line.sale_line_ids and not line.project_code:
                sale_line = line.sale_line_ids[0]
                if sale_line.order_id.project_id and sale_line.order_id.project_id.project_code:
                    line.project_code = sale_line.order_id.project_id.project_code


    def inv_action_replace_product_desc(self):
        print('rrrrrrrrrrrrrrrrrrrrrrr')
        return {
            'name': _('Enter Product Desc'),
            'type': 'ir.actions.act_window',
            'res_model': 'inv.edit.product.desc',
            'view_mode': 'form',
            # 'context': {'default_demand_quantity': self.product_uom_qty},
            'target': 'new',
        }

