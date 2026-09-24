# **Azure AD Integration Module**

Overview
The Azure AD Integration module provides comprehensive integration between Odoo HR and Microsoft Azure Active Directory. This enterprise-grade solution automates employee provisioning, license management, department distribution list synchronization, and employee code generation with seamless two-way synchronization.
Core Purpose
This module transforms standard Odoo HR into a fully integrated identity management system that automatically creates Azure AD accounts, manages Microsoft 365 licenses, synchronizes department distribution lists, and generates standardized employee codes based on business rules - eliminating manual work and ensuring consistency across platforms.

Key Features
1. Automated Azure AD Account Creation
Intelligent Email Generation:

# Automatic Azure AD user creation when employees are added in Odoo

Smart email generation from employee names (e.g., "John Smith" → john.smith@domain.com)
Duplicate detection across both Odoo and Azure AD
Automatic numbering for duplicate names (john.smith2@domain.com)
Case-insensitive uniqueness validation

User Provisioning:

Automatic account creation with initial password (Welcome@123)
Force password change on first login
Usage location set to UAE (AE)
Display name synchronization
Mail nickname generation

Validation & Security:

Pre-creation duplicate checking in both systems
Email format validation
Unique constraint enforcement
Comprehensive error handling and logging

2. Microsoft 365 License Management
License Dashboard:

Real-time license inventory tracking
Total, assigned, and available license counts
SKU ID and license type display
Color-coded availability indicators:

 Red: Less than 5 available (critical)
 Yellow: 5-9 available (warning)
 Green: 10+ available (healthy)


Last sync timestamp

License Assignment:

Manual license assignment through employee form
Automatic availability checking before assignment
License type tracking (Microsoft 365, Office 365, etc.)
Assignment status monitoring
License consumption tracking

License Removal:

Controlled license unassignment process
Automatic account disabling on license removal
Session revocation for security
Verification of account status changes
Comprehensive logging of all operations

Azure Synchronization:

One-click sync from Azure tenant
Fetches all subscribed SKUs
Updates license allocation data
Clears old records before refresh
Success/failure notifications

3. Department Distribution List Integration
Automatic DL Synchronization:

Finds existing distribution lists by department name
Supports both uppercase and lowercase DL naming conventions (DL_Test or DL_test)
Links Odoo departments to Azure AD groups
Stores DL email and group ID

Employee DL Membership:

Automatic addition to department DL on employee creation
Updates DL membership on department changes
Duplicate membership prevention
Removal handling on department change

DL Management:

Manual sync button per department
Auto-sync when employee is assigned to department
Support for naming variations (handles spaces, ampersands)
Clear success/failure messaging

4. Employee Code Generation System
Intelligent Code Generation:

Rule-based prefix assignment based on:

Engagement Location (Onsite/Offshore/Nearshore)
Payroll Location (Dubai Onsite/Dubai Offshore/TCIP India)
Employment Type (Permanent/Temporary/Bootcamp/Seconded/Freelancer)



Code Prefix Logic:

P: Onsite/Nearshore + Dubai Onsite + Permanent (P0001, P0002...)
T: Multiple scenarios for Temporary employees
TCIP: Offshore + TCIP India + Permanent (TCIP0001, TCIP0012...)
BC: Bootcamp + Onsite/Nearshore + Dubai Onsite
BCO: Bootcamp + Offshore + Dubai Offshore
BCI: Bootcamp + Offshore + TCIP India
PT: Seconded employees
TFL: Freelancer employees
EMP: Fallback for unmatched combinations

Wizard Interface:

User-friendly wizard for code generation
Real-time preview of generated code
Classification field selection
Validation before generation
Automatic employee record update

Bulk Operations:

Generate codes for multiple employees at once
Validates all employees have required fields
Sequential number assignment
Progress tracking and reporting
Error handling for incomplete records

Code Management:

Unique code enforcement
Automatic synchronization to emp_code field
Prevents duplicate code generation
Read-only after generation
Comprehensive logging

5. Extended Employee Information
Language Management:

Mother tongue tracking
Multiple language proficiency (many2many)
Language selection from system languages

Additional Fields:

Total IT experience
Alternate mobile numbers (2 additional fields)
Place of birth
First, Middle, Last name components


Integration Architecture
Azure AD Graph API Integration
Authentication:

OAuth 2.0 client credentials flow
Tenant-specific authentication
Secure token management
30-second timeout protection

API Endpoints Used:

/v1.0/users - User creation and management
/v1.0/users/{id} - User updates and status
/v1.0/users/{id}/assignLicense - License operations
/v1.0/users/{id}/revokeSignInSessions - Session management
/v1.0/subscribedSkus - License inventory
/v1.0/groups - Distribution list management
/v1.0/groups/{id}/members - DL membership

Required Permissions:

User.ReadWrite.All
Group.ReadWrite.All
Directory.ReadWrite.All

System Parameters Configuration
Required configuration in Settings → Technical → Parameters → System Parameters:
azure_tenant_id: Your Azure AD tenant ID
azure_client_id: Application (client) ID
azure_client_secret: Client secret value
azure_domain: Your email domain (e.g., techcarrot.ae)
azure_license_sku: License SKU ID for assignment

Automated Workflows
Employee Onboarding Flow

Employee Created in Odoo

HR creates employee record with name and department


Azure Account Creation

System generates unique email
Checks duplicates in Odoo and Azure
Creates Azure AD user account
Stores user ID and email in Odoo


Department DL Sync (if needed)

Checks if department has linked DL
If not, searches for DL in Azure
Links department to DL group


## DL Membership

Adds employee to department DL
Prevents duplicate additions
Logs all operations


## License Assignment (manual)

HR reviews available licenses
Assigns license through employee form
System verifies availability
Updates license tracking



Employee Offboarding Flow

License Removal Initiated

HR clicks "Unassign License" button
System confirms action


License Unassignment

Removes Microsoft 365 license
Handles "already removed" gracefully


Session Revocation

Revokes all active user sessions
Forces immediate logout


## Account Disable

Sets accountEnabled = false
Prevents future logins
Verifies account status


Record Update

Updates Odoo license status
Clears license name
Logs completion



## Department Change Flow

Department Updated

HR changes employee department


DL Membership Update

Automatically syncs new department DL if needed
Adds employee to new department DL
(Note: Manual removal from old DL required in Azure)




User Interface Components
License Management Dashboard
Location: Azure AD → License Management
Features:

List view of all license types
Color-coded availability warnings
SKU identification
Last sync timestamp
No manual creation/editing (read-only)

Employee Form Enhancements
Azure AD Info Tab:

Azure account details (email, user ID)
License status and name
Quick action buttons:

Assign License
Unassign License (with disable warning)
View in Azure Portal
View All Licenses


### Availability warnings

Employee Code Section:

Display of generated code
"Generate Employee Code" button (visible when no code exists)
Classification fields (Engagement, Payroll, Employment Type)

Language Information:

Mother tongue selection
Known languages (multi-select tags)

Department Form Additions
Distribution List Section:

"Sync DL from Azure" button in header
Azure DL email (read-only)
Azure DL ID (admin only)
Auto-sync status

Wizards
Employee Code Generation Wizard:

Employee name display
Classification field selection
Real-time code preview
Generate/Cancel buttons
Validation before creation