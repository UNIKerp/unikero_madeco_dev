import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class PlanningSlot(models.Model):
    _inherit = "planning.slot"

    ticket_id = fields.Many2one(
        comodel_name="helpdesk.ticket",
    )
    progress = fields.Float(
        string="Percentage of working day",
        compute="_compute_progress_hours",
        store=True,
        group_operator="sum",
        digits=(16, 2),
        help="Display percentage of of working day.",
    )
    overtime = fields.Float(
        compute="_compute_progress_hours",
        store=True,
    )

    @api.depends("allocated_hours")
    def _compute_progress_hours(self):
        default_planned_hours = 7

        data = (
            self.sudo()
            .mapped("employee_id.resource_calendar_id")
            .read(["hours_per_day"])
        )
        resources = {item["id"]: item["hours_per_day"] for item in data}

        for record in self:
            calendar_id = (
                record.sudo().employee_id.resource_calendar_id
                if record.employee_id
                else False
            )
            planned_hours = resources.get(calendar_id, default_planned_hours)
            if record.allocated_hours > 0.0:
                total_hours = record.allocated_hours
                record.overtime = max(total_hours - planned_hours, 0)
                if total_hours > planned_hours:
                    record.progress = 100
                else:
                    record.progress = round(100.0 * total_hours / planned_hours)
            else:
                record.progress = 0.0
                record.overtime = 0

    @api.depends("role_id", "project_id", "task_id", "ticket_id")
    def _compute_display_name(self):
        for record in self:
            if record.ticket_id:
                record.display_name = record.ticket_id.display_name
            elif record.task_id:
                record.display_name = record.task_id.display_name
            elif record.project_id:
                record.display_name = record.project_id.display_name
            elif record.role_id:
                record.display_name = record.role_id.display_name
            else:
                record.display_name = ""
