from odoo import api, fields, models


class ApikEtlTransformation(models.Model):
    _name = "apik.etl.transformation"
    _description = "Apik ETL Transformation"

    name = fields.Char("Nom")
    etl_id = fields.Many2one("apik.etl", string="ETL")
    code_etl = fields.Text("Code ETL")

    @api.onchange("name")
    def _onchange_data(self):
        self.code_etl = "" + "\n"

    def compile(self):
        for record in self:
            record._onchange_data()
