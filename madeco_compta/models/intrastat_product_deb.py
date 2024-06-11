# Copyright 2011-2020 Akretion France (http://www.akretion.com)
# Copyright 2009-2022 Noviat (http://www.noviat.com)
# @author Alexis de Lattre <alexis.delattre@akretion.com>
# @author Luc de Meyer <info@noviat.com>

import logging
import warnings
from datetime import date

from dateutil.relativedelta import relativedelta
from stdnum.vatin import is_valid

from odoo import _, api, fields, models
from odoo.exceptions import RedirectWarning, UserError, ValidationError
from odoo.tools import float_is_zero

logger = logging.getLogger(__name__)


class IntrastatProductDeclaration(models.Model):
    _name = "intrastat.product.declaration"
    _inherit = "intrastat.product.declaration"
 
    
    def _get_weight_and_supplunits(self, inv_line, hs_code, notedict):
        company = self.env.company
        line_qty = inv_line.quantity
        product = inv_line.product_id
        intrastat_unit_id = hs_code.intrastat_unit_id
        source_uom = inv_line.product_uom_id
        weight_uom_categ = self._get_uom_refs("weight_uom_categ")
        kg_uom = self._get_uom_refs("kg_uom")
        pce_uom_categ = self._get_uom_refs("pce_uom_categ")
        pce_uom = self._get_uom_refs("pce_uom")
        weight = suppl_unit_qty = 0.0

        if intrastat_unit_id.id == company.surface_unit_id.id:
            #
            # Surface : On recalcule la quantité
            # 
            if product:
                line_qty = line_qty * product.surface
                weight = line_qty * product.weight
                suppl_unit_qty = line_qty

                return weight, suppl_unit_qty


        if not source_uom:
            line_notes = [_("Missing unit of measure.")]
            self._format_line_note(inv_line, notedict, line_notes)
            return weight, suppl_unit_qty

        if intrastat_unit_id:
            target_uom = intrastat_unit_id.uom_id
            if not target_uom:
                line_notes = [
                    _("Intrastat Code %s:") % hs_code.display_name,
                    _(
                        "Conversion from Intrastat Supplementary Unit '%s' to "
                        "Unit of Measure is not implemented yet."
                    )
                    % intrastat_unit_id.name,
                ]
                self._format_line_note(inv_line, notedict, line_notes)

                return weight, suppl_unit_qty

            if target_uom.category_id == source_uom.category_id:
                suppl_unit_qty = source_uom._compute_quantity(line_qty, target_uom)
            else:
                line_notes = [
                    _(
                        "Conversion from unit of measure '%s' to '%s' "
                        "is not implemented yet."
                    )
                    % (source_uom.name, target_uom.name)
                ]
                self._format_line_note(inv_line, notedict, line_notes)
                return weight, suppl_unit_qty

        if weight:
            return weight, suppl_unit_qty

        if source_uom == kg_uom:
            weight = line_qty
        elif source_uom.category_id == weight_uom_categ:
            weight = source_uom._compute_quantity(line_qty, kg_uom)
        elif source_uom.category_id == pce_uom_categ:
            if not product.weight:  # re-create weight_net ?
                line_notes = [_("Missing weight on product %s.") % product.display_name]
                self._format_line_note(inv_line, notedict, line_notes)

                return weight, suppl_unit_qty
            if source_uom == pce_uom:
                weight = product.weight * line_qty  # product.weight_net
            else:
                # Here, I suppose that, on the product, the
                # weight is per PCE and not per uom_id
                # product.weight_net
                weight = product.weight * source_uom._compute_quantity(
                    line_qty, pce_uom
                )
        else:
            line_notes = [
                _(
                    "Conversion from unit of measure '%s' to 'Kg' "
                    "is not implemented yet. It is needed for product '%s'."
                )
                % (source_uom.name, product.display_name)
            ]
            self._format_line_note(inv_line, notedict, line_notes)
            return weight, suppl_unit_qty

        return weight, suppl_unit_qty
      

    def _get_vat(self, inv_line, notedict):
        vat = False
        inv = inv_line.move_id

        if self.declaration_type == "dispatches":
            vat = inv.commercial_partner_id.vat

            if vat:
                if vat.startswith("GB"):
                    line_notes = [
                        _(
                            "VAT number of partner '%s' is '%s'. If this partner "
                            "is from Northern Ireland, his VAT number should be "
                            "updated to his new VAT number starting with 'XI' "
                            "following Brexit. If this partner is from Great Britain, "
                            "maybe the fiscal position was wrong on invoice '%s' "
                            "(the fiscal position was '%s')."
                        )
                        % (
                            inv.commercial_partner_id.display_name,
                            vat,
                            inv.name,
                            inv.fiscal_position_id.display_name,
                        )
                    ]
                    self._format_line_note(inv_line, notedict, line_notes)

            else:
                line_notes = [
                    _("Missing VAT Number on partner '%s'")
                    % inv.commercial_partner_id.display_name
                ]
                self._format_line_note(inv_line, notedict, line_notes)
        return vat


class L10nFrIntrastatProductDeclaration(models.Model):
    _name = "l10n.fr.intrastat.product.declaration"
    _inherit = "l10n.fr.intrastat.product.declaration"

    def _update_computation_line_vals(self, inv_line, line_vals, notedict):
        super()._update_computation_line_vals(inv_line, line_vals, notedict)
        if not line_vals.get("vat"):
            inv = inv_line.move_id
            commercial_partner = inv.commercial_partner_id
            eu_countries = self.env.ref("base.europe").country_ids


            if (
                commercial_partner.country_id not in eu_countries
                and not commercial_partner.intrastat_fiscal_representative_id
            ):
                line_notes = [
                    _(
                        "Missing fiscal representative on partner '%s'."
                        % commercial_partner.display_name
                    )
                ]
                self._format_line_note(inv_line, notedict, line_notes)
            else:
                fiscal_rep = commercial_partner.intrastat_fiscal_representative_id
                if not fiscal_rep.vat:
                    line_notes = [
                        _(
                            "Missing VAT number on partner '%s' which is the "
                            "fiscal representative of partner '%s'."
                            % (fiscal_rep.display_name, commercial_partner.display_name)
                        )
                    ]
                    self._format_line_note(inv_line, notedict, line_notes)
                else:
                    line_vals["vat"] = fiscal_rep.vat
        dpt = self._get_fr_department(inv_line, notedict)
        line_vals["fr_department_id"] = dpt and dpt.id or False        