# -*- coding: utf-8 -*-

import logging

from odoo import models, fields, api

logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = "stock.picking"

    @api.depends("origin", "partner_id")
    def get_categorie_commande_id(self):
        for p in self:
            if p.origin:
                saleorder = self.env["sale.order"].search([("name", "=", p.origin)])
                p.categorie_commande_id = (
                    saleorder.categorie_commande_id.id if len(saleorder) > 0 else False
                )

    categorie_commande_id = fields.Many2one(
        "categorie.commande",
        string="Order category",
        compute="get_categorie_commande_id",
        store=True,
    )
    client_order_ref = fields.Char(
        string="Référence commande client",
        readonly=True,
        related="sale_id.client_order_ref",
        store=True,
        copy=False,
    )
    is_packaging_hidden = fields.Boolean(
        "Masquer la mise en colis", related="picking_type_id.is_packaging_hidden"
    )

    def recherche_no_commande(self, docs=False):
        no_cde = False
        for doc in docs:
            no_cde = doc.sale_id.name
        return no_cde

    def recherche_no_commande_client(self, docs=False):
        no_cde = False
        for doc in docs:
            no_cde = doc.sale_id.client_order_ref
        return no_cde

    def recherche_date_commande(self, docs=False):
        date_cde = False
        for doc in docs:
            date = str(doc.sale_id.date_order)
            date_cde = date[:10]
            date_retour = date_cde[8:] + "/" + date_cde[5:7] + "/" + date_cde[0:4]
        return date_retour

    def recherche_nombre_unite_manutention(self, docs=False):
        nb_um = 0
        for doc in docs:
            nb_um = len(doc.package_ids)
        return nb_um

    def recherche_date_prevue(self, docs=False):
        date_prevue = False
        for doc in docs:
            date = str(doc.scheduled_date)
            date_prevue = date[:10]
            date_retour = (
                date_prevue[8:] + "/" + date_prevue[5:7] + "/" + date_prevue[0:4]
            )
        return date_retour

    def recherche_date_echeance(self, docs=False):
        date_echeance = False
        for doc in docs:
            date_ech = str(doc.date_deadline)
            date_echeance = date_ech[:10]
            date_retour = (
                date_echeance[8:] + "/" + date_echeance[5:7] + "/" + date_echeance[0:4]
            )
        return date_retour

    def recherche_date_bl(self, docs=False):
        date_bl = False
        for doc in docs:
            if doc.state == "done":
                date = str(doc.date_done)
            else:
                date = str(doc.scheduled_date)
            date_bl = date[:10]
            date_retour = date_bl[8:] + "/" + date_bl[5:7] + "/" + date_bl[0:4]
        return date_retour   

    def calcul_quantite_totale(self, docs=False):
        qte_tot = 0
        for doc in docs:
            for line in doc.move_line_ids:
                qte_tot += line.qty_done
        return qte_tot

    def calcul_poids_total(self, docs=False):
        pds_tot = 0
        for doc in docs:
            for line in doc.move_line_ids:
                pds_tot += line.qty_done * line.product_id.weight
        return pds_tot

    def _get_picking_fields_to_read(self):
        res = super()._get_picking_fields_to_read()
        res.append("is_packaging_hidden")
        return res
