# HR Payroll Account Multi Currency (Enterprise Edition)

**Module Name:** Payroll Accounting Multi Currency  
**Version:** 1.2.1  
**Category:** Human Resources  
**Author:** CorTex IT Solutions Ltd.  
**Website:** http://www.cortexsolutions.net  
**License:** OPL-1  
**Price:** €150  

## Overview

The **HR Payroll Account Multi Currency** module enables comprehensive multi-currency support for payroll operations in Odoo Enterprise Edition. This powerful enhancement allows organizations operating across multiple countries and currencies to manage employee contracts, payroll calculations, and accounting entries in different currencies while maintaining accurate financial reporting and compliance.

**⚠️ Important Note**: This module is designed exclusively for **Odoo Enterprise Edition** and requires the enterprise payroll accounting features to function properly.

## Key Features

### 💰 **Multi-Currency Contract Management**
- **Currency Selection**: Set specific currencies for individual employee contracts
- **Wage Management**: Configure salaries in contract-specific currencies
- **Currency Protection**: Prevent accidental currency changes that could cause accounting errors
- **Default Currency**: Automatic assignment of company default currency for new contracts

### 📊 **Intelligent Payroll Processing**
- **Automatic Currency Inheritance**: Payslips automatically adopt the contract currency
- **Multi-Currency Calculations**: Accurate payroll computations in original contract currencies
- **Currency Conversion**: Automatic conversion for accounting entries in company currency
- **Attachment Handling**: Salary attachments converted to payslip currency automatically

### 📋 **Enhanced Accounting Integration**
- **Dual Currency Entries**: Journal entries show both company currency and original amounts
- **Amount Currency Fields**: Proper currency tracking in all accounting entries
- **Tax Calculations**: Accurate tax computations across different currencies
- **Refund Support**: Complete refund processing with currency consistency

### 📈 **Comprehensive Reporting**
- **Multi-Currency Reports**: Enhanced payslip reports with proper currency display
- **Currency Grouping**: Filter and group payroll data by currency
- **Financial Analysis**: Detailed reporting with currency-specific insights
- **Payroll Analytics**: Extended payroll reporting with currency dimensions

### 🔄 **Advanced Workflow Support**
- **Batch Processing**: Handle multiple currencies in single payroll runs
- **Journal Entry Management**: Automatic currency-aware journal entry creation
- **Reconciliation**: Simplified multi-currency payroll reconciliation
- **Audit Trail**: Complete tracking of currency-related payroll transactions

## Technical Implementation

### Contract Currency Management
**Enhanced HR Contract Model**:
The module extends the standard HR contract to include independent currency selection, overriding the default related currency field to allow per-contract currency assignment while preventing unauthorized currency modifications that could disrupt accounting integrity.

**Currency Protection Mechanism**:
Implements validation logic that prevents users from changing contract currencies after creation, requiring new contract creation for currency changes to maintain accounting consistency and prevent data corruption.

### Payroll Currency Processing
**Automatic Currency Inheritance**:
Payslips automatically inherit their currency from the associated contract, ensuring consistency between contract terms and payroll processing while maintaining proper currency tracking throughout the payroll lifecycle.

**Multi-Currency Calculations**:
The payroll engine performs calculations in the original contract currency and provides automatic conversion to company currency for accounting purposes, maintaining precision and accuracy across different exchange rates.

### Accounting Integration
**Dual Currency Journal Entries**:
Journal entries include both the company currency amounts (debit/credit) and the original transaction amounts (amount_currency), providing complete financial transparency and enabling accurate multi-currency financial reporting.

**Enhanced Line Value Preparation**:
The system prepares accounting line values with proper currency information, ensuring that each journal entry line contains accurate currency data for both the original transaction currency and the company reporting currency.

### Salary Attachment Processing
**Currency Conversion Logic**:
Salary attachments are automatically converted from the company currency to the payslip currency, ensuring that deductions and garnishments are processed correctly regardless of currency differences between company settings and employee contracts.

**Multi-Currency Attachment Support**:
The system tracks currency information for each salary attachment, enabling proper conversion and reporting while maintaining accuracy in payroll deductions across different currencies.

## Data Files Structure

