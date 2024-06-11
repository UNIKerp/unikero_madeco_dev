import logging

from mako.exceptions import RichTraceback

from odoo import fields, models

_logger = logging.getLogger(__name__)


class ApikEtl(models.Model):
    _name = "apik.etl"
    _description = "Apik ETL"

    name = fields.Char("Nom")
    code = fields.Char("Code")
    extracts = fields.One2many("apik.etl.extract", "etl_id", string="Extracts")
    transformations = fields.One2many(
        "apik.etl.transformation", "etl_id", string="Transformations"
    )
    loads = fields.One2many("apik.etl.load", "etl_id", string="Loads")
    code_etl = fields.Text("Code ETL")

    def compile(self):
        _logger.info("compile")
        code_etl = ""
        for item in self.extracts:
            item.compile()
            code_etl += item.code_etl

        for item in self.transformations:
            item.compile()
            code_etl += item.code_etl

        for item in self.loads:
            item.compile()
            code_etl += item.code_etl

        self.code_etl = code_etl

    def execute(self):
        _logger.info("execute")
        self.compile()
        _logger.info(self.code_etl)
        try:
            exec(self.code_etl)

        except Exception:
            traceback = RichTraceback()
            for filename, lineno, function, line in traceback.traceback:
                _logger.info("File %s, line %s, in %s", filename, lineno, function)
                _logger.info(line, "\n")
            _logger.info(
                "%s: %s" % (str(traceback.error.__class__.__name__), traceback.error)
            )
        return False
