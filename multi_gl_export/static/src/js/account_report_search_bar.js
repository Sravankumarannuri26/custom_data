/** @odoo-module **/

import { AccountReportSearchBar } from "@account_reports/components/account_report/search_bar/search_bar";
import { patch } from "@web/core/utils/patch";


patch(AccountReportSearchBar.prototype, {

    async search() {
        const inputText = this.searchText.el.value.trim().toLowerCase();
        const tokens = inputText
            .split(",")
            .map(t => t.trim())
            .filter(Boolean);

        const linesIDsMatched = [];
        await this.controller.reportLoadingPromise;

        if (tokens.length) {
            console.log(`🔍 Multi-account search: ${tokens.length} tokens`, tokens);

            for (const line of this.controller.lines) {
                if (!line.name) continue;

                const lineName = line.name.trim().toLowerCase();


                const match = tokens.some(token => lineName.includes(token));

                if (match) {
                    linesIDsMatched.push(line.id);
                }
            }

            this.controller.lines_searched = linesIDsMatched;
            this.controller.updateOption("filter_search_bar", inputText);
        } else {

            delete this.controller.lines_searched;
            this.controller.deleteOption("filter_search_bar");
        }
    }
});

