import requests
import json
import logging
from odoo import models, fields, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class HREmployee(models.Model):
    _inherit = 'hr.employee'

    azure_email = fields.Char("Azure Email", readonly=True)
    azure_user_id = fields.Char("Azure User ID", readonly=True)
    azure_license_assigned = fields.Boolean("License Assigned", default=False, readonly=True)
    azure_license_name = fields.Char("License Name", readonly=True)

    employee_first_name = fields.Char("First Name")
    employee_middle_name = fields.Char("Middle Name")
    employee_last_name = fields.Char("Last Name")
    place_of_birth = fields.Char("Place of Birth")
    mother_tongue_id = fields.Many2one('res.lang', ondelete='set null', string="Mother Tongue")
    language_known_ids = fields.Many2many(
        'res.lang',
        'employee_language_rel',
        'employee_id',
        'lang_id',
        string="Languages Known"
    )

    total_it_experience = fields.Char("Total IT Experience")
    alternate_mobile_number = fields.Char("Alternate Mobile Number")
    second_alternative_number = fields.Char("Second Alternative Number")

    # sharepoint_employee_id = fields.Char(
    #     "SharePoint Employee ID",
    #     readonly=True,
    #     index=True,
    #     help="Unique identifier from SharePoint"
    # )

    @api.model_create_multi
    def create(self, vals_list):
        """Automatically runs when employee is created"""

        # VALIDATE work_email for duplicates BEFORE creating
        for vals in vals_list:
            if vals.get('work_email'):
                self._validate_work_email(vals.get('work_email'))

        employees = super().create(vals_list)

        for emp in employees:
            if emp.name:
                # Step 1: Create Azure user
                emp._create_azure_email()

                # Step 2: Add to department DL automatically
                if emp.department_id and emp.azure_user_id:
                    emp._sync_dept_and_add_to_dl()

        return employees

    def write(self, vals):
        """Monitor department changes and validate email changes"""

        # VALIDATE work_email if it's being changed
        if 'work_email' in vals and vals['work_email']:
            for emp in self:
                emp._validate_work_email(vals['work_email'], exclude_id=emp.id)

        result = super().write(vals)

        # If department changed, update DL membership automatically
        if 'department_id' in vals:
            for emp in self:
                if emp.azure_user_id and emp.department_id:
                    emp._sync_dept_and_add_to_dl()

        return result

    def _validate_work_email(self, email, exclude_id=None):
        """Validate that work_email doesn't already exist"""
        if not email:
            return

        domain = [('work_email', '=', email.strip().lower())]
        if exclude_id:
            domain.append(('id', '!=', exclude_id))

        existing = self.env['hr.employee'].search(domain, limit=1)

        if existing:
            raise UserError(
                f" Email Already Exists!\n\n"
                f"The email '{email}' is already assigned to:\n"
                f"  • Employee: {existing.name}\n"
                f"  • Department: {existing.department_id.name if existing.department_id else 'N/A'}\n"
                f"  • Job Position: {existing.job_id.name if existing.job_id else 'N/A'}\n\n"
                f"Please use a different email address."
            )

    def _sync_dept_and_add_to_dl(self):
        """Sync department DL if needed, then add employee - FULLY AUTOMATIC"""
        self.ensure_one()

        _logger.info(f"=" * 80)
        _logger.info(f" Starting _sync_dept_and_add_to_dl for {self.name}")
        _logger.info(f"   Employee ID: {self.id}")
        _logger.info(f"   Azure User ID: {self.azure_user_id}")
        _logger.info(f"   Department: {self.department_id.name if self.department_id else 'None'}")
        _logger.info(f"   Department ID: {self.department_id.id if self.department_id else 'None'}")

        if not self.department_id:
            _logger.warning(f" No department for {self.name}")
            return

        if not self.azure_user_id:
            _logger.warning(f" No Azure User ID for {self.name}")
            return

        dept = self.department_id

        _logger.info(f" Current Department State:")
        _logger.info(f"   Name: {dept.name}")
        _logger.info(f"   DL ID: {dept.azure_dl_id}")
        _logger.info(f"   DL Email: {dept.azure_dl_email}")

        # If department has no DL configured, try to sync it automatically
        if not dept.azure_dl_id:
            _logger.info(f" Department '{dept.name}' has no DL, attempting auto-sync...")

            # Call sync
            sync_result = dept.action_sync_dl_from_azure()
            _logger.info(f"   Sync result: {sync_result}")

            # CRITICAL FIX: Invalidate cache AND re-browse to get fresh data
            dept.invalidate_recordset(['azure_dl_id', 'azure_dl_email'])

            # Re-browse the department record from database
            dept = self.env['hr.department'].browse(dept.id)

            # Log the values after refresh
            _logger.info(f" After sync - DL ID: {dept.azure_dl_id}")
            _logger.info(f" After sync - DL Email: {dept.azure_dl_email}")

            if not dept.azure_dl_id:
                _logger.warning(f" Could not sync DL for department '{dept.name}'")
                _logger.warning(f"   Please create DL_{dept.name}@techcarrot.ae in Azure")
                return
        else:
            _logger.info(f" Department already has DL configured")

        # If DL is now configured, add employee
        if dept.azure_dl_id:
            _logger.info(f" Department '{dept.name}' linked to {dept.azure_dl_email}")
            _logger.info(f"   DL ID: {dept.azure_dl_id}")
            _logger.info(f"   Employee: {self.name}")
            _logger.info(f"   User ID: {self.azure_user_id}")

            # Add employee to DL
            _logger.info(f" Calling _add_to_dept_dl()...")
            try:
                self._add_to_dept_dl()
                _logger.info(f" _add_to_dept_dl() completed")
            except Exception as e:
                _logger.error(f" Exception in _add_to_dept_dl(): {e}")
                import traceback
                _logger.error(traceback.format_exc())
        else:
            _logger.error(f" Department '{dept.name}' has no DL configured after sync")
            _logger.error(f"   DL ID is still: {dept.azure_dl_id}")
            _logger.error(f"   DL Email is still: {dept.azure_dl_email}")

        _logger.info(f" Finished _sync_dept_and_add_to_dl for {self.name}")
        _logger.info(f"=" * 80)

    def _create_azure_email(self):
        """Create unique email in Azure AD"""
        self.ensure_one()

        IrConfig = self.env['ir.config_parameter'].sudo()

        tenant_id = IrConfig.get_param("azure_tenant_id")
        client_id = IrConfig.get_param("azure_client_id")
        client_secret = IrConfig.get_param("azure_client_secret")
        domain = IrConfig.get_param("azure_domain")

        if not all([tenant_id, client_id, client_secret, domain]):
            _logger.error(" Azure credentials missing in System Parameters!")
            return

        try:
            # Generate base email from name
            parts = self.name.strip().lower().replace('!', '').split()  # Remove special chars
            first = parts[0]
            last = parts[-1] if len(parts) > 1 else first
            base = f"{first}.{last}"

            _logger.info(f" Processing: {self.name} → base: {base}")

            # Get Azure AD token
            token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
            token_data = {
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
                "scope": "https://graph.microsoft.com/.default"
            }

            token_response = requests.post(token_url, data=token_data, timeout=30)
            token_response.raise_for_status()
            token = token_response.json().get("access_token")

            if not token:
                _logger.error(" Failed to get access token")
                return

            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }

            # NEW: Check for unique email in BOTH Odoo AND Azure
            count = 1
            unique_email = f"{base}@{domain}"

            while count < 100:
                _logger.info(f" Trying: {unique_email}")

                # Check 1: Odoo database
                existing_in_odoo = self.env['hr.employee'].search([
                    ('azure_email', '=', unique_email),
                    ('id', '!=', self.id)
                ], limit=1)

                if existing_in_odoo:
                    _logger.warning(f" {unique_email} exists in Odoo ({existing_in_odoo.name})")
                    count += 1
                    unique_email = f"{base}{count}@{domain}"
                    continue  # Try next number

                # Check 2: Azure AD
                check_url = f"https://graph.microsoft.com/v1.0/users/{unique_email}"
                check = requests.get(check_url, headers=headers, timeout=30)

                if check.status_code == 404:
                    _logger.info(f" ✓ Email available: {unique_email}")
                    break  # Found unique email!

                elif check.status_code == 200:
                    existing_user = check.json()
                    existing_display_name = existing_user.get('displayName')
                    _logger.warning(f" {unique_email} exists in Azure ({existing_display_name})")

                    count += 1
                    unique_email = f"{base}{count}@{domain}"

                else:
                    _logger.error(f" Error checking email: {check.status_code}")
                    return

            # Create user in Azure AD with the unique email
            payload = {
                "accountEnabled": True,
                "displayName": self.name,
                "mailNickname": unique_email.split('@')[0],
                "userPrincipalName": unique_email,
                "usageLocation": "AE",
                "passwordProfile": {
                    "forceChangePasswordNextSignIn": True,
                    "password": "Welcome@123"
                }
            }

            create_url = "https://graph.microsoft.com/v1.0/users"
            create_response = requests.post(
                create_url,
                headers=headers,
                data=json.dumps(payload),
                timeout=30
            )

            if create_response.status_code == 201:
                user_data = create_response.json()
                self.write({
                    'azure_email': unique_email,
                    'work_email': unique_email,
                    'azure_user_id': user_data.get("id")
                })
                _logger.info(f" ✓ Created: {unique_email} | ID: {self.azure_user_id}")
            else:
                error = create_response.json().get('error', {}).get('message', 'Unknown')
                _logger.error(f" Failed to create user: {error}")

        except UserError:
            raise
        except Exception as e:
            _logger.error(f" Exception: {str(e)}")

    # ... (rest of your methods remain exactly the same)

    def _check_and_assign_license(self):
        """Check if license already assigned, then assign if needed"""
        self.ensure_one()

        if not self.azure_user_id:
            _logger.error(f" No Azure User ID for {self.name}")
            return False

        params = self.env['ir.config_parameter'].sudo()
        tenant = params.get_param("azure_tenant_id")
        client = params.get_param("azure_client_id")
        secret = params.get_param("azure_client_secret")
        license_sku = params.get_param("azure_license_sku")

        if not license_sku:
            _logger.warning(" No license SKU configured")
            return False

        try:
            # Get token
            token_resp = requests.post(
                f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": client,
                    "client_secret": secret,
                    "scope": "https://graph.microsoft.com/.default"
                },
                timeout=30
            ).json()

            token = token_resp.get("access_token")
            if not token:
                _logger.error(" No token for license check")
                return False

            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }

            # Check if user already has license in Azure
            check_url = f"https://graph.microsoft.com/v1.0/users/{self.azure_user_id}/licenseDetails"
            check_response = requests.get(check_url, headers=headers, timeout=30)

            if check_response.status_code == 200:
                existing_licenses = check_response.json().get('value', [])
                for lic in existing_licenses:
                    if lic.get('skuId') == license_sku:
                        license_name = lic.get('skuPartNumber', 'Microsoft 365')
                        self.write({
                            'azure_license_assigned': True,
                            'azure_license_name': license_name
                        })
                        _logger.info(f" {self.name} already has license: {license_name}")
                        return True

            # License not found, assign it
            _logger.info(f" Assigning license to {self.name}...")

            # Re-enable account if it was disabled (NEW CODE)
            enable_payload = {"accountEnabled": True}
            enable_response = requests.patch(
                f"https://graph.microsoft.com/v1.0/users/{self.azure_user_id}",
                headers=headers,
                json=enable_payload,
                timeout=30
            )

            if enable_response.status_code == 200:
                _logger.info(f" Account enabled for {self.name}")
            else:
                _logger.warning(f" Could not enable account (may already be enabled)")

            license_payload = {
                "addLicenses": [{
                    "skuId": license_sku,
                    "disabledPlans": []
                }],
                "removeLicenses": []
            }

            license_response = requests.post(
                f"https://graph.microsoft.com/v1.0/users/{self.azure_user_id}/assignLicense",
                headers=headers,
                json=license_payload,
                timeout=30
            )

            if license_response.status_code == 200:
                # Get license name
                sku_response = requests.get(
                    f"https://graph.microsoft.com/v1.0/subscribedSkus",
                    headers=headers,
                    timeout=30
                )

                license_name = "Microsoft 365"
                if sku_response.status_code == 200:
                    skus = sku_response.json().get('value', [])
                    for sku in skus:
                        if sku.get('skuId') == license_sku:
                            license_name = sku.get('skuPartNumber', 'Microsoft 365')
                            break

                self.write({
                    'azure_license_assigned': True,
                    'azure_license_name': license_name
                })
                _logger.info(f" License assigned: {license_name}")
                return True
            else:
                error_data = license_response.json().get('error', {})
                error_msg = error_data.get('message', 'Unknown')

                if 'already' in error_msg.lower():
                    _logger.info(f" License already assigned")
                    self.write({'azure_license_assigned': True})
                    return True

                _logger.error(f" License assignment failed: {error_msg}")
                return False

        except Exception as e:
            _logger.error(f" License check failed: {e}")
            return False

    def _add_to_dept_dl(self):
        """Add employee to department DL - WITH DUPLICATE PREVENTION"""
        self.ensure_one()

        if not self.department_id or not self.azure_user_id:
            _logger.warning(f" Missing dept or user_id for {self.name}")
            return

        dept = self.department_id

        if not dept.azure_dl_id:
            _logger.error(f" Department '{dept.name}' has no DL configured")
            return

        _logger.info(f" Starting DL addition for {self.name}")
        _logger.info(f"   Department: {dept.name}")
        _logger.info(f"   DL Email: {dept.azure_dl_email}")
        _logger.info(f"   DL ID: {dept.azure_dl_id}")
        _logger.info(f"   User ID: {self.azure_user_id}")

        try:
            params = self.env['ir.config_parameter'].sudo()
            tenant = params.get_param("azure_tenant_id")
            client = params.get_param("azure_client_id")
            secret = params.get_param("azure_client_secret")

            token_resp = requests.post(
                f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": client,
                    "client_secret": secret,
                    "scope": "https://graph.microsoft.com/.default"
                },
                timeout=30
            ).json()

            token = token_resp.get("access_token")
            if not token:
                _logger.error(" Failed to get token for DL addition")
                return

            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }

            # Check if already a member
            check_url = f"https://graph.microsoft.com/v1.0/groups/{dept.azure_dl_id}/members/{self.azure_user_id}"
            _logger.info(f" Checking membership: {check_url}")
            check_response = requests.get(check_url, headers=headers, timeout=30)

            if check_response.status_code == 200:
                _logger.info(f" {self.name} already in {dept.azure_dl_email}")
                return
            elif check_response.status_code == 404:
                _logger.info(f" User not in DL, will add now")
            else:
                _logger.warning(f" Unexpected status checking membership: {check_response.status_code}")

            # Not a member, add them
            _logger.info(f" Adding {self.name} to {dept.azure_dl_email}...")

            add_payload = {"@odata.id": f"https://graph.microsoft.com/v1.0/users/{self.azure_user_id}"}
            add_url = f"https://graph.microsoft.com/v1.0/groups/{dept.azure_dl_id}/members/$ref"

            _logger.info(f" POST {add_url}")
            _logger.info(f" Payload: {json.dumps(add_payload)}")

            add_response = requests.post(
                add_url,
                headers=headers,
                json=add_payload,
                timeout=30
            )

            _logger.info(f" Response Status: {add_response.status_code}")

            if add_response.status_code == 204:
                _logger.info(f" Successfully added {self.name} to {dept.azure_dl_email}")
            elif add_response.status_code == 400:
                error = add_response.json().get('error', {})
                error_msg = error.get('message', 'Unknown')
                if 'already exist' in error_msg.lower():
                    _logger.info(f" {self.name} already in {dept.azure_dl_email}")
                else:
                    _logger.error(f" Failed to add: {error_msg}")
                    _logger.error(f"   Full error: {json.dumps(error)}")
            else:
                _logger.error(f" Failed: HTTP {add_response.status_code}")
                try:
                    error_detail = add_response.json()
                    _logger.error(f"   Error details: {json.dumps(error_detail)}")
                except:
                    _logger.error(f"   Response text: {add_response.text}")

        except Exception as e:
            _logger.error(f" DL addition failed: {e}")
            import traceback
            _logger.error(traceback.format_exc())

    def action_view_azure_user(self):
        """Open Azure AD user page"""
        self.ensure_one()
        if self.azure_user_id:
            return {
                'type': 'ir.actions.act_url',
                'url': f'https://portal.azure.com/#view/Microsoft_AAD_UsersAndTenants/UserProfileMenuBlade/~/overview/userId/{self.azure_user_id}',
                'target': 'new',
            }

    def action_unassign_license(self):
        """Button to unassign license from employee"""
        self.ensure_one()

        if not self.azure_user_id:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': 'No Azure user found',
                    'type': 'warning',
                }
            }

        if not self.azure_license_assigned:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': 'No license to unassign',
                    'type': 'info',
                }
            }

        result = self._unassign_azure_license()

        if result:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': f'License unassigned and account disabled for {self.name}',
                    'type': 'success',
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': 'Failed to unassign license',
                    'type': 'danger',
                }
            }

    def _unassign_azure_license(self):
        """Unassign license, disable account, and verify the changes"""
        self.ensure_one()

        if not self.azure_user_id:
            _logger.error(f" No Azure User ID for {self.name}")
            return False

        params = self.env['ir.config_parameter'].sudo()
        tenant = params.get_param("azure_tenant_id")
        client = params.get_param("azure_client_id")
        secret = params.get_param("azure_client_secret")
        license_sku = params.get_param("azure_license_sku")

        if not license_sku:
            _logger.warning(" No license SKU configured")
            return False

        try:
            # Get token
            token_resp = requests.post(
                f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": client,
                    "client_secret": secret,
                    "scope": "https://graph.microsoft.com/.default"
                },
                timeout=30
            )

            if token_resp.status_code != 200:
                _logger.error(f" Failed to get token: {token_resp.text}")
                return False

            token = token_resp.json().get("access_token")
            if not token:
                _logger.error(" No access token in response")
                return False

            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }

            _logger.info(f"{'=' * 80}")
            _logger.info(f" Starting license removal and account disable for {self.name}")
            _logger.info(f"   User ID: {self.azure_user_id}")
            _logger.info(f"{'=' * 80}")

            # STEP 1: Check current account status
            _logger.info(f" Checking current account status...")
            check_url = f"https://graph.microsoft.com/v1.0/users/{self.azure_user_id}?$select=accountEnabled,displayName,userPrincipalName"
            check_response = requests.get(check_url, headers=headers, timeout=30)

            if check_response.status_code == 200:
                current_status = check_response.json()
                current_enabled = current_status.get('accountEnabled', 'Unknown')
                _logger.info(f"   Current accountEnabled: {current_enabled}")
                _logger.info(f"   Display Name: {current_status.get('displayName')}")
                _logger.info(f"   Email: {current_status.get('userPrincipalName')}")
            else:
                _logger.error(f" Cannot check user status: {check_response.status_code}")

            # STEP 2: Remove the license (if it exists)
            _logger.info(f" Step 1/3: Removing license...")

            license_payload = {
                "addLicenses": [],
                "removeLicenses": [license_sku]
            }

            license_response = requests.post(
                f"https://graph.microsoft.com/v1.0/users/{self.azure_user_id}/assignLicense",
                headers=headers,
                json=license_payload,
                timeout=30
            )

            if license_response.status_code == 200:
                _logger.info(f" License removed successfully")
            else:
                error_data = license_response.json().get('error', {})
                error_msg = error_data.get('message', 'Unknown')
                error_code = error_data.get('code', 'Unknown')

                # If user doesn't have a license, that's okay - continue
                if 'does not have a corresponding license' in error_msg:
                    _logger.info(f" User doesn't have a license (already removed or never had one)")
                else:
                    _logger.error(f" Failed to remove license: [{error_code}] {error_msg}")

            # STEP 3: Revoke all sessions
            _logger.info(f" Step 2/3: Revoking all active sessions...")

            revoke_response = requests.post(
                f"https://graph.microsoft.com/v1.0/users/{self.azure_user_id}/revokeSignInSessions",
                headers=headers,
                timeout=30
            )

            if revoke_response.status_code == 200 or revoke_response.status_code == 204:
                _logger.info(f" Sessions revoked successfully")
            else:
                _logger.warning(f" Could not revoke sessions: {revoke_response.status_code}")

            # STEP 4: Disable the account (CRITICAL)
            _logger.info(f" Step 3/3: Disabling account...")

            disable_payload = {
                "accountEnabled": False
            }

            disable_url = f"https://graph.microsoft.com/v1.0/users/{self.azure_user_id}"
            _logger.info(f"   PATCH URL: {disable_url}")
            _logger.info(f"   Payload: {json.dumps(disable_payload)}")

            disable_response = requests.patch(
                disable_url,
                headers=headers,
                json=disable_payload,
                timeout=30
            )

            _logger.info(f"   Response Status: {disable_response.status_code}")

            if disable_response.status_code == 200 or disable_response.status_code == 204:
                _logger.info(f"Account disable request sent successfully (HTTP {disable_response.status_code})")
            else:
                error_data = disable_response.json().get('error', {}) if disable_response.text else {}
                error_msg = error_data.get('message', 'Unknown')
                error_code = error_data.get('code', 'Unknown')
                _logger.error(f" Failed to disable account: [{error_code}] {error_msg}")
                _logger.error(f"   Full error response: {disable_response.text}")

                if 'Insufficient privileges' in error_msg or 'Authorization_RequestDenied' in error_code:
                    _logger.error(f" PERMISSION ISSUE!")
                    _logger.error(f"   Add 'User.ReadWrite.All' permission in Azure Portal")

                return False

            # STEP 5: Verify the changes with explicit field selection
            _logger.info(f" Verifying account status...")
            import time
            time.sleep(3)  # Wait 3 seconds for Azure to process

            # Request with explicit $select to ensure we get accountEnabled field
            verify_url = f"https://graph.microsoft.com/v1.0/users/{self.azure_user_id}?$select=accountEnabled,displayName,userPrincipalName"
            verify_response = requests.get(verify_url, headers=headers, timeout=30)

            if verify_response.status_code == 200:
                verified_status = verify_response.json()
                is_enabled = verified_status.get('accountEnabled')

                _logger.info(f"   Full verification response: {json.dumps(verified_status, indent=2)}")
                _logger.info(f"   Verified accountEnabled: {is_enabled}")

                if is_enabled is False:
                    _logger.info(f" ACCOUNT SUCCESSFULLY DISABLED ")
                    _logger.info(f"   User '{self.name}' can NO LONGER log in to Microsoft services")
                elif is_enabled is True:
                    _logger.error(f" ACCOUNT STILL ENABLED ")
                    _logger.error(f"   The disable operation did not work!")
                    _logger.error(f"   User can still log in - this is a critical issue!")
                    return False
                elif is_enabled is None:
                    # Sometimes Azure doesn't return the field immediately
                    _logger.warning(f" accountEnabled field is None/missing from response")
                    _logger.warning(f"   This can happen if the field wasn't returned by Azure API")
                    _logger.warning(f"   Assuming success since HTTP 204 was returned")
                    _logger.info(f" Treating as success (API returned 204)")
            else:
                _logger.warning(f" Could not verify account status: HTTP {verify_response.status_code}")
                _logger.warning(f"   But disable API returned 204, so assuming success")

            # Update Odoo record
            self.write({
                'azure_license_assigned': False,
                'azure_license_name': False
            })

            _logger.info(f"{'=' * 80}")
            _logger.info(f" PROCESS COMPLETED for {self.name}")
            _logger.info(f"   - License removed (or wasn't assigned)")
            _logger.info(f"   - Sessions revoked")
            _logger.info(f"   - Account disabled (HTTP 204 received)")
            _logger.info(f"{'=' * 80}")

            return True

        except Exception as e:
            _logger.error(f" EXCEPTION OCCURRED: {e}")
            import traceback
            _logger.error(f"Full traceback:\n{traceback.format_exc()}")
            return False

    def action_assign_license(self):
        """Button to manually assign license to employee"""
        self.ensure_one()

        if not self.azure_user_id:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': 'No Azure user found',
                    'type': 'warning',
                }
            }

        if self.azure_license_assigned:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': 'License already assigned',
                    'type': 'info',
                }
            }

        # Check if licenses are available
        license_config = self.env['azure.license.config'].search([
            ('available_licenses', '>', 0)
        ], limit=1)

        if not license_config:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': ' No licenses available! Please purchase more licenses or unassign from other users.',
                    'type': 'warning',
                    'sticky': True
                }
            }

        result = self._check_and_assign_license()

        if result:
            # Refresh license count
            self.env['azure.license.config'].search([]).action_sync_licenses_from_azure()

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': f' License assigned to {self.name}',
                    'type': 'success',
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': 'Failed to assign license',
                    'type': 'danger',
                }
            }