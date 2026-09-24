# -*- coding: utf-8 -*-
import json
import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

FIELD_LABELS = {
    'work_phone': 'Work Phone', 'private_email': 'Personal Email',
    'private_phone': 'Personal Phone', 'private_street': 'Address Line 1',
    'private_street2': 'Address Line 2', 'private_city': 'City (Private)',
    'private_zip': 'ZIP Code',
    'private_state_id': 'Permanent Address State',
    'private_country_id': 'Permanent Address Country',
    'whatsapp': 'WhatsApp', 'linkedin': 'LinkedIn',
    'legal_name': 'Legal Name', 'facebook_profile': 'Facebook Profile',
    'insta_profile': 'Instagram Profile', 'twitter_profile': 'Twitter Profile',
    'blood_group': 'Blood Group', 'lang': 'Payslip Language',
    'issue_date': 'Passport Issue Date', 'expiry_date': 'Passport Expiry Date',
    'emirates_id_number': 'Emirates ID', 'emirates_expiry_date': 'Emirates ID Expiry',
    'passport_id': 'Passport Number', 'identification_id': 'Identification No',
    'ssnid': 'SSN No', 'visa_no': 'Visa No', 'permit_no': 'Work Permit No',
    'nationality_at_birth_id': 'Nationality At Birth',
    'country_id': 'Nationality',
    'issue_countries_id': 'Passport Issuing Country',
    'countries_id': 'Country',
    'father_nationalities_id': 'Father Nationality',
    'mother_nationalities_id': 'Mother Nationality',
    'l10n_in_relationship': 'Emergency Relationship',
    'emergency_phone': 'Emergency Phone', 'e_private_city': 'Emergency Address',
    'emergency_contact_person_name': 'Emergency Contact Name',
    'emergency_contact_person_phone': 'Emergency Contact Phone',
    'alternate_mobile_number': 'Alternate Mobile',
    'emergency_contact_person_name_1': 'Emergency Contact Name (2)',
    'emergency_contact_person_phone_1': 'Emergency Contact Phone (2)',
    'second_alternative_number': 'Second Alternative Number',
    'home_land_line_no': 'Home Land Line',
    'relationship_with_emp_id': 'Relationship with Employee',
    'spouse_passport_no': 'Spouse Passport No',
    'spouse_passport_issue_date': 'Spouse Passport Issue Date',
    'spouse_passport_expiry_date': 'Spouse Passport Expiry Date',
    'spouse_visa_no': 'Spouse Visa No',
    'spouse_visa_expire_date': 'Spouse Visa Expiry Date',
    'spouse_emirates_id_no': 'Spouse Emirates ID No',
    'spouse_emirates_issue_date': 'Spouse Emirates Issue Date',
    'spouse_emirates_id_expiry_date': 'Spouse Emirates ID Expiry Date',
    'spouse_aadhar_no': 'Spouse Aadhar No',
    'dependent_child_name_1': 'Child 1 Name', 'dependent_child_dob_1': 'Child 1 DOB',
    'dependent_child_passport_no': 'Child 1 Passport No',
    'dependent_child_passport_issue_date_1': 'Child 1 Passport Issue Date',
    'dependent_child_passport_expiry_date_1': 'Child 1 Passport Expiry Date',
    'dependent_child_visa_no_1': 'Child 1 Visa No',
    'dependent_child_visa_expiration_date_1': 'Child 1 Visa Expiry Date',
    'dependent_child_emirates_id_no_1': 'Child 1 Emirates ID No',
    'dependent_child_emirates_id_issue_date_1': 'Child 1 Emirates Issue Date',
    'dependent_child_emirates_id_expiry_date_1': 'Child 1 Emirates Expiry Date',
    'dependent_child_aadhar_no_1': 'Child 1 Aadhar No',
    'dependent_child_passport_issuing_countries_1_id': 'Child 1 Passport Issuing Country',
    'father_name': 'Father Name', 'father_dob': 'Father DOB',
    'mother_name': 'Mother Name', 'mother_dob': 'Mother DOB',
    'children': 'No. of Children', 'career_break_detail': 'Career Break Detail',
    'marital': 'Marital Status',
    'employee_nominee_name': 'Nominee Name',
    'employee_nominee_contact_no': 'Nominee Contact No',
    'domain_worked': 'Domains Worked', 'primary_skill': 'Primary Skills',
    'secondary_skill': 'Secondary Skills', 'tool_used': 'Tools Used',
    'industry_ref_name': 'Industry Reference Name',
    'industry_ref_email': 'Industry Reference Email',
    'industry_ref_mob_no': 'Industry Reference Mobile',
    'home_country_id_name': 'Home Country ID Name',
    'home_country_id_number': 'Home Country ID Number',
    'mother_tongue_name': 'Mother Tongue', 'language_known_name': 'Languages Known',
    'u_private_city': 'Address Inside UAE', 'current_address': 'Current Work Address',
    'phone_code_1': 'Country Code (ISD)', 'house_no': 'House No / Building',
    'area_name': 'Area / Town', 'city': 'City (Work)', 'zip_code': 'Zip Code',
    'experience': 'Experience', 'current_role': 'Current / Additional Role',
    'industry_start_date': 'Industry Start Date',
    'last_organisation_name': 'Last Organisation Name',
    'last_location': 'Last Location',
    'last_salary_per_annum_currency': 'Last Salary Currency',
    'last_salary_per_annum_amt': 'Last Salary Amount',
    'reason_for_leaving': 'Reason for Leaving',
    'last_report_manager_name': 'Reporting Manager Name',
    'last_report_manager_designation': 'Reporting Manager Designation',
    'last_report_manager_mob_no': 'Reporting Manager Mobile',
    'last_report_manager_mail': 'Reporting Manager Email',
    'previous_company_name': 'Previous Company Name',
    'designation': 'Designation', 'period_in_company': 'Period in Company',
    'reason_of_leaving': 'Reason of Leaving',
    'emirates_id_file': 'Emirates ID Copy',
    'passport_file': 'Passport Copy',
    'other_documents': 'Other Documents',
    'has_work_permit': 'Work Permit File',
    'states_id': 'Work Location State',
    'country_residences_id': 'Country of Residency',
    'pan': 'PAN', 'aadhar_no': 'Aadhar Number',
    'no_of_career_break': 'No. of Career Break',
    'career_break': 'Career Break',
    'career_break_start_date': 'Career Break Start Date',
    'career_break_end_date': 'Career Break End Date',
    'institute_name': 'Institution Name', 'degree_name': 'Degree Name',
    'field_of_study': 'Field of Study', 'study_field': 'Study Field (Other)',
    'start_date_of_degree': 'Start Date of Degree',
    'completion_date_of_degree': 'Completion Date of Degree',
    'year_of_passing': 'Year of Passing', 'score': 'Score',
    'certification_obtained': 'Certification Obtained',
}

MANY2ONE_FIELDS = {
    'nationality_at_birth_id', 'country_id', 'issue_countries_id', 'countries_id',
    'father_nationalities_id', 'mother_nationalities_id', 'religion',
    'states_id', 'private_state_id', 'private_country_id',
    'country_residences_id',
    'dependent_child_passport_issuing_countries_1_id',
    'relationship_with_emp_id',
    'spouse_passport_issuing_countries_id',
}

