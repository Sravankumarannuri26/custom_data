 
from odoo import models, api, SUPERUSER_ID
import requests
import logging
from odoo.exceptions import AccessDenied
_logger = logging.getLogger(__name__)

class ResUsers(models.Model):
    # Extend Odoo users model to customize Microsoft Azure SSO authentication
    _inherit = 'res.users'
    def _auth_oauth_validate(self, provider, access_token):
        # Validate Azure access token by fetching user profile from Microsoft Graph API
        headers = {'Authorization': f'Bearer {access_token}'}
        response = requests.get(
            'https://graph.microsoft.com/v1.0/me',
            headers=headers
        )
        if response.status_code != 200:
            raise Exception(f"Microsoft Graph error: {response.text}")
        data = response.json()
        user_id = data.get('id')
        email = data.get('mail') or data.get('userPrincipalName')
        return {
            'sub': user_id,
            'user_id': user_id,
            'id': user_id,
            'email': email,
            'name': data.get('displayName'),
            'login': email,
        }
    @api.model
    def _auth_oauth_signin(self, provider, validation, params):
        # Handle Azure SSO login by validating user existence and linking OAuth credentials
        email = validation.get('email')
        oauth_uid = validation.get('user_id')
 
        if not email:
            raise Exception("Email not provided by Azure AD")
 
        original_login = email.strip()
 
        # 🔹 Variant 1: First letter CAPITAL
        cap_login = original_login[:1].upper() + original_login[1:]
        # 🔹 Variant 2: First letter lowercase
        low_login = original_login[:1].lower() + original_login[1:]
        #  Try both variants
        user = self.sudo().search([('login', '=', cap_login)], limit=1)
        if not user:
            user = self.sudo().search([('login', '=', low_login)], limit=1)
        if not user:
            # Block login if user is not pre-created in Odoo
            _logger.warning("Azure SSO: Login blocked for %s — user not found in Odoo", email)
            raise Exception("Access denied. Your account does not exist in the system. Please contact your administrator.")
        # Link Azure account if not already linked
        if oauth_uid and not user.oauth_uid:
            user.sudo().write({
                'oauth_uid': oauth_uid,
                'oauth_provider_id': provider,
            })
        _logger.info("Azure SSO: Existing user login success: %s", email)
        return super()._auth_oauth_signin(provider, validation, params)

    def _login(self, credential, user_agent_env=None):
        login = credential.get('login')
        if not login:
            return super()._login(credential, user_agent_env=user_agent_env)
        original_login = login.strip()
        # 🔹 Variant 1: First letter CAPITAL
        cap_login = original_login[:1].upper() + original_login[1:]
        # 🔹 Variant 2: First letter lowercase
        low_login = original_login[:1].lower() + original_login[1:]
        tried = []
        #  Try capitalized first
        try:
            _logger.info(" Trying capitalized login: %s", cap_login)
            credential['login'] = cap_login
            return super()._login(credential, user_agent_env=user_agent_env)
        except Exception:
            tried.append(cap_login)
            _logger.warning(" Capitalized login failed")
        #  Then try lowercase
        try:
            _logger.info(" Trying lowercase login: %s", low_login)
            credential['login'] = low_login
            return super()._login(credential, user_agent_env=user_agent_env)
        except Exception:
            tried.append(low_login)
            _logger.error(" Both attempts failed: %s", tried)
            raise AccessDenied()
 
 

        
