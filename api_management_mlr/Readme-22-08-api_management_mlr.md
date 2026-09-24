# API Management Base (MLR)

**Module Name:** API Management Base  
**Version:** 18.1  
**Category:** Technical  
**Author:** Lovaraju Mylapalli  
**Maintainer:** Lovaraju Mylapalli  
**License:** LGPL-3  

## Overview

The **API Management Base** module provides a comprehensive foundation for managing secure API access in Odoo 18. It enables administrators to create, manage, and monitor API keys while providing dynamic endpoint configuration without requiring code modifications. This module is designed for organizations that need to expose Odoo data through controlled REST APIs with proper authentication, logging, and monitoring capabilities.

## Key Features

### 🔐 Advanced API Key Management
- **Secure Key Generation**: Automatic generation using cryptographically secure tokens (40-character hex)
- **User Association**: Link API keys to specific Odoo users for proper access control
- **Expiry Management**: Set expiration dates for enhanced security
- **Admin Access Control**: Special admin privileges for elevated API access
- **Multi-Company Support**: Restrict API access to specific companies
- **Model-Level Permissions**: Control which Odoo models each key can access

### 🛠 Dynamic Endpoint Configuration
- **No-Code Endpoint Creation**: Define API endpoints through intuitive UI wizards
- **Model Field Selection**: Choose specific fields to expose for each endpoint
- **Flexible URL Paths**: Custom URL paths with automatic uniqueness validation
- **Real-time Activation**: Enable/disable endpoints without server restarts
- **Permission Mapping**: Associate specific API keys with designated endpoints

### 📊 Comprehensive Access Logging
- **Request Tracking**: Log every API call with timestamp and metadata
- **Status Monitoring**: Track success, unauthorized, and failure responses
- **IP Address Logging**: Monitor access patterns and detect anomalies
- **Query Parameter Capture**: Full request parameter logging for debugging
- **Performance Analytics**: Response time tracking and analysis

### 📈 Built-in Dashboard & Monitoring
- **Usage Analytics**: Visual dashboard showing API usage patterns
- **Key Performance Metrics**: Active keys, request volumes, and success rates
- **Endpoint Statistics**: Most used endpoints and performance data
- **Real-time Monitoring**: Live view of API activity and system status

### 🔄 Intelligent Data Handling
- **Multi-Company Filtering**: Automatic company-based data filtering
- **SQL Optimization**: Direct database queries for improved performance
- **Field Serialization**: Smart handling of different Odoo field types
- **Error Recovery**: Robust error handling with transaction rollback
- **Security Bypass**: Controlled security bypass for API access

## Technical Architecture

### Core Models

#### ResApiKey (`res.api.key`)
**Purpose**: Central API key management and authentication

**Key Fields**:
- `name`: Descriptive identifier for the API key
- `key`: 40-character secure token (auto-generated)
- `user_id`: Associated Odoo user for permissions
- `active`: Enable/disable key functionality
- `expiry_date`: Optional expiration date
- `is_admin`: Administrative access privileges
- `allowed_model_ids`: Permitted Odoo models
- `company_ids`: Accessible companies
- `endpoint_ids`: Associated API endpoints

**Key Methods**:
- `generate_key()`: Creates new secure token using secrets.token_hex(20)
- `_compute_endpoint_ids()`: Dynamically calculates available endpoints
- `unlink()`: Prevents deletion of keys with active endpoints

#### ApiEndpoint (`res.api.endpoint`)
**Purpose**: Dynamic endpoint configuration and management

**Key Fields**:
- `name`: Human-readable endpoint description
- `url_path`: Unique URL path for the endpoint
- `model_id`: Target Odoo model to expose
- `field_ids`: Selected fields to include in responses
- `active`: Enable/disable endpoint
- `api_key_ids`: Authorized API keys for this endpoint

**Key Methods**:
- `_onchange_model_id()`: Auto-generates unique URL paths
- **SQL Constraints**: Ensures URL path uniqueness

#### ApiAccessLog (`api.access.log`)
**Purpose**: Comprehensive API usage tracking and audit trail