MANY2ONE_MODEL_MAP = {
    'nationality_at_birth_id': 'res.country',
    'country_id': 'res.country',
    'issue_countries_id': 'res.country',
    'countries_id': 'res.country',
    'country_residences_id': 'res.country',
    'states_id': 'res.country.state',
    'private_state_id': 'res.country.state',
    'private_country_id': 'res.country',
    'religion': 'tec.religion',
    'father_nationalities_id': 'res.country',
    'mother_nationalities_id': 'res.country',
    'dependent_child_passport_issuing_countries_1_id': 'res.country',
    'relationship_with_emp_id': 'employee.relationship',
    'spouse_passport_issuing_countries_id': 'res.country',
}

SELECTION_FIELDS = {
    'blood_group', 'sex', 'marital', 'dependent_child_gender_1',
}

SKIP_ON_APPROVE = {
    'csrf_token', 'submit',
    'emirates_id_file', 'passport_file', 'other_documents', 'has_work_permit',
    '_cert_change',
}

CODED_VALUE_LABELS = {
    'blood_group': {
        'a+': 'A+', 'a-': 'A-', 'b+': 'B+', 'b-': 'B-',
        'ab+': 'AB+', 'ab-': 'AB-', 'o+': 'O+', 'o-': 'O-', 'unknown': 'Unknown',
    },
    'sex': {'male': 'Male', 'female': 'Female', 'other': 'Other'},
    'marital': {
        'single': 'Single', 'married': 'Married', 'cohabitant': 'Legal Cohabitant',
        'widower': 'Widower', 'divorced': 'Divorced',
    },
    'dependent_child_gender_1': {'male': 'Male', 'female': 'Female', 'other': 'Other'},
}


def _get_current_field_display(employee, key, env):
    try:
        if key in MANY2ONE_FIELDS:
            current_rec = getattr(employee, key, False)
            if current_rec and hasattr(current_rec, 'id') and current_rec.id:
                return current_rec.name or ''
            return ''
        else:
            current_raw = getattr(employee, key, None)
            if current_raw is None or current_raw is False:
                return ''
            if hasattr(current_raw, 'name'):
                return current_raw.name or ''
            s = str(current_raw).strip()
            return '' if s in ('False', 'None', '0') else s
    except Exception:
        return ''


def _resolve_submitted_m2o(env, model_name, record_id):
    try:
        rec = env[model_name].sudo().browse(int(record_id))
        if rec.exists():
            return rec.name or ''
        return ''
    except Exception:
        return ''


def _unwrap_cert_batch(raw):
    if isinstance(raw, dict):
        return raw.get('changes', [])
    if isinstance(raw, list):
        return raw
    return []


def _copy_attachment_to_skill(env, att, skill_record_id, pcr_name):
    """
    FIX: Copy attachment from hr.profile.change.request to hr.employee.skill.
    Uses att.datas directly (ORM field) instead of att.read(['datas'])
    because read() silently returns datas=False in Odoo 19 sudo context.
    """
    try:
        att_datas = att.sudo().datas
        att_name = att.sudo().name
        att_mime = att.sudo().mimetype or 'application/octet-stream'
        if att_datas:
            env['ir.attachment'].sudo().create({
                'name': att_name,
                'datas': att_datas,
                'res_model': 'hr.employee.skill',
                'res_id': skill_record_id,
                'mimetype': att_mime,
            })
            _logger.info('PCR %s: attached %s to skill id=%s', pcr_name, att_name, skill_record_id)
            return True
        else:
            _logger.warning('PCR %s: attachment %s has empty datas (id=%s)', pcr_name, att_name, att.id)
            return False
    except Exception as e:
        _logger.error('PCR %s: attachment copy failed: %s', pcr_name, e)
        return False


