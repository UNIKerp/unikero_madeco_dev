from mako.template import Template

from odoo import api, fields, models


class ApikEtlSourceSsType(models.Model):
    _name = "apik.etl.source.ss_type"
    _description = "Apik ETL Source sous-type"

    name = fields.Char("Nom")
    ttype = fields.Selection(
        [
            ("DB", "DB"),
            ("File", "File"),
            ("Manuel", "Manuel"),
            ("Odoo", "Odoo"),
            ("Python", "Python"),
        ],
        string="Type",
        default="Python",
        required=True,
    )
    code_etl = fields.Text("Code ETL")
    template = fields.Text("Template ETL")
    fields_name = fields.Text("Fields name (séparés par des ,)")

    @api.onchange("ttype")
    def _onchange_ttype(self):
        if self.ttype == "Manuel":
            self.template = ""
            self.fields_name = ""

    def compile(self, source):
        if self.template and self.fields_name:
            template = Template(self.template)
            dict_fields = {}
            for f in self.fields_name.split(","):
                dict_fields[f] = source[f]

            self.code_etl = template.render(fields=dict_fields)


class ApikEtlSource(models.Model):
    _name = "apik.etl.source"

    name = fields.Char("Nom")
    ttype = fields.Selection(
        [
            ("DB", "DB"),
            ("File", "File"),
            ("Manuel", "Manuel"),
            ("Odoo", "Odoo"),
            ("Python", "Python"),
        ],
        string="Type",
        default="Python",
        required=True,
    )
    ss_type = fields.Many2one("apik.etl.source.ss_type", string="Sous Type")
    code_etl = fields.Text("Code ETL")
    python_list = fields.Text("Liste Python")
    python_list_header = fields.Char("Header")

    python_dict = fields.Text("Dict Python")
    python_dict_header = fields.Char("Header")

    file_binary = fields.Binary("Fichier CSV")
    file_delimiter = fields.Char("Delimiter")
    file_encoding = fields.Selection([("utf-8", "utf-8")])
    file_header = fields.Boolean("Header")
    file_type = fields.Selection(
        [("CSV", "CSV"), ("JSON", "JSON"), ("XLS", "XLS"), ("XLSX", "XLSX")],
        string="File Type",
    )
    file_sheet = fields.Char("Feuille")
    file_name = fields.Char("Nom du fichier")

    odoo_local_model = fields.Many2one("ir.model", string="Modèle")
    odoo_local_domain = fields.Char("Domaine")
    odoo_local_limit = fields.Integer("Limite")

    odoo_distant_model = fields.Char("Modèle")
    odoo_distant_domain = fields.Char("Domaine")
    odoo_distant_limit = fields.Integer("Limite")

    db_sql = fields.Text("Requete SQL")
    db_user = fields.Char("User")
    db_password = fields.Char("Password")
    db_base = fields.Char("Database")
    db_host = fields.Char("Serveur")
    db_port = fields.Char("Port")

    @api.onchange("ttype")
    def _onchange_ttype(self):
        if self.ttype:
            return {"domain": {"ss_type": [("ttype", "=", self.ttype)]}}
