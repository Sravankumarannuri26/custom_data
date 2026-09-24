import logging

from odoo import models

_logger = logging.getLogger(__name__)


class HrLeaveType(models.Model):
    _inherit = "hr.leave.type"

    def write(self, vals):

        # Only trigger for:
        # Annual Leave -> Half-Day
        is_annual_leave_migration = (
            vals.get("request_unit") == "half_day"
            and any(
                leave_type.name == "Annual Leave"
                for leave_type in self
            )
        )

        if not is_annual_leave_migration:
            return super().write(vals)

        _logger.warning(
            "================================================="
        )
        _logger.warning(
            "ANNUAL LEAVE DAY -> HALF-DAY MIGRATION STARTED"
        )
        _logger.warning(
            "================================================="
        )

        Leave = self.env["hr.leave"]

        existing_leaves = Leave.search([
            ("holiday_status_id", "in", self.ids),
        ])

        old_values = {}

        for leave in existing_leaves:
            old_values[leave.id] = {
                "number_of_days": leave.number_of_days,
                "number_of_hours": leave.number_of_hours,
            }

            _logger.warning(
                "SAVE Leave ID=%s | Days=%s | Hours=%s | State=%s",
                leave.id,
                leave.number_of_days,
                leave.number_of_hours,
                leave.state,
            )

        _logger.warning(
            "Total existing Annual Leave records: %s",
            len(old_values),
        )


        result = super(
            HrLeaveType,
            self.with_context(
                leave_skip_state_check=True
            )
        ).write(vals)

        _logger.warning(
            "Annual Leave type changed successfully to Half-Day."
        )


        for leave_id, values in old_values.items():

            self.env.cr.execute(
                """
                UPDATE hr_leave
                SET
                    number_of_days = %s,
                    number_of_hours = %s
                WHERE id = %s
                """,
                (
                    values["number_of_days"],
                    values["number_of_hours"],
                    leave_id,
                ),
            )

        _logger.warning(
            "Historical Annual Leave durations restored."
        )


        self.env["hr.leave.allocation"].invalidate_model(
            ["leaves_taken", "max_leaves"]
        )

        _logger.warning(
            "Allocation cache invalidated."
        )

        _logger.warning(
            "================================================="
        )
        _logger.warning(
            "ANNUAL LEAVE DAY -> HALF-DAY MIGRATION COMPLETED"
        )
        _logger.warning(
            "================================================="
        )

        return result