**Key Fields**:
- `api_key_id`: Reference to the API key used
- `endpoint`: Called endpoint path
- `status`: Request outcome (success/unauthorized/fail)
- `timestamp`: Request time with automatic population
- `ip_address`: Client IP address
- `query_string`: Full query parameters

### Controllers & API Logic

#### DynamicAPI Controller (`controllers/dynamic.py`)
**Purpose**: Handles all incoming API requests and security validation

**Route**: `/api/<string:endpoint_path>`
- **Authentication**: None (handles own validation)
- **Methods**: GET
- **CSRF**: Disabled for API access

**Key Features**:
- **Multi-Authentication**: Supports both header (`x-api-key`) and URL parameter (`?key=`) authentication
- **Comprehensive Validation**: Validates API key, expiry, endpoint permissions
- **Company Filtering**: Intelligent company-based data filtering using raw SQL
- **Error Handling**: Robust exception handling with proper HTTP status codes
- **Logging Integration**: Automatic logging of all requests and responses

**Security Flow**:
1. Extract API key from request headers or parameters
2. Validate key existence, activation status, and expiry
3. Verify endpoint permissions and associations
4. Apply company-based access control
5. Execute data retrieval with proper serialization
6. Log request outcome and return response

### Views & User Interface

#### API Key Management
- **List View**: Overview of all API keys with status indicators
- **Form View**: Detailed key configuration with permission settings
- **Wizard Integration**: Streamlined endpoint creation process

#### Endpoint Configuration
- **Dynamic Forms**: Model-based field selection with real-time validation
- **Permission Matrix**: Visual representation of key-endpoint associations
- **Status Management**: Easy enable/disable controls

#### Access Log Analysis
- **Comprehensive Logging**: Detailed request history with filtering options
- **Dashboard Integration**: Visual analytics and reporting tools
- **Export Capabilities**: Data export for external analysis

## Data Files Structure

```
api_management_mlr/
├── security/
│   └── ir.model.access.csv              # Model access permissions
├── models/
│   ├── __init__.py                      # Model imports
│   ├── res_api_key.py                   # API key management model
│   ├── res_api_endpoint.py              # Dynamic endpoint configuration
│   ├── api_access_log.py                # Request logging model
│   └── res_api_endpoint_wizard.py       # Endpoint creation wizard
├── controllers/
│   ├── __init__.py                      # Controller imports
│   ├── controllers.py                   # Base controller (template)
│   └── dynamic.py                       # Dynamic API request handler
├── views/
│   ├── res_api_key_views.xml            # API key management interface
│   ├── res_api_endpoint_views.xml       # Endpoint configuration forms
│   ├── res_api_endpoint_wizard_views.xml # Endpoint creation wizard
│   ├── api_access_log_views.xml         # Logging interface
│   ├── api_dashboard_views.xml          # Analytics dashboard
│   └── views.xml                        # Additional view templates
└── demo/                                # Sample data for testing
```

## Installation & Configuration

### Prerequisites
- Odoo 18.0 or higher
- `base` module (automatically satisfied)
- Appropriate server permissions for API access

### Installation Process
1. **Module Installation**:
   ```bash
   # Copy module to addons directory
   cp -r api_management_mlr /path/to/odoo/addons/
   
   # Update apps list
   # Install via Apps interface
   ```

2. **Post-Installation Setup**:
   - Navigate to Settings → Technical → API Management
   - Create initial API keys for testing
   - Configure endpoint permissions
   - Test API connectivity

### Security Configuration
1. **Access Rights**: Ensure proper user groups have access to API management
2. **Company Restrictions**: Configure company-specific access controls
3. **Model Permissions**: Set up model-level access restrictions
4. **Network Security**: Consider firewall and reverse proxy configurations

## Usage Guide

### Creating API Keys

1. **Navigate to API Management**:
   - Go to Settings → Technical → API Management → API Keys
   - Click "Create" to add new key

2. **Configure Key Settings**:
   ```
   Name: "BI Integration Key"
   User: Select appropriate Odoo user
   Expiry Date: Set expiration (optional)
   Admin Access: Check if elevated permissions needed
   Allowed Models: Select accessible models
   Allowed Companies: Choose company restrictions
   ```

