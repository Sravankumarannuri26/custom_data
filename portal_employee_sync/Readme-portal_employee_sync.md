### Portal Employee Sync Module

OverviewThe Portal Employee Sync module provides a robust REST API integration that enables external systems (primarily SharePoint) to create and update employee records in Odoo HR. This module serves as a bridge between external employee data sources and Odoo, supporting comprehensive employee data synchronization with intelligent field mapping, data validation, and automated record management.Core PurposeThis module transforms Odoo into an API-enabled HR system that can receive employee data from external portals, automatically process complex data structures (including SharePoint JSON objects), intelligently map fields, create related records (departments, jobs, relationships), and maintain synchronization timestamps - all while ensuring data integrity through extensive validation and error handling.Key Features1. REST API Employee EndpointAPI Endpoint:

POST /odoo/api/employeesAuthentication:

API Key-based authentication via HTTP header
Secure key verification: api-key: a7cf0c4f99a71e9f63c60fda3aa32c0ecba87669
Public endpoint with authorization control
CSRF protection disabled for external integrations
CORS enabled for cross-origin requests
Request Format:

Content-Type: application/json
Method: POST
Required Header: api-key: <your-api-key>
Supported Operations:

Create new employees
Update existing employees (matched by name)
Automatic duplicate detection and handling

2. Intelligent Data ProcessingSharePoint JSON Object Handling:

Automatically detects SharePoint JSON objects: {"Value": "actual_data"}
Extracts values from nested structures
Supports both Value and value key variations
Falls back to raw string if parsing fails
Handles string, dictionary, and complex object types
Data Extraction Logic:
python# Handles all these formats:
- Plain string: "John Doe"
- SharePoint JSON string: '{"Value": "John Doe"}'
- Dictionary object: {"Value": "John Doe"}
- Mixed structures with null/empty valuesField Mapping:
The module intelligently maps 60+ fields from external systems to Odoo HR fields, including:

Personal information (name, email, phone, addresses)
Employment details (department, job title, employment type)
Identification documents (passport, employee code)
Contact information (emergency contacts, references)
Educational background (degrees, institutes, scores)
Work history (previous company, manager details)
Classification (engagement, payroll, employment type)
Dates (birthday, passport expiry, degree completion)
Relationships and emergency contacts


3. Language Management IntegrationMother Tongue Tracking:

Maps language names to res.lang records
Supports multiple language name formats
Intelligent language code mapping
Handles common language variations
Multiple Languages Known:

Processes comma-separated language lists
Maps each language to res.lang table
Uses Many2many relationship (language_known_ids)
Comprehensive language lookup with fallbacks
Language Search Strategy:

Exact code match (e.g., 'en_US')
Language mapping (e.g., 'English' → 'en_US')
Exact name match (case-insensitive)
Partial name match
ISO code match

# ... and more4. Automated Record CreationDepartment Auto-Creation:

Searches for existing department by name
Creates new department if not found
Returns department ID for employee assignment
Handles null/empty department names gracefully
Job Position Auto-Creation:

Searches for existing job by name
Creates new job position if not found
Links job to employee record
Supports dynamic job creation from external data
Employee Relationship Creation:

Creates relationship types on-demand
Uses employee.relationship model
Handles missing model gracefully
Supports emergency contact relationships


5. Geographic Data ManagementCountry Mapping:

Exact code match priority (IN, AE, US)
Case-insensitive name matching
Partial name matching as fallback
Supports multiple country fields:

Main country (country_id)
Private address country (private_country_id)
Passport issue country (issue_countries_id)


State/Province Mapping:

Country-specific state lookup
Partial name matching
Validates state belongs to correct country
Handles missing state data


6. Date and Data Type HandlingFlexible Date Parsing:
Supports multiple date formats:

ISO 8601: 2024-01-30T10:30:00.000Z
ISO Date: 2024-01-30
DD-MM-YYYY: 30-01-2024
MM/DD/YYYY: 01/30/2024
DD/MM/YYYY: 30/01/2024
YYYY/MM/DD: 2024/01/30
Date Fields Supported:

Birthday
Passport issue and expiry dates
Degree start and completion dates
Leave dates
Document expiry dates
Numeric Field Handling:

Salary conversion to float
Graceful handling of invalid numbers
Null/empty value management


7. Comprehensive Field CoveragePersonal Information:

Full name (first, middle, last)
Email (work and private)
Phone numbers (mobile, private, alternate × 2)
Place of birth
Gender (male/female/other)
Marital status (single/married/cohabitant/widower/divorced)
Employment Details:

Employee code (from external system)
Department
Job title
Engagement location (onsite/offshore/nearshore)
Payroll location (Dubai Onsite/Dubai Offshore/TCIP India)
Employment type (permanent/temporary/bootcamp/seconded/freelancer)
Total IT experience
Last location
Address Information:

Current address (full text)
Private street, city, zip
Private state and country
Private phone
Identification Documents:

Passport ID
Passport issue and expiry dates
Issue country
Employee code
Emergency Contacts:

Primary emergency contact (name, phone)
Secondary emergency contact (name, phone)
Relationship tracking
Previous Employment:

Last organization name
Period in company
Notice period
Reason for leaving
Last salary (per annum)
Last reporting manager details:

Name
Designation
Email
Mobile number


References:

Industry reference name
Industry reference email
Industry reference mobile
Education:

Degree certificate legal name
Degree name
Institute name
Score/percentage
Start and completion dates
Skills:

Primary skill
Secondary skill
Special Fields:

Relationship with employee
Second relationship with employee (conditional)


8. Sync Tracking and MonitoringPortal Sync Fields:

employee_code: Code from external portal
portal_sync_date: Last synchronization timestamp
Automatic timestamp update on sync
Indexed employee_code for fast lookups
User Interface Integration:

Portal sync information in HR Settings tab
Employee code searchable in employee list
Sync date visible in tree view (optional)
Employee code visible in tree view


9. Error Handling and LoggingComprehensive Logging:

Request data logging (full JSON payload)
Step-by-step operation logging
Language processing diagnostics
Field existence validation
Many2many operation verification
Success/failure tracking
Log Categories:

Success indicators
 Warnings for missing data
 Errors with full stack traces
 Data summaries
 Diagnostic information
Error Recovery:

Transaction rollback on failure
Graceful handling of missing fields
Continue processing on optional field errors
Clear error messages in API response
Validation Checks:

Required field validation (name)
API key verification
Field existence checking
Data type validation
Duplicate detection