```
hr_payroll_account_multi_currency_ee/
├── models/
│   ├── hr_contracy.py              # Enhanced contract with currency support
│   └── hr_payroll_account.py       # Multi-currency payroll processing
├── views/
│   ├── hr_contract_view.xml        # Contract currency fields
│   ├── hr_payslip_line_view.xml    # Enhanced payslip line display
│   └── report_payslip_template.xml # Multi-currency payslip reports
├── doc/
│   └── changelog.rst               # Version history and changes
└── static/
    └── description/                # Module documentation and images
```

## Installation & Prerequisites

### System Requirements
- **Odoo Enterprise Edition** 18.0 or higher
- **hr_payroll** module (Enterprise feature)
- **hr_payroll_account** module (Enterprise feature)
- **account** module with multi-currency support enabled
- **Multi-currency** feature activated in company settings

### Installation Process

1. **Verify Prerequisites**:
   - Ensure Odoo Enterprise Edition is installed
   - Confirm payroll modules are available
   - Activate multi-currency support in company settings

2. **Module Installation**:
   - Install through Apps interface
   - The module will automatically extend existing payroll functionality
   - No additional configuration required for basic operation

3. **Post-Installation Verification**:
   - Check contract forms show currency field
   - Verify payslip currency inheritance
   - Test journal entry currency tracking

### Configuration Steps

1. **Currency Setup**:
   - Configure required currencies in Accounting > Configuration > Currencies
   - Set appropriate exchange rates
   - Enable multi-currency in company settings

2. **Contract Configuration**:
   - Review existing contracts for currency assignment
   - Set appropriate currencies for new contracts
   - Ensure wage amounts reflect correct currency values

3. **Payroll Structure Verification**:
   - Verify payroll structures work with multiple currencies
   - Test calculation accuracy across currencies
   - Validate accounting journal configuration

## Usage Guide

### Creating Multi-Currency Contracts

1. **New Contract Creation**:
   - Navigate to Employees > Contracts
   - Create new contract
   - Select appropriate currency from dropdown
   - Set wage amount in selected currency
   - Save contract (currency cannot be changed afterward)

2. **Currency Selection Guidelines**:
   - Choose currency based on employee location
   - Consider local labor law requirements
   - Align with payroll processing capabilities
   - Ensure exchange rate availability

### Processing Multi-Currency Payroll

1. **Payslip Generation**:
   - Create payslips normally through payroll process
   - Currency automatically inherited from contract
   - Calculations performed in contract currency
   - Attachments converted automatically

2. **Payroll Calculation Workflow**:
   - System calculates in original currency
   - Automatic conversion for accounting entries
   - Proper currency tracking maintained
   - Journal entries include dual currency information

### Managing Salary Attachments

1. **Multi-Currency Attachments**:
   - Create attachments with appropriate currency
   - System converts to payslip currency automatically
   - Track attachment amounts in original currency
   - Maintain conversion audit trail

2. **Attachment Processing**:
   - Automatic currency conversion during payroll
   - Proper reporting in payslip currency
   - Accurate deduction calculations
   - Consistent financial reporting

### Accounting Entry Management

1. **Journal Entry Review**:
   - Entries show company currency amounts
   - Amount currency field displays original amounts
   - Currency information properly tracked
   - Reconciliation simplified with currency data

2. **Financial Reporting**:
   - Generate reports with currency breakdown
   - Analyze payroll costs by currency
   - Monitor exchange rate impact
   - Maintain compliance across jurisdictions

## Advanced Features

### Refund Processing
**Complete Refund Support**:
The module handles payslip refunds with full currency consistency, ensuring that refunded amounts are processed in the original currency and properly converted for accounting purposes, maintaining accuracy throughout the refund lifecycle.

### Batch Processing
**Multi-Currency Batch Operations**:
Process payrolls for employees with different contract currencies in single batch operations, with automatic currency handling and proper segregation of accounting entries by currency for efficient payroll management.

### Exchange Rate Management
**Automatic Rate Application**:
The system applies current exchange rates automatically during payroll processing and accounting entry creation, ensuring that currency conversions reflect accurate market rates at the time of processing.

## Reporting & Analytics

### Enhanced Payslip Reports
**Currency-Aware Reporting**:
- Payslip reports display amounts in correct currencies
- Proper currency symbols and formatting
- Multi-currency totals and summaries
- Export capabilities with currency information

