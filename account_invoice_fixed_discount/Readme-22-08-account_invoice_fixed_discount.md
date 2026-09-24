# Account Invoice Fixed Discount

**Module Name:** Account Fixed Discount  
**Version:** 18.0.1.0.0  
**Category:** Accounting & Finance  
**Author:** ForgeFlow, Odoo Community Association (OCA)  
**License:** AGPL-3  
**Maturity:** Beta
**Website:** https://github.com/OCA/account-invoicing

## Overview

This module extends Odoo's invoicing functionality to allow users to apply fixed monetary amount discounts at the invoice line level, providing greater flexibility beyond traditional percentage-based discounts. The module seamlessly integrates with existing invoice workflows and automatically handles tax calculations and report generation.

## Key Features

### 🔢 Fixed Amount Discounts
- Apply specific monetary amounts as discounts on individual invoice lines
- Amount is multiplied by quantity for proper line-level calculations
- Automatic percentage conversion for tax computation compatibility
- Validation to prevent discounts exceeding line totals

### 🧮 Smart Calculations
- Automatic recalculation of totals when fixed discounts are applied
- Tax computation integration with converted discount percentages
- Real-time onchange events for discount synchronization
- Currency-aware rounding and precision handling

### 🔐 Security & Access Control
- Dedicated security group: `group_fixed_discount`
- Proper access rights for discount management
- Integration with existing invoice security model

### 📊 Enhanced Reporting
- Updated invoice reports to display both fixed amounts and equivalent percentages
- Conditional display logic for mixed discount types
- Professional invoice layout with clear discount presentation

### 🔄 Seamless Integration
- Compatible with existing percentage discount workflows
- Mutual exclusivity handling between fixed and percentage discounts
- Preserves all standard invoice functionality

## Technical Architecture

### Models Extended

#### AccountMoveLine (`account.move.line`)
- **New Field**: `discount_fixed` (Monetary) - Stores the fixed discount amount
- **Methods**:
  - `_compute_totals()`: Overridden to handle fixed discount calculations
  - `_get_discount_from_fixed_discount()`: Converts fixed amount to percentage
  - `_onchange_discount_fixed()`: Handles fixed discount changes
  - `_onchange_discount()`: Resets fixed discount when percentage is used

#### AccountTax (`account.tax`)
- **Method**: `_prepare_base_line_for_taxes_computation()`: Enhanced for fixed discount tax calculations

### Views Enhanced

#### Invoice Form View
- Added `discount_fixed` field in both list and form views
- Positioned before existing discount percentage field
- Conditional visibility based on security groups
- Optional display in list view for space optimization

#### Reports
- Enhanced invoice report template to show fixed discounts
- Intelligent display logic for mixed discount scenarios
- Clear labeling: "Discount Amount (%)" when fixed discounts are present

## Dependencies

- **Core**: `account` - Essential accounting functionality
- **Compatible with**: `sale_fixed_discount` - For sales order integration

## Installation & Setup

### Prerequisites
⚠️ **Important**: This module is incompatible with `account_invoice_triple_discount` from OCA/account-invoicing

### Installation Steps
1. Download module to your Odoo addons directory
2. Update the app list: Settings → Apps → Update Apps List
3. Install via Apps interface or activate developer mode for manual installation
4. The module automatically creates necessary security groups and extends views

### Post-Installation Configuration
1. Navigate to Settings → Users & Companies → Groups
2. Verify `Fixed Discount` group is created
3. Assign appropriate users to the discount group
4. Test functionality with a sample invoice

## Usage Guide

### Basic Usage
1. **Navigate**: Accounting → Customers → Invoices
2. **Create/Edit**: Open an invoice for editing
3. **Apply Discount**: 
   - Enter fixed amount in "Discount (Fixed)" field
   - System automatically calculates equivalent percentage
   - Total updates in real-time
4. **Validation**: Ensure discount doesn't exceed line total

### Advanced Features
- **Mixed Discounts**: Use either fixed or percentage, not both simultaneously
- **Multi-Currency**: Fixed discounts respect invoice currency
- **Reporting**: Discounts appear clearly on printed/PDF invoices
- **Tax Integration**: Taxes calculated correctly on discounted amounts

### Best Practices
- ✅ Use fixed discounts for specific promotional amounts
- ✅ Verify totals before confirming invoices
- ✅ Train users on mutual exclusivity with percentage discounts
- ❌ Avoid entering both fixed and percentage discounts simultaneously

## Data Files Structure

```
account_invoice_fixed_discount/
├── security/
│   └── res_groups.xml              # Security groups and access rights
├── views/
│   └── account_move_view.xml       # Enhanced invoice form/list views
├── reports/
│   └── report_account_invoice.xml  # Updated invoice report templates
└── models/
    ├── account_move_line.py        # Core discount logic
    └── account_tax.py              # Tax computation integration
```

## Configuration Options

### Security Groups
- **group_fixed_discount**: Controls visibility of fixed discount fields
- **Integration**: Automatically assigned to invoice management groups

### Field Properties
- **Currency Field**: Respects invoice currency
- **Precision**: Uses currency rounding for calculations
- **Help Text**: Contextual guidance for users

## Troubleshooting

### Common Issues

**Q: Fixed discount field not visible**
- **A**: Check user belongs to `Fixed Discount` security group

**Q: Discount exceeds line total**
- **A**: Module automatically resets to 0 when discount > subtotal

**Q: Tax calculation incorrect**
- **A**: Module converts fixed amount to percentage for tax computation

**Q: Report not showing discounts**
- **A**: Ensure report templates are updated and no template customizations conflict

### Validation Rules
- Fixed discount cannot exceed line subtotal (quantity × unit price)
- Automatic reset to 0.00 when validation fails
- Real-time feedback during data entry

## Integration Notes

### Sale Order Integration
- Works seamlessly with `sale_fixed_discount` module
- Discounts transfer from sales orders to invoices
- Maintains consistency across sales workflow

### Multi-Company Support
- Respects company-specific currency settings
- Proper access control across companies
- Individual configuration per company instance

## Technical Specifications

- **Odoo Version**: 18.0+
- **Python Version**: 3.8+
- **License**: AGPL-3.0
- **Module Type**: Extension/Enhancement
- **Performance Impact**: Minimal (optimized calculations)

## Support & Maintenance

### Community Support
- **GitHub Issues**: https://github.com/OCA/account-invoicing/issues
- **Documentation**: OCA community documentation
- **Translation**: Weblate translation platform

### Contributing
- Follow OCA development guidelines
- Submit pull requests with proper test coverage
- Maintain backward compatibility

## Changelog

### Version 18.0.1.0.0
- ✅ Initial release for Odoo 18.0
- ✅ Core fixed discount functionality
- ✅ Tax computation integration
- ✅ Enhanced invoice reports
- ✅ Security group implementation
- ✅ Comprehensive validation logic
