from datetime import datetime

from dateutil.relativedelta import relativedelta

from odoo import models


class PublisherWarrantyContract(models.AbstractModel):
    _inherit = "publisher_warranty.contract"

    def update_notification(self, cron_mode=True):
        expiration_date = datetime.now() + relativedelta(years=1)

        set_param = self.env["ir.config_parameter"].sudo().set_param

        set_param("database.expiration_date", expiration_date)
        set_param("database.expiration_reason", "trial")
        set_param("database.enterprise_code", False)

        return True
