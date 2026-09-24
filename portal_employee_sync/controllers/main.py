from odoo import http
from odoo.http import request
import json
import logging
from datetime import datetime

_logger = logging.getLogger(__name__)


class PortalEmployeeSyncController(http.Controller):

    def _verify_api_key(self, api_key):
        if not api_key:
            _logger.warning("API key missing from header!")
            return False
        return True

    def _get_api_key_from_request(self):
        return request.httprequest.headers.get('api-key', '')

    def _val(self, value):
        if not value:
            return None
        if isinstance(value, str) and value.startswith('{'):
            try:
                if '"Value"' in value or '"value"' in value:
                    parsed = json.loads(value)
                    value = parsed.get('Value') or parsed.get('value')
            except:
                pass
        if isinstance(value, dict):
            value = value.get('Value') or value.get('value')
        if value is None:
            return None
        value = str(value).strip()
        return value if value else None

    def _normalize_engagement_location(self, value):
        if not value:
            return None
        raw = str(value).lower().strip()
        clean = raw.replace('-', '').replace('_', '').replace(' ', '')
        if clean == 'onsite':
            return 'onsite'
        elif clean == 'offshore':
            return 'offshore'
        elif clean == 'nearshore':
            return 'near-shore'
        else:
            raise ValueError(
                f"Invalid engagement_location: '{value}'. "
                f"Must be one of: onsite, offshore, nearshore"
            )

    def _normalize_payroll_location(self, value):
        if not value:
            return None
        raw = str(value).lower().strip()
        clean = raw.replace('_', '-').replace(' ', '-')
        if 'dubai' in clean and 'onsite' in clean:
            return 'dubai-onsite'
        elif 'dubai' in clean and 'offshore' in clean:
            return 'dubai-offshore'
        elif 'tcip' in clean or 'india' in clean:
            return 'tcip-india'
        else:
            raise ValueError(
                f"Invalid payroll_location: '{value}'. "
                f"Must be one of: dubai-onsite, dubai-offshore, tcip-india"
            )

    def _normalize_employment_type(self, value):
        if not value:
            return None
        raw = str(value).lower().strip()
        valid_types = {
            'permanent': 'permanent', 'temporary': 'temporary',
            'bootcamp': 'bootcamp', 'seconded': 'seconded',
            'freelancer': 'freelancer', 'temp': 'temporary', 'perm': 'permanent',
        }
        if raw in valid_types:
            return valid_types[raw]
        else:
            raise ValueError(
                f"Invalid employment_type: '{value}'. "
                f"Must be one of: permanent, temporary, bootcamp, seconded, freelancer"
            )

    def _parse_date(self, value):
        value = self._val(value)
        if not value:
            return None
        formats = [
            '%Y-%m-%d', '%d-%m-%Y', '%m/%d/%Y', '%d/%m/%Y', '%Y/%m/%d',
            '%Y-%m-%dT%H:%M:%S.%fZ', '%Y-%m-%dT%H:%M:%SZ'
        ]
        for fmt in formats:
            try:
                return datetime.strptime(value, fmt).date()
            except:
                pass
        return None

    def _find_country(self, name):
        name = self._val(name)
        if not name:
            return None
        country = request.env['res.country'].sudo().search([('code', '=', name.upper())], limit=1)
        if country:
            return country
        country = request.env['res.country'].sudo().search([('name', '=ilike', name)], limit=1)
        if country:
            return country
        return request.env['res.country'].sudo().search([('name', 'ilike', name)], limit=1, order='name')

    def _find_state(self, name, country_id=None):
        name = self._val(name)
        if not name:
            return None
        domain = [('name', 'ilike', name)]
        if country_id:
            domain.append(('country_id', '=', country_id))
        return request.env['res.country.state'].sudo().search(domain, limit=1)

    def _find_language_in_res_lang(self, name):
        name = self._val(name)
        if not name:
            return None
        language_map = {
            'english': 'en_US', 'hindi': 'hi_IN', 'telugu': 'te_IN', 'tamil': 'ta_IN',
            'kannada': 'kn_IN', 'malayalam': 'ml_IN', 'marathi': 'mr_IN', 'bengali': 'bn_IN',
            'gujarati': 'gu_IN', 'punjabi': 'pa_IN', 'urdu': 'ur_IN', 'arabic': 'ar_001',
            'french': 'fr_FR', 'german': 'de_DE', 'spanish': 'es_ES', 'chinese': 'zh_CN',
            'japanese': 'ja_JP',
        }
        lang = request.env['res.lang'].sudo().search([('code', '=', name)], limit=1)
        if lang:
            return lang
        if name.lower() in language_map:
            code = language_map[name.lower()]
            lang = request.env['res.lang'].sudo().search([('code', '=', code)], limit=1)
            if lang:
                return lang
        lang = request.env['res.lang'].sudo().search([('name', '=ilike', name)], limit=1)
        if lang:
            return lang
        return request.env['res.lang'].sudo().search([('name', 'ilike', name)], limit=1)

    def _get_or_create_department(self, name):
        name = self._val(name)
        if not name:
            return False
        dept = request.env['hr.department'].sudo().search([('name', '=', name)], limit=1)
        return dept.id if dept else request.env['hr.department'].sudo().create({'name': name}).id

    def _get_or_create_job(self, name):
        name = self._val(name)
        if not name:
            return False
        job = request.env['hr.job'].sudo().search([('name', '=', name)], limit=1)
        return job.id if job else request.env['hr.job'].sudo().create({'name': name}).id

    def _get_or_create_relationship(self, name):
        name = self._val(name)
        if not name:
            return False
        try:
            Relationship = request.env['employee.relationship'].sudo()
            rel = Relationship.search([('name', '=', name)], limit=1)
            if not rel:
                rel = Relationship.create({'name': name})
            return rel.id
        except:
            return False

    def _find_employee(self, name):
        name = self._val(name)
        if not name:
            return None
        return request.env['hr.employee'].sudo().search([('name', '=ilike', name)], limit=1)

    def _get_company_from_address(self, current_address):
        if not current_address:
            return None
        address = str(current_address).lower().strip()
        india_keywords = ['india', 'hyderabad', 'bangalore', 'mumbai', 'delhi',
                          'chennai', 'pune', 'kolkata', 'noida', 'gurugram']
        uae_keywords = ['dubai', 'uae', 'abu dhabi', 'sharjah', 'ajman',
                        'united arab emirates', 'abudhabi']
        for keyword in india_keywords:
            if keyword in address:
                company = request.env['res.company'].sudo().search(
                    [('name', '=', 'techcarrot India Private Limited')], limit=1)
                if company:
                    return company.id
                break
        for keyword in uae_keywords:
            if keyword in address:
                company = request.env['res.company'].sudo().search(
                    [('name', '=', 'techcarrot FZ-LLC')], limit=1)
                if company:
                    return company.id
                break
        return None

    def _get_company_from_payroll_location(self, payroll_location):
        if not payroll_location:
            company = request.env['res.company'].sudo().search(
                [('name', '=', 'techcarrot FZ-LLC')], limit=1)
            return company.id if company else False
        location = str(payroll_location).lower().strip()
        if 'india' in location:
            company = request.env['res.company'].sudo().search(
                [('name', '=', 'techcarrot India Private Limited')], limit=1)
            return company.id if company else False
        else:
            company = request.env['res.company'].sudo().search(
                [('name', '=', 'techcarrot FZ-LLC')], limit=1)
            return company.id if company else False

    def _json_response(self, data, status=200):
        return request.make_response(
            json.dumps(data, indent=2),
            headers=[
                ('Content-Type', 'application/json'),
                ('Access-Control-Allow-Origin', '*'),
            ],
            status=status
        )

    # ══════════════════════════════════════════════════════════════
    # ROUTE 1: Create/Update Employee (from SharePoint full sync)
    # ══════════════════════════════════════════════════════════════
    @http.route('/odoo/api/employees', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def create_employee(self, **kwargs):
        admin_user = request.env.ref('base.user_admin')
        request.update_env(user=admin_user.id)

        try:
            api_key = self._get_api_key_from_request()
            if not self._verify_api_key(api_key):
                return self._json_response({'success': False, 'error': 'Invalid API key'}, 401)

            data = json.loads(request.httprequest.data or "{}")
            _logger.info(f" API Request: {json.dumps(data, indent=2)}")

            if not self._val(data.get('name')):
                return self._json_response({'success': False, 'error': 'Name is required'}, 400)

            Employee = request.env['hr.employee']
            employee = Employee.search([('name', '=', self._val(data.get('name')))], limit=1)

            engagement_location_raw = self._val(data.get('engagement_location'))
            payroll_location_raw = self._val(data.get('payroll_location'))
            employment_type_raw = self._val(data.get('employment_type'))
            emp_code_from_sharepoint = self._val(data.get('emp_code'))

            try:
                engagement_location_normalized = self._normalize_engagement_location(engagement_location_raw)
                payroll_location_normalized = self._normalize_payroll_location(payroll_location_raw)
                employment_type_normalized = self._normalize_employment_type(employment_type_raw)
            except ValueError as e:
                error_response = {
                    'success': False, 'error': str(e),
                    'invalid_data': {
                        'engagement_location': engagement_location_raw,
                        'payroll_location': payroll_location_raw,
                        'employment_type': employment_type_raw
                    }
                }
                return self._json_response(error_response, 400)

            vals = {
                'name': self._val(data.get('name')),
                'work_email': self._val(data.get('email')),
                'mobile_phone': self._val(data.get('phone')),
                'total_it_experience': self._val(data.get('total_it_experience')),
                'alternate_mobile_number': self._val(data.get('alternate_mobile_number')),
                'second_alternative_number': self._val(data.get('second_alternative_number')),
                'last_location': self._val(data.get('last_location')),
                'department_id': self._get_or_create_department(data.get('department')),
                'job_id': self._get_or_create_job(data.get('job_title')),
                'employee_first_name': self._val(data.get('employee_first_name')),
                'employee_middle_name': self._val(data.get('employee_middle_name')),
                'employee_last_name': self._val(data.get('employee_last_name')),
                'private_email': self._val(data.get('private_email')),
                'place_of_birth': self._val(data.get('place_of_birth')),
                'passport_id': self._val(data.get('passport_id')),
                'primary_skill': self._val(data.get('primary_skill')),
                'secondary_skill': self._val(data.get('secondary_skill')),
                'last_organisation_name': self._val(data.get('last_organisation_name')),
                'current_address': self._val(data.get('current_address')),
                'notice_period': self._val(data.get('notice_period')),
                'reason_for_leaving': self._val(data.get('reason_for_leaving')),
                'emergency_contact_person_name': self._val(data.get('emergency_contact_person_name')),
                'emergency_contact_person_phone': self._val(data.get('emergency_contact_person_phone')),
                'emergency_contact_person_name_1': self._val(data.get('emergency_contact_person_name_1')),
                'emergency_contact_person_phone_1': self._val(data.get('emergency_contact_person_phone_1')),
                'last_report_manager_name': self._val(data.get('last_report_manager_name')),
                'last_report_manager_designation': self._val(data.get('last_report_manager_designation')),
                'last_report_manager_mail': self._val(data.get('last_report_manager_mail')),
                'last_report_manager_mob_no': self._val(data.get('last_report_manager_mob_no')),
                'industry_ref_name': self._val(data.get('industry_ref_name')),
                'industry_ref_email': self._val(data.get('industry_ref_email')),
                'industry_ref_mob_no': self._val(data.get('industry_ref_mob_no')),
                'degree_certificate_legal': self._val(data.get('degree_certificate_legal')),
                'degree_name': self._val(data.get('degree_name')),
                'institute_name': self._val(data.get('institute_name')),
                'score': self._val(data.get('score')),
                'period_in_company': self._val(data.get('period_in_company')),
            }

            current_address_val = self._val(data.get('current_address'))
            company_id = self._get_company_from_payroll_location(payroll_location_raw)
            if company_id:
                vals['company_id'] = company_id

            if emp_code_from_sharepoint:
                vals['emp_code'] = emp_code_from_sharepoint
            if engagement_location_normalized:
                vals['engagement_location'] = engagement_location_normalized
            if payroll_location_normalized:
                vals['payroll_location'] = payroll_location_normalized
            if employment_type_normalized:
                vals['employment_type'] = employment_type_normalized

            line_manager = self._find_employee(data.get('line_manager'))
            if line_manager:
                vals['line_manager_id'] = line_manager.id

            second_relation_value = self._val(data.get('second_relation_with_employee'))
            if second_relation_value:
                vals['second_relation_with_employee'] = second_relation_value
                if second_relation_value == 'Father':
                    vals['father_name'] = self._val(data.get('emergency_contact_person_1'))
                elif second_relation_value == 'Mother':
                    vals['mother_name'] = self._val(data.get('emergency_contact_person_1'))

            if self._val(data.get('private_street')):
                vals['private_street'] = self._val(data.get('private_street'))
            if self._val(data.get('private_city')):
                vals['private_city'] = self._val(data.get('private_city'))
            if self._val(data.get('private_zip')):
                vals['private_zip'] = self._val(data.get('private_zip'))
            if self._val(data.get('private_phone')):
                vals['private_phone'] = self._val(data.get('private_phone'))

            relationship_id = self._get_or_create_relationship(data.get('relationship_with_emp_id'))
            if relationship_id:
                vals['relationship_with_emp_id'] = relationship_id
                if relationship_id == '1':
                    vals['father_name'] = self._val(data.get('emergency_contact_person'))

            if self._val(data.get('sex')):
                sex_value = self._val(data.get('sex')).lower()
                if sex_value in ['male', 'female', 'other']:
                    vals['sex'] = sex_value

            if self._val(data.get('marital')):
                marital_value = self._val(data.get('marital')).lower()
                if marital_value in ['single', 'married', 'cohabitant', 'widower', 'divorced']:
                    vals['marital'] = marital_value

            vals.update({
                'birthday': self._parse_date(data.get('birthday')),
                'issue_date': self._parse_date(data.get('issue_date')),
                'passport_expiration_date': self._parse_date(data.get('passport_expiration_date')),
                'leave_date_from': self._parse_date(data.get('leave_date_from')),
                'start_date_of_degree': self._parse_date(data.get('start_date_of_degree')),
                'completion_date_of_degree': self._parse_date(data.get('completion_date_of_degree')),
                'expiry_date': self._parse_date(data.get('passport_expiration_date')),
            })

            try:
                salary = self._val(data.get('last_salary_per_annum_amt'))
                if salary:
                    vals['last_salary_per_annum_amt'] = float(salary)
            except:
                pass

            country = self._find_country(data.get('country_id'))
            if country:
                vals['country_id'] = country.id

            private_country = self._find_country(data.get('private_country_id'))
            if private_country:
                vals['private_country_id'] = private_country.id

            issue_country = self._find_country(data.get('issue_countries_id'))
            if issue_country:
                vals['issue_countries_id'] = issue_country.id

            private_state = self._find_state(data.get('private_state_id'),
                                             private_country.id if private_country else None)
            if private_state:
                vals['private_state_id'] = private_state.id

            mother_tongue = self._find_language_in_res_lang(data.get('mother_tongue_id'))
            if mother_tongue:
                vals['mother_tongue_id'] = mother_tongue.id

            langs_raw_data = (
                data.get('language_known_ids') or data.get('names') or
                data.get('languages') or data.get('language_known')
            )
            langs_raw = self._val(langs_raw_data)
            language_ids_to_set = []
            if langs_raw:
                lang_names = [name.strip() for name in langs_raw.split(',') if name.strip()]
                for name in lang_names:
                    lang_obj = self._find_language_in_res_lang(name)
                    if lang_obj:
                        language_ids_to_set.append(lang_obj.id)

            if employee:
                _logger.info(f" UPDATING: {employee.name} (ID: {employee.id})")
                employee.write(vals)
                action = "updated"
            else:
                _logger.info(f" CREATING new employee")
                employee = Employee.with_context(auto_generate_code=False).create(vals)
                action = "created"

            if language_ids_to_set:
                try:
                    employee.write({'language_known_ids': [(6, 0, language_ids_to_set)]})
                    employee.invalidate_cache(['language_known_ids'])
                except Exception as e:
                    _logger.error(f" Language error: {e}")

            response_data = {
                'success': True, 'action': action,
                'employee_id': employee.id, 'name': employee.name,
                'email': employee.work_email or '', 'emp_code': employee.emp_code or '',
                'normalized_fields': {
                    'engagement_location': employee.engagement_location,
                    'payroll_location': employee.payroll_location,
                    'employment_type': employee.employment_type
                }
            }
            return self._json_response(response_data)

        except Exception as e:
            _logger.error(f" ERROR: {str(e)}", exc_info=True)
            try:
                request.env.cr.rollback()
            except:
                pass
            return self._json_response({'success': False, 'error': str(e)}, 500)

    # ══════════════════════════════════════════════════════════════
    # ROUTE 2: Get/Update Employee (Power Automate → Odoo)
    # ══════════════════════════════════════════════════════════════
    @http.route('/techcarrot/api/employees', type='json', auth='none', methods=['POST'], csrf=False, cors='*')
    def get_employee(self, **kwargs):
        try:
            api_key = self._get_api_key_from_request()
            if not self._verify_api_key(api_key):
                return {'success': False, 'error': 'Invalid API key'}

            action = kwargs.get('action', 'get')


            admin_user = request.env.ref('base.user_admin')
            request.update_env(user=admin_user.id)

            # ── UPDATE ──
            if action == 'update':
                email = kwargs.get('email', '').strip()
                new_emp_code = kwargs.get('new_emp_code', '').strip()
                fields = kwargs.get('fields', {})

                if not email:
                    return {'success': False, 'error': 'email is required'}

                employee = request.env['hr.employee'].with_user(admin_user).search(
                    [('work_email', '=ilike', email), ('active', '=', True)], limit=1
                )
                if not employee:
                    return {'success': False, 'error': f'No employee found: {email}'}

                current_emp_code = employee.emp_code or ''
                update_vals = {}

                if fields.get('employee_first_name'):
                    update_vals['employee_first_name'] = fields['employee_first_name']
                if fields.get('employee_last_name'):
                    update_vals['employee_last_name'] = fields['employee_last_name']
                if fields.get('employee_middle_name') is not None:
                    update_vals['employee_middle_name'] = fields['employee_middle_name']
                if fields.get('work_email'):
                    update_vals['work_email'] = fields['work_email']
                if fields.get('mobile_phone'):
                    update_vals['mobile_phone'] = fields['mobile_phone']
                if fields.get('private_email'):
                    update_vals['private_email'] = fields['private_email']
                if fields.get('private_phone'):
                    update_vals['private_phone'] = fields['private_phone']
                if fields.get('passport_id'):
                    update_vals['passport_id'] = fields['passport_id']
                if fields.get('passport_expiry'):
                    update_vals['passport_expiration_date'] = self._parse_date(fields['passport_expiry'])
                if fields.get('birthday'):
                    update_vals['birthday'] = self._parse_date(fields['birthday'])
                if fields.get('place_of_birth'):
                    update_vals['place_of_birth'] = fields['place_of_birth']
                if fields.get('sex'):
                    update_vals['sex'] = fields['sex'].lower()
                if fields.get('marital'):
                    update_vals['marital'] = fields['marital'].lower()
                if fields.get('department'):
                    dept_id = self._get_or_create_department(fields['department'])
                    if dept_id:
                        update_vals['department_id'] = dept_id
                if fields.get('job_title'):
                    job_id = self._get_or_create_job(fields['job_title'])
                    if job_id:
                        update_vals['job_id'] = job_id
                if fields.get('employment_type'):
                    try:
                        normalized = self._normalize_employment_type(fields['employment_type'])
                        if normalized:
                            update_vals['employment_type'] = normalized
                    except ValueError:
                        pass
                if fields.get('engagement_location'):
                    try:
                        normalized = self._normalize_engagement_location(fields['engagement_location'])
                        if normalized:
                            update_vals['engagement_location'] = normalized
                    except ValueError:
                        pass
                if fields.get('payroll_location'):
                    try:
                        normalized = self._normalize_payroll_location(fields['payroll_location'])
                        if normalized:
                            update_vals['payroll_location'] = normalized
                    except ValueError:
                        pass
                if fields.get('nationality'):
                    country = self._find_country(fields['nationality'])
                    if country:
                        update_vals['country_id'] = country.id
                if fields.get('primary_skill'):
                    update_vals['primary_skill'] = fields['primary_skill']
                if fields.get('secondary_skill'):
                    update_vals['secondary_skill'] = fields['secondary_skill']

                # ── Emp code changed → archive old, create new ──
                if new_emp_code and new_emp_code != current_emp_code:
                    _logger.info("Emp code changed: %s → %s", current_emp_code, new_emp_code)

                    # ══════════════════════════════════════════════════════
                    # STEP 1: Extract all field IDs safely BEFORE anything
                    # ══════════════════════════════════════════════════════
                    try:
                        parent_id = employee.parent_id.id if employee.parent_id else False
                    except Exception:
                        parent_id = False
                    try:
                        dept_id = employee.department_id.id if employee.department_id else False
                    except Exception:
                        dept_id = False
                    try:
                        job_id = employee.job_id.id if employee.job_id else False
                    except Exception:
                        job_id = False
                    try:
                        company_id = employee.company_id.id if employee.company_id else False
                    except Exception:
                        company_id = False
                    try:
                        country_id = employee.country_id.id if employee.country_id else False
                    except Exception:
                        country_id = False
                    try:
                        private_country_id = employee.private_country_id.id if employee.private_country_id else False
                    except Exception:
                        private_country_id = False
                    try:
                        private_state_id = employee.private_state_id.id if employee.private_state_id else False
                    except Exception:
                        private_state_id = False
                    try:
                        mother_tongue_id = employee.mother_tongue_id.id if employee.mother_tongue_id else False
                    except Exception:
                        mother_tongue_id = False
                    try:
                        issue_countries_id = employee.issue_countries_id.id if employee.issue_countries_id else False
                    except Exception:
                        issue_countries_id = False
                    try:
                        language_ids = employee.language_known_ids.ids if employee.language_known_ids else []
                    except Exception:
                        language_ids = []

                    # ══════════════════════════════════════════════════════
                    # STEP 2: Save old_email, old_user_id, original_email
                    # original_email = what new employee + res.users must have
                    # ══════════════════════════════════════════════════════
                    old_email = employee.work_email or ''
                    old_user_id = employee.user_id.id if employee.user_id else False
                    original_email = update_vals.get('work_email', old_email)
                    _logger.info("✓ old_email='%s', old_user_id=%s, original_email='%s'",
                                 old_email, old_user_id, original_email)

                    # ══════════════════════════════════════════════════════
                    # STEP 3: Detach user from OLD employee only
                    # Never touch res.users groups or email here
                    # ══════════════════════════════════════════════════════
                    if old_user_id:
                        try:
                            employee.with_user(admin_user).write({'user_id': False})
                            _logger.info("✓ User (ID: %s) detached from old employee (%s)",
                                         old_user_id, current_emp_code)
                        except Exception as e:
                            _logger.warning("Could not detach user: %s", str(e))

                    # ══════════════════════════════════════════════════════
                    # STEP 4: Archive old employee
                    #

                    # ══════════════════════════════════════════════════════
                    archived_email = f"{current_emp_code}_{old_email}" if old_email else old_email
                    admin_env = request.env(user=admin_user.id)
                    try:
                        admin_env['hr.employee'].browse(employee.id).write({
                            'active': True,
                            'work_email': archived_email,
                            'work_contact_id': False,
                        })
                        _logger.info("✓ Old employee (%s) kept ACTIVE with renamed email: %s",
                                     current_emp_code, archived_email)
                    except Exception as e:
                        _logger.warning("STEP 4 write failed: %s", str(e))
                        raise

                    # ══════════════════════════════════════════════════════
                    # STEP 5: Build new_vals — work_email = original_email
                    # ══════════════════════════════════════════════════════
                    new_vals = {
                        'user_id': False,
                        'emp_code': new_emp_code,
                        'active': True,

                        'employee_first_name': update_vals.get('employee_first_name', employee.employee_first_name),
                        'employee_middle_name': update_vals.get('employee_middle_name', employee.employee_middle_name),
                        'employee_last_name': update_vals.get('employee_last_name', employee.employee_last_name),
                        'name': (
                            (update_vals.get('employee_first_name') or employee.employee_first_name or '') + ' ' +
                            (update_vals.get('employee_last_name') or employee.employee_last_name or '')
                        ).strip() or employee.name,

                        # ALWAYS original_email — never archived email
                        'work_email': original_email,
                        'mobile_phone': update_vals.get('mobile_phone', employee.mobile_phone),
                        'alternate_mobile_number': employee.alternate_mobile_number,
                        'second_alternative_number': employee.second_alternative_number,
                        'private_email': update_vals.get('private_email', employee.private_email),
                        'private_phone': update_vals.get('private_phone', employee.private_phone),

                        'department_id': update_vals.get('department_id', dept_id),
                        'job_id': update_vals.get('job_id', job_id),
                        'employment_type': update_vals.get('employment_type', employee.employment_type),
                        'engagement_location': update_vals.get('engagement_location', employee.engagement_location),
                        'payroll_location': update_vals.get('payroll_location', employee.payroll_location),
                        'company_id': company_id,
                        # 'parent_id': parent_id,
                        'total_it_experience': employee.total_it_experience,
                        'last_location': employee.last_location,

                        'sex': update_vals.get('sex', employee.sex),
                        'marital': update_vals.get('marital', employee.marital),
                        'birthday': update_vals.get('birthday', employee.birthday),
                        'place_of_birth': update_vals.get('place_of_birth', employee.place_of_birth),
                        'country_id': update_vals.get('country_id', country_id),
                        'private_country_id': private_country_id,
                        'private_state_id': private_state_id,
                        'private_street': employee.private_street,
                        'private_city': employee.private_city,
                        'private_zip': employee.private_zip,
                        'mother_tongue_id': mother_tongue_id,

                        'passport_id': update_vals.get('passport_id', employee.passport_id),
                        'passport_expiration_date': update_vals.get('passport_expiration_date',
                                                                    employee.passport_expiration_date),
                        'issue_date': employee.issue_date,
                        'expiry_date': employee.expiry_date,
                        'issue_countries_id': issue_countries_id,

                        'primary_skill': update_vals.get('primary_skill', employee.primary_skill),
                        'secondary_skill': update_vals.get('secondary_skill', employee.secondary_skill),

                        'last_organisation_name': employee.last_organisation_name,
                        'last_salary_per_annum_amt': employee.last_salary_per_annum_amt,
                        'reason_for_leaving': employee.reason_for_leaving,
                        'notice_period': employee.notice_period,
                        'last_report_manager_name': employee.last_report_manager_name,
                        'last_report_manager_designation': employee.last_report_manager_designation,
                        'last_report_manager_mail': employee.last_report_manager_mail,
                        'last_report_manager_mob_no': employee.last_report_manager_mob_no,

                        'emergency_contact_person_name': employee.emergency_contact_person_name,
                        'emergency_contact_person_phone': employee.emergency_contact_person_phone,
                        'emergency_contact_person_name_1': employee.emergency_contact_person_name_1,
                        'emergency_contact_person_phone_1': employee.emergency_contact_person_phone_1,

                        'degree_name': employee.degree_name,
                        'institute_name': employee.institute_name,
                        'score': employee.score,
                        'start_date_of_degree': employee.start_date_of_degree,
                        'completion_date_of_degree': employee.completion_date_of_degree,
                        'degree_certificate_legal': employee.degree_certificate_legal,

                        'industry_ref_name': employee.industry_ref_name,
                        'industry_ref_email': employee.industry_ref_email,
                        'industry_ref_mob_no': employee.industry_ref_mob_no,
                    }

                    # ══════════════════════════════════════════════════════
                    # STEP 6: CREATE new employee
                    # ══════════════════════════════════════════════════════
                    new_emp = request.env['hr.employee'].with_user(admin_user).with_context(
                        auto_generate_code=False,
                        no_check_ids=True,
                        tracking_disable=True,
                        mail_notrack=True,
                        mail_create_nolog=True,
                    ).create(new_vals)
                    _logger.info("✓ New employee created — ID: %s, emp_code: %s, work_email: %s",
                                 new_emp.id, new_emp_code, new_emp.work_email)

                    try:

                        old_emp_admin = admin_env['hr.employee'].browse(employee.id)
                        if old_emp_admin.image_1920:
                            new_emp.with_user(admin_user).write({
                                'image_1920': old_emp_admin.image_1920,
                            })
                            _logger.info("✓ Employee image copied to new employee (ID: %s)", new_emp.id)
                        else:
                            _logger.info("No image on old employee to copy")
                    except Exception as e:
                        _logger.warning("Image copy failed: %s", str(e))

                    # ══════════════════════════════════════════════════════
                    # STEP 7: Restore res.users email, then link to new emp
                    # ══════════════════════════════════════════════════════
                    if old_user_id:
                        try:
                            # A: Restore res.users login/email to original_email
                            request.env['res.users'].with_user(admin_user).browse(old_user_id).write({
                                'login': original_email,
                                'email': original_email,
                            })
                            _logger.info("✓ res.users restored to: %s", original_email)

                            # B: Link portal user to new employee
                            new_emp.with_user(admin_user).write({'user_id': old_user_id})
                            _logger.info("✓ Portal user (ID: %s) linked to new employee (ID: %s)",
                                         old_user_id, new_emp.id)

                            # C: Safety — if new_emp work_email drifted, reset it
                            if new_emp.work_email != original_email:
                                _logger.warning("new_emp.work_email drifted to '%s', resetting",
                                                new_emp.work_email)
                                new_emp.with_user(admin_user).write({'work_email': original_email})

                        except Exception as e:
                            _logger.warning("Could not link portal user: %s", str(e))

                    _logger.info("✓ FINAL — old emp work_email=%s | new emp work_email=%s",
                                 employee.work_email, new_emp.work_email)

                    # ── Copy salary attachments ──
                    try:
                        salary_attachments = request.env['hr.salary.attachment'].with_user(admin_user).search(
                            [('employee_id', '=', employee.id)]
                        )
                        for att in salary_attachments:
                            att_data = att.copy_data()[0]
                            att_data['employee_id'] = new_emp.id
                            request.env['hr.salary.attachment'].with_user(admin_user).create(att_data)
                        _logger.info("✓ Salary attachments copied: %s", len(salary_attachments))
                    except Exception as e:
                        _logger.warning("Salary attachment copy failed: %s", str(e))

                    # ── Copy contracts ──
                    try:
                        contracts = request.env['hr.contract'].with_user(admin_user).search(
                            [('employee_id', '=', employee.id)]
                        )
                        for contract in contracts:
                            contract_data = contract.copy_data()[0]
                            contract_data['employee_id'] = new_emp.id
                            contract_data['state'] = 'draft'
                            request.env['hr.contract'].with_user(admin_user).create(contract_data)
                        _logger.info("✓ Contracts copied: %s", len(contracts))
                    except Exception as e:
                        _logger.warning("Contract copy failed: %s", str(e))

                    # ── Copy languages ──
                    if language_ids:
                        try:
                            new_emp.with_user(admin_user).write({
                                'language_known_ids': [(6, 0, language_ids)]
                            })
                            _logger.info("✓ Languages copied to new employee")
                        except Exception as lang_err:
                            _logger.warning("Language copy failed: %s", str(lang_err))

                    _logger.info("✓ Done — old (%s) archived, new (%s) created ID=%s",
                                 current_emp_code, new_emp_code, new_emp.id)

                    return {
                        'success': True,
                        'action': 'archived_and_created',
                        'old_emp_code': current_emp_code,
                        'new_employee_id': new_emp.id,
                        'new_emp_code': new_emp_code,
                        'message': f'Old employee ({current_emp_code}) archived. New employee ({new_emp_code}) created.',
                    }

                else:
                    if new_emp_code:
                        update_vals['emp_code'] = new_emp_code
                    employee.with_user(admin_user).write(update_vals)
                    return {
                        'success': True,
                        'action': 'updated',
                        'employee_id': employee.id,
                        'emp_code': employee.emp_code,
                        'updated_fields': list(update_vals.keys()),
                        'message': 'Employee updated successfully.',
                    }

            # ── GET (default) ──
            email = kwargs.get('email', '').strip()
            if not email:
                return {'success': False, 'error': 'email is required'}

            employee = request.env['hr.employee'].with_user(admin_user).search(
                [('work_email', '=ilike', email), ('active', '=', True)], limit=1
            )
            if not employee:
                return {'success': False, 'error': f'No active employee found: {email}'}

            return {
                'success': True,
                'employee_id': employee.id,
                'active': employee.active,
                'name': employee.name or '',
                'emp_code': employee.emp_code or '',
                'work_email': employee.work_email or '',
                'mobile_phone': employee.mobile_phone or '',
                'employee_first_name': employee.employee_first_name or '',
                'employee_middle_name': employee.employee_middle_name or '',
                'employee_last_name': employee.employee_last_name or '',
                'employment_type': employee.employment_type or '',
                'engagement_location': employee.engagement_location or '',
                'payroll_location': employee.payroll_location or '',
                'department': employee.department_id.name if employee.department_id else '',
                'job_title': employee.job_id.name if employee.job_id else '',
                'company': employee.company_id.name if employee.company_id else '',
                'sex': employee.sex or '',
                'marital': employee.marital or '',
                'birthday': str(employee.birthday) if employee.birthday else '',
                'place_of_birth': employee.place_of_birth or '',
                'private_email': employee.private_email or '',
                'private_phone': employee.private_phone or '',
                'private_street': employee.private_street or '',
                'private_city': employee.private_city or '',
                'private_zip': employee.private_zip or '',
                'private_country': employee.private_country_id.name if employee.private_country_id else '',
                'private_state': employee.private_state_id.name if employee.private_state_id else '',
                'mother_tongue': employee.mother_tongue_id.name if employee.mother_tongue_id else '',
                'languages_known': ', '.join(
                    employee.language_known_ids.mapped('name')) if employee.language_known_ids else '',
                'nationality': employee.country_id.name if employee.country_id else '',
                'passport_id': employee.passport_id or '',
                'passport_expiry': str(employee.passport_expiration_date) if employee.passport_expiration_date else '',
                'primary_skill': employee.primary_skill or '',
                'secondary_skill': employee.secondary_skill or '',
                'emergency_contact_person_name': employee.emergency_contact_person_name or '',
                'emergency_contact_person_phone': employee.emergency_contact_person_phone or '',
                'emergency_contact_person_name_1': employee.emergency_contact_person_name_1 or '',
                'emergency_contact_person_phone_1': employee.emergency_contact_person_phone_1 or '',
                'last_organisation_name': employee.last_organisation_name or '',
                'last_location': employee.last_location or '',
                'last_salary_per_annum_amt': employee.last_salary_per_annum_amt or 0,
                'reason_for_leaving': employee.reason_for_leaving or '',
                'notice_period': employee.notice_period or '',
                'last_report_manager_name': employee.last_report_manager_name or '',
                'last_report_manager_designation': employee.last_report_manager_designation or '',
                'last_report_manager_mail': employee.last_report_manager_mail or '',
                'last_report_manager_mob_no': employee.last_report_manager_mob_no or '',
                'degree_name': employee.degree_name or '',
                'institute_name': employee.institute_name or '',
                'start_date_of_degree': str(employee.start_date_of_degree) if employee.start_date_of_degree else '',
                'completion_date_of_degree': str(
                    employee.completion_date_of_degree) if employee.completion_date_of_degree else '',
                'score': employee.score or '',
                'industry_ref_name': employee.industry_ref_name or '',
                'industry_ref_email': employee.industry_ref_email or '',
                'industry_ref_mob_no': employee.industry_ref_mob_no or '',
            }

        except Exception as e:
            _logger.error("Employee API error: %s", str(e), exc_info=True)
            return {'success': False, 'error': str(e)}