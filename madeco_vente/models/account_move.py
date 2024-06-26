# -*- coding: utf-8 -*-
"""
    License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
    Default Docstring
"""
import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError

logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = 'account.move'

    '''
    @api.depends("global_discount",'invoice_line_ids')    
    def _compute_amount_global_discount(self):
        for move in self:
            total_ht = 0
            price_unit = 0
            amount_global_discount = 0
            amount_before_discount = 0
            if move.global_discount:
                total_ht = 0
                price_unit = 0
                for line in move.invoice_line_ids:
                    if not line.line_global_discount:
                        total_ht += line.price_subtotal
                if total_ht > 0:
                    price_unit = total_ht * move.global_discount  # ICI  / 100

                for line in move.invoice_line_ids:
                    line_price_unit = 0
                    if line.line_global_discount:
                        amount_global_discount = price_unit * line.quantity
                        line_price_unit = price_unit
                    if line.line_global_discount:  
                        mtt_line = line.quantity * line_price_unit
                        if move.move_type == 'in_invoice' or move.move_type == 'in_refund': 
                            debit = price_unit
                            credit = 0
                        else:
                            debit = 0
                            credit = price_unit

                        if debit > 0 or debit < 0:
                            amount_currency = debit
                        if credit > 0 or credit < 0:
                            amount_currency = credit * (-1)
                        tax_base_amount = price_unit


                        line.update({
                            'price_unit': line_price_unit,
                            'price_subtotal': mtt_line,
                            'debit': debit,
                            'credit' : credit,
                            'tax_base_amount': tax_base_amount,
                        })    
                   
                amount_before_discount = total_ht 
            move.update({
                'amount_global_discount': amount_global_discount,
                'amount_before_discount': amount_before_discount,
            })
        '''


    @api.depends('invoice_line_ids')    
    def _compute_amount_global_discount_new(self):
        for move in self:
            total_ht = 0
            price_unit = 0
            amount_global_discount = 0
            amount_before_discount = 0
            for line in move.invoice_line_ids:
                if not line.line_global_discount:
                    amount_before_discount += line.price_subtotal
                else:
                    amount_global_discount += line.price_subtotal

            move.update({
                'amount_global_discount': amount_global_discount,
                'amount_before_discount': amount_before_discount,
            })
        


    groupe_id = fields.Many2one('res.partner',string='Groupe', related='partner_id.groupe_id', store=True, copy=False)
    centrale_id = fields.Many2one('res.partner',string='Centrale', related='partner_id.centrale_id', store=True, copy=False)
    enseigne_id = fields.Many2one('res.partner',string='Enseigne', related='partner_id.enseigne_id', store=True, copy=False)
    destinataire_relance = fields.Selection([('client', 'Client'),('centrale', 'Centrale'),], string='Destinataire des relances', 
        related='partner_id.destinataire_relance', store=True, copy=False)
    piece_imprime = fields.Boolean(string="Pièce imprimée",store=True,default=False)
    partner_order_id = fields.Many2one('res.partner',string='Adresse de commande', compute='_compute_partner_order_id', store=True, copy=False)
    categorie_commande_id = fields.Many2one('categorie.commande',string='Order category', copy=True)
    typologie_commande_id = fields.Many2one('typologie.commande',string='Order typology', copy=True)
    #global_discount = fields.Float(string="Global discount", digits="discount", required=False, default=0.0)
    amount_before_discount = fields.Float(string="Amount before discount", compute='_compute_amount_global_discount_new',default=0)
    amount_global_discount = fields.Float(string="Global discount amount", compute='_compute_amount_global_discount_new',default=0)
    #has_remise_globale_line = fields.Boolean(string="has a global discount line", default=False, store=True, copy=False)

    def _compute_partner_order_id(self):
        sale_obj = self.env['sale.order'] 
        for move in self:
            move.partner_order_id = False
            if move.invoice_origin:
                cde_ids = sale_obj.search([('name', '=', move.invoice_origin)],limit=1)
                if len(cde_ids)>0:
                    for cde in cde_ids:
                        move.partner_order_id = cde.partner_id.id


    @api.model
    def update_piece_imprime(self,docs=False):
        facture_obj = self.env['account.move']        
        flag_imprime = False
        for doc in docs:
            factures = facture_obj.search([('id', '=', doc.id)],)
            if len(factures)>0:
                for fact in factures:
                    if not fact.piece_imprime:
                        flag_imprime = True
                        values_facture = {'piece_imprime': flag_imprime}
                        fact.write(values_facture)

    @api.model  
    def generation_texte_dzb(self,docs=False):
        texte = ''
        for doc in docs:
            if doc.partner_id.num_client_dzb:
                texte = doc.company_id.html_client_dzb_pied % doc.partner_id.num_client_dzb
            else:
                erreur_client_dzb = 'erreur no client dzb'
                texte = doc.company_id.html_client_dzb_pied % doc.partner_id.erreur_client_dzb   
        return texte                    

    #@api.onchange('partner_id')
    #def onchange_partner_id_madeco_vente_facture(self):
    #    for move in self:
    #        if not move.global_discount:
    #            if move.partner_id.sale_global_discount:
    #                move.global_discount = move.partner_id.sale_global_discount   

    #==========================================================================================
    #
    #                 Recherche des tax_tag_ids des lignes Escompte
    #
    #==========================================================================================    
    def recherche_tax_tag_ids_line_escompte(self, tax_id, move_type, type_tag):
        rep_taxe_obj = self.env['account.tax.repartition.line']
        tax_tag_ids = []    
        if move_type == 'out_invoice' or move_type == 'out_refund':
            if tax_id:         
                tax = self.env['account.tax'].search([('id', '=', tax_id), ('type_tax_use', '=', 'purchase')])
                if not tax:
                    raise Warning(_('"%s" Taxe non disponible dans votre système') % tax_id)
                if move_type == 'out_invoice':
                    if type_tag == 'base':
                        rep_taxe = rep_taxe_obj.search([('invoice_tax_id', '=', tax.id), ('repartition_type', '=', 'base')])
                        if rep_taxe:
                            tax_tag_ids = rep_taxe.tag_ids 
                    else:
                        rep_taxe = rep_taxe_obj.search([('invoice_tax_id', '=', tax.id), ('repartition_type', '=', 'tax')])
                        if rep_taxe:
                            tax_tag_ids = rep_taxe.tag_ids    
                else:
                    if type_tag == 'base':
                        rep_taxe = rep_taxe_obj.search([('refund_tax_id', '=', tax.id), ('repartition_type', '=', 'base')])
                        if rep_taxe:
                            tax_tag_ids = rep_taxe.tag_ids 
                    else:
                        rep_taxe = rep_taxe_obj.search([('refund_tax_id', '=', tax.id), ('repartition_type', '=', 'tax')])
                        if rep_taxe:
                            tax_tag_ids = rep_taxe.tag_ids                
            
        else:
            if tax_id:                
                tax = self.env['account.tax'].search([('id', '=', tax_id), ('type_tax_use', '=', 'sale')])
                if not tax:
                    raise Warning(_('"%s" Taxe non disponible dans votre système') % tax_id)
                if move_type == 'in_invoice':
                    if type_tag == 'base':
                        rep_taxe = rep_taxe_obj.search([('invoice_tax_id', '=', tax.id), ('repartition_type', '=', 'base')])
                        if rep_taxe:
                            tax_tag_ids = rep_taxe.tag_ids 
                    else:
                        rep_taxe = rep_taxe_obj.search([('invoice_tax_id', '=', tax.id), ('repartition_type', '=', 'tax')])
                        if rep_taxe:
                            tax_tag_ids = rep_taxe.tag_ids
                else:
                    if type_tag == 'base':
                        rep_taxe = rep_taxe_obj.search([('refund_tax_id', '=', tax.id), ('repartition_type', '=', 'base')])
                        if rep_taxe:
                            tax_tag_ids = rep_taxe.tag_ids 
                    else:
                        rep_taxe = rep_taxe_obj.search([('refund_tax_id', '=', tax.id), ('repartition_type', '=', 'tax')])
                        if rep_taxe:
                            tax_tag_ids = rep_taxe.tag_ids             
                         
            
        return tax_tag_ids   

    #==========================================================================================
    #
    #                 Calcul du montant de l'escompte 
    #
    #==========================================================================================  
    def calcul_montant_total_des_lignes(self,move): 
        company_id =  self.env.user.company_id       
                
        mont_tot_escompte = 0
        for line in move.invoice_line_ids:

            if line.price_subtotal:
                mont_tot_escompte += line.price_subtotal                

        mont_a_escompter = 0
        if mont_tot_escompte > 0:
            if company_id.taux_escompte:
                tx = company_id.taux_escompte/100
                mont_a_escompter = mont_tot_escompte * tx  

        return mont_a_escompter

    
    #==========================================================================================================
    #
    #                 Surcharge de la création d'une facture pour calcul de l'escompte DZB + Remise Globale
    #
    #==========================================================================================================  
    @api.model_create_multi
    def create(self, vals_list):
        company_id =  self.env.company
        remise_zfra = False

        if any('invoice_line_ids' in vals for vals in vals_list):
            for vals in vals_list:
                vals = dict(vals)
                if vals.get('invoice_line_ids'):
                    invoice_lines = vals.get('invoice_line_ids')
                    remise_zfra = False
                    # 
                    # On recherche si une remise globale est présente sur la facture 
                    #
                    for lines in invoice_lines:                        
                        line = lines[2]
                        product_id = line['product_id']
                        if product_id == company_id.product_rem_global_id.id:
                            remise_zfra = True 
                            break                        
                    # 
                    # On a trouve une remise globale 
                    #            
                    if remise_zfra:
                        mtt_ht = 0
                        tx_remise = 0
                        # 
                        # On recalcule le montant de la remise par rapport aux montants HT des lignes facturées
                        #
                        for lines in invoice_lines:                        
                            line = lines[2]
                            product_id = line['product_id']
                            quantity = line['quantity']
                            price_unit = line['price_unit']
                            rem1 = line['discount']
                            rem2 = line['discount2']
                            rem3 = line['discount3']
                            
                            if product_id != company_id.product_rem_global_id.id:
                                mtt_ligne = quantity * price_unit 
                                if rem1 != 0:
                                    mtt_ligne = mtt_ligne * (1 + (rem1/100))
                                if rem2 != 0:
                                    mtt_ligne = mtt_ligne * (1 + (rem2/100))
                                if rem3 != 0:    
                                    mtt_ligne = mtt_ligne * (1 + (rem3/100))
                                remise_zfra = True 
                                mtt_ht += mtt_ligne
                            else:
                                sale_line_ids = line['sale_line_ids']
                                for sale_line in sale_line_ids:
                                    logger.info(sale_line) 
                                    logger.info(sale_line[1]) 
                                    sale_line_id = sale_line[1]  
                                    sale_line_trouve = self.env['sale.order.line'].search([('id', '=', sale_line_id)])
                                    if sale_line_trouve:
                                        tx_remise = sale_line_trouve.order_id.global_discount
                                        break
                        mtt_remise = mtt_ht * tx_remise                          
                        # 
                        # On met à jour le montant de la ligne de remise globale 
                        #
                        for lines in invoice_lines:                        
                            line = lines[2]
                            product_id = line['product_id']
                            price_unit = line['price_unit']
                            if product_id == company_id.product_rem_global_id.id:
                                line['price_unit'] = mtt_remise
                                break

        rslt = super(AccountMove, self).create(vals_list)

        if rslt: 
            if remise_zfra:
                if rslt.invoice_origin:
                    self.maj_ligne_remise_zrfa_sur_commande(rslt)
        
        return rslt  

    #==========================================================================================
    #
    #      Mise à jour des quantités facturées sur la ligne de remise globale si présente
    #
    #==========================================================================================    
    def maj_ligne_remise_zrfa_sur_commande(self, account_move): 
        company_id =  self.env.company
        if account_move.invoice_origin:
            sale_trouve = self.env['sale.order'].search([('name', '=', account_move.invoice_origin)],limit=1)
            if sale_trouve:  
                tout_facture = True 
                for line in sale_trouve.order_line:
                    if line.product_qty != line.qty_invoiced:
                        tout_facture = False 
                        break
                if not tout_facture:  
                    for line in sale_trouve.order_line:
                        if line.product_id.id == company_id.product_rem_global_id.id:  
                            line.qty_invoiced = 0                       

    #==========================================================================================
    #
    #                 Recherche des tax_tag_ids des lignes Article
    #
    #==========================================================================================    
    def recherche_tax_tag_ids_line_article(self, tax_id, move_type, type_tag):
        rep_taxe_obj = self.env['account.tax.repartition.line']
        tax_tag_ids = []    
        if move_type == 'out_invoice' or move_type == 'out_refund':
            if tax_id:         
                tax = self.env['account.tax'].search([('id', '=', tax_id), ('type_tax_use', '=', 'sale')])
                if not tax:
                    raise Warning(_('"%s" Taxe non disponible dans votre système') % tax_id)
                if move_type == 'out_invoice':
                    if type_tag == 'base':
                        rep_taxe = rep_taxe_obj.search([('invoice_tax_id', '=', tax.id), ('repartition_type', '=', 'base')])
                        if rep_taxe:
                            tax_tag_ids = rep_taxe.tag_ids 
                    else:
                        rep_taxe = rep_taxe_obj.search([('invoice_tax_id', '=', tax.id), ('repartition_type', '=', 'tax')])
                        if rep_taxe:
                            tax_tag_ids = rep_taxe.tag_ids    
                else:
                    if type_tag == 'base':
                        rep_taxe = rep_taxe_obj.search([('refund_tax_id', '=', tax.id), ('repartition_type', '=', 'base')])
                        if rep_taxe:
                            tax_tag_ids = rep_taxe.tag_ids 
                    else:
                        rep_taxe = rep_taxe_obj.search([('refund_tax_id', '=', tax.id), ('repartition_type', '=', 'tax')])
                        if rep_taxe:
                            tax_tag_ids = rep_taxe.tag_ids                
            
        else:
            if tax_id:                
                tax = self.env['account.tax'].search([('id', '=', tax_id), ('type_tax_use', '=', 'purchase')])
                if not tax:
                    raise Warning(_('"%s" Taxe non disponible dans votre système') % tax_id)
                if move_type == 'in_invoice':
                    if type_tag == 'base':
                        rep_taxe = rep_taxe_obj.search([('invoice_tax_id', '=', tax.id), ('repartition_type', '=', 'base')])
                        if rep_taxe:
                            tax_tag_ids = rep_taxe.tag_ids 
                    else:
                        rep_taxe = rep_taxe_obj.search([('invoice_tax_id', '=', tax.id), ('repartition_type', '=', 'tax')])
                        if rep_taxe:
                            tax_tag_ids = rep_taxe.tag_ids
                else:
                    if type_tag == 'base':
                        rep_taxe = rep_taxe_obj.search([('refund_tax_id', '=', tax.id), ('repartition_type', '=', 'base')])
                        if rep_taxe:
                            tax_tag_ids = rep_taxe.tag_ids 
                    else:
                        rep_taxe = rep_taxe_obj.search([('refund_tax_id', '=', tax.id), ('repartition_type', '=', 'tax')])
                        if rep_taxe:
                            tax_tag_ids = rep_taxe.tag_ids             
            
        return tax_tag_ids 


    '''
    #==========================================================================================================
    #
    #                 On calcule la ligne de remise globale à ajouter 
    #
    #==========================================================================================================  
    def create_remise_globale_line(self):
        accountmoveline = self.env['account.move.line']
        company_id = self.env.company 

        # Apply fiscal position
        taxes = company_id.product_rem_global_id.taxes_id.filtered(lambda t: t.company_id.id == self.company_id.id)
        taxes_ids = taxes.ids
        if self.partner_id and self.fiscal_position_id:
            taxes_ids = self.fiscal_position_id.map_tax(taxes, company_id.product_rem_global_id, self.partner_id).ids
        
        # 
        # on calcule le prix unitaire en fonction du taux de remise et de la somme des lignes HT
        #
        if self.invoice_line_ids:
            total_ht = 0
            for line in self.invoice_line_ids:
                if not line.line_global_discount:
                    total_ht += line.price_subtotal
            if total_ht > 0:
                price_unit = total_ht * self.global_discount      # ICI / 100  
            self.has_remise_globale_line = True
            if company_id.product_rem_global_id.description_sale:
                designation = company_id.product_rem_global_id.description_sale
            else:
                designation = company_id.product_rem_global_id.name
            no_ligne = 9998

            if self.move_type == 'in_invoice' or self.move_type == 'in_refund': 
                compte = company_id.product_rem_global_id.product_tmpl_id.property_account_expense_id.id
            else:
                compte = company_id.product_rem_global_id.product_tmpl_id.property_account_income_id.id  

            tax_ids = [] 
            if self.move_type == 'in_invoice' or self.move_type == 'in_refund': 
                if company_id.product_rem_global_id.supplier_taxes_id:     
                    for rem_global_id in company_id.product_rem_global_id.supplier_taxes_id:
                        rem_global = self.env['account.tax'].search([('id', '=', rem_global_id.id), ('type_tax_use', '=', 'purchase')])
                        if not rem_global:
                            raise Warning(_('"%s" Taxe non disponible dans votre système') % company_id.product_rem_global_id.taxes_id.name)
                        tax_ids.append(rem_global.id)  
            else:    
                if company_id.product_rem_global_id.taxes_id:     
                    for rem_global_id in company_id.product_rem_global_id.taxes_id:
                        rem_global = self.env['account.tax'].search([('id', '=', rem_global_id.id), ('type_tax_use', '=', 'sale')])
                        if not rem_global:
                            raise Warning(_('"%s" Taxe non disponible dans votre système') % company_id.product_rem_global_id.taxes_id.name)
                        tax_ids.append(rem_global.id) 

            if self.move_type == 'in_invoice' or self.move_type == 'in_refund': 
                debit = price_unit
                credit = 0
            else:
                debit = 0
                credit = price_unit

            if debit > 0 or debit < 0:
                amount_currency = debit
            if credit > 0 or credit < 0:
                amount_currency = credit * (-1)
            tax_base_amount = price_unit

            if self.move_type == 'in_invoice' or self.move_type == 'in_refund': 
                if company_id.product_rem_global_id.supplier_taxes_id:
                    tax = company_id.product_rem_global_id.supplier_taxes_id.id
                    type_tag = 'tax'
                    tax_tag_ids = self.recherche_tax_tag_ids_line_article(tax, self.move_type, type_tag)
                else:
                    tax_tag_ids = [[6, False, []]] 
            else:
                if company_id.product_rem_global_id.taxes_id:        
                    tax = company_id.product_rem_global_id.taxes_id.id
                    type_tag = 'tax'
                    tax_tag_ids = self.recherche_tax_tag_ids_line_article(tax, self.move_type, type_tag)
                else:
                    tax_tag_ids = [[6, False, []]]     

            values = {
                'move_id': self.id,
                'quantity': -1,
                'product_uom_id': company_id.product_rem_global_id.uom_id.id,
                'product_id': company_id.product_rem_global_id.id,
                'price_unit': price_unit,
                'line_global_discount': True,
                'tax_ids': [(6, 0, taxes_ids)],
                'account_id': compte,
                'recompute_tax_line': False, 
                'name': designation,
                'exclude_from_invoice_tab': False,
                'debit': debit,
                'credit': credit,
                'tax_repartition_line_id': False,
                'tax_base_amount': tax_base_amount,
                'amount_currency': amount_currency,
                'date_maturity': False,     
                'tax_exigible': True, 
                'analytic_account_id': False, 
                'analytic_tag_ids': [[6, False, []]], 
                'display_type': False, 
                'is_rounding_line': False, 
                'exclude_from_invoice_tab': False, 
                'predict_from_name': False,
                'partner_id': self.partner_id.id,
                'sequence': no_ligne,   
            }
            
            dict = {
                'name': designation,
                'price_unit': price_unit,
                'quantity': -1,
                'product_uom_id': company_id.product_rem_global_id.uom_id.id,
                'product_id': company_id.product_rem_global_id.id,
                'debit': debit,
                'credit': credit,
                'account_id': compte,
                'move_id': self.id,
                'exclude_from_invoice_tab': True,
                'partner_id': self.partner_id.id,
                'company_id': company_id.id,
                'company_currency_id': company_id.currency_id.id,
                'line_global_discount': True,
            }
           
            new_line = accountmoveline.sudo().create(dict)              
        else:
            new_line = False    
        return new_line

    
    #==========================================================================================================
    #
    #                 Surcharge de la modification d'une facture pour calcul de la remise globale
    #
    #==========================================================================================================  
    def write(self, vals):
        facture_obj = self.env['account.move'] 
        res = super(AccountMove, self).write(vals)
        if res:
            facture = facture_obj.search([('id','=',self.id)], limit=1) 
            if facture:
                if not facture.has_remise_globale_line:
                    if facture.global_discount != 0:
                        facture.create_remise_globale_line()    
        return res 
    '''