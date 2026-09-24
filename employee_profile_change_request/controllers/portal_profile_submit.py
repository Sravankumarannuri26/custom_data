# -*- coding: utf-8 -*-
import json
import logging
import re
import base64

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

ALLOWED_DOCUMENT_FIELDS = {
    'emirates_id_file',
    'passport_file',
    'other_documents',
    'has_work_permit',
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

EDITABLE_FIELDS = [
    'work_phone', 'private_email', 'private_phone',
    'private_street', 'private_street2', 'private_city', 'private_zip',
    'private_state_id', 'private_country_id',
    'whatsapp', 'linkedin', 'legal_name',
    'facebook_profile', 'insta_profile', 'twitter_profile',
    'blood_group', 'place_of_birth', 'birthday',
    'issue_date', 'expiry_date',
    'emirates_id_number', 'emirates_expiry_date',
    'passport_id', 'identification_id', 'ssnid', 'visa_no', 'permit_no',
    'pan', 'aadhar_no',
    'nationality_at_birth_id', 'country_id', 'issue_countries_id', 'countries_id', 'religion',
    'l10n_in_relationship', 'emergency_phone', 'e_private_city',
    'phone_code_1',
    'u_private_city', 'current_address',
    'house_no', 'area_name', 'city', 'zip_code',
    'country_residences_id', 'states_id',
    'no_of_career_break', 'career_break', 'career_break_detail',
    'career_break_start_date', 'career_break_end_date',
    'emergency_contact_person_name', 'emergency_contact_person_phone',
    'second_relation_with_employee',
    'alternate_mobile_number', 'emergency_contact_person_name_1',
    'emergency_contact_person_phone_1', 'second_alternative_number',
    'home_land_line_no', 'relationship_with_emp_id',
    'spouse_passport_no', 'spouse_passport_issue_date',
    'spouse_passport_expiry_date', 'spouse_passport_issuing_countries_id', 'spouse_visa_no',
    'spouse_visa_expire_date', 'spouse_emirates_id_no',
    'spouse_emirates_issue_date', 'spouse_emirates_id_expiry_date',
    'spouse_aadhar_no',
    'dependent_child_name_1', 'dependent_child_dob_1',
    'dependent_child_passport_no',
    'dependent_child_passport_issue_date_1', 'dependent_child_passport_expiry_date_1',
    'dependent_child_visa_no_1', 'dependent_child_visa_expiration_date_1',
    'dependent_child_emirates_id_no_1', 'dependent_child_emirates_id_issue_date_1',
    'dependent_child_emirates_id_expiry_date_1', 'dependent_child_aadhar_no_1',
    'dependent_child_gender_1', 'dependent_child_passport_issuing_countries_1_id',
    'father_name', 'father_dob', 'mother_name', 'mother_dob',
    'father_nationalities_id', 'mother_nationalities_id',
    'children', 'marital',
    'employee_nominee_name', 'employee_nominee_contact_no',
    'domain_worked', 'primary_skill', 'secondary_skill', 'tool_used',
    'industry_ref_name', 'industry_ref_email', 'industry_ref_mob_no',
    'home_country_id_name', 'home_country_id_number',
    'mother_tongue_name', 'language_known_name',
    'institute_name', 'degree_name', 'field_of_study',
    'study_field', 'start_date_of_degree', 'completion_date_of_degree',
    'year_of_passing', 'score', 'certification_obtained',
    'experience', 'current_role', 'industry_start_date',
    'last_organisation_name', 'last_location',
    'last_salary_per_annum_currency', 'last_salary_per_annum_amt',
    'reason_for_leaving', 'last_report_manager_name',
    'last_report_manager_designation', 'last_report_manager_mob_no',
    'last_report_manager_mail',
    'previous_company_name', 'designation', 'period_in_company',
    'reason_of_leaving',
]

FILE_FIELDS = [
    'emirates_id_file',
    'passport_file',
    'other_documents',
    'has_work_permit',
]

EMAIL_PATTERN = re.compile(r'^[^\s@]+@[^\s@]+\.[^\s@]+$')
ISD_PATTERN   = re.compile(r'^\+[1-9][0-9]{0,2}$')

ISD_CODES = [
    ('+1','USA / Canada (+1)'),('+7','Russia (+7)'),('+20','Egypt (+20)'),
    ('+27','South Africa (+27)'),('+30','Greece (+30)'),('+31','Netherlands (+31)'),
    ('+32','Belgium (+32)'),('+33','France (+33)'),('+34','Spain (+34)'),
    ('+36','Hungary (+36)'),('+39','Italy (+39)'),('+40','Romania (+40)'),
    ('+41','Switzerland (+41)'),('+43','Austria (+43)'),('+44','UK (+44)'),
    ('+45','Denmark (+45)'),('+46','Sweden (+46)'),('+47','Norway (+47)'),
    ('+48','Poland (+48)'),('+49','Germany (+49)'),('+51','Peru (+51)'),
    ('+52','Mexico (+52)'),('+54','Argentina (+54)'),('+55','Brazil (+55)'),
    ('+56','Chile (+56)'),('+57','Colombia (+57)'),('+58','Venezuela (+58)'),
    ('+60','Malaysia (+60)'),('+61','Australia (+61)'),('+62','Indonesia (+62)'),
    ('+63','Philippines (+63)'),('+64','New Zealand (+64)'),('+65','Singapore (+65)'),
    ('+66','Thailand (+66)'),('+81','Japan (+81)'),('+82','South Korea (+82)'),
    ('+84','Vietnam (+84)'),('+86','China (+86)'),('+90','Turkey (+90)'),
    ('+91','India (+91)'),('+92','Pakistan (+92)'),('+93','Afghanistan (+93)'),
    ('+94','Sri Lanka (+94)'),('+95','Myanmar (+95)'),('+98','Iran (+98)'),
    ('+212','Morocco (+212)'),('+213','Algeria (+213)'),('+216','Tunisia (+216)'),
    ('+218','Libya (+218)'),('+220','Gambia (+220)'),('+221','Senegal (+221)'),
    ('+234','Nigeria (+234)'),('+249','Sudan (+249)'),('+254','Kenya (+254)'),
    ('+256','Uganda (+256)'),('+255','Tanzania (+255)'),('+260','Zambia (+260)'),
    ('+263','Zimbabwe (+263)'),('+966','Saudi Arabia (+966)'),('+967','Yemen (+967)'),
    ('+968','Oman (+968)'),('+970','Palestine (+970)'),('+971','UAE (+971)'),
    ('+972','Israel (+972)'),('+973','Bahrain (+973)'),('+974','Qatar (+974)'),
    ('+975','Bhutan (+975)'),('+976','Mongolia (+976)'),('+977','Nepal (+977)'),
    ('+994','Azerbaijan (+994)'),('+995','Georgia (+995)'),('+996','Kyrgyzstan (+996)'),
    ('+998','Uzbekistan (+998)'),
]

READ_ONLY_MODE = True

def _write_blocked_response():
    return request.make_json_response({
        'success': False,
        'error': 'Profile editing has been disabled. Please contact HR for any changes.',
    })


def _normalize_str(val):
    if val is None or val is False:
        return ''
    s = str(val).strip()
    return '' if s in ('False', 'None') else s


def _get_employee():
    return request.env['hr.employee'].sudo().search(
        [('user_id', '=', request.env.user.id)], limit=1
    )


def _ensure_sequence_exists(env):
    try:
        existing = env['ir.sequence'].sudo().search(
            [('code', '=', 'hr.profile.change.request')], limit=1
        )
        if not existing:
            env['ir.sequence'].sudo().create({
                'name': 'Profile Change Request',
                'code': 'hr.profile.change.request',
                'prefix': 'PCR/%(year)s/',
                'padding': 4,
                'company_id': False,
            })
            env.cr.commit()
            _logger.info('PCR sequence auto-created in DB')
    except Exception as e:
        _logger.warning('_ensure_sequence_exists error: %s', e)


def _fix_stuck_pcrs(env, employee):
    try:
        env['hr.profile.change.request'].sudo().resend_stuck_notifications_to_hr()

        all_new_pcrs = env['hr.profile.change.request'].sudo().search([
            ('name', '=', 'New'),
            ('state', '=', 'pending'),
        ])
        for pcr in all_new_pcrs:
            seq = env['ir.sequence'].sudo().next_by_code('hr.profile.change.request')
            if seq:
                pcr.sudo().write({'name': seq})
                _logger.info('Auto-fixed PCR name for %s -> %s', pcr.employee_id.name, seq)

        if employee.last_submission_state == 'pending':
            pending = env['hr.profile.change.request'].sudo().search([
                ('employee_id', '=', employee.id),
                ('state', '=', 'pending'),
            ], limit=1)
            if not pending:
                employee.sudo().write({
                    'last_submission_state': False,
                    'last_portal_submission': False,
                })
                _logger.info('Cleared stuck pending state for %s', employee.name)

        latest_any_pcr = env['hr.profile.change.request'].sudo().search([
            ('employee_id', '=', employee.id),
        ], order='create_date desc', limit=1)
        if latest_any_pcr:
            pcr_state = latest_any_pcr.state
            emp_state = employee.last_submission_state
            if pcr_state == 'approved' and emp_state not in ('approved', False):
                employee.sudo().write({'last_submission_state': 'approved', 'last_portal_submission': False})
                employee.sudo().invalidate_recordset()
            elif pcr_state == 'rejected' and emp_state != 'rejected':
                employee.sudo().write({'last_submission_state': 'rejected'})
            elif pcr_state in ('draft',) and emp_state == 'pending':
                employee.sudo().write({'last_submission_state': False, 'last_portal_submission': False})
    except Exception as e:
        _logger.warning('_fix_stuck_pcrs error: %s', e)


def _unwrap_cert_batch(raw):
    """
    Safely unwrap _cert_batch value into a list of cert-change dicts.
    Portal controller stores: {'_cert_batch': {'changes': [...]}}
    Older records may store:  {'_cert_batch': [...]}
    Always returns a plain list.
    """
    if isinstance(raw, dict):
        return raw.get('changes', [])
    if isinstance(raw, list):
        return raw
    return []


def _build_pending_cert_changes(pcr_list, env):
    """
    Build the pending_cert_changes list for portal display.
    Handles both old _cert_change (single) and new _cert_batch (multi) formats.
    Attachment matching: first tries by row_id in description, then falls back positionally.
    """
    pending_cert_changes = []
    for pcr in pcr_list:
        if not pcr.submitted_data:
            continue
        try:
            data = json.loads(pcr.submitted_data)

            # ── Old single-change format ──
            cert_change = data.get('_cert_change')
            if cert_change and isinstance(cert_change, dict):
                pcr_attachment = env['ir.attachment'].sudo().search([
                    ('res_model', '=', 'hr.profile.change.request'),
                    ('res_id', '=', pcr.id),
                ], limit=1)
                pending_cert_changes.append({
                    'pcr_name':        pcr.name,
                    'pcr_id':          pcr.id,
                    'cert_action':     cert_change.get('cert_action', ''),
                    'skill_name':      cert_change.get('skill_name', '—'),
                    'valid_from':      cert_change.get('valid_from') or '',
                    'valid_to':        cert_change.get('valid_to') or '',
                    'attachment_name': cert_change.get('attachment_name') or '',
                    'pcr_attachment':  pcr_attachment or False,
                    'skill_record_id': cert_change.get('skill_record_id'),
                })

            # ── New batch format ──
            cert_batch_raw = data.get('_cert_batch')
            cert_batch = _unwrap_cert_batch(cert_batch_raw)
            if cert_batch:
                # Load ALL attachments for this PCR ordered by id ascending
                all_attachments = env['ir.attachment'].sudo().search([
                    ('res_model', '=', 'hr.profile.change.request'),
                    ('res_id', '=', pcr.id),
                ], order='id asc')
                att_list = list(all_attachments)

                # Build a map: row_id string -> attachment (for description-based match)
                row_id_to_att = {}
                for att in att_list:
                    desc = att.description or ''
                    if 'row' in desc:
                        parts = desc.split('row ')
                        if len(parts) > 1:
                            rid = parts[-1].strip()
                            row_id_to_att[rid] = att

                positional_index = 0

                for ci in cert_batch:
                    if not isinstance(ci, dict):
                        continue
                    row_id = str(ci.get('row_id', ''))
                    attachment_name = ci.get('attachment_name') or ''
                    has_file = bool(attachment_name) or bool(ci.get('has_file')) or bool(ci.get('has_attachment'))

                    matched_att = False
                    if has_file:
                        if row_id and row_id in row_id_to_att:
                            matched_att = row_id_to_att[row_id]
                        else:
                            if positional_index < len(att_list):
                                matched_att = att_list[positional_index]
                                positional_index += 1

                    pending_cert_changes.append({
                        'pcr_name':        pcr.name,
                        'pcr_id':          pcr.id,
                        'cert_action':     ci.get('type', '') or ci.get('cert_action', ''),
                        'skill_name':      ci.get('skill_name', '—'),
                        'valid_from':      ci.get('valid_from') or '',
                        'valid_to':        ci.get('valid_to') or '',
                        'attachment_name': attachment_name,
                        'pcr_attachment':  matched_att,
                        'skill_record_id': ci.get('skill_record_id'),
                    })

        except Exception as e:
            _logger.warning('_build_pending_cert_changes error for PCR %s: %s', pcr.name, e)
            continue
    return pending_cert_changes


def _build_cert_attachments_map(certifications, env):
    """
    Build a dict {skill_record_id: [attachment_records]} for approved certifications.
    Searches ir.attachment where res_model='hr.employee.skill'.
    This is the FIX: always use this helper so the portal template can display attachments.
    """
    cert_attachments_map = {}
    if not certifications:
        return cert_attachments_map
    try:
        cert_ids = certifications.ids if hasattr(certifications, 'ids') else [c.id for c in certifications]
        if not cert_ids:
            return cert_attachments_map
        all_cert_atts = env['ir.attachment'].sudo().search([
            ('res_model', '=', 'hr.employee.skill'),
            ('res_id', 'in', cert_ids),
        ])
        for att in all_cert_atts:
            cert_attachments_map.setdefault(att.res_id, []).append(att)
    except Exception as e:
        _logger.warning('_build_cert_attachments_map error: %s', e)
    return cert_attachments_map


class EmployeePortalProfileSubmit(http.Controller):

    # ─────────────────────────────────────────────────────────────────────────
    # HOME
    # ─────────────────────────────────────────────────────────────────────────
    @http.route('/my/employee', type='http', auth='user', website=True, methods=['GET'])
    def portal_employee_home(self, **kwargs):
        return request.redirect('/my/employee/personal')

    # ─────────────────────────────────────────────────────────────────────────
    # STATES JSON
    # ─────────────────────────────────────────────────────────────────────────
    @http.route('/portal/get_states', type='json', auth='user', website=True)
    def get_states_by_country(self, country_id=0, **kwargs):
        try:
            states = request.env['res.country.state'].sudo().search(
                [('country_id', '=', int(country_id))], order='name'
            )
            return [{'id': s.id, 'name': s.name} for s in states]
        except Exception:
            return []

    # ─────────────────────────────────────────────────────────────────────────
    # SECURE DOCUMENT DOWNLOAD
    # ─────────────────────────────────────────────────────────────────────────
    @http.route(
        '/my/employee/document/<string:field_name>',
        type='http', auth='user', website=True, methods=['GET'],
    )
    def portal_employee_document(self, field_name, download=False, **kwargs):
        if field_name not in ALLOWED_DOCUMENT_FIELDS:
            return request.not_found()
        employee = _get_employee()
        if not employee:
            return request.not_found()
        try:
            if isinstance(download, str):
                download = download.lower() in ('true', '1', 'yes')
            file_data = getattr(employee, field_name, False)
            if not file_data:
                return request.not_found()
            file_bytes = base64.b64decode(file_data)
            filename_field = field_name + '_filename'
            filename = getattr(employee, filename_field, None) or field_name
            import mimetypes

            mimetype = None
            if file_bytes[:4] == b'\x89PNG':
                mimetype = 'image/png'
                if not filename.lower().endswith('.png'):
                    filename = filename + '.png'
            elif file_bytes[:3] == b'\xff\xd8\xff':
                mimetype = 'image/jpeg'
                if not filename.lower().endswith(('.jpg', '.jpeg')):
                    filename = filename + '.jpg'
            elif file_bytes[:4] == b'%PDF':
                mimetype = 'application/pdf'
                if not filename.lower().endswith('.pdf'):
                    filename = filename + '.pdf'
            else:
                mimetype = mimetypes.guess_type(filename)[0] or 'application/octet-stream'

            headers = [
                ('Content-Type', mimetype),
                ('Content-Length', len(file_bytes)),
            ]
            if download:
                headers.append(('Content-Disposition', f'attachment; filename="{filename}"'))
            else:
                headers.append(('Content-Disposition', f'inline; filename="{filename}"'))
            headers.append(('X-Content-Type-Options', 'nosniff'))
            return request.make_response(file_bytes, headers=headers)
        except Exception as e:
            _logger.error('Error serving document %s: %s', field_name, e)
            return request.not_found()

    # ─────────────────────────────────────────────────────────────────────────
    # SECURE RESUME DOWNLOAD
    # ─────────────────────────────────────────────────────────────────────────
    @http.route(
        '/my/employee/resume',
        type='http', auth='user', website=True, methods=['GET'],
    )
    def portal_employee_resume(self, download=False, **kwargs):
        employee = _get_employee()
        if not employee:
            return request.not_found()
        try:
            if isinstance(download, str):
                download = download.lower() in ('true', '1', 'yes')
            file_data = employee.resume_file
            if not file_data:
                return request.not_found()
            file_bytes = base64.b64decode(file_data)
            filename = employee.resume_file_filename or 'resume'
            import mimetypes

            mimetype = None
            if file_bytes[:4] == b'\x89PNG':
                mimetype = 'image/png'
                if not filename.lower().endswith('.png'):
                    filename = filename + '.png'
            elif file_bytes[:3] == b'\xff\xd8\xff':
                mimetype = 'image/jpeg'
                if not filename.lower().endswith(('.jpg', '.jpeg')):
                    filename = filename + '.jpg'
            elif file_bytes[:4] == b'%PDF':
                mimetype = 'application/pdf'
                if not filename.lower().endswith('.pdf'):
                    filename = filename + '.pdf'
            else:
                mimetype = mimetypes.guess_type(filename)[0] or 'application/octet-stream'

            headers = [
                ('Content-Type', mimetype),
                ('Content-Length', len(file_bytes)),
            ]
            if download:
                headers.append(('Content-Disposition', f'attachment; filename="{filename}"'))
            else:
                headers.append(('Content-Disposition', f'inline; filename="{filename}"'))
            headers.append(('X-Content-Type-Options', 'nosniff'))
            return request.make_response(file_bytes, headers=headers)
        except Exception as e:
            _logger.error('Error serving resume: %s', e)
            return request.not_found()

    # ─────────────────────────────────────────────────────────────────────────
    # PERSONAL DETAILS — GET + POST
    # ─────────────────────────────────────────────────────────────────────────
    @http.route(
        '/my/employee/personal',
        type='http', auth='user', website=True,
        methods=['GET', 'POST'], csrf=False,
    )
    def portal_employee_personal(self, **post):
        employee = _get_employee()
        if not employee:
            return request.redirect('/my')

        # if request.httprequest.method == 'POST':
        #     return self._handle_post(employee, post)

        if request.httprequest.method == 'POST':
            return _write_blocked_response()

        employee.sudo().invalidate_recordset()
        _ensure_sequence_exists(request.env)
        _fix_stuck_pcrs(request.env, employee)

        portal_overlay = {}
        if (employee.last_portal_submission
                and employee.last_submission_state in ('pending', 'rejected')):
            try:
                portal_overlay = json.loads(employee.last_portal_submission)
            except Exception:
                portal_overlay = {}

        notification = None

        latest_personal_pcr = None
        for _pcr in request.env['hr.profile.change.request'].sudo().search([
            ('employee_id', '=', employee.id),
        ], order='create_date desc', limit=50):
            try:
                _data = json.loads(_pcr.submitted_data or '{}')
                if '_skill_change' not in _data and '_cert_change' not in _data and '_resume_change' not in _data and '_cert_batch' not in _data:
                    latest_personal_pcr = _pcr
                    break
            except Exception:
                latest_personal_pcr = _pcr
                break

        if latest_personal_pcr and latest_personal_pcr.state == 'pending':
            employee.sudo().write({'last_submission_state': 'pending'})
            notification = {
                'type':         'warning',
                'message':      'Your profile change request is awaiting HR review.',
                'reason':       False,
                'request_name': latest_personal_pcr.name,
            }
        elif latest_personal_pcr and latest_personal_pcr.state == 'approved':
            employee.sudo().write({'last_submission_state': 'approved'})
            notification = {
                'type':         'success',
                'message':      'Your profile has been updated by HR successfully.',
                'reason':       False,
                'request_name': latest_personal_pcr.name,
            }
        elif latest_personal_pcr and latest_personal_pcr.state == 'rejected':
            employee.sudo().write({'last_submission_state': 'rejected'})
            notification = {
                'type':         'danger',
                'message':      'Your profile update request was rejected by HR.',
                'reason':       latest_personal_pcr.rejection_reason or 'No reason provided.',
                'request_name': latest_personal_pcr.name,
            }
        else:
            employee.sudo().write({'last_submission_state': False})

        pending_req = latest_personal_pcr if (latest_personal_pcr and latest_personal_pcr.state == 'pending') else None

        countries = request.env['res.country'].sudo().search([], order='name')
        religions = request.env['tec.religion'].sudo().search([], order='name')

        try:
            relationships = request.env['employee.relationship'].sudo().search([], order='name')
        except Exception:
            relationships = []

        skill_types = request.env['hr.skill.type'].sudo().search([
            ('is_certification', '=', False)
        ], order='name')
        all_skills = request.env['hr.skill'].sudo().search([
            ('skill_type_id', 'in', skill_types.ids)
        ], order='skill_type_id, name')
        all_levels = request.env['hr.skill.level'].sudo().search([
            ('skill_type_id', 'in', skill_types.ids)
        ], order='skill_type_id, name')
        skill_data = {'skills': {}, 'levels': {}}
        for sk in all_skills:
            tid = str(sk.skill_type_id.id)
            skill_data['skills'].setdefault(tid, [])
            skill_data['skills'][tid].append({'id': str(sk.id), 'name': sk.name})
        for lv in all_levels:
            tid = str(lv.skill_type_id.id)
            skill_data['levels'].setdefault(tid, [])
            skill_data['levels'][tid].append({'id': str(lv.id), 'name': lv.name})
        employee_skills = request.env['hr.employee.skill'].sudo().search([
            ('employee_id', '=', employee.id),
            ('skill_type_id.is_certification', '=', False),
        ], order='skill_type_id, id')
        cert_skill_types = request.env['hr.skill.type'].sudo().search([('name', 'ilike', 'certif')])
        certificate_skills = request.env['hr.skill'].sudo().search([
            ('skill_type_id', 'in', cert_skill_types.ids)
        ], order='name')
        certifications = request.env['hr.employee.skill'].sudo().search([
            ('employee_id', '=', employee.id),
            ('skill_type_id.name', 'ilike', 'certif'),
        ], order='id desc')

        # ── FIX: Use shared helper for cert_attachments_map ──
        cert_attachments_map = _build_cert_attachments_map(certifications, request.env)

        # All pending PCRs for this employee
        all_pending_pcrs = request.env['hr.profile.change.request'].sudo().search([
            ('employee_id', '=', employee.id),
            ('state', '=', 'pending'),
        ], order='id desc')

        pending_skill_changes = []
        pending_resume_change = None

        for pcr in all_pending_pcrs:
            try:
                data = json.loads(pcr.submitted_data or '{}')
                sc = data.get('_skill_change')
                if sc:
                    if sc.get('cert_action') == 'add_batch':
                        for item in sc.get('skills', []):
                            pending_skill_changes.append({
                                'pcr_name': pcr.name, 'cert_action': 'add',
                                'type_name': item.get('type_name', '—'),
                                'skill_name': item.get('skill_name', '—'),
                                'level_name': item.get('level_name', '—'),
                            })
                    else:
                        pending_skill_changes.append({
                            'pcr_name': pcr.name, 'cert_action': sc.get('cert_action', ''),
                            'type_name': sc.get('type_name', '—'),
                            'skill_name': sc.get('skill_name', '—'),
                            'level_name': sc.get('level_name', '—'),
                        })
                rc = data.get('_resume_change')
                if rc and not pending_resume_change:
                    pending_resume_change = {'pcr_name': pcr.name, 'filename': rc.get('filename', '—')}
            except Exception:
                continue

        pending_cert_changes = _build_pending_cert_changes(all_pending_pcrs, request.env)

        return request.render(
            'employee_self_service_portal.portal_employee_profile_personal',
            {
                'employee':              employee,
                'countries':             countries,
                'all_countries':         countries,
                'isd_codes':             ISD_CODES,
                'notification':          notification,
                'portal_overlay':        portal_overlay,
                'religions':             religions,
                'relationships':         relationships,
                'skill_types':           skill_types,
                'skill_data_json':       json.dumps(skill_data),
                'employee_skills':       employee_skills,
                'certificate_skills':    certificate_skills,
                'certifications':        certifications,
                'pending_skill_changes': pending_skill_changes,
                'pending_resume_change': pending_resume_change,
                'pending_cert_changes':  pending_cert_changes,
                'cert_attachments_map':  cert_attachments_map,
            },
        )

    def _handle_post(self, employee, post):
        try:
            if employee.last_submission_state == 'rejected':
                employee.sudo().write({
                    'last_submission_state': False,
                    'last_portal_submission': False,
                })

            pending_req = request.env['hr.profile.change.request'].sudo().search([
                ('employee_id', '=', employee.id),
                ('state', '=', 'pending'),
            ], limit=1)
            employee_state = employee.sudo().read(['last_submission_state'])[0]['last_submission_state']
            if pending_req and employee_state == 'pending':
                return request.make_json_response({
                    'success': False,
                    'error': 'Your previous request is still pending HR approval.',
                })

            for field in ['private_email', 'industry_ref_email', 'last_report_manager_mail']:
                val = post.get(field, '').strip()
                if val and not EMAIL_PATTERN.match(val):
                    return request.make_json_response({'success': False, 'error': f'Invalid email format: {field}'})

            isd_val = post.get('phone_code_1', '').strip()
            if isd_val and not ISD_PATTERN.match(isd_val):
                return request.make_json_response({'success': False, 'error': 'ISD code must start with + followed by 1-3 digits'})

            changed = {}

            for field in EDITABLE_FIELDS:
                val = post.get(field)
                if val is None:
                    continue
                new_val = str(val).strip()

                if field in MANY2ONE_FIELDS:
                    try:
                        new_id = int(new_val) if new_val else 0
                    except (ValueError, TypeError):
                        continue
                    current_rec = getattr(employee, field, False)
                    current_id = (current_rec.id or 0) if (current_rec and hasattr(current_rec, 'id')) else 0
                    if new_id and new_id != current_id:
                        changed[field] = str(new_id)
                    continue

                try:
                    current = getattr(employee, field, None)
                    current_str = _normalize_str(current.name if hasattr(current, 'name') else current)
                    if new_val != current_str:
                        changed[field] = new_val
                except Exception:
                    if new_val:
                        changed[field] = new_val

            file_changed_fields = {}
            file_attachment_data = {}

            for field in FILE_FIELDS:
                file_obj = request.httprequest.files.get(field)
                if file_obj and file_obj.filename:
                    try:
                        raw = file_obj.read()
                        file_data = base64.b64encode(raw).decode('utf-8')
                        file_changed_fields[field] = file_data
                        changed[field] = f'[FILE:{file_obj.filename}]'
                        file_attachment_data[field] = (
                            file_obj.filename,
                            file_data,
                            file_obj.content_type or 'application/octet-stream',
                        )
                    except Exception as e:
                        _logger.warning('File upload failed for %s: %s', field, e)

            if not changed and not file_changed_fields:
                return request.make_json_response({
                    'success': True, 'reference': '', 'no_change': True,
                    'message': 'No changes detected. Your profile is already up to date.',
                })

            if file_changed_fields:
                try:
                    employee.sudo().write(file_changed_fields)
                except Exception as e:
                    _logger.warning('Direct file write to employee failed: %s', e)

            ref = ''
            if changed:
                req_record = request.env['hr.profile.change.request'].sudo().create({
                    'employee_id':    employee.id,
                    'submitted_data': json.dumps(changed),
                    'state':          'draft',
                })
                req_record.action_submit()
                ref = req_record.name

                for field, (fname, fdata, fmime) in file_attachment_data.items():
                    try:
                        from odoo.addons.employee_self_service_portal.models.hr_profile_change_request import FIELD_LABELS
                        field_label = FIELD_LABELS.get(field, field.replace('_', ' ').title())
                    except Exception:
                        field_label = field.replace('_', ' ').title()
                    request.env['ir.attachment'].sudo().create({
                        'name': f'[{field_label}] {fname}',
                        'datas': fdata,
                        'res_model': 'hr.profile.change.request',
                        'res_id': req_record.id,
                        'mimetype': fmime,
                        'description': f'Document uploaded by employee: {field}',
                    })
                _logger.info('PCR %s created for %s — fields: %s', ref, employee.name, list(changed.keys()))

            return request.make_json_response({
                'success': True, 'reference': ref, 'no_change': False,
                'message': 'Your changes have been submitted. HR will review and notify you.' if ref else 'Your documents have been uploaded successfully.',
            })

        except Exception as e:
            _logger.error('Profile change error for %s: %s', employee.name, str(e))
            return request.make_json_response({'success': False, 'error': str(e)})

    # ─────────────────────────────────────────────────────────────────────────
    # EXPERIENCE AND SKILLS — GET + POST
    # ─────────────────────────────────────────────────────────────────────────
    @http.route('/my/employee/experience', type='http', auth='user', website=True, methods=['GET', 'POST'])
    def portal_employee_experience(self, **post):
        employee = _get_employee()
        if not employee:
            return request.redirect('/my')

        if request.httprequest.method == 'POST':
            return _write_blocked_response()
        if False:
            action = post.get('action')
            try:
                if action == 'submit_combined':
                    batch_raw    = post.get('batch_skills', '')
                    skill_action = post.get('skill_action', '')
                    resume_file  = request.httprequest.files.get('resume_file')

                    combined_payload = {}

                    if batch_raw:
                        try:
                            batch_skills = json.loads(batch_raw)
                            combined_payload['_skill_change'] = {
                                'cert_action': 'add_batch',
                                'skills': batch_skills,
                            }
                        except Exception:
                            pass
                    elif skill_action:
                        combined_payload['_skill_change'] = {
                            'cert_action': skill_action,
                            'skill_record_id': int(post.get('skill_record_id', 0) or 0),
                            'skill_name': post.get('skill_name', ''),
                            'type_name': post.get('type_name', ''),
                            'level_id': int(post.get('level_id', 0) or 0),
                            'level_name': post.get('level_name', ''),
                        }

                    resume_data = None
                    if resume_file and resume_file.filename:
                        allowed_types = [
                            'application/pdf',
                            'application/msword',
                            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                        ]
                        if resume_file.content_type not in allowed_types:
                            return request.make_json_response({'success': False, 'error': 'Only PDF, DOC, DOCX files allowed for resume.'})
                        file_content = resume_file.read()
                        if len(file_content) > 10 * 1024 * 1024:
                            return request.make_json_response({'success': False, 'error': 'Resume file size must not exceed 10 MB.'})
                        resume_data = base64.b64encode(file_content).decode()
                        combined_payload['_resume_change'] = {
                            'filename': resume_file.filename,
                            'mimetype': resume_file.content_type or 'application/octet-stream',
                        }

                    if not combined_payload:
                        return request.make_json_response({'success': False, 'error': 'No changes provided.'})

                    pcr = request.env['hr.profile.change.request'].sudo().create({
                        'employee_id': employee.id,
                        'submitted_data': json.dumps(combined_payload),
                        'state': 'draft',
                    })
                    pcr.action_submit()

                    if resume_data and resume_file:
                        request.env['ir.attachment'].sudo().create({
                            'name': resume_file.filename,
                            'datas': resume_data,
                            'res_model': 'hr.profile.change.request',
                            'res_id': pcr.id,
                            'mimetype': resume_file.content_type or 'application/octet-stream',
                            'description': 'Resume submitted by employee for approval',
                        })

                    return request.make_json_response({'success': True, 'reference': pcr.name})

                elif action == 'upload_resume':
                    resume_file = request.httprequest.files.get('resume_file')
                    if not resume_file or not resume_file.filename:
                        return request.make_json_response({'success': False, 'error': 'No file provided.'})
                    allowed_types = [
                        'application/pdf',
                        'application/msword',
                        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                    ]
                    if resume_file.content_type not in allowed_types:
                        return request.make_json_response({'success': False, 'error': 'Only PDF, DOC, DOCX files allowed.'})
                    file_content = resume_file.read()
                    if len(file_content) > 10 * 1024 * 1024:
                        return request.make_json_response({'success': False, 'error': 'File size must not exceed 10 MB.'})
                    file_data = base64.b64encode(file_content).decode()
                    payload = {
                        '_resume_change': {
                            'filename': resume_file.filename,
                            'mimetype': resume_file.content_type or 'application/octet-stream',
                        }
                    }
                    pcr = request.env['hr.profile.change.request'].sudo().create({
                        'employee_id': employee.id,
                        'submitted_data': json.dumps(payload),
                        'state': 'draft',
                    })
                    pcr.action_submit()
                    request.env['ir.attachment'].sudo().create({
                        'name': resume_file.filename,
                        'datas': file_data,
                        'res_model': 'hr.profile.change.request',
                        'res_id': pcr.id,
                        'mimetype': resume_file.content_type or 'application/octet-stream',
                        'description': 'Resume submitted by employee for approval',
                    })
                    return request.make_json_response({'success': True, 'reference': pcr.name})

                elif action == 'add_skill':
                    batch_raw = post.get('batch_skills', '')
                    if batch_raw:
                        try:
                            batch_skills = json.loads(batch_raw)
                        except Exception:
                            return request.make_json_response({'success': False, 'error': 'Invalid batch data.'})
                        if not batch_skills:
                            return request.make_json_response({'success': False, 'error': 'No skills provided.'})
                        for item in batch_skills:
                            skill = request.env['hr.skill'].sudo().browse(int(item.get('skill_id', 0)))
                            if not skill.exists():
                                return request.make_json_response({'success': False, 'error': f'Skill "{item.get("skill_name", "")}" not found.'})
                        payload = {
                            '_skill_change': {
                                'cert_action': 'add_batch',
                                'skills': batch_skills,
                            }
                        }
                        pcr = request.env['hr.profile.change.request'].sudo().create({
                            'employee_id': employee.id,
                            'submitted_data': json.dumps(payload),
                            'state': 'draft',
                        })
                        pcr.action_submit()
                        return request.make_json_response({'success': True, 'reference': pcr.name})
                    else:
                        skill_id = int(post.get('skill_id', 0) or 0)
                        level_id = int(post.get('level_id', 0) or 0)
                        type_id  = int(post.get('type_id', 0) or 0)
                        skill_name = post.get('skill_name', '')
                        level_name = post.get('level_name', '')
                        type_name  = post.get('type_name', '')
                        if not skill_id:
                            return request.make_json_response({'success': False, 'error': 'Skill is required.'})
                        skill = request.env['hr.skill'].sudo().browse(skill_id)
                        if not skill.exists():
                            return request.make_json_response({'success': False, 'error': 'Skill not found.'})
                        payload = {
                            '_skill_change': {
                                'cert_action': 'add',
                                'skill_id': skill_id, 'skill_name': skill_name,
                                'level_id': level_id, 'level_name': level_name,
                                'type_id': type_id or skill.skill_type_id.id, 'type_name': type_name,
                            }
                        }
                        pcr = request.env['hr.profile.change.request'].sudo().create({
                            'employee_id': employee.id,
                            'submitted_data': json.dumps(payload),
                            'state': 'draft',
                        })
                        pcr.action_submit()
                        return request.make_json_response({'success': True, 'reference': pcr.name})

                elif action == 'edit_skill':
                    record_id  = int(post.get('skill_record_id', 0) or 0)
                    level_id   = int(post.get('level_id', 0) or 0)
                    level_name = post.get('level_name', '')
                    skill_record = request.env['hr.employee.skill'].sudo().browse(record_id)
                    if not skill_record.exists() or skill_record.employee_id.id != employee.id:
                        return request.make_json_response({'success': False, 'error': 'Record not found.'})
                    payload = {
                        '_skill_change': {
                            'cert_action': 'edit',
                            'skill_record_id': record_id,
                            'skill_name': skill_record.skill_id.name,
                            'type_name': skill_record.skill_type_id.name,
                            'level_id': level_id, 'level_name': level_name,
                        }
                    }
                    pcr = request.env['hr.profile.change.request'].sudo().create({
                        'employee_id': employee.id,
                        'submitted_data': json.dumps(payload),
                        'state': 'draft',
                    })
                    pcr.action_submit()
                    return request.make_json_response({'success': True, 'reference': pcr.name})

                elif action == 'delete_skill':
                    record_id = int(post.get('skill_record_id', 0) or 0)
                    skill_record = request.env['hr.employee.skill'].sudo().browse(record_id)
                    if not skill_record.exists() or skill_record.employee_id.id != employee.id:
                        return request.make_json_response({'success': False, 'error': 'Record not found.'})
                    payload = {
                        '_skill_change': {
                            'cert_action': 'delete',
                            'skill_record_id': record_id,
                            'skill_name': skill_record.skill_id.name,
                            'type_name': skill_record.skill_type_id.name,
                        }
                    }
                    pcr = request.env['hr.profile.change.request'].sudo().create({
                        'employee_id': employee.id,
                        'submitted_data': json.dumps(payload),
                        'state': 'draft',
                    })
                    pcr.action_submit()
                    return request.make_json_response({'success': True, 'reference': pcr.name})

                else:
                    return request.make_json_response({'success': False, 'error': 'Unknown action.'})

            except Exception as e:
                import traceback
                _logger.error("Experience portal error: %s\n%s", str(e), traceback.format_exc())
                return request.make_json_response({'success': False, 'error': str(e)})

        # ── GET ──
        _ensure_sequence_exists(request.env)
        _fix_stuck_pcrs(request.env, employee)

        skill_types = request.env['hr.skill.type'].sudo().search([
            ('is_certification', '=', False)
        ], order='name')

        all_skills = request.env['hr.skill'].sudo().search([
            ('skill_type_id', 'in', skill_types.ids)
        ], order='skill_type_id, name')

        all_levels = request.env['hr.skill.level'].sudo().search([
            ('skill_type_id', 'in', skill_types.ids)
        ], order='skill_type_id, name')

        skill_data = {'skills': {}, 'levels': {}}
        for sk in all_skills:
            tid = str(sk.skill_type_id.id)
            skill_data['skills'].setdefault(tid, [])
            skill_data['skills'][tid].append({'id': str(sk.id), 'name': sk.name})
        for lv in all_levels:
            tid = str(lv.skill_type_id.id)
            skill_data['levels'].setdefault(tid, [])
            skill_data['levels'][tid].append({'id': str(lv.id), 'name': lv.name})

        employee_skills = request.env['hr.employee.skill'].sudo().search([
            ('employee_id', '=', employee.id),
            ('skill_type_id.is_certification', '=', False),
        ], order='skill_type_id, id')

        pending_pcrs = request.env['hr.profile.change.request'].sudo().search([
            ('employee_id', '=', employee.id),
            ('state', '=', 'pending'),
        ], order='create_date desc')

        pending_skill_changes = []
        pending_resume_change = None

        for pcr in pending_pcrs:
            try:
                data = json.loads(pcr.submitted_data or '{}')

                skill_change = data.get('_skill_change')
                if skill_change:
                    action_type = skill_change.get('cert_action', '')
                    if action_type == 'add_batch':
                        for item in skill_change.get('skills', []):
                            pending_skill_changes.append({
                                'pcr_name':    pcr.name,
                                'cert_action': 'add',
                                'type_name':   item.get('type_name', '—'),
                                'skill_name':  item.get('skill_name', '—'),
                                'level_name':  item.get('level_name', '—'),
                            })
                    else:
                        pending_skill_changes.append({
                            'pcr_name':    pcr.name,
                            'cert_action': action_type,
                            'type_name':   skill_change.get('type_name', '—'),
                            'skill_name':  skill_change.get('skill_name', '—'),
                            'level_name':  skill_change.get('level_name', '—'),
                        })

                resume_change = data.get('_resume_change')
                if resume_change and not pending_resume_change:
                    pending_resume_change = {
                        'pcr_name': pcr.name,
                        'filename': resume_change.get('filename', '—'),
                    }
            except Exception:
                continue

        exp_notification = None
        latest_exp_pcr = None
        for _pcr in request.env['hr.profile.change.request'].sudo().search([
            ('employee_id', '=', employee.id),
        ], order='create_date desc', limit=20):
            try:
                _d = json.loads(_pcr.submitted_data or '{}')
                if '_skill_change' in _d or '_resume_change' in _d:
                    latest_exp_pcr = _pcr
                    break
            except Exception:
                pass

        if latest_exp_pcr and latest_exp_pcr.state == 'pending':
            exp_notification = {
                'type': 'warning',
                'message': 'Your skills/resume change is awaiting HR review.',
                'request_name': latest_exp_pcr.name,
            }
        elif latest_exp_pcr and latest_exp_pcr.state == 'approved':
            exp_notification = {
                'type': 'success',
                'message': 'Your skills/resume update has been approved by HR.',
                'request_name': latest_exp_pcr.name,
            }
        elif latest_exp_pcr and latest_exp_pcr.state == 'rejected':
            exp_notification = {
                'type': 'danger',
                'message': 'Your skills/resume update was rejected by HR.',
                'reason': latest_exp_pcr.rejection_reason or 'No reason provided.',
                'request_name': latest_exp_pcr.name,
            }

        return request.render(
            'employee_self_service_portal.portal_employee_profile_experience',
            {
                'employee':              employee,
                'section':               'experience',
                'employee_skills':       employee_skills,
                'skill_types':           skill_types,
                'skill_data_json':       json.dumps(skill_data),
                'pending_skill_changes': pending_skill_changes,
                'pending_resume_change': pending_resume_change,
                'exp_notification':      exp_notification,
            }
        )

    # ─────────────────────────────────────────────────────────────────────────
    # CERTIFICATIONS — GET + POST
    # ─────────────────────────────────────────────────────────────────────────
    @http.route('/my/employee/certification', type='http', auth='user', website=True, methods=['GET', 'POST'])
    def portal_employee_certification(self, **post):
        employee = _get_employee()
        if not employee:
            return request.redirect('/my')

        cert_skill_types = request.env['hr.skill.type'].sudo().search([('name', 'ilike', 'certif')])
        certificate_skills = request.env['hr.skill'].sudo().search([
            ('skill_type_id', 'in', cert_skill_types.ids)
        ], order='name')

        if request.httprequest.method == 'POST':
            return _write_blocked_response()
        if False:
            action = post.get('action')
            try:

                if action == 'batch_certifications':
                    batch_meta_raw = post.get('batch_changes', '')
                    if not batch_meta_raw:
                        return request.make_json_response({'success': False, 'error': 'No changes provided.'})
                    try:
                        batch_changes = json.loads(batch_meta_raw)
                    except Exception:
                        return request.make_json_response({'success': False, 'error': 'Invalid batch data.'})

                    if not batch_changes:
                        return request.make_json_response({'success': False, 'error': 'Empty batch.'})

                    validated_changes = []
                    file_map = {}  # row_id -> (name, data, mime)

                    for item in batch_changes:
                        change_type = item.get('type', '')
                        row_id = str(item.get('rowId', ''))

                        file_key = f'file_{row_id}'
                        file_obj = request.httprequest.files.get(file_key)
                        attachment_name = None
                        attachment_data = None
                        attachment_mime = None
                        if file_obj and file_obj.filename:
                            raw_bytes = file_obj.read()
                            attachment_data = base64.b64encode(raw_bytes).decode()
                            attachment_name = file_obj.filename
                            attachment_mime = file_obj.content_type or 'application/octet-stream'
                            file_map[row_id] = (attachment_name, attachment_data, attachment_mime)

                        if change_type == 'add':
                            skill_id = int(item.get('skillId', 0) or 0)
                            if not skill_id:
                                return request.make_json_response({'success': False, 'error': 'Certificate Name is required for an add change.'})
                            skill = request.env['hr.skill'].sudo().browse(skill_id)
                            if not skill.exists():
                                return request.make_json_response({'success': False, 'error': f'Skill not found: {skill_id}'})
                            validated_changes.append({
                                'type': 'add',
                                'row_id': row_id,
                                'skill_id': skill_id,
                                'skill_name': skill.name,
                                'skill_type_id': skill.skill_type_id.id,
                                'valid_from': item.get('validFrom') or '',
                                'valid_to': item.get('validTo') or '',
                                'has_file': bool(attachment_data),
                                'attachment_name': attachment_name or '',
                            })

                        elif change_type == 'edit':
                            record_id = int(item.get('rowId', 0) or 0)
                            skill_record = request.env['hr.employee.skill'].sudo().browse(record_id)
                            if not skill_record.exists() or skill_record.employee_id.id != employee.id:
                                return request.make_json_response({'success': False, 'error': f'Certification record not found: {record_id}'})
                            validated_changes.append({
                                'type': 'edit',
                                'row_id': row_id,
                                'skill_record_id': record_id,
                                'skill_name': skill_record.skill_id.name,
                                'valid_from': item.get('validFrom') or '',
                                'valid_to': item.get('validTo') or '',
                                'has_file': bool(attachment_data),
                                'attachment_name': attachment_name or '',
                            })

                        elif change_type == 'delete':
                            record_id = int(item.get('rowId', 0) or 0)
                            skill_record = request.env['hr.employee.skill'].sudo().browse(record_id)
                            if not skill_record.exists() or skill_record.employee_id.id != employee.id:
                                return request.make_json_response({'success': False, 'error': f'Certification record not found: {record_id}'})
                            validated_changes.append({
                                'type': 'delete',
                                'row_id': row_id,
                                'skill_record_id': record_id,
                                'skill_name': skill_record.skill_id.name,
                            })

                        else:
                            return request.make_json_response({'success': False, 'error': f'Unknown change type: {change_type}'})

                    if not validated_changes:
                        return request.make_json_response({'success': False, 'error': 'No valid changes to submit.'})

                    pcr = request.env['hr.profile.change.request'].sudo().create({
                        'employee_id': employee.id,
                        'submitted_data': json.dumps({'_cert_batch': {'changes': validated_changes}}),
                        'state': 'draft',
                    })
                    pcr.action_submit()

                    for row_id, (fname, fdata, fmime) in file_map.items():
                        request.env['ir.attachment'].sudo().create({
                            'name': fname,
                            'datas': fdata,
                            'res_model': 'hr.profile.change.request',
                            'res_id': pcr.id,
                            'mimetype': fmime,
                            'description': f'Certification attachment for row {row_id}',
                        })

                    _logger.info(
                        'Cert batch PCR %s created for %s — %d change(s), %d file(s)',
                        pcr.name, employee.name, len(validated_changes), len(file_map),
                    )

                    return request.make_json_response({
                        'success': True,
                        'message': 'Your certification changes have been submitted for HR approval.',
                        'reference': pcr.name,
                    })

                # ── legacy single-action handlers ──
                attachment_data = None
                attachment_name = None
                attachment_mime = None
                attachment_file = request.httprequest.files.get('attachment_file')
                if attachment_file and attachment_file.filename:
                    attachment_data = base64.b64encode(attachment_file.read()).decode()
                    attachment_name = attachment_file.filename
                    attachment_mime = attachment_file.content_type or 'application/octet-stream'

                if action == 'add_certification':
                    skill_id = int(post.get('skill_id', 0) or 0)
                    if not skill_id:
                        return request.make_json_response({'success': False, 'error': 'Certificate Name is required.'})
                    skill = request.env['hr.skill'].sudo().browse(skill_id)
                    if not skill.exists():
                        return request.make_json_response({'success': False, 'error': 'Selected skill not found.'})
                    cert_payload = {
                        'cert_action':     'add',
                        'skill_id':        skill_id,
                        'skill_name':      skill.name,
                        'skill_type_id':   skill.skill_type_id.id,
                        'valid_from':      post.get('valid_from') or '',
                        'valid_to':        post.get('valid_to') or '',
                        'has_attachment':  bool(attachment_data),
                        'attachment_name': attachment_name or '',
                    }
                    if attachment_data:
                        cert_payload['attachment_data'] = attachment_data
                        cert_payload['attachment_mime'] = attachment_mime

                elif action == 'edit_certification':
                    record_id = int(post.get('skill_record_id', 0) or 0)
                    skill_record = request.env['hr.employee.skill'].sudo().browse(record_id)
                    if not skill_record.exists() or skill_record.employee_id.id != employee.id:
                        return request.make_json_response({'success': False, 'error': 'Record not found or access denied.'})
                    cert_payload = {
                        'cert_action':     'edit',
                        'skill_record_id': record_id,
                        'skill_name':      skill_record.skill_id.name,
                        'valid_from':      post.get('valid_from') or '',
                        'valid_to':        post.get('valid_to') or '',
                        'has_attachment':  bool(attachment_data),
                        'attachment_name': attachment_name or '',
                    }
                    if attachment_data:
                        cert_payload['attachment_data'] = attachment_data
                        cert_payload['attachment_mime'] = attachment_mime

                elif action == 'delete_certification':
                    record_id = int(post.get('skill_record_id', 0) or 0)
                    skill_record = request.env['hr.employee.skill'].sudo().browse(record_id)
                    if not skill_record.exists() or skill_record.employee_id.id != employee.id:
                        return request.make_json_response({'success': False, 'error': 'Record not found or access denied.'})
                    cert_payload = {
                        'cert_action':     'delete',
                        'skill_record_id': record_id,
                        'skill_name':      skill_record.skill_id.name,
                    }

                else:
                    return request.make_json_response({'success': False, 'error': 'Unknown action.'})

                pcr = request.env['hr.profile.change.request'].sudo().create({
                    'employee_id':    employee.id,
                    'submitted_data': json.dumps({'_cert_change': cert_payload}),
                    'state':          'draft',
                })
                pcr.action_submit()

                if attachment_data:
                    request.env['ir.attachment'].sudo().create({
                        'name':        attachment_name,
                        'datas':       attachment_data,
                        'res_model':   'hr.profile.change.request',
                        'res_id':      pcr.id,
                        'mimetype':    attachment_mime,
                        'description': 'Certification attachment submitted by employee',
                    })

                return request.make_json_response({
                    'success':   True,
                    'message':   'Your certification change has been submitted for HR approval.',
                    'reference': pcr.name,
                })

            except Exception as e:
                import traceback
                _logger.error("Certification portal error: %s\n%s", str(e), traceback.format_exc())
                return request.make_json_response({'success': False, 'error': str(e)})

        # ── GET ──
        _ensure_sequence_exists(request.env)
        _fix_stuck_pcrs(request.env, employee)

        certifications = request.env['hr.employee.skill'].sudo().search([
            ('employee_id', '=', employee.id),
            ('skill_type_id.name', 'ilike', 'certif'),
        ], order='id desc')

        # ── FIX: Use shared helper — fetches from hr.employee.skill so attachments show ──
        cert_attachments_map = _build_cert_attachments_map(certifications, request.env)

        pending_pcrs = request.env['hr.profile.change.request'].sudo().search([
            ('employee_id', '=', employee.id),
            ('state', '=', 'pending'),
        ], order='id desc')

        pending_cert_changes = _build_pending_cert_changes(pending_pcrs, request.env)

        # Cert tab notification
        cert_notification = None
        latest_cert_pcr = None
        for _pcr in request.env['hr.profile.change.request'].sudo().search([
            ('employee_id', '=', employee.id),
        ], order='create_date desc', limit=20):
            try:
                _d = json.loads(_pcr.submitted_data or '{}')
                if '_cert_change' in _d or '_cert_batch' in _d:
                    latest_cert_pcr = _pcr
                    break
            except Exception:
                pass

        try:
            _latest_data = json.loads(latest_cert_pcr.submitted_data or '{}') if latest_cert_pcr else {}
            _cc = _latest_data.get('_cert_change')
            _cb_raw = _latest_data.get('_cert_batch')
            _cb = _unwrap_cert_batch(_cb_raw)
            if _cc and isinstance(_cc, dict):
                _cert_sname = _cc.get('skill_name', '')
            elif _cb:
                _changes = [c for c in _cb if isinstance(c, dict)]
                _cert_sname = ', '.join(c.get('skill_name', '') for c in _changes[:3])
                if len(_changes) > 3:
                    _cert_sname += f' (+{len(_changes) - 3} more)'
            else:
                _cert_sname = ''
        except Exception:
            _cert_sname = ''

        if latest_cert_pcr and latest_cert_pcr.state == 'pending':
            cert_notification = {
                'type': 'warning',
                'message': 'Your certification change is awaiting HR review.',
                'request_name': latest_cert_pcr.name,
                'skill_name': _cert_sname,
            }
        elif latest_cert_pcr and latest_cert_pcr.state == 'approved':
            cert_notification = {
                'type': 'success',
                'message': 'Your certification update has been approved by HR.',
                'request_name': latest_cert_pcr.name,
                'skill_name': _cert_sname,
            }
        elif latest_cert_pcr and latest_cert_pcr.state == 'rejected':
            cert_notification = {
                'type': 'danger',
                'message': 'Your certification change request was rejected by HR.',
                'reason': latest_cert_pcr.rejection_reason or 'No reason provided.',
                'request_name': latest_cert_pcr.name,
                'skill_name': _cert_sname,
            }

        return request.render(
            'employee_self_service_portal.portal_employee_profile_certification',
            {
                'employee':              employee,
                'section':               'certification',
                'certifications':        certifications,
                'certificate_skills':    certificate_skills,
                'pending_cert_changes':  pending_cert_changes,
                'cert_notification':     cert_notification,
                'cert_attachments_map':  cert_attachments_map,
            }
        )