3. **Generate Secure Token**:
   - Click "Generate Key" button
   - System creates 40-character secure token
   - Copy token for client application use

### Creating Dynamic Endpoints

1. **Use Endpoint Wizard**:
   - Navigate to API Management → API Endpoints
   - Click "Create" or use wizard action
   - Select target model (e.g., `res.partner`, `sale.order`)

2. **Configure Endpoint**:
   ```
   Name: "Customer Data Export"
   URL Path: "customers" (auto-generated from model)
   Model: res.partner
   Fields: name, email, phone, city, country_id
   API Keys: Select authorized keys
   ```

3. **Activate Endpoint**:
   - Ensure "Active" checkbox is checked
   - Endpoint immediately available at `/api/customers`

### Making API Requests

#### Authentication Methods

**Header Authentication** (Recommended):
```bash
curl -H "x-api-key: your_40_character_api_key" \
     "https://your-odoo-domain.com/api/customers"
```

**URL Parameter Authentication**:
```bash
curl "https://your-odoo-domain.com/api/customers?key=your_40_character_api_key"
```

#### Response Format
```json
{
  "data": [
    {
      "id": 1,
      "name": "Customer Name",
      "email": "customer@example.com",
      "phone": "+1234567890",
      "city": "New York",
      "country_id": [233, "United States"]
    }
  ],
  "status": "success",
  "timestamp": "2025-08-22T10:30:00Z"
}
```

### Monitoring & Analytics

1. **Access Logs Review**:
   - Monitor API usage patterns
   - Identify unauthorized access attempts
   - Track performance metrics

2. **Dashboard Analysis**:
   - View real-time API statistics
   - Monitor key usage patterns
   - Analyze endpoint performance

3. **Security Monitoring**:
   - Review failed authentication attempts
   - Monitor IP address patterns
   - Track unusual usage spikes

## Advanced Features

### Multi-Company Data Filtering
The module automatically filters data based on company associations:

```python
# Automatic company filtering logic
has_company_id = 'company_id' in model_fields
has_company_ids = 'company_ids' in model_fields

if has_company_id:
    # Single company field filtering
    records = model.search([('company_id', 'in', allowed_companies)])
elif has_company_ids:
    # Multi-company many2many filtering
    records = model.search([('company_ids', 'in', allowed_companies)])
```

### Field Serialization
Smart handling of different Odoo field types:
- **Many2one**: Returns `[id, "Display Name"]` format
- **Many2many/One2many**: Returns list of IDs or formatted data
- **Date/Datetime**: ISO format conversion
- **Binary**: Base64 encoding
- **Selection**: Returns key and display value

### Error Handling & Recovery
- **Transaction Rollback**: Automatic rollback on database errors
- **Graceful Degradation**: Continues processing even with partial failures
- **Comprehensive Logging**: All errors logged for debugging
- **HTTP Status Codes**: Proper status code responses (200, 401, 403, 500)

## Security Considerations

### Authentication Security
- **Secure Token Generation**: Uses cryptographically secure random tokens
- **Token Validation**: Comprehensive validation including expiry checks
- **Access Control**: Model and company-level restrictions
- **Session Management**: Stateless authentication for scalability

### Data Protection
- **Field-Level Security**: Only configured fields exposed
- **Company Isolation**: Automatic multi-company data separation
- **IP Logging**: Track and monitor access patterns
- **Audit Trail**: Complete request history maintained

### Best Practices
- ✅ Regularly rotate API keys
- ✅ Set appropriate expiry dates
- ✅ Monitor access logs for anomalies
- ✅ Use HTTPS for all API communications
- ✅ Implement rate limiting at proxy level
- ✅ Restrict API key permissions to minimum required
- ❌ Never expose admin keys in client applications
- ❌ Avoid overly broad model permissions

## Integration Examples

### Business Intelligence Integration
```python
# Python client example
import requests

headers = {'x-api-key': 'your_api_key_here'}
response = requests.get(
    'https://odoo.company.com/api/sales_orders',
    headers=headers
)
data = response.json()
```

