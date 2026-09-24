/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";

class CheckboxWidget extends Component {
    toggleCheckbox(ev) {
        const isChecked = ev.target.checked;
        this.props.record.update({ [this.props.name]: isChecked });
    }

    get value() {
        return this.props.record.data[this.props.name];
    }
}
CheckboxWidget.template = "techcarret_rental.CheckboxWidgetTemplate";
registry.category("field_widgets").add("checkbox_widget", CheckboxWidget);
