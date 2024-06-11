# -*- coding: utf-8 -*-
"""
    License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
    Default Docstring
"""
import logging
import datetime
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import timedelta

from functools import partial
from itertools import groupby

from odoo.addons.apik_calendar.models import apik_calendar

logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = 'sale.order'  

    '''
    def return_multi_doc(self):        
        # on va chercher tous les picking de ce sale order
        picking_ids = self.env["stock.picking"].search([('origin','=',self.name)])
        
        # on va chercher le rapport picking "Bon de livraison" via son ID (à mieux faire évidement)
        action2 = self.env['ir.actions.report'].browse(376).report_action(picking_ids.ids)
        
        # on va chercher le rapport sale order via son ID
        action1 = self.env['ir.actions.report'].browse(284).report_action(self.ids)
        
        return {
            "type": 'ir.actions.act_multi',
            'actions': [
                action1,
                action2
            ]
        }
    '''    

    @api.depends("global_discount",'order_line')
    def _compute_amount_global_discount(self):
        for sale in self:
            total_ht = 0
            price_unit = 0
            amount_global_discount = 0
            amount_before_discount = 0
            if sale.global_discount:
                total_ht = 0
                price_unit = 0
                for line in sale.order_line:
                    if not line.line_global_discount:
                        total_ht += line.price_subtotal
                if total_ht > 0:
                    price_unit = total_ht * sale.global_discount   # ICI / 100  
                for line in sale.order_line:
                    line_price_unit = 0
                    if line.line_global_discount:
                        amount_global_discount = price_unit * line.product_uom_qty
                        line_price_unit = price_unit
                    if line.line_global_discount:  
                        line.update({
                            'price_unit': line_price_unit,
                        })    
                   
                amount_before_discount = total_ht 
            sale.update({
                'amount_global_discount': amount_global_discount,
                'amount_before_discount': amount_before_discount,
            })



    groupe_id = fields.Many2one('res.partner',string='Groupe', related='partner_id.groupe_id', store=True, copy=False)
    centrale_id = fields.Many2one('res.partner',string='Centrale', related='partner_id.centrale_id', store=True, copy=False)
    enseigne_id = fields.Many2one('res.partner',string='Enseigne', related='partner_id.enseigne_id', store=True, copy=False)
    discount1 = fields.Float(string="Disc. 1 (%)", digits="Discount", default=0.0,)
    discount2 = fields.Float(string="Disc. 2 (%)", digits="Discount", default=0.0,)
    discount3 = fields.Float(string="Disc. 3 (%)", digits="Discount", default=0.0,)
    discounting_type = fields.Selection(
        string="Discounting type",
        selection=[("additive", "Additive"), ("multiplicative", "Multiplicative")],
        default="multiplicative",
        required=True,
        help="Specifies whether discounts should be additive "
        "or multiplicative.\nAdditive discounts are summed first and "
        "then applied.\nMultiplicative discounts are applied sequentially.\n"
        "Multiplicative discounts are default",)
    rem_a_affecter = fields.Boolean(string='Remises à affecter sur les lignes', default=0, store=True, copy=False)
    error_warning = fields.Char(string='Warning Erreur', store=False)
    remises_existantes = fields.Integer(string='Nb remises existantes les lignes', compute='_calcul_nb_remise_lignes', store=True, copy=False)
    rem_a_affecter_sans_valid = fields.Boolean(string='Remises à affecter sur les lignes sans valid', default=0, store=True, copy=False)
    rem_a_affecter_avec_valid = fields.Boolean(string='Remises à affecter sur les lignes avec valid', default=0, store=True, copy=False)
    categorie_commande_id = fields.Many2one('categorie.commande',string='Order category', copy=True)
    typologie_commande_id = fields.Many2one('typologie.commande',string='Order typology', copy=True)
    date_livraison_demandee = fields.Date(string="Date de livraison demandée", compute='_compute_date_livraison_demandee', store=True, copy=True)
    date_livraison_calculee = fields.Date(string="Date de livraison calculée", compute='_compute_date_livraison_calculee', store=True, copy=True)
    date_base_calcul = fields.Date(string="Date base calcul", store=True, copy=True)
    commitment_date = fields.Datetime(track_visibility ='onchange')
    route_id = fields.Many2one('stock.location.route',string='Route', copy=True)
    global_discount = fields.Float(string="Global discount", digits="discount", required=False, default=0.0)
    amount_before_discount = fields.Float(string="Amount before discount", compute='_compute_amount_global_discount',default=0)
    amount_global_discount = fields.Float(string="Global discount amount", compute='_compute_amount_global_discount',default=0)
    has_remise_globale_line = fields.Boolean(string="has a global discount line", default=False, store=True, copy=False)
    recoupe = fields.Boolean(string="Commande de recoupe", default=False, store=True, copy=False)
    implantation = fields.Boolean(string="Commande d'implantation", default=False, store=True, copy=False)
    xdock = fields.Boolean(string="Livraison XDOCK", default=False, store=True, copy=False)
    affect_auto_route_logistique = fields.Boolean(string="Affectation automatique des routes logistiques", default=True, store=True)
    commande_a_facturer = fields.Boolean(string="Commande à facturer", compute='_compute_picking_ids_sale_order', store=True)


    @api.depends("date_order",'partner_id')
    def _compute_date_livraison_demandee(self):
        company_id = self.env.company 
        for sale in self:
            if not sale.date_livraison_demandee:
                date_ouvree = sale.date_order
                #sale.date_livraison_demandee = sale.calcule_jour_ouvre_francais(date_ouvree)
                sale.date_livraison_demandee = apik_calendar.calcul_date_ouvree(sale.date_order, 0, company_id.nb_weekend_days, company_id.zone_geo)  

    @api.depends('date_order','partner_id','date_livraison_demandee')
    def _compute_date_livraison_calculee(self):
        company_id = self.env.company 
        for sale in self:
            if sale.date_base_calcul:
                if sale.partner_id.delai_livraison:
                    nb_jour = sale.partner_id.delai_livraison
                else:
                    nb_jour = 0  
                #date_ouvree = sale.date_base_calcul + datetime.timedelta(days=nb_jour)      
                #sale.date_livraison_calculee = sale.calcule_jour_ouvre_francais(date_ouvree)  
                sale.date_livraison_calculee = apik_calendar.calcul_date_ouvree(sale.date_base_calcul, nb_jour, company_id.nb_weekend_days, company_id.zone_geo)  
            else:    
                if sale.date_order:
                    if sale.partner_id.delai_livraison:
                        nb_jour = sale.partner_id.delai_livraison
                    else:
                        nb_jour = 0  
                    #date_ouvree = sale.date_order + datetime.timedelta(days=nb_jour)      
                    #sale.date_livraison_calculee = sale.calcule_jour_ouvre_francais(date_ouvree)
                    sale.date_livraison_calculee = apik_calendar.calcul_date_ouvree(sale.date_order, nb_jour, company_id.nb_weekend_days, company_id.zone_geo)  
                else:
                    if sale.partner_id.delai_livraison:
                        nb_jour = sale.partner_id.delai_livraison
                    else:
                        nb_jour = 0
                    #date_ouvree = datetime.datetime.now() + datetime.timedelta(days=nb_jour)      
                    #sale.date_livraison_calculee = sale.calcule_jour_ouvre_francais(date_ouvree)  
                    date_ouvree = datetime.datetime.now()
                    sale.date_livraison_calculee = apik_calendar.calcul_date_ouvree(date_ouvree, nb_jour, company_id.nb_weekend_days, company_id.zone_geo)  

    @api.onchange("date_livraison_demandee", 'date_livraison_calculee')
    def onchange_date_livraison_commitment_date(self):
        for sale in self:
            if sale.date_livraison_calculee and sale.date_livraison_demandee:
                if sale.date_livraison_calculee > sale.date_livraison_demandee:
                    sale.commitment_date = sale.date_livraison_calculee
                else:
                    sale.commitment_date = sale.date_livraison_demandee
            else:
                sale.commitment_date = sale.date_order                      
    
    @api.depends("order_line","order_line.discount")
    def _calcul_nb_remise_lignes(self):
        for sale in self:
            sale.remises_existantes = 0
            for line in self.order_line:
                if line.discount > 0:
                    sale.remises_existantes += 1
                if line.discount2 > 0:
                    sale.remises_existantes += 1
                if line.discount3 > 0:
                    sale.remises_existantes += 1   
    
    @api.onchange("route_id")
    def onchange_route_id_entete(self):
        for sale in self:
            if sale.route_id:
                for line in sale.order_line:
                    line.route_id = sale.route_id.id   

    # 
    # On regarde si article de recoupe
    # 
    @api.onchange("order_line")
    def onchange_article_recoupe_entete(self):
        for sale in self:
            sale.recoupe = False
            for line in sale.order_line:
                if line.product_id.typologie_article == 'A2':
                    sale.recoupe = True 
                    break

    # 
    # On regarde si adresse de livraison est XDOCK
    # 
    @api.onchange("partner_shipping_id")
    def onchange_partner_shipping_id_xdock_entete(self):
        for sale in self:
            sale.xdock = False
            if sale.partner_shipping_id.xdock:
                sale.xdock = True
            if sale.partner_shipping_id.intrastat_transport_id:
                sale.intrastat_transport_id = sale.partner_shipping_id.intrastat_transport_id.id    

    @api.onchange('partner_id')
    def onchange_partner_id_madeco_vente(self):
        for sale in self:
            if sale.partner_id.sale_global_discount:
                sale.global_discount = sale.partner_id.sale_global_discount
            
            if sale.partner_id:
                sale.user_id = sale.partner_id.user_id
            else:
                sale.user_id = self.env.user

    @api.depends('picking_ids')
    def _compute_picking_ids_sale_order(self):    
        for sale in self:      
            if sale.picking_ids:
                #logger.info("_______________")
                a_facturer = True  
                for picking in sale.picking_ids:
                    #logger.info(picking.name)
                    #logger.info(picking.state)
                    if picking.state not in ('done','cancel'):
                        a_facturer = False
                        break
                #logger.info(a_facturer)            
                #logger.info("_______________")    
            else:
                a_facturer = False
            sale.commande_a_facturer = a_facturer 
    
    def update_prices(self):
        list_prix_obj = self.env['product.pricelist.item'] 
        self.ensure_one()
        lines_to_update = []
        for line in self.order_line.filtered(lambda line: not line.display_type):
            product = line.product_id.with_context(
                partner=self.partner_id,
                quantity=line.product_uom_qty,
                date=self.date_order,
                pricelist=self.pricelist_id.id,
                uom=line.product_uom.id
            )
            price_unit = self.env['account.tax']._fix_tax_included_price_company(
                line._get_display_price(product), line.product_id.taxes_id, line.tax_id, line.company_id)
            if self.pricelist_id.discount_policy == 'without_discount' and price_unit:
                discount = max(0, (price_unit - product.price) * 100 / price_unit)
            else:
                discount = 0
            prix_promo_trouve = False    
            if self.pricelist_id and line.product_id:
                list_prix = list_prix_obj.search([('product_tmpl_id','=',line.product_id.product_tmpl_id.id),('pricelist_id','=',self.pricelist_id.id)], limit=1) 
                if list_prix:
                    prix_promo_article = list_prix.prix_promo_item
                    prix_promo_trouve = True

            if prix_promo_trouve:
                lines_to_update.append((1, line.id, {'price_unit': price_unit, 'discount': discount,'prix_promo': prix_promo_article}))    
            else:        
                lines_to_update.append((1, line.id, {'price_unit': price_unit, 'discount': discount}))
        self.update({'order_line': lines_to_update})
        self.show_update_pricelist = False
        self.message_post(body=_("Product prices have been recomputed according to pricelist <b>%s<b> ", self.pricelist_id.display_name))
    
    
    @api.depends("order_line.price_total")
    def _amount_all(self):
        prev_values = dict()
        for order in self:
            prev_values.update(order.order_line.prix_promo_preprocess())
        super()._amount_all()
        self.env["sale.order.line"].prix_promo_postprocess(prev_values)
       

    def write(self, values):
        commande_obj = self.env['sale.order'] 
        if 'discount1' in values:
            rem1 = values['discount1']
            if rem1 != 0:
                rem_true = True
            else: 
                rem_true = False   
            values['rem_a_affecter'] = rem_true
        if 'discount2' in values:
            rem2 = values['discount2']
            if rem2 != 0:
                rem_true = True
            else: 
                rem_true = False             
            values['rem_a_affecter'] = rem_true
        if 'discount3' in values:
            rem3 = values['discount3']
            if rem3 != 0:
                rem_true = True
            else: 
                rem_true = False  
            values['rem_a_affecter'] = rem_true
        if 'discounting_type' in values:
            rem_true = True
            values['rem_a_affecter'] = rem_true  

        
        if 'rem_a_affecter' in values:
            remaffect = values['rem_a_affecter']
            if remaffect:
                if self.remises_existantes:
                    values['rem_a_affecter_avec_valid'] = True  
                    values['rem_a_affecter_sans_valid'] = False   
                else:
                    values['rem_a_affecter_avec_valid'] = False  
                    values['rem_a_affecter_sans_valid'] = True  
            else:
                values['rem_a_affecter_avec_valid'] = False  
                values['rem_a_affecter_sans_valid'] = False         
        if 'remises_existantes' in values:           
            rem_exit = values['remises_existantes']
            if self.rem_a_affecter:
                if rem_exit:
                    values['rem_a_affecter_avec_valid'] = True  
                    values['rem_a_affecter_sans_valid'] = False   
                else:
                    values['rem_a_affecter_avec_valid'] = False  
                    values['rem_a_affecter_sans_valid'] = True    

        res = super(SaleOrder, self).write(values)
        if res:
            commandes = commande_obj.search([('name','=',self.name)])
            for commande in commandes:
                if not commande.date_base_calcul:
                    commande.date_base_calcul = commande.date_order
                if not commande.has_remise_globale_line:
                    if commande.global_discount != 0:
                        commande.create_remise_globale_line()    
                #
                # On réaffecte les routes logistiques sur les lignes de la commande si on est sur un devis.
                #             
                if commande.state in ('draft','sent'):
                    if commande.affect_auto_route_logistique:
                        affect = self.affectation_routes_logistiques_sale_order_line(commande)
                if not commande.route_id:
                    ent_route_id = self.recherche_route_unique_sur_commande(commande)   
                    if ent_route_id:
                        commande.route_id = ent_route_id 
                
        return res    

    def action_reaffecte_remise(self):
        for cde in self:
            for line in cde.order_line:
                if line.line_global_discount != True:
                    if cde.discount1 > 0 or cde.discount2 > 0 or cde.discount3 > 0:
                        line.discounting_type = cde.discounting_type
                        if cde.discount1 > 0:
                            line.discount = cde.discount1
                        if cde.discount2 > 0:
                            line.discount2 = cde.discount2
                        if cde.discount3 > 0:  
                            line.discount3 = cde.discount3  
                        line._compute_amount()
            self.rem_a_affecter = False 

    def action_confirm(self):
        if not self.partner_id:
            return False
        warning = {}
        title = False
        message = False
        partner = self.partner_id
        bloquant = False

        if partner.sale_warn == 'no-message' and partner.parent_id:
            partner = partner.parent_id

        if partner.sale_warn and partner.sale_warn != 'no-message':
            # Block if partner only has warning but parent company is blocked
            if partner.sale_warn != 'block' and partner.parent_id and partner.parent_id.sale_warn == 'block':
                partner = partner.parent_id
            title = ("Warning for %s") % partner.name
            message = partner.sale_warn_msg
            warning = title + ' : ' + message  
            if partner.sale_warn == 'block':
                bloquant = True

        if warning and bloquant:
            self.error_warning = warning  
            return {
                'name': _('Warning Sales Order'),
                'view_mode': 'form',
                'res_model': 'sale.order.warning',
                'view_id': self.env.ref('madeco_vente.sale_order_error_valid_view_form').id,
                'type': 'ir.actions.act_window',
                'context': {'default_order_id': self.id, 'default_error_warning': self.error_warning},
                'target': 'new'
            }   
        else:
            erreur_type_article = self.controle_validation_commande_type_article()
            if not self.commande_presta:
                if erreur_type_article != "0":
                    if erreur_type_article == '2':    
                        raise UserError(_("Enregistrement impossible, adresse de livraison non XDOCK."))
                    else:
                        raise UserError(_("Enregistrement impossible, incohérence sur les typologies d'articles."))
                if self.commande_edi:
                    # 
                    # On regarde s'il y a un blocage sur le partner 
                    #
                    if self.partner_id.sale_warn != 'no-message' or self.partner_id.invoice_warn  != 'no-message' or self.partner_id.invoice_warn != 'no-message': 
                        message_blocage = "Existence d'un blocage ou avertissement sur le contact"
                        self.message_post(body=message_blocage)
                        raise UserError(_(message_blocage))
                    # 
                    # On regarde s'il y a un blocage sur un des articles de la commande 
                    #  
                    for line_cde in self.order_line:
                        if line_cde.product_id.sale_line_warn == 'block':
                            message_blocage = "Existence d'un blocage sur l'article {}".format(line_cde.product_id.name)  
                            self.message_post(body=message_blocage)
                            raise UserError(_(message_blocage))

                result = super(SaleOrder, self).action_confirm()
            else:
                if erreur_type_article != "0":
                    if erreur_type_article == '2':    
                        lib_erreur_controle_art = "Validation de la commande impossible, adresse de livraison non XDOCK."
                    else:
                        lib_erreur_controle_art = "Validation de la commande impossible, incohérence sur les typologies d'articles."
                    company_id =  self.env.company 
                    sujet = str(self.env.company.name) + ' - Gestion PrestaShop - Commandes client du ' + str(self.date_order.date()) 
                    corps = "{} <br/><br>".format(lib_erreur_controle_art)   
                    corps+= "La pièce {} reste en devis. <br/><br>".format(self.name)                         
                    corps+= "<br><br> {} <br> {} ".format(self.env.user.name,self.env.user.email) 
                    destinataire = company_id.gestion_user_id.email
                    if destinataire:
                        self.presta_generation_mail(destinataire, sujet, corps)
                    code_erreur = self.env['erreur.presta'].search([('name','=', '9999')], limit=1) 
                    message = "{}  ".format(lib_erreur_controle_art)   
                    message+= "La pièce {} reste en devis. ".format(self.name)    
                    self.presta_generation_erreur(code_erreur, sujet, message)   
                    result = False   
                else:
                    result = super(SaleOrder, self).action_confirm()     
            return result

    def presta_generation_mail(self, destinataire, sujet, corps):
        #
        # On envoie un mail au destinataire reçu
        #
        mail_obj = self.env['mail.mail']
        '''
        today = fields.Date.from_string(fields.Date.context_today(self))
        if len(destinataire)>0:
            mail_data = {
                        'subject': sujet,
                        'body_html': corps,
                        'email_from': self.env.user.email,
                        'email_to': destinataire,                        
                        }
            mail_id = mail_obj.create(mail_data)
            mail_id.send()
        '''   

    def presta_generation_erreur(self, erreur,  sujet, corps):
        #
        # On cree un enregistrement dans le suivi PrestaShop
        #
        company_id =  self.env.company 
        suivi_presta = self.env['suivi.presta']
        today = fields.Date.from_string(fields.Date.context_today(self))
        if len(sujet)>0:
            suivi_data = {
                        'company_id': company_id.id,
                        'name': sujet,
                        'libelle_mvt_presta': corps,
                        'erreur_id': erreur.id,                        
                        }
            suivi = suivi_presta.create(suivi_data)     

    def button_confirm_reaffect_remise(self):
        return {
            'name': 'Confirmation',
            'view_mode': 'form',
            'view_id': self.env.ref('madeco_vente.action_reaffecte_remise_avec_valid').id,
            'res_model': 'sale.order',
            'type': "ir.actions.act_window",
            'target': 'new',
            'res_id': self.id,
            }

    def confirm_action_reaffectation_remise(self):
        for cde in self:
            for line in cde.order_line:
                if cde.discount1 > 0 or cde.discount2 > 0 or cde.discount3 > 0:
                    line.discounting_type = cde.discounting_type
                    if cde.discount1 > 0:
                        line.discount = cde.discount1
                    if cde.discount2 > 0:
                        line.discount2 = cde.discount2
                    if cde.discount3 > 0:  
                        line.discount3 = cde.discount3  
                    line._compute_amount()
            self.rem_a_affecter = False 

    def _prepare_invoice(self):
        invoice_vals = super(SaleOrder, self)._prepare_invoice()
        if self.categorie_commande_id:
            invoice_vals['categorie_commande_id'] = self.categorie_commande_id.id
        if self.typologie_commande_id:
            invoice_vals['typologie_commande_id'] = self.typologie_commande_id.id
        '''
        if self.has_remise_globale_line:
            invoice_vals['has_remise_globale_line'] = self.has_remise_globale_line
        if self.global_discount > 0:
            invoice_vals['global_discount'] = self.global_discount
        '''      
        return invoice_vals

    # 
    # On reprend la fonction standard de création de facture dans laquelle on ajoute la génération de la ligne d'escompte DZB 
    #  
    # Flag : DZB
    # 
    def _create_invoices(self, grouped=False, final=False, date=None):   
        """
        Create the invoice associated to the SO.
        :param grouped: if True, invoices are grouped by SO id. If False, invoices are grouped by
                        (partner_invoice_id, currency)
        :param final: if True, refunds will be generated if necessary
        :returns: list of created invoices
        """
        if not self.env['account.move'].check_access_rights('create', False):
            try:
                self.check_access_rights('write')
                self.check_access_rule('write')
            except AccessError:
                return self.env['account.move']

        # 1) Create invoices.
        invoice_vals_list = []
        invoice_item_sequence = 0 # Incremental sequencing to keep the lines order on the invoice.
        for order in self:
            order = order.with_company(order.company_id)
            current_section_vals = None
            down_payments = order.env['sale.order.line']

            invoice_vals = order._prepare_invoice()
            invoiceable_lines = order._get_invoiceable_lines(final)

            if not any(not line.display_type for line in invoiceable_lines):
                continue

            invoice_line_vals = []
            down_payment_section_added = False
            for line in invoiceable_lines:
                if not down_payment_section_added and line.is_downpayment:
                    # Create a dedicated section for the down payments
                    # (put at the end of the invoiceable_lines)
                    invoice_line_vals.append(
                        (0, 0, order._prepare_down_payment_section_line(
                            sequence=invoice_item_sequence,
                        )),
                    )
                    down_payment_section_added = True
                    invoice_item_sequence += 1
                invoice_line_vals.append(
                    (0, 0, line._prepare_invoice_line(
                        sequence=invoice_item_sequence,
                    )),
                )
                invoice_item_sequence += 1

            invoice_vals['invoice_line_ids'] += invoice_line_vals
            invoice_vals_list.append(invoice_vals)

        if not invoice_vals_list:
            raise self._nothing_to_invoice_error()

        # 2) Manage 'grouped' parameter: group by (partner_id, currency_id).
        if not grouped:
            new_invoice_vals_list = []
            invoice_grouping_keys = self._get_invoice_grouping_keys()
            invoice_vals_list = sorted(invoice_vals_list, key=lambda x: [x.get(grouping_key) for grouping_key in invoice_grouping_keys])
            for grouping_keys, invoices in groupby(invoice_vals_list, key=lambda x: [x.get(grouping_key) for grouping_key in invoice_grouping_keys]):
                origins = set()
                payment_refs = set()
                refs = set()
                ref_invoice_vals = None
                for invoice_vals in invoices:
                    if not ref_invoice_vals:
                        ref_invoice_vals = invoice_vals
                    else:
                        ref_invoice_vals['invoice_line_ids'] += invoice_vals['invoice_line_ids']
                    origins.add(invoice_vals['invoice_origin'])
                    payment_refs.add(invoice_vals['payment_reference'])
                    refs.add(invoice_vals['ref'])
                ref_invoice_vals.update({
                    'ref': ', '.join(refs)[:2000],
                    'invoice_origin': ', '.join(origins),
                    'payment_reference': len(payment_refs) == 1 and payment_refs.pop() or False,
                })
                new_invoice_vals_list.append(ref_invoice_vals)
            invoice_vals_list = new_invoice_vals_list

        # 3) Create invoices.

        # As part of the invoice creation, we make sure the sequence of multiple SO do not interfere
        # in a single invoice. Example:
        # SO 1:
        # - Section A (sequence: 10)
        # - Product A (sequence: 11)
        # SO 2:
        # - Section B (sequence: 10)
        # - Product B (sequence: 11)
        #
        # If SO 1 & 2 are grouped in the same invoice, the result will be:
        # - Section A (sequence: 10)
        # - Section B (sequence: 10)
        # - Product A (sequence: 11)
        # - Product B (sequence: 11)
        #
        # Resequencing should be safe, however we resequence only if there are less invoices than
        # orders, meaning a grouping might have been done. This could also mean that only a part
        # of the selected SO are invoiceable, but resequencing in this case shouldn't be an issue.
        if len(invoice_vals_list) < len(self):
            SaleOrderLine = self.env['sale.order.line']
            for invoice in invoice_vals_list:
                sequence = 1
                for line in invoice['invoice_line_ids']:
                    line[2]['sequence'] = SaleOrderLine._get_invoice_line_sequence(new=sequence, old=line[2]['sequence'])
                    sequence += 1

        # Début développement DZB
        # 
        # On ajoute un escompte si paramétrage DZB dans la fiche partner 
        # 
        if len(invoice_vals_list):
            for invoice in invoice_vals_list:
                partner_obj = self.env['res.partner'] 
                facture_type = invoice.get('move_type') 
                company_id =  self.env.user.company_id 
                if facture_type == 'out_invoice':
                    partner_fact = invoice.get('partner_id')    
                    if partner_fact:
                        partner_facture = partner_obj.search([('id','=',partner_fact)], limit=1) 
                        if partner_facture:
                            if partner_facture.code_dzb:
                                #
                                # On génère une ligne dans la facture
                                #  
                                mont_tot_escompte = 0
                                mont_a_escompter = 0
                                for line in invoice['invoice_line_ids']:

                                    if line[2]['product_id'] != company_id.product_escompte_id.id or line[2]['line_global_discount'] == True:
                                        mtt_ligne = line[2]['quantity'] * line[2]['price_unit'] 
                                        if line[2]['discount']:
                                            mtt_ligne = mtt_ligne * (1 - (line[2]['discount']/100))
                                        if line[2]['discount2']:
                                            mtt_ligne = mtt_ligne * (1 - (line[2]['discount2']/100))
                                        if line[2]['discount3']:
                                            mtt_ligne = mtt_ligne * (1 - (line[2]['discount3']/100))  
                                        mont_tot_escompte += mtt_ligne      

                                if mont_tot_escompte > 0:
                                    if company_id.taux_escompte:
                                        tx = company_id.taux_escompte/100
                                        mont_a_escompter = mont_tot_escompte * tx  

                                if mont_a_escompter > 0:
                                    qte = -1
                                    designation = company_id.product_escompte_id.name
                                    compte = company_id.product_escompte_id.product_tmpl_id.property_account_income_id.id
                                    unite = company_id.product_escompte_id.uom_id.id
                                    discount = 0  

                                    #
                                    # On recherche la TVA de l'escompte
                                    #        
                                    #fpos_dzb = self.fiscal_position_id or self.fiscal_position_id.get_fiscal_position(self.order_partner_id.id)
                                    fpos_dzb = self.fiscal_position_id or self.fiscal_position_id.get_fiscal_position(partner_facture.id)
                                    # If company_id is set, always filter taxes by the company
                                    taxes_dzb = self.company_id.product_escompte_id.taxes_id.filtered(lambda t: t.company_id == self.company_id)
                                    tax_id_dzb = fpos_dzb.map_tax(taxes_dzb, self.company_id.product_escompte_id, self.partner_shipping_id)                          
                                
                                    values_ligne_dzb = {
                                        'display_type': False, 
                                        'sequence': 9990, 
                                        'name': designation, 
                                        'product_id': company_id.product_escompte_id.id,  
                                        'product_uom_id': unite, 
                                        'quantity': qte, 
                                        'discount': discount, 
                                        'price_unit': mont_a_escompter,
                                        'tax_ids': [(6, 0, [1])], 
                                        'tax_ids': [(6, 0, tax_id_dzb.ids)],
                                        'analytic_account_id': False, 
                                        'analytic_tag_ids': [(6, 0, [])], 
                                        'discount2': discount, 
                                        'discount3': discount, 
                                        'prix_promo': False, 
                                        'line_global_discount': False,
                                    }
                                    base_invoice_line_ids = invoice.get('invoice_line_ids') 
                                    base_invoice_line_ids.append((0,0,values_ligne_dzb))
                                    invoice.update({'invoice_line_ids': base_invoice_line_ids,})

        # Fin développement DZB                                    

        # Manage the creation of invoices in sudo because a salesperson must be able to generate an invoice from a
        # sale order without "billing" access rights. However, he should not be able to create an invoice from scratch.
        moves = self.env['account.move'].sudo().with_context(default_move_type='out_invoice').create(invoice_vals_list)

        # 4) Some moves might actually be refunds: convert them if the total amount is negative
        # We do this after the moves have been created since we need taxes, etc. to know if the total
        # is actually negative or not
        if final:
            moves.sudo().filtered(lambda m: m.amount_total < 0).action_switch_invoice_into_refund_credit_note()
        for move in moves:
            move.message_post_with_view('mail.message_origin_link',
                values={'self': move, 'origin': move.line_ids.mapped('sale_line_ids.order_id')},
                subtype_id=self.env.ref('mail.mt_note').id
            )
        return moves

    #
    # On modifie la fonction de recalcul des prix en fonction de la date de livraison pour ne
    # pas modifier les prix unitaires des commandes Web Prestashop
    #
    # Module OCA : sale_pricelist_from_commitment_date
    #
    def _apply_pricelist_from_commitment_date(self):
        self.ensure_one()
        for line in self.order_line:
            # Price unit is still modifiable if not quantity invoiced
            if not line.qty_invoiced:
                # Call product_uom_change as it only updates price_unit using pricelist
                if not line.lig_commande_presta :
                    # On ne fait pas la modification sur les lignes de commande Web PrestaShop
                    line.with_context(
                        force_pricelist_date=self.commitment_date
                    ).product_uom_change()

    #
    # On calcule la ligne de remise globale à ajouter
    #
    def create_remise_globale_line(self):
        SaleOrderLine = self.env['sale.order.line']
        company_id = self.env.company 

        # Apply fiscal position
        taxes = company_id.product_rem_global_id.taxes_id.filtered(lambda t: t.company_id.id == self.company_id.id)
        taxes_ids = taxes.ids
        if self.partner_id and self.fiscal_position_id:
            taxes_ids = self.fiscal_position_id.map_tax(taxes, company_id.product_rem_global_id, self.partner_id).ids
        
        # 
        # on calcule le prix unitaire en fonction du taux de remise et de la somme des lignes HT
        #
        if self.order_line:
            total_ht = 0
            price_unit = 0
            for line in self.order_line:
                if not line.line_global_discount:
                    total_ht += line.price_subtotal
            if total_ht > 0:
                price_unit = total_ht * self.global_discount  # ICI / 100       
            self.has_remise_globale_line = True
            if company_id.product_rem_global_id.description_sale:
                libelle = company_id.product_rem_global_id.description_sale
            else:
                libelle = company_id.product_rem_global_id.name

            values = {
                'order_id': self.id,
                'name': libelle,
                'product_uom_qty': -1,
                'product_uom': company_id.product_rem_global_id.uom_id.id,
                'product_id': company_id.product_rem_global_id.id,
                'price_unit': price_unit,
                'line_global_discount': True,
                'tax_id': [(6, 0, taxes_ids)],
            }
            if self.order_line:
                values['sequence'] = self.order_line[-1].sequence + 1
            new_line = SaleOrderLine.sudo().create(values)    
        else:
            new_line = False    
        return new_line

    @api.model
    def create(self, vals):
        new_sale = super(SaleOrder, self).create(vals)   
        if not new_sale.has_remise_globale_line:
            if new_sale.global_discount != 0:
                new_sale.create_remise_globale_line()
        #
        # On réaffecte les routes logistiques sur les lignes de la commande si on est sur un devis.
        #
        if new_sale:             
            if new_sale.state in ('draft','sent'):
                if new_sale.affect_auto_route_logistique:
                    affect = self.affectation_routes_logistiques_sale_order_line(new_sale)

            if not new_sale.route_id:
                    ent_route_id = self.recherche_route_unique_sur_commande(new_sale)   
                    if ent_route_id:
                        new_sale.route_id = ent_route_id

        if new_sale.partner_id:
            new_sale.user_id = new_sale.partner_id.user_id

        return new_sale    

    # 
    #  Affectation des routes logistiques sur les lignes de commandes
    #       
    def affectation_routes_logistiques_sale_order_line(self, sale):
        param_route_obj = self.env['parametrage.route']
        if sale:
            route_sur_mesure_gen = param_route_obj.search([('xdock','=',False),('recoupe','=',False),('implantation','=',False),('typologie_article','=','A3'),], limit=1) 
            if not route_sur_mesure_gen:
                raise UserError(_("Paramétrage route 'Sur-mesure' inexistante, veuillez revoir les paramétrages des routes."))
            route_dropship_gen = param_route_obj.search([('xdock','=',False),('recoupe','=',False),('implantation','=',False),('typologie_article','=','A4'),], limit=1) 
            if not route_dropship_gen:
                raise UserError(_("Paramétrage route 'DropShip' inexistante, veuillez revoir les paramétrages des routes."))
            #
            # On traite les cas des Implantations, Recoupe et XDOCK de l'entête de la commande 
            #
            if sale.implantation:
                # 
                # on recherche la route d'implantation et on l'affecte sur toutes les lignes de la commande
                #
                route_impl = param_route_obj.search([('xdock','=',False),('recoupe','=',False),('implantation','=',True),('typologie_article','=','A1'),], limit=1) 
                if route_impl:
                    for line in sale.order_line:
                        line.route_id = route_impl.route_id.id
                return True 
            if sale.recoupe:
                if sale.xdock:
                    # 
                    # on recherche la route de recoupe XDOCK et on l'affecte sur toutes les lignes de la commande
                    #
                    route_rec_xdock = param_route_obj.search([('xdock','=',True),('recoupe','=',True),('implantation','=',False),('typologie_article','=','A2'),], limit=1) 
                    if route_rec_xdock:
                        for line in sale.order_line:
                            line.route_id = route_rec_xdock.route_id.id

                    return True 
                else:
                    # 
                    # on recherche la route de recoupe et on l'affecte sur toutes les lignes de la commande
                    #
                    route_rec = param_route_obj.search([('xdock','=',False),('recoupe','=',True),('implantation','=',False),('typologie_article','=','A2'),], limit=1) 
                    if route_rec:
                        for line in sale.order_line:
                            # 
                            # On regarde si article Sur Mesure (A3) ou Droship (A4)
                            # 
                            if line.product_id.typologie_article == 'A3':
                                line.route_id = route_sur_mesure_gen.route_id.id
                            else:
                                if line.product_id.typologie_article == 'A4':
                                    line.route_id = route_dropship_gen.route_id.id
                                else:        
                                    line.route_id = route_rec.route_id.id
                    return True
            #
            # On traite les autres cas  
            #                 
            if not sale.implantation and not sale.recoupe and not sale.xdock:
                for line in sale.order_line:
                    if line.product_id.typologie_article == 'A1':
                        # 
                        # Article standard 
                        #
                        route_std = param_route_obj.search([('xdock','=',False),('recoupe','=',False),('implantation','=',False),('typologie_article','=','A1'),], limit=1) 
                        if route_std:
                            line.route_id = route_std.route_id.id
                    if line.product_id.typologie_article == 'A3':
                        # 
                        # Article Sur-Mesure 
                        #
                        route_sm = param_route_obj.search([('xdock','=',False),('recoupe','=',False),('implantation','=',False),('typologie_article','=','A3'),], limit=1) 
                        if route_sm:
                            line.route_id = route_sm.route_id.id   
                    if line.product_id.typologie_article == 'A4':
                        # 
                        # Article Dropship 
                        #
                        route_ds = param_route_obj.search([('xdock','=',False),('recoupe','=',False),('implantation','=',False),('typologie_article','=','A4'),], limit=1) 
                        if route_ds:
                            line.route_id = route_ds.route_id.id               
                return True    
            if not sale.implantation and not sale.recoupe and sale.xdock:
                for line in sale.order_line:
                    if line.product_id.typologie_article == 'A1':
                        # 
                        # Article standard 
                        #
                        route_std = param_route_obj.search([('xdock','=',True),('recoupe','=',False),('implantation','=',False),('typologie_article','=','A1'),], limit=1) 
                        if route_std:
                            line.route_id = route_std.route_id.id
                    if line.product_id.typologie_article == 'A3':
                        # 
                        # Article Sur-Mesure 
                        #
                        route_sm = param_route_obj.search([('xdock','=',True),('recoupe','=',False),('implantation','=',False),('typologie_article','=','A3'),], limit=1) 
                        if route_sm:
                            line.route_id = route_sm.route_id.id   
                    if line.product_id.typologie_article == 'A4':
                        # 
                        # Article Dropship
                        #
                        route_ds = param_route_obj.search([('xdock','=',False),('recoupe','=',False),('implantation','=',False),('typologie_article','=','A4'),], limit=1) 
                        if route_ds:
                            line.route_id = route_ds.route_id.id       
                return True          

    #   
    #  Controle de cohérence des routes logistiques de la commande 
    #           
    def controle_validation_commande_type_article(self):
        erreur_type_article = "0"
        for sale in self:
            #
            # On traite le cas 1 : Si Recoupe coché et pas d'article recoupe 
            #  
            if sale.recoupe:
                erreur_recoupe = True
                for line in sale.order_line:
                    if line.product_id.type == 'service':
                        continue
                    if line.product_id.typologie_article == 'A2':
                        erreur_recoupe = False
                        break
                if erreur_recoupe:
                    erreur_type_article = "1"
                    return erreur_type_article    
            #   
            # On traite le cas 2 : Si XDOCK coché et l'adresse de livraison non XDOCK 
            #     
            if sale.xdock:
                erreur_xdock = False
                if sale.partner_shipping_id.xdock:
                    erreur_xdock = False
                else:
                    erreur_xdock = True  
                if erreur_xdock:
                    erreur_type_article = "2"
                    return erreur_type_article    
            #   
            # On traite le cas 3 : Si un article SM présent dans SO line et un autre article d'un autre type est présent 
            #     
            article_sm = False
            autre_article = False   
            for line in sale.order_line:
                if line.product_id.type == 'service':
                    continue
                if line.product_id.typologie_article == 'A3':
                    article_sm = True 
                else:
                    autre_article = True 
            if article_sm:
                if autre_article:
                    #erreur_type_article = "3"
                    erreur_type_article = "0"
                    return erreur_type_article    
            #   
            # On traite le cas 4 : Si un article Dropship présent dans SO line et si un autre article de type Recoupe ou SM de présent 
            #     
            article_dropship = False
            autre_article = False   
            for line in sale.order_line:
                if line.product_id.type == 'service':
                    continue
                if line.product_id.typologie_article == 'A4':
                    article_dropship = True 
                else:
                    if line.product_id.typologie_article == 'A2' or line.product_id.typologie_article == 'A3':
                        autre_article = True 
            if article_dropship:
                if autre_article:
                    #erreur_type_article = "4"
                    erreur_type_article = "0"
                    return erreur_type_article                      
        return erreur_type_article  

    # 
    #  Recherche route unique sur les lignes 
    #       
    def recherche_route_unique_sur_commande(self, sale):
        if sale:
            nb = 0
            route_id = False
            for line in sale.order_line:
                nb = nb + 1
                if nb == 1:
                    route_id = line.route_id.id
                if line.route_id.id != route_id:
                    route_id = False
                    break
            return route_id 
        else:
            return False    

    #############################################################################################
    #                       Recherche Validation automatique de la commande                     #
    #############################################################################################
    #                                                                                           #
    # 0     - Pas de commande EDI                                                               #
    # 1     - Client n'est pas flagué en « Validation auto »                                    #
    # 2     - Comprenant un article de recoupe (Typologie = article à recouper)                 #
    # 3     - Contient un article SM (Typologie = article sur-mesure)                           #
    # 4     - Contient un article de frais de transport                                         #
    # 5     - Délai demandé supérieur à 21 jours (à affiner)                                    #
    # 6     - Délai demandé inférieur à délai dans fiche client                                 #
    # 7     - Montant supérieure à montant dans fiche client                                    #
    # 8     - Erreur de prix (prix EDI <> de tarif / Si pas de prix EDI => pas d’erreur)        #
    # 9     - N’atteint pas le franco défini dans la fiche client                               #
    # 10    - Existence d'un blocage ou avertissement sur le contact                            #
    # 11    - Existence d'un blocage sur l'article                                              #
    #                                                                                           #
    #############################################################################################
    def recherche_validation_automatique_commande(self, commande):
        company_id = self.env.company 
        for sale in commande:
            # Condition 0 - Pas de commande EDI  
            if sale.commande_edi == False:
                logger.info("_________________")
                logger.info("| blocage N° 0  |")
                logger.info("_________________")
                message_blocage = "Condition 0 - Ce n'est pas une commande EDI "
                sale.message_post(body=message_blocage)
                return False
            # Condition 1 - Client n'est pas flagué en « Validation auto »  
            if sale.partner_id.edi_valid_auto == False:
                logger.info("_________________")
                logger.info("| blocage N° 1  |")
                logger.info("_________________")
                message_blocage = "Condition 1 - Client n'est pas flagué en « Validation auto »"
                sale.message_post(body=message_blocage)
                return False
            # Condition 2 - Comprenant un article de recoupe (Typologie = article à recouper) 
            if sale.recoupe == True:
                logger.info("_________________")
                logger.info("| blocage N° 2  |")
                logger.info("_________________")
                message_blocage = "Condition 2 - Comprenant un article de recoupe (Typologie = article à recouper)"
                sale.message_post(body=message_blocage)
                return False  
            # Condition 3 - Contient un article SM (Typologie = article sur-mesure) 
            article_sm = False
            for line in sale.order_line:
                if line.product_id.type == 'service':
                    continue
                if line.product_id.typologie_article == 'A3':
                    article_sm = True 
            if article_sm:
                logger.info("_________________")
                logger.info("| blocage N° 3  |")
                logger.info("_________________")
                message_blocage = "Condition 3 - Contient un article SM (Typologie = article sur-mesure)"
                sale.message_post(body=message_blocage)
                return False      
            # Condition 4 - Contient un article de frais de transport  
            article_frais_tps = False
            for line in sale.order_line:                
                if line.product_id.art_frais_transport: 
                    article_frais_tps = True 
            if article_frais_tps:
                logger.info("_________________")
                logger.info("| blocage N° 4  |")
                logger.info("_________________")
                message_blocage = "Condition 4 - Contient un article de frais de transport"
                sale.message_post(body=message_blocage)
                return False      
            # Condition 5 - Délai demandé supérieur à 21 jours (fiche client)            
            today = fields.Date.from_string(fields.Date.context_today(self))
            if not sale.partner_id.delai_demande_sup_a:
                nb_jour = 0
            else:
                nb_jour = sale.partner_id.delai_demande_sup_a   
            date_delai = apik_calendar.calcul_date_ouvree(today, nb_jour, company_id.nb_weekend_days, company_id.zone_geo)  
            if sale.date_livraison_demandee > date_delai:    
                logger.info("_________________")
                logger.info("| blocage N° 5  |")
                logger.info("_________________")
                message_blocage = "Condition 5 - Délai demandé supérieur au délai maximum dans la fiche client EDI "
                sale.message_post(body=message_blocage)
                return False
            # Condition 6 - Délai demandé inférieur à délai de livraison dans fiche client             
            if not sale.partner_id.delai_livraison:
                nb_jour = 0
            else:
                nb_jour = sale.partner_id.delai_livraison         
            today = fields.Date.from_string(fields.Date.context_today(self))
            date_delai = apik_calendar.calcul_date_ouvree(today, nb_jour, company_id.nb_weekend_days, company_id.zone_geo)  
            
            logger.info("date_livraison_demandee")
            logger.info(sale.date_livraison_demandee) 
            logger.info("date delai")
            logger.info(date_delai)
                        
            if sale.date_livraison_demandee < date_delai:
                logger.info("_________________")
                logger.info("| blocage N° 6  |")
                logger.info("_________________")
                message_blocage = "Condition 6 - Délai demandé inférieur à délai de livraison dans fiche client"
                sale.message_post(body=message_blocage)
                return False
            # Condition 7 - Montant supérieure à montant dans fiche client             
            if not sale.partner_id.mtt_superieur:
                mtt_superieur = 0
            else:
                mtt_superieur = sale.partner_id.mtt_superieur
            if sale.amount_untaxed > mtt_superieur:
                logger.info("_________________")
                logger.info("| blocage N° 7  |")
                logger.info("_________________")
                message_blocage = "Condition 7 - Montant supérieure à montant dans fiche client"
                sale.message_post(body=message_blocage)
                return False
            # Condition 8 - Erreur de prix (prix EDI <> de tarif / Si pas de prix EDI => pas d’erreur)
            article_erreur = False
            for line in sale.order_line:
                if line.pun_edi:
                    if line.price_unit != line.pun_edi:
                        article_erreur = True
            if article_erreur:
                logger.info("_________________")
                logger.info("| blocage N° 8  |")
                logger.info("_________________")
                message_blocage = "Condition 8 - Erreur de prix (prix EDI <> prix tarif)"
                sale.message_post(body=message_blocage)
                return False
            # Condition 9 - N’atteint pas le franco défini dans la fiche client 
            article_erreur = False
            if sale.amount_untaxed < sale.partner_id.franco_port:
                logger.info("_________________")
                logger.info("| blocage N° 9  |")
                logger.info("_________________")  
                message_blocage = "Condition 9 - N’atteint pas le franco défini dans la fiche client "
                sale.message_post(body=message_blocage)              
                return False
            # condition 10 - Existence d'un blocage ou avertissement sur le contact   
            if sale.partner_id.sale_warn != 'no-message' or sale.partner_id.invoice_warn  != 'no-message' or sale.partner_id.invoice_warn != 'no-message': 
                logger.info("_________________")
                logger.info("| blocage N° 10 |")
                logger.info("_________________")
                message_blocage = "Condition 10 - Existence d'un blocage ou avertissement sur le contact"
                sale.message_post(body=message_blocage)
                return False
            # condition 11 - Existence d'un blocage sur un article  
            article_alerte = False
            for line in sale.order_line:
                if line.product_id.sale_line_warn == 'block':
                    article_alerte = True
            if article_alerte:
                logger.info("_________________")
                logger.info("| blocage N° 11 |")
                logger.info("_________________")
                message_blocage = "Condition 11 - Existence d'un blocage sur un article"
                sale.message_post(body=message_blocage)
                return False 
            logger.info("__________________")
            logger.info("| pas de blocage |")
            logger.info("__________________")
            return True 


class SaleOrderRemisesWizard(models.TransientModel):
    _name = "sale.order.remise.wizard"

    is_return = fields.Boolean('Retour',default=False)

    def confirm_action_reaffectation_remise(self):
        for cde in self:
            for line in cde.order_line:
                if cde.discount1 > 0 or cde.discount2 > 0 or cde.discount3 > 0:
                    line.discounting_type = cde.discounting_type
                    if cde.discount1 > 0:
                        line.discount = cde.discount1
                    if cde.discount2 > 0:
                        line.discount2 = cde.discount2
                    if cde.discount3 > 0:  
                        line.discount3 = cde.discount3  
                    line._compute_amount()
            self.rem_a_affecter = False 
   
 