### Mobile Application Integration
```javascript
// JavaScript client example
const apiKey = 'your_api_key_here';
const response = await fetch('/api/customers', {
    headers: {
        'x-api-key': apiKey
    }
});
const data = await response.json();
```

### Third-Party System Integration
```bash
# Shell script example
API_KEY="your_api_key_here"
ENDPOINT="https://odoo.company.com/api/products"

curl -H "x-api-key: $API_KEY" "$ENDPOINT" | jq '.'
```

## Troubleshooting

### Common Issues

**Q: API returns 401 Unauthorized**
- **A**: Verify API key is correct and active
- **A**: Check key expiry date
- **A**: Ensure endpoint permissions are configured

**Q: Empty response data**
- **A**: Verify company restrictions match data
- **A**: Check model permissions for API key
- **A**: Ensure target model has accessible records

**Q: Field not appearing in response**
- **A**: Verify field is selected in endpoint configuration
- **A**: Check field permissions for associated user
- **A**: Ensure field exists in target model

**Q: Performance issues with large datasets**
- **A**: Implement pagination at application level
- **A**: Consider adding domain filters to endpoints
- **A**: Monitor SQL query performance

### Debugging Steps
1. **Check Access Logs**: Review recent API calls for error patterns
2. **Validate Configuration**: Verify endpoint and key settings
3. **Test with Admin Key**: Use admin-level key to isolate permission issues
4. **Monitor Server Logs**: Check Odoo server logs for detailed errors
5. **Database Inspection**: Verify data exists and is accessible

## Performance Optimization

### Query Optimization
- **Direct SQL Queries**: Bypass ORM for improved performance
- **Company Filtering**: Early filtering reduces data processing
- **Field Selection**: Only retrieve configured fields
- **Transaction Management**: Efficient database transaction handling

### Caching Strategies
- **Endpoint Caching**: Cache endpoint configurations
- **Key Validation**: Cache valid key status
- **Model Metadata**: Cache field information
- **Response Caching**: Consider reverse proxy caching

### Scaling Considerations
- **Database Indexing**: Ensure proper indexes on lookup fields
- **Connection Pooling**: Configure appropriate database connections
- **Load Balancing**: Consider multiple Odoo instances for high traffic
- **Rate Limiting**: Implement request rate limiting

## Future Enhancements

### Planned Features
- ✅ **Rate Limiting**: Per-key request rate limits
- ✅ **Field-Level Security**: Granular field access control
- ✅ **Response Transformation**: Custom response format templates
- ✅ **Webhook Support**: Real-time data push capabilities
- ✅ **GraphQL Integration**: Alternative query interface
- ✅ **Bulk Operations**: Support for POST/PUT/DELETE operations

### Integration Roadmap
- **OAuth 2.0 Support**: Modern authentication standards
- **OpenAPI Documentation**: Auto-generated API documentation
- **SDK Generation**: Client library generation for popular languages
- **Analytics Enhancement**: Advanced usage analytics and reporting

## Support & Maintenance

### Documentation Resources
- **Technical Documentation**: Complete API reference guide
- **Integration Examples**: Sample implementations for various platforms
- **Best Practices Guide**: Security and performance recommendations
- **Troubleshooting FAQ**: Common issues and solutions

### Development Support
- **Custom Endpoints**: Assistance with specialized endpoint requirements
- **Performance Tuning**: Optimization for high-volume environments
- **Integration Consulting**: Architecture guidance for complex integrations
- **Security Audits**: Comprehensive security assessment services

## Changelog

### Version 18.1
- ✅ **Initial Release**: Core API management functionality
- ✅ **Dynamic Endpoints**: No-code endpoint creation
- ✅ **Comprehensive Logging**: Full request/response tracking
- ✅ **Multi-Company Support**: Company-based data filtering
- ✅ **Dashboard Analytics**: Usage monitoring and reporting
- ✅ **Security Framework**: Robust authentication and authorization
- ✅ **Error Handling**: Comprehensive error recovery mechanisms
- ✅ **Performance Optimization**: Direct SQL queries and efficient processing
