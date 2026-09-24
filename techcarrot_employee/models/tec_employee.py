# -*- coding: utf-8 -*-

from odoo import api, models, _, fields
from odoo.exceptions import ValidationError
from datetime import datetime
import re
import phonenumbers

# employee_type field removed from this model added to hr.version (sriman)
class HrEmployeeInherit(models.Model):
    _inherit = 'hr.employee'

    hr_manager_id = fields.Many2one(
        comodel_name='hr.employee',
        string='Assigned HR Manager',
        help='The HR person responsible for reviewing this employee profile change requests.',
        tracking=True,
    )

    mother_tongue_name = fields.Char(string='Mother Tongue')
    language_known_name = fields.Char(string='language known')
    spouse_passport_expiry_date = fields.Datetime(string='Spouse Passport Expiry Date')

    bank_account_no = fields.Char(string='Bank Account Number')

    # Professional Development & Supporting Documents
    resume_file = fields.Binary(string='Resume/CV', attachment=True)
    resume_file_filename = fields.Char(string='Resume/CV Filename')

    training_certificates = fields.Binary(string='Training Certificates', attachment=True)
    training_certificates_filename = fields.Char(string='Training Certificates Filename')

    awards_files = fields.Binary(string='Awards & Recognition', attachment=True)
    awards_files_filename = fields.Char(string='Awards & Recognition Filename')

    x_experience = fields.Text(
        string='Professional Experience Summary',
        help='Describe professional experience, roles, responsibilities and achievements'
    )
    x_skills = fields.Char(
        string='Technical & Professional Skills',
        help='Separate skills with commas. e.g., Python, Project Management'
    )

    # Document Management
    emirates_id_file = fields.Binary(string='Emirates ID Copy', attachment=True)
    emirates_id_filename = fields.Char(string='Emirates ID Filename')

    passport_file = fields.Binary(string='Passport Copy', attachment=True)
    passport_filename = fields.Char(string='Passport Filename')

    other_documents = fields.Binary(string='Other Documents', attachment=True)
    other_documents_filename = fields.Char(string='Other Documents Filename')

    resource_id = fields.Many2one('resource.resource', required=False)
    employee_first_name = fields.Char('Employee First Name', copy=False)
    employee_middle_name = fields.Char('Employee Middle Name', copy=False)
    employee_last_name = fields.Char('Employee Last Name', copy=False)
    employee_name_english = fields.Char('Employee Name-English', copy=False)
    employee_name_arabic = fields.Char('Employee Name-Arabic', copy=False)
    nationality_at_birth_id = fields.Many2one("res.country", string="Nationality At Birth", copy=False)
    second_relation_with_employee = fields.Char("Relationship with Employee (1)", copy=False)


    total_it_experience = fields.Char("Total IT Experience")
    alternate_mobile_number = fields.Char("Alternate Mobile Number")
    second_alternative_number = fields.Char("Second Alternative Number")
    # sriman removed the country_code because it is already present in hr_employee,if we add this field it is disturbing the UI in the employee payroll page
    # country_code = fields.Char('Country Code', copy=False)

    #Notebook Pages Field
    home_land_line_no = fields.Char('Home Land Line Number', copy=False)
    home_land_line_no_1 = fields.Char('Home Land Line Number', copy=False)
    # phone_code_of_second_person = fields.Selection(string="Countrycode", selection=_country_code_get, copy=False)
    relationship_with_emp_id = fields.Many2one('employee.relationship', string= "Relationship with Employee", copy=False)
    emergency_contact_person_name = fields.Char('Emergency Contact Person Name', copy=False)
    emergency_contact_person_name_1 = fields.Char('Emergency Contact Person Name(1)', copy=False)
    emergency_contact_person_phone = fields.Char('Emergency Contact Person Phone Number', copy=False)
    emergency_contact_person_phone_1 = fields.Char('Emergency Contact Person Phone Number(1)', copy=False)
    linkedin = fields.Char('LinkedIn', copy=False)
    industry_start_date = fields.Date('Industry Start Date', copy=False)
    experience = fields.Char('Experience', copy=False)
    religion = fields.Many2one('tec.religion', string='Religion', copy=False)
    emp_code = fields.Char('Emp Code', copy=False)
    issue_date = fields.Date('Passport Issue Date', copy=False)
    expiry_date = fields.Date('Passport Expiry Date', copy=False)
    issue_countries_id = fields.Many2one('res.country', string="Passport Issuing Country", copy=False)
    entry_exit_date = fields.Date('First Entry Date / Exit Date', copy=False)
    visa_sponsor = fields.Char('Visa Sponsor', copy=False)
    visa_issue_date = fields.Date('Visa Issue Date', copy=False)
    emirates_id_number = fields.Char('Emirates ID Number', copy=False)
    emirates_issue_date = fields.Date('Emirates ID Issue Date', copy=False)
    emirates_expiry_date = fields.Date('Emirates ID Expiry Date', copy=False)
    aadhar_no = fields.Char('Aadhar Number', copy=False)
    pan = fields.Char('PAN', copy=False)
    uan = fields.Char('UAN', copy=False)
    pf_number = fields.Char('PF Number', copy=False)
    country_residences_id = fields.Many2one('res.country', string="Country of Residence", copy=False)
    # country_code_for_personal_mob_no = fields.Integer(string='Country Code', related='country_residences_id.phone_code', copy=False)
    whatsapp = fields.Char('WhatsApp', copy=False)
    doj = fields.Date('DOJ', copy=False)
    original_hire_date = fields.Date('Original Hire Date', copy=False)
    payroll = fields.Char('Payroll', copy=False)
    mentor_names_id = fields.Many2one('hr.employee', string="Mentor Name", copy=False)
    current_role = fields.Char('Current / Additional Role', copy=False)
    # current_address = fields.Selection([
    #     ('india', 'India'),
    #     ('uae', 'UAE'),
    #     ('others', 'Others'),
    # ], string='Current Work Address', copy=False)
    current_address = fields.Char(string='Current Work Address', copy=False)
    # phone_code_1 = fields.Integer(string="ISD Code", related='private_country_id.phone_code', copy=False)
    employment_status_id = fields.Many2one('employment.status', string='Employment Status', copy=False)
    notice_period = fields.Char('Notice Period(in days)', copy=False)
    resign_date = fields.Date('Resignation Date', copy=False)
    end_date = fields.Date('End Date', copy=False)
    lwd = fields.Date('LWD', copy=False)
    house_no = fields.Text('House Number and Building Name', copy=False)
    area_name = fields.Char('Area / Town Name', copy=False)
    city = fields.Char('City', copy=False)
    countries_id = fields.Many2one('res.country', string='Country', copy=False)
    states_id = fields.Many2one('res.country.state', string='State', copy=False)
    zip_code = fields.Char('Zip Code', copy=False)
    spouse_passport_no = fields.Char('Spouse Passport No', copy=False)
    spouse_passport_issue_date = fields.Date('Spouse Passport Issue Date', copy=False)
    spouse_passport_expiry_date = fields.Date('Spouse Passport Expiry Date', copy=False)
    spouse_passport_issuing_countries_id = fields.Many2one('res.country', string='Spouse Passport Issuing Country', copy=False)
    spouse_visa_no = fields.Char('Spouse Visa No', copy=False)
    spouse_visa_expire_date = fields.Date('Spouse Visa Expiration Date', copy=False)
    spouse_emirates_id_no = fields.Char('Spouse Emirates ID Number', copy=False)
    spouse_emirates_issue_date = fields.Date('Spouse Emirates Issue Date', copy=False)
    spouse_emirates_id_expiry_date = fields.Date('Spouse Emirates ID Expiry Date', copy=False)
    spouse_aadhar_no = fields.Char('Spouse Aadhar Number', copy=False)
    dependent_child_name_1 = fields.Char('Dependent Child 1 Name', copy=False)
    dependent_child_dob_1 = fields.Date('Dependent Child 1 DOB', copy=False)
    dependent_child_gender_1 = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
        ('transgender', 'Transgender')], string='Dependent Child 1 Gender', copy=False)
    dependent_child_passport_no = fields.Char('Dependent Child 1 Passport No', copy=False)
    dependent_child_passport_issue_date_1 = fields.Date('Dependent Child 1 Passport Issue Date', copy=False)
    dependent_child_passport_expiry_date_1 = fields.Date('Dependent Child 1 Passport Expiry Date', copy=False)
    dependent_child_passport_issuing_countries_1_id = fields.Many2one('res.country', string='Dependent Child 1 Passport Issuing Country', copy=False)
    dependent_child_visa_no_1 = fields.Char('Dependent Child 1 Visa No', copy=False)
    dependent_child_visa_expiration_date_1 = fields.Date('Dependent Child 1 Visa Expiration Date', copy=False)
    dependent_child_emirates_id_no_1 = fields.Text('Dependent Child 1 Emirates ID Number', copy=False)
    dependent_child_emirates_id_issue_date_1 = fields.Date('Dependent Child 1 Emirates ID Issue Date', copy=False)
    dependent_child_emirates_id_expiry_date_1 = fields.Date('Dependent Child 1 Emirates ID Expiry Date', copy=False)
    dependent_child_aadhar_no_1 = fields.Text('Dependent Child 1 Aadhar Number', copy=False)
    father_name = fields.Char('Father Name', copy=False)
    father_nationalities_id = fields.Many2one('res.country', string='Father Nationality', copy=False)
    dependent_status = fields.Selection([
        ('active', 'Active'),
        ('inactive', 'Inactive')], string='Dependent Status', copy=False)
    father_dob = fields.Date('Father DOB', copy=False)
    mother_name = fields.Char('Mother Name', copy=False)
    dependent_status_1 = fields.Selection([
        ('active', 'Active'),
        ('inactive', 'Inactive')], string='Dependent Status_1', copy=False)
    mother_dob = fields.Date('Mother DOB', copy=False)
    mother_nationalities_id = fields.Many2one('res.country', string='Mother Nationality', copy=False)
    employee_nominee_name = fields.Char('Employee Nominee Name', copy=False)
    employee_nominee_contact_no = fields.Char('Employee Nominee Contact Number', copy=False)
    domain_worked = fields.Char('Domains Worked', copy=False)
    primary_skill = fields.Char('Primary Skills', copy=False)
    secondary_skill = fields.Char('Secondary Skills', copy=False)
    tool_used = fields.Char('Tools Used', copy=False)
    institute_name = fields.Char('Institution Name', copy=False)
    degree_name = fields.Char('Degree Name', copy=False)
    field_of_study = fields.Char('Field of Study', copy=False)
    start_date_of_degree = fields.Date('Start Date of Degree', copy=False)
    completion_date_of_degree = fields.Date('Completion Date of Degree', copy=False)
    year_of_passing = fields.Char('Year of Passing', copy=False)
    score = fields.Char('Score', copy=False)
    degree_certificate_legal = fields.Char('Degree Certificate Legalisation', copy=False)
    certification_obtained = fields.Char('Certification Obtained', copy=False)
    customer_acc_name = fields.Char('Customer / Account Name', copy=False)
    parent_id = fields.Many2one('hr.employee', string='Account Manager', copy=False)
    practice = fields.Many2one('employee.practice', copy=False)
    sub_practice = fields.Many2one('sub.practice', copy=False)
    practice_heads_id = fields.Many2one('hr.employee', string='Practice Head', copy=False)
    engagement_location = fields.Selection(
        [
            ('onsite', 'Onsite'),
            ('offshore', 'Offshore'),
            ('near-shore', 'Nearshore'),
        ],
        string='Engagement Location',
        ondelete={'onsite': 'set null', 'offshore': 'set null', 'near-shore': 'set null'}
    )


    created_by = fields.Many2one('res.users', string='Created By', readonly=True, copy=False)
    created_date_time = fields.Datetime('Created Date and Time', readonly=True, copy=False)
    last_modified_by = fields.Many2one('res.users', string='Last Modified By', readonly=True, copy=False)
    modify_date_time = fields.Datetime('Modified Date and Time', readonly=True, copy=False)
    emp_inside_uae = fields.Char('Employee Inside UAE', copy=False)
    candidate_source = fields.Char('Candidate Source', copy=False)
    blood_group = fields.Selection([
        ('a+', 'A+'),
        ('a-', 'A-'),('b+', 'B+'),('b-', 'B-'),('o+', 'O+'),('o-', 'O-'),('ab+', 'AB+'),('ab-', 'AB-')], string='Blood Group', copy=False)
    facebook_profile = fields.Char('Facebook Profile', copy=False)
    insta_profile = fields.Char('Instagram Profile', copy=False)
    twitter_profile = fields.Char('Twitter Profile', copy=False)
    no_of_career_break = fields.Char('No. of career break', copy=False)
    career_break = fields.Char('Career Break', copy=False)
    career_break_detail = fields.Char('Career Break Detail', copy=False)
    career_break_start_date = fields.Date('Career Break Start Date', copy=False)
    career_break_end_date = fields.Date('Career Break End Date', copy=False)
    names = fields.Many2many('language.master', string='Language Known', copy=False)
    # mother_tongue_id = fields.Many2one('language.master', string='Mother Tongue', copy=False)
    last_organisation_name = fields.Char('Last Organisation Name', copy=False)
    last_location = fields.Char('Last Location', copy=False)
    last_salary_per_annum_currency = fields.Char('Last Salary Per Annum Currency', copy=False)
    last_salary_per_annum_amt = fields.Float('Last Salary Per Annum Amount', copy=False)
    reason_for_leaving = fields.Char('Reason for Leaving', copy=False)
    last_report_manager_name = fields.Char('Last Reporting Manager Name', copy=False)
    last_report_manager_designation = fields.Char('Last Reporting Manager Designation', copy=False)
    last_report_manager_mail = fields.Char('Last Reporting Manager Email-ID', copy=False)
    # phone_code_2 = fields.Integer(string="Country Code for Mobile Number", related='e_private_country_id.phone_code', copy=False)
    last_report_manager_mob_no = fields.Char('Last Reporting Manager Mobile Number', copy=False)
    industry_ref_name = fields.Char('Industry Reference Name', copy=False)
    industry_ref_email = fields.Char('Industry Reference Email', copy=False)
    industry_ref_mob_no = fields.Char('Industry Reference Mobile Number', copy=False)
    previous_company_name = fields.Char('Previous Company Name', copy=False)
    designation = fields.Char('Designation', copy=False)
    period_in_company = fields.Char('Period in Company', copy=False)
    reason_of_leaving = fields.Char('Reason of Leaving', copy=False)
    exit_type_id = fields.Many2one('exit.type', string='Exit Type', copy=False)
    exit_reason_id = fields.Many2one('exit.reason', string='Exit Reason', copy=False)
    home_country_id_name = fields.Char('Home Country ID Name', copy=False)
    home_country_id_number = fields.Char('Home Country ID Number', copy=False)
    industry_ref_name_1 = fields.Char('Industry Reference Name', copy=False)
    industry_ref_email_1 = fields.Char('Industry Reference Email', copy=False)
    industry_ref_mob_no_1 = fields.Char('Industry Reference Mobile Number', copy=False)
    previous_company_name_1 = fields.Char('Previous Company Name', copy=False)
    designation_1 = fields.Char('Designation', copy=False)
    period_in_company_1 = fields.Char('Period in Company', copy=False)
    reason_of_leaving_1 = fields.Char('Reason of Leaving', copy=False)
    exit_type_id_1 = fields.Many2one('exit.type', string='Exit Type', copy=False)
    exit_reason_id_1 = fields.Many2one('exit.reason', string='Exit Reason', copy=False)
    home_country_id_name_1 = fields.Char('Home Country ID Name', copy=False)
    home_country_id_number_1 = fields.Char('Home Country ID Number', copy=False)
    is_expiry_today = fields.Boolean(compute='_compute_is_expiry_today', string="Expiry Today")
    # country_code_for_emergency_contact_person_phone_no = fields.Integer(string='Country Code', related='private_country_id.phone_code', copy=False)
    # country_code_for_work_mobile = fields.Selection(selection=_country_code_get, string='Country ISD Code', copy=False)
    # country_code_for_industry_id = fields.Many2one('res.country', string='Country Code', copy=False)
    bank_name = fields.Text('Bank Name', copy=False)
    billable = fields.Selection([
        ('yes', 'Yes'),
        ('no', 'No')], string='Billable', copy=False)
    billing_amt = fields.Char('Billing Amount', copy=False)
    billing_currency_id = fields.Many2one('res.currency', string='Billing Currency', copy=False)
    emp_category_id = fields.Many2one('employee.category', string='Employee Category', copy=False)


    # Emergency contact person address fields
    e_private_street = fields.Char(string="Private Street", copy=False)
    e_private_street2 = fields.Char(string="Private Street2", copy=False)
    e_private_city = fields.Char(string="Private City", copy=False)
    e_private_state_id = fields.Many2one(
        "res.country.state", string="Private State",
        domain="[('country_id', '=', e_private_country_id)]", copy=False)
    e_private_zip = fields.Char(string="Private Zip", copy=False)
    e_private_country_id = fields.Many2one("res.country", string="Private Country", copy=False)
    # phone_code = fields.Integer(string="Countrycode", related='u_private_country_id.phone_code', copy=False)

    #Bank Details
    branch_name = fields.Char('Branch Name / Branch Code', copy=False)
    bank_city = fields.Char('Bank City', copy=False)
    iban_no = fields.Char('IBAN Number', copy=False)
    ifsc_code = fields.Char('Bank SWIFT / IFSC Code', copy=False)

    # Full address inside UAE
    u_private_street = fields.Char(string="Private Street", copy=False)
    u_private_street2 = fields.Char(string="Private Street2", copy=False)
    u_private_city = fields.Char(string="Private City", copy=False)
    u_private_state_id = fields.Many2one(
        "res.country.state", string="Private State",
        domain="[('country_id', '=', u_private_country_id)]", copy=False)
    u_private_zip = fields.Char(string="Private Zip", copy=False)
    u_private_country_id = fields.Many2one("res.country", string="Private Country", copy=False)

    # _sql_constraints = [('unique_emp_code', 'unique (emp_code)', 'Employee Code must be unique.')]
    # code change by sriman
    #_emp_code_unique = models.Constraint(
    #    'unique (emp_code)',
    #    'Employee code must be unique!'
    #)





    # @api.constrains('issue_date')
    # def _onchange_date(self):
    #     if self.issue_date:
    #         if self.issue_date > fields.Date.today():
    #             raise ValidationError(_("The Date Should Not be a Future Date"))
    #
    # @api.constrains('emirates_issue_date')
    # def _onchange_emirates_issue_date(self):
    #     if self.emirates_issue_date:
    #         if self.emirates_issue_date > fields.Date.today():
    #             raise ValidationError(_("The Date Should Not be a Future Date"))
    #
    # @api.constrains('spouse_passport_issue_date')
    # def _onchange_spouse_passport_issue_date(self):
    #     if self.spouse_passport_issue_date:
    #         if self.spouse_passport_issue_date > fields.Date.today():
    #             raise ValidationError(_("The Date Should Not be a Future Date"))

    @api.constrains('spouse_emirates_issue_date')
    def _onchange_spouse_emirates_issue_date(self):
        if self.spouse_emirates_issue_date:
            if self.spouse_emirates_issue_date > fields.Date.today():
                raise ValidationError(_("The Date Should Not be a Future Date"))

    @api.onchange('dependent_child_passport_issue_date_1')
    def _onchange_dependent_child_passport_issue_date(self):
        if self.dependent_child_passport_issue_date_1:
            if self.dependent_child_passport_issue_date_1 > fields.Date.today():
                raise ValidationError(_("The Date Should Not be a Future Date"))

    @api.onchange('dependent_child_emirates_id_issue_date_1')
    def _onchange_dependent_child_emirates_id_issue_date(self):
        if self.dependent_child_emirates_id_issue_date_1:
            if self.dependent_child_emirates_id_issue_date_1 > fields.Date.today():
                raise ValidationError(_("The Date Should Not be a Future Date"))

    @api.constrains('issue_date', 'expiry_date')
    def _check_expiry_date(self):
        for record in self:
            if record.issue_date and record.expiry_date:
                if record.expiry_date <= record.issue_date:
                    raise ValidationError("The expiry date should be greater than the issue date.")

    @api.constrains('emirates_issue_date', 'emirates_expiry_date')
    def _check_emirates_dates(self):
        for record in self:
            if record.emirates_issue_date and record.emirates_expiry_date:
                # Check if expiry date is greater than issue date
                if record.emirates_expiry_date <= record.emirates_issue_date:
                    raise ValidationError("The Emirates expiry date should be greater than the Emirates issue date.")

    @api.constrains('spouse_emirates_issue_date', 'spouse_emirates_id_expiry_date')
    def _check_spouse_emirates_dates(self):
        for record in self:
            # Ensure both issue date and expiry date are provided
            if record.spouse_emirates_issue_date and record.spouse_emirates_id_expiry_date:
                if record.spouse_emirates_id_expiry_date <= record.spouse_emirates_issue_date:
                    raise ValidationError(
                        "The spouse's Emirates ID expiry date should be greater than the Emirates ID issue date.")

    @api.constrains('spouse_passport_issue_date', 'spouse_passport_expiry_date')
    def _check_spouse_passport_dates(self):
        for record in self:
            # Ensure both issue date and expiry date are provided
            if record.spouse_passport_issue_date and record.spouse_passport_expiry_date:
                if record.spouse_passport_expiry_date <= record.spouse_passport_issue_date:
                    raise ValidationError(
                        "The spouse's passport expiry date should be greater than the passport issue date.")

    @api.constrains('dependent_child_passport_expiry_date_1', 'dependent_child_passport_issue_date_1')
    def _check_passport_dates(self):
        for record in self:
            # Check if the expiry date is not greater than the issue date
            if record.dependent_child_passport_expiry_date_1 and record.dependent_child_passport_issue_date_1:
                if record.dependent_child_passport_expiry_date_1 <= record.dependent_child_passport_issue_date_1:
                    raise ValidationError(
                        "The dependent child's passport expiry date should be greater than the passport issue date.")

    @api.constrains('last_report_manager_mail')
    def _check_email_validity(self):
        for record in self:
            if record.last_report_manager_mail:
                pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
                if not re.match(pattern, record.last_report_manager_mail):
                    raise ValidationError(
                        "Invalid email format for %s. Please ensure it follows the correct structure." % record.last_report_manager_mail)

    @api.depends('expiry_date', 'emirates_expiry_date', 'spouse_passport_expiry_date',
                 'spouse_visa_expire_date', 'spouse_emirates_id_expiry_date',
                 'dependent_child_passport_expiry_date_1', 'dependent_child_visa_expiration_date_1',
                 'dependent_child_emirates_id_expiry_date_1')
    def _compute_is_expiry_today(self):
        today = fields.Date.today()
        for record in self:
            record.is_expiry_today = (
                    record.expiry_date == today or
                    record.emirates_expiry_date == today or
                    record.spouse_passport_expiry_date == today or
                    record.spouse_visa_expire_date == today or
                    record.spouse_emirates_id_expiry_date == today or
                    record.dependent_child_passport_expiry_date_1 == today or
                    record.dependent_child_visa_expiration_date_1 == today or
                    record.dependent_child_emirates_id_expiry_date_1 == today
            )


    @api.model_create_multi
    def create(self, vals):
        for val in vals:
            print('tttttttttttttttt',val)
            val['created_by'] = self.env.uid
            val['created_date_time'] = fields.Datetime.now()
        return super(HrEmployeeInherit, self).create(vals)

    def write(self, vals):
        vals['last_modified_by'] = self.env.uid
        vals['modify_date_time'] = fields.Datetime.now()
        return super(HrEmployeeInherit, self).write(vals)

    #For billing validation
    @api.constrains('billable', 'billing_amt', 'billing_currency_id')
    def _check_billing_fields(self):
        for record in self:
            # Check if billable is 'yes' and if the necessary fields are filled
            if record.billable == 'yes':
                if not record.billing_amt:
                    raise ValidationError("Billing Amount is required when Billable is 'Yes'.")
                if not record.billing_currency_id:
                    raise ValidationError("Billing Currency is required when Billable is 'Yes'.")
            elif record.billable == 'no':
                pass

    @api.model
    def _country_code_get(self):
        # Using phonenumbers library to get all country calling codes
        country_calling_codes = []

        # Loop over all countries provided by phonenumbers
        for region_code in phonenumbers.SUPPORTED_REGIONS:
            try:
                # Get the country calling code for each region
                country_code = phonenumbers.country_code_for_region(region_code)
                if country_code:
                    str_country_code = (f"+{country_code}", f"+{country_code}")
                    if str_country_code not in country_calling_codes:
                        country_calling_codes.append(str_country_code)
            except Exception as e:
                # In case of any issues, just skip that region
                continue

        return country_calling_codes

    # Define the country_code_for_work_mobile field
    country_code_for_work_mobile = fields.Selection(
        selection=_country_code_get,
        string='Country ISD Code',
        copy=False,
    )
    country_code_for_personal_mob_no = fields.Selection(string='Country Code', selection=_country_code_get, copy=False)
    phone_code_2 = fields.Selection(string="Country Code for Mobile Number", selection=_country_code_get, copy=False)
    country_code_for_emergency_contact_person_phone_no = fields.Selection(string='Country Code', selection=_country_code_get, copy=False)
    country_code_for_industry = fields.Selection(string='Country Code', selection=_country_code_get, copy=False)
    phone_code = fields.Selection(string="Countrycode", selection=_country_code_get, copy=False)
    phone_code_1 = fields.Selection(string="ISD Code", selection=_country_code_get, copy=False)




class HrVersionInherit(models.Model):
    _inherit = 'hr.version'

    employee_type = fields.Selection(
        selection_add=[('bootcamp', 'Bootcamp'), ('permanent', 'Permanent'), ('temporary', 'Temporary'),
                       ('seconded', 'Seconded')],
        ondelete={'bootcamp': 'cascade', 'permanent': 'cascade', 'temporary': 'cascade', 'seconded': 'cascade'})



# models/hr_employee_skill.py
from odoo import fields, models

class HrEmployeeSkill(models.Model):
    _inherit = 'hr.employee.skill'

    certificate_attachment_ids = fields.Many2many(
        comodel_name='ir.attachment',
        relation='hr_employee_skill_attachment_rel',
        column1='skill_id',
        column2='attachment_id',
        string='Attachments',
        copy=False,
    )