### Payroll Analytics
**Multi-Currency Insights**:
- Group payroll data by currency
- Analyze costs across different currencies
- Monitor exchange rate impact on payroll costs
- Generate compliance reports by jurisdiction

### Financial Integration
**Accounting Report Enhancement**:
- Enhanced general ledger with currency details
- Multi-currency trial balance support
- Currency-specific payroll cost analysis
- Consolidated reporting across currencies

## Compliance & Legal Considerations

### International Payroll Compliance
**Multi-Jurisdiction Support**:
- Support for local currency requirements
- Compliance with international accounting standards
- Proper documentation for tax authorities
- Audit trail maintenance across currencies

### Exchange Rate Documentation
**Rate Tracking and Compliance**:
- Historical exchange rate preservation
- Rate change impact analysis
- Compliance documentation generation
- Regulatory reporting support

## Troubleshooting

### Common Issues

**Q: Contract currency field not visible**
- **A**: Verify multi-currency is enabled in company settings
- **A**: Check user permissions for multi-currency features
- **A**: Ensure Odoo Enterprise Edition is installed

**Q: Payslip showing wrong currency**
- **A**: Verify contract currency is properly set
- **A**: Check payslip generation process
- **A**: Ensure contract is active and current

**Q: Journal entries missing currency information**
- **A**: Verify payroll accounting module is installed
- **A**: Check journal configuration for currency support
- **A**: Ensure proper payroll structure setup

**Q: Currency conversion rates incorrect**
- **A**: Update exchange rates in currency configuration
- **A**: Verify rate effective dates
- **A**: Check automatic rate update settings

### Error Prevention
**Best Practices**:
- Always verify currency setup before payroll processing
- Maintain current exchange rates
- Test currency conversions with sample data
- Regular backup before major payroll runs

### Debug and Diagnostics
**Troubleshooting Tools**:
- Review payroll computation logs
- Check currency conversion calculations
- Validate journal entry creation
- Monitor exchange rate applications

## Performance Considerations

### Optimization Tips
**Efficient Multi-Currency Processing**:
- Batch process employees by currency when possible
- Maintain current exchange rate data
- Optimize journal entry creation for large payrolls
- Monitor system performance during currency conversions

### Scalability
**Large Organization Support**:
- Efficient handling of multiple currencies simultaneously
- Optimized database queries for currency-specific data
- Streamlined reporting across large employee populations
- Automated processing capabilities for complex scenarios

## Security & Data Protection

### Currency Data Security
**Financial Data Protection**:
- Secure storage of currency information
- Audit trail for all currency-related changes
- Access control for currency configuration
- Protection against unauthorized currency modifications

### Access Controls
**User Permission Management**:
- Role-based access to currency features
- Controlled access to exchange rate configuration
- Audit logging for sensitive currency operations
- Secure handling of financial calculations

## Support & Maintenance

### Technical Support
**CorTex IT Solutions Support**:
- Professional support for implementation
- Assistance with currency configuration
- Troubleshooting complex scenarios
- Updates and maintenance services

### Documentation Resources
**Comprehensive Documentation**:
- Detailed implementation guides
- Currency setup instructions
- Best practices documentation
- Video tutorials and training materials

## Changelog

### Version 1.2.1
- ✅ **Currency Conversion Fix**: Resolved issues in amount currency calculations
- ✅ **Improved Accuracy**: Enhanced conversion precision for financial reporting

### Version 1.2.0
- ✅ **Payment Patch Fix**: Corrected payment processing issues
- ✅ **Enhanced Payslip Support**: Improved multi-currency payslip functionality

### Version 1.0.2
- ✅ **Report Enhancement**: Added currency support to payslip reports
- ✅ **Display Improvements**: Better currency formatting in reports

### Version 1.0.1
- ✅ **Currency Protection**: Fixed prevention of unauthorized currency changes
- ✅ **Validation Enhancement**: Improved contract currency validation

### Version 1.0.0
- ✅ **Initial Release**: Multi-currency support for HR payroll
- ✅ **Contract Enhancement**: Currency selection for employee contracts
- ✅ **Automatic Inheritance**: Payslip currency from contract currency
- ✅ **Attachment Processing**: Currency-aware salary attachment calculations
- ✅ **Refund Support**: Complete refund processing with currency consistency