class HrProfileChangeRequest(models.Model):
    _name = 'hr.profile.change.request'
    _description = 'Employee Profile Change Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    _rec_name = 'name'
    _check_company_auto = False

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, default='New')
    employee_id = fields.Many2one(
        comodel_name='hr.employee', string='Employee',
        required=True, ondelete='cascade', tracking=True, check_company=False,
    )
    department_id = fields.Many2one(
        comodel_name='hr.department', related='employee_id.department_id',
        string='Department', store=True, readonly=True,
    )
    work_location_id = fields.Many2one(
        related='employee_id.work_location_id',
        string='Work Location', store=True, readonly=True,
    )
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('pending', 'Pending HR Review'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
        ],
        string='Status', default='draft', tracking=True, index=True,
    )
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    submitted_data = fields.Text(string='Submitted Data (JSON)', readonly=True)
    changed_fields_display = fields.Html(
        string='Submitted Changes', compute='_compute_changed_fields_display', sanitize=False,
    )
    submission_date = fields.Datetime(string='Submitted On', default=fields.Datetime.now, readonly=True)
    review_date = fields.Datetime(string='Reviewed On', readonly=True)
    reviewed_by = fields.Many2one(comodel_name='res.users', string='Reviewed By', readonly=True)
    rejection_reason = fields.Text(string='Rejection Reason', tracking=True)
    trail_ids = fields.One2many(
        comodel_name='hr.profile.change.request.trail',
        inverse_name='request_id', string='Audit Trail', readonly=True,
    )
    has_emirates_id_doc = fields.Boolean(string='Emirates ID Uploaded', compute='_compute_doc_flags', store=True)
    has_passport_doc = fields.Boolean(string='Passport Uploaded', compute='_compute_doc_flags', store=True)
    has_other_doc = fields.Boolean(string='Other Doc Uploaded', compute='_compute_doc_flags', store=True)
    has_work_permit_doc = fields.Boolean(string='Work Permit Uploaded', compute='_compute_doc_flags', store=True)
    has_any_doc = fields.Boolean(string='Has Any Document', compute='_compute_doc_flags', store=True)
    total_docs_uploaded = fields.Integer(string='Total Documents', compute='_compute_doc_flags', store=True)
    attachment_ids = fields.Many2many(
        'ir.attachment', string='Supporting Documents', compute='_compute_attachment_ids',
    )

    def _compute_attachment_ids(self):
        for rec in self:
            if rec.id:
                rec.attachment_ids = self.env['ir.attachment'].sudo().search([
                    ('res_model', '=', 'hr.profile.change.request'),
                    ('res_id', '=', rec.id),
                ])
            else:
                rec.attachment_ids = self.env['ir.attachment']

    @api.depends('submitted_data')
    def _compute_doc_flags(self):
        doc_field_map = {
            'emirates_id_file': 'has_emirates_id_doc',
            'passport_file': 'has_passport_doc',
            'other_documents': 'has_other_doc',
            'has_work_permit': 'has_work_permit_doc',
        }
        for rec in self:
            flags = {f: False for f in doc_field_map.values()}
            if rec.submitted_data:
                try:
                    data = json.loads(rec.submitted_data)
                    for fn, flag in doc_field_map.items():
                        val = data.get(fn, '')
                        if val and str(val).strip() not in ('', 'False', 'None', 'false'):
                            flags[flag] = True
                except Exception:
                    pass
            for flag, value in flags.items():
                setattr(rec, flag, value)
            rec.total_docs_uploaded = sum(1 for v in flags.values() if v)
            rec.has_any_doc = any(flags.values())

    def _get_hr_reviewer_users(self):
        try:
            hr_group = self.env.ref(
                'employee_profile_change_request.group_profile_change_hr_reviewer',
                raise_if_not_found=False,
            )
            if not hr_group:
                return self.env['res.users']
            self.env.cr.execute('SELECT uid FROM res_groups_users_rel WHERE gid = %s', [hr_group.id])
            user_ids = [row[0] for row in self.env.cr.fetchall()]
            return self.env['res.users'].sudo().browse(user_ids) if user_ids else self.env['res.users']
        except Exception as e:
            _logger.error('_get_hr_reviewer_users error: %s', e)
            return self.env['res.users']

    def _is_hr_reviewer(self):
        try:
            hr_group = self.env.ref(
                'employee_profile_change_request.group_profile_change_hr_reviewer',
                raise_if_not_found=False,
            )
            if not hr_group:
                return False
            self.env.cr.execute(
                'SELECT 1 FROM res_groups_users_rel WHERE gid = %s AND uid = %s',
                [hr_group.id, self.env.uid])
            return bool(self.env.cr.fetchone())
        except Exception:
            return False

    @api.model
    def search(self, domain, offset=0, limit=None, order=None):
        if self._is_hr_reviewer() and not self.env.su:
            return super(HrProfileChangeRequest, self.sudo()).search(
                domain, offset=offset, limit=limit, order=order)
        return super().search(domain, offset=offset, limit=limit, order=order)

    @api.model
    def search_count(self, domain, limit=None):
        if self._is_hr_reviewer() and not self.env.su:
            return super(HrProfileChangeRequest, self.sudo()).search_count(domain, limit=limit)
        return super().search_count(domain, limit=limit)

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None, **kwargs):
        if self._is_hr_reviewer() and not self.env.su:
            return super(HrProfileChangeRequest, self.sudo())._search(
                domain, offset=offset, limit=limit, order=order, **kwargs)
        return super()._search(domain, offset=offset, limit=limit, order=order, **kwargs)

    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        if self._is_hr_reviewer() and not self.env.su:
            return super(HrProfileChangeRequest, self.sudo()).read_group(
                domain, fields, groupby,
                offset=offset, limit=limit, orderby=orderby, lazy=lazy)
        return super().read_group(
            domain, fields, groupby,
            offset=offset, limit=limit, orderby=orderby, lazy=lazy)

    def write(self, vals):
        result = super().write(vals)
        if 'state' in vals:
            new_state = vals['state']
            for rec in self:
                try:
                    data = json.loads(rec.submitted_data or '{}')
                    is_personal = (
                        '_cert_change' not in data and
                        '_cert_batch' not in data and
                        '_skill_change' not in data and
                        '_resume_change' not in data
                    )
                    if not is_personal:
                        continue
                    if new_state == 'pending':
                        rec.employee_id.sudo().write({'last_submission_state': 'pending'})
                    elif new_state == 'approved':
                        rec.employee_id.sudo().write({
                            'last_submission_state': 'approved',
                            'last_portal_submission': False,
                        })
                        rec.employee_id.sudo().invalidate_recordset()
                    elif new_state == 'rejected':
                        rec.employee_id.sudo().write({'last_submission_state': 'rejected'})
                except Exception as e:
                    _logger.warning('PCR write sync error: %s', e)
        return result

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            name_val = vals.get('name', '')
            if not name_val or not name_val.startswith('PCR/'):
                seq = self.env['ir.sequence'].sudo().next_by_code('hr.profile.change.request')
                if not seq:
                    _logger.warning('PCR sequence missing — auto-creating now')
                    try:
                        self.env['ir.sequence'].sudo().create({
                            'name': 'Profile Change Request',
                            'code': 'hr.profile.change.request',
                            'prefix': 'PCR/%(year)s/',
                            'padding': 4,
                            'company_id': False,
                        })
                        self.env.cr.commit()
                        seq = self.env['ir.sequence'].sudo().next_by_code('hr.profile.change.request')
                    except Exception as e:
                        _logger.error('Failed to auto-create PCR sequence: %s', e)
                if seq:
                    vals['name'] = seq
                else:
                    import datetime
                    vals['name'] = 'PCR/%s/TEMP' % datetime.datetime.now().strftime('%Y/%m%d%H%M%S')
                    _logger.error('PCR sequence still not available — used temp name')
        return super().create(vals_list)

    @api.depends('submitted_data', 'employee_id')
    def _compute_changed_fields_display(self):
        for rec in self:
            if not rec.submitted_data:
                rec.changed_fields_display = '<p class="text-muted">No data submitted yet.</p>'
                continue
            try:
                data = json.loads(rec.submitted_data)

                cert_batch_raw = data.get('_cert_batch')
                cert_batch = _unwrap_cert_batch(cert_batch_raw)
                if cert_batch:
                    action_labels = {'add': 'Add', 'edit': 'Edit', 'delete': 'Delete'}
                    rows = ''
                    for item in cert_batch:
                        if not isinstance(item, dict):
                            continue
                        action = item.get('cert_action', '') or item.get('type', '')
                        rows += (
                            f'<tr style="background:#fffde7;">'
                            f'<td style="padding:8px 12px;border:1px solid #ddd;">'
                            f'<span style="background:#4e73df;color:white;padding:2px 8px;border-radius:4px;font-size:11px;">'
                            f'{action_labels.get(action, action)}</span></td>'
                            f'<td style="padding:8px 12px;border:1px solid #ddd;font-weight:600;">'
                            f'{item.get("skill_name", "—")}</td>'
                            f'<td style="padding:8px 12px;border:1px solid #ddd;">'
                            f'{item.get("valid_from") or "Indefinite"}</td>'
                            f'<td style="padding:8px 12px;border:1px solid #ddd;">'
                            f'{item.get("valid_to") or "Indefinite"}</td>'
                            f'<td style="padding:8px 12px;border:1px solid #ddd;">'
                            f'{"✅ Attached" if item.get("attachment_name") else "—"}</td>'
                            f'</tr>'
                        )
                    rec.changed_fields_display = f'''
                        <div style="overflow-x:auto;">
                          <p style="font-weight:600;color:#2e7d32;margin-bottom:8px;">
                            <i class="fa fa-certificate me-1"></i>{len(cert_batch)} Certification Change(s)
                          </p>
                          <table style="width:100%;border-collapse:collapse;font-size:13px;">
                            <thead><tr style="background:#4e73df;color:white;">
                              <th style="padding:10px 12px;border:1px solid #3a5ec9;">Action</th>
                              <th style="padding:10px 12px;border:1px solid #3a5ec9;">Certificate</th>
                              <th style="padding:10px 12px;border:1px solid #3a5ec9;">Valid From</th>
                              <th style="padding:10px 12px;border:1px solid #3a5ec9;">Valid To</th>
                              <th style="padding:10px 12px;border:1px solid #3a5ec9;">Attachment</th>
                            </tr></thead>
                            <tbody>{rows}</tbody>
                          </table>
                        </div>
                        <p style="font-size:11px;color:#999;margin-top:8px;">
                          ⚠ These changes will only be applied after you click Approve.
                        </p>'''
                    continue

                cert_change = data.get('_cert_change')
                if cert_change:
                    action_labels = {
                        'add': 'Add Certification',
                        'edit': 'Edit Certification',
                        'delete': 'Delete Certification',
                    }
                    action = cert_change.get('cert_action', '')
                    skill_name = cert_change.get('skill_name', '—')
                    valid_from = cert_change.get('valid_from') or 'Indefinite'
                    valid_to = cert_change.get('valid_to') or 'Indefinite'
                    has_att = bool(cert_change.get('has_attachment')) or bool(cert_change.get('attachment_name'))
                    rec.changed_fields_display = (
                        '<div style="overflow-x:auto;">'
                        '<table style="width:100%;border-collapse:collapse;font-size:13px;font-family:Arial,sans-serif;">'
                        '<thead><tr style="background:#4e73df;color:white;">'
                        '<th style="padding:10px 12px;border:1px solid #3a5ec9;">Field</th>'
                        '<th style="padding:10px 12px;border:1px solid #3a5ec9;">Value</th>'
                        '</tr></thead><tbody>'
                        f'<tr style="background:#fffde7;">'
                        f'<td style="padding:8px 12px;border:1px solid #ddd;"><strong>Action</strong></td>'
                        f'<td style="padding:8px 12px;border:1px solid #ddd;color:#2e7d32;font-weight:600;">{action_labels.get(action, action)}</td>'
                        f'</tr>'
                        f'<tr><td style="padding:8px 12px;border:1px solid #ddd;"><strong>Certificate</strong></td>'
                        f'<td style="padding:8px 12px;border:1px solid #ddd;">{skill_name}</td></tr>'
                        f'<tr><td style="padding:8px 12px;border:1px solid #ddd;"><strong>Valid From</strong></td>'
                        f'<td style="padding:8px 12px;border:1px solid #ddd;">{valid_from}</td></tr>'
                        f'<tr><td style="padding:8px 12px;border:1px solid #ddd;"><strong>Valid To</strong></td>'
                        f'<td style="padding:8px 12px;border:1px solid #ddd;">{valid_to}</td></tr>'
                        f'<tr><td style="padding:8px 12px;border:1px solid #ddd;"><strong>Attachment</strong></td>'
                        f'<td style="padding:8px 12px;border:1px solid #ddd;">{"✅ File attached" if has_att else "—"}</td></tr>'
                        '</tbody></table></div>'
                        '<p style="font-size:11px;color:#999;margin-top:8px;">⚠ This certification change will only be applied after you click Approve.</p>'
                    )
                    continue

                skill_change = data.get('_skill_change')
                if skill_change and skill_change.get('cert_action') == 'add_batch':
                    skills = skill_change.get('skills', [])
                    rows = ''.join(
                        f'<tr>'
                        f'<td style="padding:8px 12px;border:1px solid #ddd;">{i.get("type_name", "—")}</td>'
                        f'<td style="padding:8px 12px;border:1px solid #ddd;font-weight:600;">{i.get("skill_name", "—")}</td>'
                        f'<td style="padding:8px 12px;border:1px solid #ddd;">'
                        f'<span class="badge bg-primary">{i.get("level_name", "—")}</span></td>'
                        f'</tr>'
                        for i in skills
                    )
                    rec.changed_fields_display = (
                        f'<div style="overflow-x:auto;">'
                        f'<p style="font-weight:600;color:#2e7d32;margin-bottom:8px;">Add {len(skills)} Skill(s)</p>'
                        '<table style="width:100%;border-collapse:collapse;font-size:13px;font-family:Arial,sans-serif;">'
                        '<thead><tr style="background:#4e73df;color:white;">'
                        '<th style="padding:10px 12px;border:1px solid #3a5ec9;">Skill Type</th>'
                        '<th style="padding:10px 12px;border:1px solid #3a5ec9;">Skill</th>'
                        '<th style="padding:10px 12px;border:1px solid #3a5ec9;">Level</th>'
                        f'</tr></thead><tbody>{rows}</tbody></table></div>'
                    )
                    continue

                resume_change = data.get('_resume_change')
                if resume_change:
                    rec.changed_fields_display = (
                        '<div style="overflow-x:auto;">'
                        '<table style="width:100%;border-collapse:collapse;font-size:13px;font-family:Arial,sans-serif;">'
                        '<thead><tr style="background:#4e73df;color:white;">'
                        '<th style="padding:10px 12px;border:1px solid #3a5ec9;">Field</th>'
                        '<th style="padding:10px 12px;border:1px solid #3a5ec9;">Value</th>'
                        '</tr></thead><tbody>'
                        '<tr style="background:#fffde7;">'
                        '<td style="padding:8px 12px;border:1px solid #ddd;"><strong>Action</strong></td>'
                        '<td style="padding:8px 12px;border:1px solid #ddd;color:#2e7d32;font-weight:600;">Upload Resume / CV</td>'
                        '</tr>'
                        f'<tr><td style="padding:8px 12px;border:1px solid #ddd;"><strong>File Name</strong></td>'
                        f'<td style="padding:8px 12px;border:1px solid #ddd;">{resume_change.get("filename", "—")}</td></tr>'
                        '</tbody></table></div>'
                    )
                    continue

                rows = ''
                row_count = 0

                for key, new_val in data.items():
                    if key.startswith('_'):
                        continue
                    label = FIELD_LABELS.get(key, key.replace('_', ' ').title())

                    if new_val and str(new_val).startswith('[FILE:'):
                        fname = str(new_val).replace('[FILE:', '').rstrip(']')
                        previous_html = '<span style="color:#aaa;font-style:italic;">No previous file</span>'
                        new_html = f'<span style="color:#198754;font-weight:600;"><i class="fa fa-file-o me-1"></i> {fname}</span>'
                    elif key in MANY2ONE_FIELDS:
                        model_name = MANY2ONE_MODEL_MAP.get(key, 'res.country')
                        previous_display = _get_current_field_display(rec.employee_id, key, rec.env)
                        new_display = _resolve_submitted_m2o(rec.env, model_name, new_val)
                        if not new_display:
                            continue
                        previous_html = (
                            f'<span style="color:#6c757d;">{previous_display}</span>'
                            if previous_display
                            else '<span style="color:#aaa;font-style:italic;">—</span>'
                        )
                        new_html = f'<span style="color:#198754;font-weight:600;">{new_display}</span>'
                    elif key in SELECTION_FIELDS:
                        coded_map = CODED_VALUE_LABELS.get(key, {})
                        previous_raw = _get_current_field_display(rec.employee_id, key, rec.env)
                        previous_display = coded_map.get(previous_raw, previous_raw) if previous_raw else ''
                        nv = str(new_val).strip() if new_val else ''
                        new_display = coded_map.get(nv, nv) if nv else ''
                        if not new_display:
                            continue
                        previous_html = (
                            f'<span style="color:#6c757d;">{previous_display}</span>'
                            if previous_display
                            else '<span style="color:#aaa;font-style:italic;">—</span>'
                        )
                        new_html = f'<span style="color:#198754;font-weight:600;">{new_display}</span>'
                    else:
                        previous_display = _get_current_field_display(rec.employee_id, key, rec.env)
                        new_display = str(new_val).strip() if new_val else ''
                        if not new_display:
                            continue
                        if new_display.isdigit() and key.endswith('_id'):
                            for try_model in ('res.country', 'res.country.state', 'tec.religion', 'employee.relationship'):
                                try:
                                    resolved = rec.env[try_model].sudo().browse(int(new_display))
                                    if resolved.exists() and hasattr(resolved, 'name') and resolved.name:
                                        new_display = resolved.name
                                        break
                                except Exception:
                                    pass
                        previous_html = (
                            f'<span style="color:#6c757d;">{previous_display}</span>'
                            if previous_display
                            else '<span style="color:#aaa;font-style:italic;">—</span>'
                        )
                        new_html = f'<span style="color:#198754;font-weight:600;">{new_display}</span>'

                    rows += (
                        f'<tr style="background:#fffde7;">'
                        f'<td style="padding:9px 14px;border:1px solid #e2e8f0;font-weight:600;'
                        f'color:#374151;min-width:180px;">{label}</td>'
                        f'<td style="padding:9px 14px;border:1px solid #e2e8f0;">{previous_html}</td>'
                        f'<td style="padding:9px 14px;border:1px solid #e2e8f0;">{new_html}</td>'
                        f'<td style="padding:9px 14px;border:1px solid #e2e8f0;text-align:center;">'
                        f'<span style="background:#f59e0b;color:white;padding:2px 8px;'
                        f'border-radius:4px;font-size:11px;font-weight:600;letter-spacing:0.5px;">CHANGED</span>'
                        f'</td>'
                        f'</tr>'
                    )
                    row_count += 1

                if row_count == 0:
                    rec.changed_fields_display = (
                        '<div style="padding:20px;text-align:center;color:#6c757d;">'
                        '<i class="fa fa-info-circle me-2"></i>No field changes to display.</div>'
                    )
                    continue

                rec.changed_fields_display = (
                    '<div style="overflow-x:auto;">'
                    '<table style="width:100%;border-collapse:collapse;font-size:13px;'
                    'font-family:Arial,sans-serif;border:1px solid #e2e8f0;">'
                    '<thead>'
                    '<tr style="background:#2d3748;color:white;">'
                    '<th style="padding:11px 14px;text-align:left;border:1px solid #4a5568;'
                    'font-weight:600;font-size:12px;letter-spacing:0.5px;text-transform:uppercase;">Field</th>'
                    '<th style="padding:11px 14px;text-align:left;border:1px solid #4a5568;'
                    'font-weight:600;font-size:12px;letter-spacing:0.5px;text-transform:uppercase;">Previous Value</th>'
                    '<th style="padding:11px 14px;text-align:left;border:1px solid #4a5568;'
                    'font-weight:600;font-size:12px;letter-spacing:0.5px;text-transform:uppercase;">New Value</th>'
                    '<th style="padding:11px 14px;text-align:center;border:1px solid #4a5568;'
                    'font-weight:600;font-size:12px;letter-spacing:0.5px;text-transform:uppercase;">Status</th>'
                    '</tr>'
                    '</thead>'
                    f'<tbody>{rows}</tbody>'
                    '</table>'
                    '</div>'
                    f'<p style="font-size:11px;color:#6b7280;margin-top:8px;">'
                    f'<i class="fa fa-info-circle me-1"></i>'
                    f'{row_count} field(s) changed. '
                    f'Previous Value shows what was in the record before submission. '
                    f'Blank (—) means the field was empty before.</p>'
                )

            except Exception as e:
                _logger.error('_compute_changed_fields_display error for PCR %s: %s', rec.name, e)
                rec.changed_fields_display = (
                    f'<div class="alert alert-danger">'
                    f'<i class="fa fa-exclamation-triangle me-2"></i>'
                    f'Error rendering change summary: {e}</div>'
                )

    def action_submit(self):
        self.ensure_one()
        if not self.name or self.name == 'New' or self.name.startswith('PCR/') is False:
            seq = self.env['ir.sequence'].sudo().next_by_code('hr.profile.change.request')
            if not seq:
                try:
                    self.env['ir.sequence'].sudo().create({
                        'name': 'Profile Change Request',
                        'code': 'hr.profile.change.request',
                        'prefix': 'PCR/%(year)s/',
                        'padding': 4,
                        'company_id': False,
                    })
                    self.env.cr.commit()
                    seq = self.env['ir.sequence'].sudo().next_by_code('hr.profile.change.request')
                except Exception as e:
                    _logger.error('Sequence auto-create failed: %s', e)
            if seq:
                self.sudo().write({'name': seq})
            else:
                import datetime
                self.sudo().write({'name': 'PCR/%s/TEMP' % datetime.datetime.now().strftime('%Y/%m%d%H%M%S')})
        self.write({'state': 'pending'})
        try:
            _data = json.loads(self.submitted_data or '{}')
            _is_personal = (
                '_cert_change' not in _data and
                '_cert_batch' not in _data and
                '_skill_change' not in _data and
                '_resume_change' not in _data
            )
        except Exception:
            _is_personal = True
        if _is_personal:
            self.employee_id.sudo().write({
                'last_portal_submission': self.submitted_data,
                'last_submission_state': 'pending',
            })
        self._add_trail(action='submitted', note=f'Submitted by {self.employee_id.name}')
        self._send_mail_to_hr()
        return True

    def action_approve(self):
        self.ensure_one()
        if self.state != 'pending':
            raise UserError(_('Only pending requests can be approved.'))
        try:
            data = json.loads(self.submitted_data or '{}')
        except Exception:
            raise UserError(_('Submitted data is corrupted.'))

        cert_change = data.get('_cert_change')
        if cert_change:
            self._apply_cert_change(cert_change)
            self._finalize_approval()
            try:
                self._repair_cert_attachments_after_approve([cert_change])
            except Exception as e:
                _logger.warning('PCR %s: post-approve repair error (non-fatal): %s', self.name, e)
            return True
        cert_batch_raw = data.get('_cert_batch')
        cert_batch = _unwrap_cert_batch(cert_batch_raw)
        if cert_batch:
            all_attachments = self.env['ir.attachment'].sudo().search([
                ('res_model', '=', 'hr.profile.change.request'),
                ('res_id', '=', self.id),
            ], order='id asc')
            att_list = list(all_attachments)
            att_index = 0
            _logger.info('PCR %s cert_batch: %d items, %d attachments', self.name, len(cert_batch), len(att_list))
            for cert_item in cert_batch:
                if not isinstance(cert_item, dict):
                    _logger.warning('PCR %s: skipping non-dict cert_batch item: %r', self.name, cert_item)
                    continue
                try:
                    action_type = cert_item.get('cert_action', '') or cert_item.get('type', '')
                    has_attachment = bool(cert_item.get('attachment_name') or cert_item.get('has_attachment') or cert_item.get('has_file'))
                    _logger.info(
                        'PCR %s: processing cert_item action=%s skill=%s has_att=%s att_index=%s total_atts=%s',
                        self.name, action_type, cert_item.get('skill_name'), has_attachment, att_index, len(att_list),
                    )
                    if action_type == 'add':
                        att = None
                        if has_attachment and att_index < len(att_list):
                            att = att_list[att_index]
                            att_index += 1
                        self._apply_cert_change_with_attachment(cert_item, att)
                    else:
                        self._apply_cert_change(cert_item)
                except Exception as e:
                    _logger.error('PCR %s: cert_batch item %r error: %s', self.name, cert_item, e)
            self.write({
                'state': 'approved',
                'reviewed_by': self.env.user.id,
                'review_date': fields.Datetime.now(),
            })
            self._add_trail(action='approved', note=f'Approved by {self.env.user.name}. {len(cert_batch)} cert(s).')
            self._send_mail_to_employee('approved')
            self.employee_id.sudo().invalidate_recordset()

            # ── BULLETPROOF REPAIR: always run after approval ──
            # Fixes any attachments that failed to copy during _apply_cert_change_with_attachment
            # This runs directly in the web server context, guaranteed to work
            try:
                self._repair_cert_attachments_after_approve(cert_batch)
            except Exception as e:
                _logger.warning('PCR %s: post-approve repair error (non-fatal): %s', self.name, e)

            return True

        skill_change = data.get('_skill_change')
        if skill_change:
            self._apply_skill_change(skill_change)
            self._finalize_approval()
            return True

        resume_change = data.get('_resume_change')
        if resume_change:
            self._apply_resume_change(resume_change)
            self._finalize_approval()
            return True

        write_vals = {}
        for k, v in data.items():
            if k in SKIP_ON_APPROVE:
                continue
            if v and str(v).startswith('[FILE:'):
                continue
            if v is None or v == '':
                continue
            if k in MANY2ONE_FIELDS:
                model_name = MANY2ONE_MODEL_MAP.get(k, 'res.country')
                try:
                    int_val = int(str(v))
                    linked_rec = self.env[model_name].sudo().browse(int_val)
                    if linked_rec.exists():
                        write_vals[k] = int_val
                    else:
                        _logger.warning('PCR %s: %s id %s not found in %s', self.name, k, int_val, model_name)
                except (ValueError, TypeError) as e:
                    _logger.warning('PCR %s: cannot convert %s=%r: %s', self.name, k, v, e)
                continue
            if k in SELECTION_FIELDS:
                field_obj = self.employee_id._fields.get(k)
                if field_obj and hasattr(field_obj, 'selection'):
                    sel = field_obj.selection
                    valid_keys = [s[0] for s in (sel(self.employee_id) if callable(sel) else sel)]
                    if v not in valid_keys:
                        _logger.warning('PCR %s: invalid selection %s=%r', self.name, k, v)
                        continue
                write_vals[k] = v
                continue
            if k == 'children':
                try:
                    write_vals[k] = int(v)
                except Exception:
                    pass
                continue
            if k == 'last_salary_per_annum_amt':
                try:
                    write_vals[k] = float(v)
                except Exception:
                    pass
                continue
            write_vals[k] = v

        if write_vals:
            try:
                self.employee_id.sudo().write(write_vals)
                self.employee_id.sudo().invalidate_recordset()
                _logger.info('PCR %s approved — %d fields written: %s', self.name, len(write_vals), list(write_vals.keys()))
            except Exception as e:
                _logger.error('PCR %s: write error: %s', self.name, e)
                raise UserError(_(
                    'Error writing approved data: %s\nFields: %s'
                ) % (str(e), ', '.join(str(k) for k in write_vals.keys())))

        self._finalize_approval(fields_written=len(write_vals))
        return True

    def _repair_cert_attachments_after_approve(self, changes):
        """
        BULLETPROOF POST-APPROVE REPAIR.
        Runs directly on the web server after every cert approval.
        Guarantees attachments are copied from PCR to hr.employee.skill
        even if _apply_cert_change_with_attachment failed silently.
        Uses att.datas directly (never .read()) to avoid Odoo 19 sudo bug.
        """
        cert_types = self.env['hr.skill.type'].sudo().search([('name', 'ilike', 'certif')])
        pcr_atts = self.env['ir.attachment'].sudo().search([
            ('res_model', '=', 'hr.profile.change.request'),
            ('res_id', '=', self.id),
        ], order='id asc')

        if not pcr_atts:
            return

        att_idx = 0
        for c in changes:
            if not isinstance(c, dict):
                continue
            has_file = bool(c.get('attachment_name') or c.get('has_file') or c.get('has_attachment'))
            if not has_file:
                continue
            action = c.get('cert_action') or c.get('type', '')
            if action not in ('add', 'edit'):
                continue
            if att_idx >= len(pcr_atts):
                break
            att = pcr_atts[att_idx]
            att_idx += 1

            skill_name = c.get('skill_name', '')
            emp_certs = self.env['hr.employee.skill'].sudo().search([
                ('employee_id', '=', self.employee_id.id),
                ('skill_type_id', 'in', cert_types.ids),
            ], order='id desc')

            for s in emp_certs:
                if skill_name and s.skill_id.name != skill_name:
                    continue
                existing = self.env['ir.attachment'].sudo().search([
                    ('res_model', '=', 'hr.employee.skill'),
                    ('res_id', '=', s.id),
                ])
                if not existing:
                    # Use att.datas directly — never .read() which returns False in Odoo 19
                    att_datas = att.sudo().datas
                    att_name = att.sudo().name
                    att_mime = att.sudo().mimetype or 'application/octet-stream'
                    if att_datas:
                        self.env['ir.attachment'].sudo().create({
                            'name': att_name,
                            'datas': att_datas,
                            'res_model': 'hr.employee.skill',
                            'res_id': s.id,
                            'mimetype': att_mime,
                        })
                        _logger.info('PCR %s: REPAIR copied %s -> skill %s id=%s',
                            self.name, att_name, skill_name, s.id)
                    break

    def _finalize_approval(self, fields_written=0):
        self.write({
            'state': 'approved',
            'reviewed_by': self.env.user.id,
            'review_date': fields.Datetime.now(),
        })
        self._add_trail(
            action='approved',
            note=f'Approved by {self.env.user.name}. {fields_written} field(s) written.',
        )
        self._send_mail_to_employee('approved')
        try:
            _fd = json.loads(self.submitted_data or '{}')
            _fp = (
                '_cert_change' not in _fd and
                '_cert_batch' not in _fd and
                '_skill_change' not in _fd and
                '_resume_change' not in _fd
            )
        except Exception:
            _fp = True
        if _fp:
            self.employee_id.sudo().write({
                'last_portal_submission': False,
                'last_submission_state': 'approved',
            })
        try:
            self.env.cr.execute('SELECT 1')
        except Exception:
            pass
        self.employee_id.sudo().invalidate_recordset()
        self.env['hr.employee'].sudo().invalidate_model()
        _logger.info('PCR %s finalized — employee cache cleared', self.name)

    def _apply_cert_change_with_attachment(self, cert_change, attachment=None):
        """
        FIX: Uses _copy_attachment_to_skill() which accesses att.datas directly
        instead of att.read(['datas']) — read() returns datas=False in Odoo 19 sudo context.
        """
        action = cert_change.get('cert_action') or cert_change.get('type', '')
        employee = self.employee_id
        if action == 'add':
            skill_id = cert_change.get('skill_id')
            try:
                skill_id = int(skill_id)
            except (TypeError, ValueError):
                raise UserError(_('Invalid skill ID.'))
            skill = self.env['hr.skill'].sudo().browse(skill_id)
            if not skill.exists():
                raise UserError(_('Skill no longer exists.'))
            skill_level = self.env['hr.skill.level'].sudo().search([
                ('skill_type_id', '=', skill.skill_type_id.id), ('default_level', '=', True),
            ], limit=1)
            if not skill_level:
                skill_level = self.env['hr.skill.level'].sudo().search(
                    [('skill_type_id', '=', skill.skill_type_id.id)], limit=1)
            if not skill_level:
                raise UserError(_('No skill level configured for this certificate type.'))
            new_skill = self.env['hr.employee.skill'].sudo().create({
                'employee_id': employee.id,
                'skill_id': skill_id,
                'skill_type_id': skill.skill_type_id.id,
                'skill_level_id': skill_level.id,
                'valid_from': cert_change.get('valid_from') or False,
                'valid_to': cert_change.get('valid_to') or False,
            })
            _logger.info('PCR %s: created cert skill %s (id=%s) for employee %s',
                self.name, skill.name, new_skill.id, employee.name)
            if attachment and attachment.exists():
                _copy_attachment_to_skill(self.env, attachment, new_skill.id, self.name)

        elif action == 'edit':
            record_id = cert_change.get('skill_record_id')
            if record_id:
                skill_record = self.env['hr.employee.skill'].sudo().browse(int(record_id))
                if skill_record.exists() and skill_record.employee_id.id == employee.id:
                    vals = {}
                    if cert_change.get('valid_from') is not None:
                        vals['valid_from'] = cert_change['valid_from'] or False
                    if cert_change.get('valid_to') is not None:
                        vals['valid_to'] = cert_change['valid_to'] or False
                    if vals:
                        skill_record.sudo().write(vals)
                    if attachment and attachment.exists():
                        _copy_attachment_to_skill(self.env, attachment, skill_record.id, self.name)

        elif action == 'delete':
            record_id = cert_change.get('skill_record_id')
            if record_id:
                skill_record = self.env['hr.employee.skill'].sudo().browse(int(record_id))
                if skill_record.exists() and skill_record.employee_id.id == employee.id:
                    skill_record.sudo().unlink()

    def _apply_cert_change(self, cert_change):
        """
        FIX: Uses _copy_attachment_to_skill() which accesses att.datas directly
        instead of att.read(['datas']) — read() returns datas=False in Odoo 19 sudo context.
        """
        action = cert_change.get('cert_action') or cert_change.get('type', '')
        employee = self.employee_id
        pcr_attachments = self.env['ir.attachment'].sudo().search([
            ('res_model', '=', 'hr.profile.change.request'), ('res_id', '=', self.id),
        ])
        if action == 'add':
            skill_id = cert_change.get('skill_id')
            try:
                skill_id = int(skill_id)
            except (TypeError, ValueError):
                raise UserError(_('Invalid skill ID.'))
            skill = self.env['hr.skill'].sudo().browse(skill_id)
            if not skill.exists():
                raise UserError(_('Skill no longer exists.'))
            skill_level = self.env['hr.skill.level'].sudo().search([
                ('skill_type_id', '=', skill.skill_type_id.id), ('default_level', '=', True),
            ], limit=1)
            if not skill_level:
                skill_level = self.env['hr.skill.level'].sudo().search(
                    [('skill_type_id', '=', skill.skill_type_id.id)], limit=1)
            if not skill_level:
                raise UserError(_('No skill level configured for this certificate type.'))
            new_skill = self.env['hr.employee.skill'].sudo().create({
                'employee_id': employee.id, 'skill_id': skill_id,
                'skill_type_id': skill.skill_type_id.id, 'skill_level_id': skill_level.id,
                'valid_from': cert_change.get('valid_from') or False,
                'valid_to': cert_change.get('valid_to') or False,
            })
            if pcr_attachments:
                for att in pcr_attachments:
                    _copy_attachment_to_skill(self.env, att, new_skill.id, self.name)

        elif action == 'edit':
            record_id = cert_change.get('skill_record_id')
            skill_record = self.env['hr.employee.skill'].sudo().browse(record_id)
            if not skill_record.exists() or skill_record.employee_id.id != employee.id:
                raise UserError(_('Certification record not found.'))
            vals = {}
            if cert_change.get('valid_from') is not None:
                vals['valid_from'] = cert_change['valid_from'] or False
            if cert_change.get('valid_to') is not None:
                vals['valid_to'] = cert_change['valid_to'] or False
            if vals:
                skill_record.sudo().write(vals)
            if pcr_attachments:
                for att in pcr_attachments:
                    _copy_attachment_to_skill(self.env, att, skill_record.id, self.name)

        elif action == 'delete':
            record_id = cert_change.get('skill_record_id')
            skill_record = self.env['hr.employee.skill'].sudo().browse(record_id)
            if skill_record.exists() and skill_record.employee_id.id == employee.id:
                skill_record.sudo().unlink()

    def _apply_skill_change(self, skill_change):
        action = skill_change.get('cert_action')
        employee = self.employee_id
        if action == 'add_batch':
            skills = skill_change.get('skills', [])
            seen = set()
            deduped = []
            for item in skills:
                sid = str(item.get('skill_id', ''))
                if sid and sid not in seen:
                    seen.add(sid)
                    deduped.append(item)
            existing_ids = set(self.env['hr.employee.skill'].sudo().search([
                ('employee_id', '=', employee.id),
                ('skill_type_id.is_certification', '=', False),
            ]).mapped('skill_id.id'))
            for item in deduped:
                skill_id = int(item.get('skill_id', 0))
                if skill_id in existing_ids:
                    continue
                skill = self.env['hr.skill'].sudo().browse(skill_id)
                if not skill.exists():
                    continue
                type_id = item.get('type_id')
                level_id = item.get('level_id')
                self.env['hr.employee.skill'].sudo().create({
                    'employee_id': employee.id, 'skill_id': skill_id,
                    'skill_type_id': int(type_id) if type_id else skill.skill_type_id.id,
                    'skill_level_id': int(level_id) if level_id else False,
                })
                existing_ids.add(skill_id)
        elif action == 'add':
            skill_id = int(skill_change.get('skill_id', 0))
            if self.env['hr.employee.skill'].sudo().search([
                ('employee_id', '=', employee.id), ('skill_id', '=', skill_id),
                ('skill_type_id.is_certification', '=', False),
            ], limit=1):
                return
            skill = self.env['hr.skill'].sudo().browse(skill_id)
            if not skill.exists():
                raise UserError(_('Skill no longer exists.'))
            type_id = skill_change.get('type_id')
            level_id = skill_change.get('level_id')
            self.env['hr.employee.skill'].sudo().create({
                'employee_id': employee.id, 'skill_id': skill_id,
                'skill_type_id': int(type_id) if type_id else skill.skill_type_id.id,
                'skill_level_id': int(level_id) if level_id else False,
            })
        elif action == 'edit':
            record_id = int(skill_change.get('skill_record_id', 0))
            level_id = skill_change.get('level_id')
            skill_record = self.env['hr.employee.skill'].sudo().browse(record_id)
            if skill_record.exists() and skill_record.employee_id.id == employee.id:
                skill_record.sudo().write({'skill_level_id': int(level_id) if level_id else False})
        elif action == 'delete':
            record_id = int(skill_change.get('skill_record_id', 0))
            skill_record = self.env['hr.employee.skill'].sudo().browse(record_id)
            if skill_record.exists() and skill_record.employee_id.id == employee.id:
                skill_record.sudo().unlink()

    def _apply_resume_change(self, resume_change):
        employee = self.employee_id
        pcr_attachment = self.env['ir.attachment'].sudo().search([
            ('res_model', '=', 'hr.profile.change.request'), ('res_id', '=', self.id),
            ('description', '=', 'Resume submitted by employee for approval'),
        ], limit=1)
        if not pcr_attachment:
            _logger.warning('PCR %s: No resume attachment found.', self.name)
            return
        try:
            # FIX: use .datas directly instead of .read(['datas'])
            att_datas = pcr_attachment.sudo().datas
            att_name = pcr_attachment.sudo().name
            if not att_datas:
                _logger.warning('PCR %s: Resume attachment datas empty.', self.name)
                return
            employee.sudo().write({
                'resume_file': att_datas,
                'resume_file_filename': resume_change.get('filename', att_name),
            })
            _logger.info('PCR %s: Resume saved for %s', self.name, employee.name)
        except Exception as e:
            _logger.error('PCR %s: Resume apply error: %s', self.name, e)

    def action_reject(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Reject Profile Change Request'),
            'res_model': 'hr.profile.change.request.reject.wizard',
            'view_mode': 'form', 'target': 'new',
            'context': {'default_request_id': self.id},
        }

    @api.model
    def resend_stuck_notifications_to_hr(self):
        try:
            pending_pcrs = self.sudo().search([('state', '=', 'pending')])
            fixed = 0
            for pcr in pending_pcrs:
                if not pcr.name or pcr.name == 'New':
                    seq = self.env['ir.sequence'].sudo().next_by_code('hr.profile.change.request')
                    if not seq:
                        try:
                            self.env['ir.sequence'].sudo().create({
                                'name': 'Profile Change Request',
                                'code': 'hr.profile.change.request',
                                'prefix': 'PCR/%(year)s/',
                                'padding': 4,
                                'company_id': False,
                            })
                            seq = self.env['ir.sequence'].sudo().next_by_code('hr.profile.change.request')
                        except Exception:
                            pass
                    if seq:
                        pcr.sudo().write({'name': seq})
                        fixed += 1
                try:
                    _rd = json.loads(pcr.submitted_data or '{}')
                    _rp = (
                        '_cert_change' not in _rd and
                        '_cert_batch' not in _rd and
                        '_skill_change' not in _rd and
                        '_resume_change' not in _rd
                    )
                except Exception:
                    _rp = True
                if _rp and pcr.employee_id.last_submission_state != 'pending':
                    pcr.employee_id.sudo().write({'last_submission_state': 'pending'})
            if fixed:
                _logger.info('resend_stuck_notifications: fixed %d PCR name(s)', fixed)
            return fixed
        except Exception as e:
            _logger.warning('resend_stuck_notifications error: %s', e)
            return 0

    def action_reset_to_pending(self):
        self.ensure_one()
        if self.state != 'rejected':
            raise UserError(_('Only rejected requests can be re-opened.'))
        self.write({
            'state': 'pending', 'rejection_reason': False,
            'reviewed_by': False, 'review_date': False,
        })
        self.employee_id.sudo().write({
            'last_submission_state': False, 'last_portal_submission': False,
        })
        self._add_trail(action='reopened', note=f'Re-opened by {self.env.user.name}')
        return True

    def _add_trail(self, action, note, reason=None):
        self.env['hr.profile.change.request.trail'].sudo().create({
            'request_id': self.id, 'action': action, 'note': note,
            'reason': reason or '', 'user_id': self.env.user.id,
            'action_date': fields.Datetime.now(),
        })

    def _send_mail_to_hr(self):
        try:
            hr_users = self._get_hr_reviewer_users()
            if not hr_users:
                return
            hr_emails, hr_names_list = [], []
            for u in hr_users:
                email = u.work_email or u.partner_id.email or (
                    u.login if '@' in (u.login or '') else None)
                if email:
                    hr_emails.append(email)
                    hr_names_list.append(u.name)
            if not hr_emails:
                return
            try:
                base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '')
                direct_link = f'{base_url}/odoo/action-employee_profile_change_request.action_hr_profile_change_request/{self.id}' if self.id else ''
            except Exception:
                direct_link = ''

            mail = self.env['mail.mail'].sudo().create({
                'subject': f'Profile Change Request: {self.name} — {self.employee_id.name} [Action Required]',
                'email_to': ', '.join(hr_emails),
                'email_from': self.employee_id.company_id.email or 'notifications@techcarrot-fz-llc1.odoo.com',
                'auto_delete': False,
                'body_html': (
                    f'<div style="font-family:Arial,sans-serif;max-width:620px;margin:auto;'
                    f'border:1px solid #ddd;border-radius:8px;overflow:hidden;">'
                    f'<div style="background:#4e73df;padding:24px 28px;">'
                    f'<h2 style="color:white;margin:0;font-size:20px;">📋 Profile Change Request — Action Required</h2>'
                    f'</div>'
                    f'<div style="padding:24px;background:#f9f9f9;">'
                    f'<p>Dear HR Team,<br><b>{self.employee_id.name}</b> has submitted a profile update request that needs your approval.</p>'
                    f'<table style="width:100%;border-collapse:collapse;background:white;">'
                    f'<tr style="background:#eef2ff;"><td style="padding:10px 14px;border:1px solid #ddd;font-weight:bold;width:38%;">Reference</td>'
                    f'<td style="padding:10px 14px;border:1px solid #ddd;">{self.name}</td></tr>'
                    f'<tr><td style="padding:10px 14px;border:1px solid #ddd;font-weight:bold;">Employee</td>'
                    f'<td style="padding:10px 14px;border:1px solid #ddd;">{self.employee_id.name}</td></tr>'
                    f'<tr style="background:#eef2ff;"><td style="padding:10px 14px;border:1px solid #ddd;font-weight:bold;">Company</td>'
                    f'<td style="padding:10px 14px;border:1px solid #ddd;">{self.company_id.name if self.company_id else "—"}</td></tr>'
                    f'<tr><td style="padding:10px 14px;border:1px solid #ddd;font-weight:bold;">Submitted On</td>'
                    f'<td style="padding:10px 14px;border:1px solid #ddd;">{self.submission_date}</td></tr>'
                    f'</table>'
                    f'{"<p style=margin-top:16px;><a href=" + chr(39) + direct_link + chr(39) + " style=background:#4e73df;color:white;padding:10px 20px;border-radius:6px;text-decoration:none;font-weight:bold;>👉 Click here to Review &amp; Approve/Reject</a></p>" if direct_link else ""}'
                    f'<p style="margin-top:12px;">Or go to: <b>Odoo → Profile Change Requests → Pending Review</b></p>'
                    f'<p style="color:#999;font-size:11px;">Sent to: {", ".join(hr_names_list)}</p>'
                    f'</div></div>'
                ),
            })
            mail.sudo().send()
        except Exception as e:
            _logger.warning('PCR %s: Failed to send HR notification: %s', self.name, e)

    def _send_mail_to_employee(self, status):
        try:
            emp_user = self.employee_id.user_id
            emp_email = (
                (emp_user.login if emp_user and '@' in (emp_user.login or '') else None)
                or self.employee_id.work_email
                or self.employee_id.private_email
            )
            if not emp_email:
                return
            if status == 'approved':
                subject = f'Profile Update Approved - {self.name}'
                body = (
                    f'<p>Dear <b>{self.employee_id.name}</b>,</p>'
                    f'<p>Your request <b>{self.name}</b> has been <b style="color:green">APPROVED</b>.</p>'
                    f'<p>Approved by: <b>{self.reviewed_by.name if self.reviewed_by else "HR"}</b></p>'
                )
            else:
                subject = f'Profile Update Rejected - {self.name}'
                body = (
                    f'<p>Dear <b>{self.employee_id.name}</b>,</p>'
                    f'<p>Your request <b>{self.name}</b> has been <b style="color:red">REJECTED</b>.</p>'
                    f'<p><b>Reason:</b> {self.rejection_reason or "No reason provided"}</p>'
                )
            mail = self.env['mail.mail'].sudo().create({
                'subject': subject, 'email_to': emp_email,
                'email_from': 'notifications@techcarrot-fz-llc1.odoo.com',
                'auto_delete': False, 'body_html': body,
            })
            mail.sudo().send()
        except Exception as e:
            _logger.warning('PCR %s: Failed to send employee notification: %s', self.name, e)


RELIGIONS = [
    'Christianity', 'Islam', 'Hinduism', 'Buddhism', 'Sikhism', 'Judaism',
    "Baha'i", 'Jainism', 'Shinto', 'Taoism', 'Confucianism', 'Zoroastrianism',
]


def post_init_hook(cr, registry):
    from odoo import api, SUPERUSER_ID
    env = api.Environment(cr, SUPERUSER_ID, {})
    Religion = env['tec.religion']
    existing_names = Religion.search([]).mapped('name')
    created = []
    for name in RELIGIONS:
        if name not in existing_names:
            Religion.create({'name': name})
            created.append(name)
    if created:
        _logger.info('[post_init_hook] Created %d religion(s): %s', len(created), created)
    else:
        _logger.info('[post_init_hook] All religions already exist.')