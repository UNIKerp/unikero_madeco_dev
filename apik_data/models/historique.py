from odoo import fields, models


class ApikHistorique(models.Model):
    _name = "apik.historique"
    _description = "Apik Historique"

    name = fields.Text("Requete SQL")
    requete = fields.Many2one("apik.data", string="Requete")

    def remplacer(self):
        for h in self:
            h.requete.requete = h.name
            h.requete.executer()
