# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging
logger = logging.getLogger(__name__)
from odoo.addons.http_routing.models.ir_http import slugify
import base64
import io
import csv
from . import utils
import datetime
from mako.exceptions import RichTraceback
from odoo.addons.import_data.models.lib import odoolib

class import_log(models.Model):
    _name = "import.log"

    name = fields.Char('Nom')
    message = fields.Char('Message')
    import_data = fields.Many2one("import.data")

class import_encodage(models.Model):
    _name = "import.encodage"

    name = fields.Char('Nom')
    code = fields.Char('Code')



class import_type_source(models.Model):
    _name = "import.type_source"

    def get_default_encodage(self):
        return self.env.ref('import_data.record_import_encodage_utf8')

    name = fields.Char('Nom',required=True)
    chargeable = fields.Boolean('Chargeable')
    creable = fields.Boolean('Créable')
    type_fichier = fields.Boolean('Fichier')
    type_odoo = fields.Boolean('Odoo')
    type_base = fields.Boolean('Base données')
    code = fields.Char('Code',required=True)
    encodage = fields.Many2one('import.encodage',string='Encodage',default=get_default_encodage)
    

class import_source(models.Model):
    _name = "import.source"

    def get_champs(self):
        for s in self:
            if len(s.modele)>0:
                s.champs = ""
                for f in s.modele.field_id:
                    s.champs += f.name + ", "
            else:
                s.champs = ""

    def get_default_ttype(self):
        return self.env.ref('import_data.record_type_source_1')

    name = fields.Char('Nom',required=True)
    ttype = fields.Many2one('import.type_source',string='Type Source',required=True,default=get_default_ttype)
    type_fichier = fields.Boolean('Type fichier',related='ttype.type_fichier')
    creable = fields.Boolean('Créable',related='ttype.creable')
    chargeable = fields.Boolean('Chargeable',related='ttype.chargeable')
    fichier = fields.Binary('Fichier')
    type_odoo = fields.Boolean('Odoo',related='ttype.type_odoo')
    type_base = fields.Boolean('Base données',related='ttype.type_base')
    modele = fields.Many2one('ir.model')
    model_cree = fields.Boolean("Modèle crée")
    champs = fields.Char('Champs',compute=get_champs)
    donnees_chargees = fields.Boolean("Données chargées")
    encodage = fields.Many2one('import.encodage',string='Encodage',related='ttype.encodage')
    identifiant = fields.Char('Identifiant')
    motdepasse = fields.Char('Mot de passe')
    serveur = fields.Char('Serveur')
    base = fields.Char('Base')
    sql = fields.Text('Requête SQL')
    object_odoo = fields.Char('Objet Odoo')
    delimiter = fields.Char('Delimiter',default=";")
    port = fields.Char('Port',default='5432')
    
    @api.depends('modele')
    def depends_modele(self):
        if len(self.modele)>0:
            self.model_cree = True

    def _create_modele(self,mes_fields):
        model_obj = self.env['ir.model']
        field_obj = self.env['ir.model.fields']
        action_obj = self.env['ir.actions.act_window']
        menu_obj = self.env['ir.ui.menu']
        access_obj = self.env['ir.model.access']

        name_model = 'x_'+slugify(self.name)
        name_model = name_model.replace('-','_')
        name_model = name_model.replace(':','_')
        name_model = name_model.replace('/','_')

        # on crée le modèle avec les champs contenant les colonnes du fichier CSV (tout en char)

        mon_model = model_obj.search([('model','=',name_model)])

        if len(mon_model) == 0:

            value_model = {
                'name': self.name,
                'model': name_model,
                'state': 'manual',
            }
            mon_model = model_obj.create(value_model)


            # on crée les droits d'accès
            value_access = {
                'name': self.name,
                'model_id': mon_model.id,
                'perm_create': True,
                'perm_read': True,
                'perm_unlink': True,
                'perm_write': True,
                'group_id': self.env.ref('base.group_system').id

            }
            access = access_obj.create(value_access)


            for field in mes_fields:
                field = field.replace('-','_')
                field = field.replace(':','_')
                field = field.replace('/','_')
                
                if field == "name":
                    field = "_name"
                if field == "active":
                    field = "_active"
                value_field = {
                    'name': 'x_'+field,
                    'field_description': field,
                    'store': True,
                    'ttype': 'char',
                    'model_id': mon_model.id,
                }
                field_obj.create(value_field)

            value_field = {
                'name': 'x_importe',
                'ttype': 'boolean',
                'model_id': mon_model.id,
            }
            field_obj.create(value_field)
            logger.info(value_field)
            
            value_field = {
                'name': 'x_date_import',
                'ttype': 'date',
                'model_id': mon_model.id,
            }
            field_obj.create(value_field)

        self.modele = mon_model.id
        self.model_cree = True

        action = action_obj.search([('name','=',self.name)])

        if len(action) == 0:
            # on va chercher le model data
            model_data_obj = self.env['ir.model.data']
            view_obj = self.env['ir.ui.view']
            action_view_obj = self.env['ir.actions.act_window.view']

            # on crée l'action qui va permettre de l'afficher et le menu
            value_action = {
                'name': self.name,
                'res_model': name_model,
                'binding_model_id': mon_model.id,
                'view_mode': 'tree,form',
            }

            action = action_obj.create(value_action)

            arch_base = '<?xml version="1.0"?><tree string="' + name_model + '">'
            for f in self.modele.field_id:
                arch_base += '<field name="'+f.name+'"/>'
            arch_base += '</tree>'

            # on ajoute la vue tree (pour ne pas avoir que le champs name)
            value_view_tree = {
                'name': self.name + " tree",
                'type': 'tree',
                'arch_base': arch_base,
                'model': name_model,
            }

            view = view_obj.create(value_view_tree)

            value_action_view = {
                'view_id': view.id,
                'view_mode': 'tree',
                'act_window_id': action.id,

            }

            action_view = action_view_obj.create(value_action_view)


            # on ajoute le menu

            value_menu = {
                'name': self.name,
                'action': "ir.actions.act_window,"+str(action.id),
                'parent_id': self.env.ref('import_data.menu_import_data_data').id,
            }
            menu = menu_obj.create(value_menu)

    def supprimer_modele(self):
        self.ensure_one()
        model_obj = self.env['ir.model']
        field_obj = self.env['ir.model.fields']
        action_obj = self.env['ir.actions.act_window']
        menu_obj = self.env['ir.ui.menu']
        access_obj = self.env['ir.model.access']
        view_obj = self.env['ir.ui.view']
        
        name_model = 'x_'+slugify(self.name)
        name_model = name_model.replace('-','_')
        name_model = name_model.replace(':','_')
        name_model = name_model.replace('/','_')
        
        mon_model = model_obj.search([('model','=',name_model)])
        
        # on supprime le menu
        menu = menu_obj.search([('name','=',self.name)])
        if len(menu)>0:
            menu.unlink()
            
        views = view_obj.search([('model','=',name_model)])
        actions = action_obj.search([('res_model','=',name_model)])
        # on supprime l'action
        actions.unlink()
        # on supprime la vue
        views.unlink()
        # on supprime les règles d'accès
        access = access_obj.search([('model_id','=',mon_model.id)])
        access.unlink()
        
        # on supprime les champs
        mon_model = model_obj.search([('model','=',name_model)])
        # on supprime le modèle
        mon_model.unlink()
        
        fields = field_obj.search([('model_id','=',mon_model.id)])
        fields.unlink()
        
        
        
        

    def creer_modele(self):

        for i in self:
            if i.type_base and i.serveur and i.base and i.sql:
                if i.ttype.code == "mysql":
                    import mysql.connector
                    conn = mysql.connector.connect(host=i.serveur,user=i.identifiant,password=i.motdepasse, database=i.base,port=i.port)
                    cursor = conn.cursor()
                    # on lance la requête sur le serveur
                    # on récupère le liste des colonnes pour construire le modèle dans odoo
                    cursor.execute(i.sql+" LIMIT 0")
                    columns = cursor.column_names
                    i._create_modele(columns)
                if i.ttype.code == "postgresql":
                    import psycopg2
                    conn = psycopg2.connect(host=i.serveur,user=i.identifiant,password=i.motdepasse, database=i.base,port=i.port)
                    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
                    # on lance la requête sur le serveur
                    # on récupère le liste des colonnes pour construire le modèle dans odoo
                    cursor.execute(i.sql+" LIMIT 0")
                    columns = [desc[0] for desc in cursor.description]
                    i._create_modele(columns)


            if i.type_fichier and i.fichier:
                # on ouvre le fichier csv avec ligne de titre
                data = base64.b64decode(i.fichier).decode(i.encodage.code)
                output = io.StringIO(data)
                if i.ttype.code == 'csv':
                    reader = csv.DictReader(output, delimiter=i.delimiter)
                    mes_fields = reader.fieldnames
                    
                    i._create_modele(mes_fields)

            if i.type_odoo and i.ttype.code == 'odoo_distant' and i.serveur and i.port and i.base and i.identifiant and i.motdepasse and i.object_odoo:
                connection = odoolib.get_connection(hostname=i.serveur,database=i.base,login=i.identifiant,password=i.motdepasse,port=int(i.port))
                obj = connection.get_model(i.object_odoo)
                data = obj.search_read([],limit=1)
                if len(data)>0:
                    logger.info([*data[0]])
                    i._create_modele([*data[0]])
                else:
                    logger.info("erreur, aucun objet trouvé")
                
                 

        return {
            'name': "Source",
            'view_mode': 'form',
            'view_id': self.env.ref('import_data.import_source_form').id,
            'view_type': 'form',
            'res_model': 'import.source',
            'res_id': self.id,
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'self',
            'domain': '[]',
        }



    def charger_donnees(self):
        for i in self:
            if i.chargeable:
                if i.type_base and i.sql:
                    if i.ttype.code == 'mysql':
                        import mysql.connector
                        conn = mysql.connector.connect(host=i.serveur,user=i.identifiant,password=i.motdepasse, database=i.base,port=i.port)
                        cursor = conn.cursor(dictionary=True)
                        # on lance la requête sur le serveur
                        cursor.execute(i.sql)
                        columns = cursor.column_names
                        name_model = 'x_'+slugify(i.name)
                        name_model = name_model.replace('-','_')
                        name_model = name_model.replace(':','_')
                        name_model = name_model.replace('/','_')
                        
                        obj = self.env[name_model]

                        for row in cursor.fetchall():
                            value = {}
                            for field in columns:
                                if field in ["name","active"]:
                                    field = "_name"
                                value['x_'+field] = row[field]

                            value['x_importe'] = True
                            value['x_date_import'] = fields.Date.today()


                            obj.create(value)
                        i.donnees_chargees = True
                    if i.ttype.code == 'postgresql':
                        import psycopg2
                        conn = psycopg2.connect(host=i.serveur,user=i.identifiant,password=i.motdepasse, database=i.base,port=i.port)
                        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
                        # on lance la requête sur le serveur
                        cursor.execute(i.sql)
                        columns = [desc[0] for desc in cursor.description]
                        name_model = 'x_'+slugify(i.name)
                        name_model = name_model.replace('-','_')
                        name_model = name_model.replace(':','_')
                        name_model = name_model.replace('/','_')
                        
                        obj = self.env[name_model]

                        for row in cursor.fetchall():
                            value = {}
                            for field in columns:
                                if field in [ "name", "active"]:
                                    value['x__'+field] = row[field]
                                else:
                                    value['x_'+field] = row[field]

                            value['x_importe'] = True
                            value['x_date_import'] = fields.Date.today()


                            obj.create(value)
                        i.donnees_chargees = True


                if i.type_fichier and i.fichier:
                    data = base64.b64decode(i.fichier).decode(i.encodage.code)
                    output = io.StringIO(data)

                    if i.ttype.code=="csv":
                        reader = csv.DictReader(output, delimiter=i.delimiter)
                        mes_fields = reader.fieldnames
                        
                        logger.info(mes_fields)
                        name_model = 'x_'+slugify(i.name)
                        name_model = name_model.replace('-','_')
                        name_model = name_model.replace(':','_')
                        name_model = name_model.replace('/','_')
                        
                        obj = self.env[name_model]

                        for index, row in enumerate(reader):
                            value = {}
                            for field in mes_fields:
                                field2 = field
                                field2 = field2.replace('-','_')
                                field2 = field2.replace(':','_')
                                field2 = field2.replace('/','_')
                                if field2 == "name":
                                    value['x__'+field2] = row[field]
                                else:
                                    value['x_'+field2] = row[field]

                            value['x_importe'] = True
                            value['x_date_import'] = fields.Date.today()


                            obj.create(value)
                        i.donnees_chargees = True

                if i.type_odoo and i.ttype.code == 'odoo_distant' and i.serveur and i.port and i.base and i.identifiant and i.motdepasse and i.object_odoo:
                    name_model = 'x_'+slugify(i.name)
                    name_model = name_model.replace('-','_')
                    name_model = name_model.replace(':','_')
                    name_model = name_model.replace('/','_')
                    
                    obj_odoo = self.env[name_model]
                    
                    connection = odoolib.get_connection(hostname=i.serveur,database=i.base,login=i.identifiant,password=i.motdepasse,port=int(i.port))
                    obj = connection.get_model(i.object_odoo)
                    data = obj.search_read([],limit=1)
                    if len(data)>0:
                        mes_fields = [*data[0]]
                        datas = obj.search_read([])
                        for data in datas:
                            value = {}
                            for field in mes_fields:
                                field2 = field
                                field2 = field2.replace('-','_')
                                field2 = field2.replace(':','_')
                                field2 = field2.replace('/','_')
                                if field2 in [ "name", 'active' ]:
                                    value['x__'+field2] = "{}".format(data[field])
                                
                                else:
                                    value['x_'+field2] = "{}".format(data[field])
                                    
                            value['x_importe'] = True
                            value['x_date_import'] = fields.Date.today()
                            logger.info(value)
                            res = obj_odoo.create(value)
                            logger.info(res)
                        i.donnees_chargees = True


class import_data(models.Model):
    _name = "import.data"
    _order = "ordre"

    name = fields.Char('Nom')
    source = fields.Many2one('import.source',string='Source de données',required=True)
    domain = fields.Char('Domaine',default='[]')
    limit = fields.Integer('Limite',default=0)
    offset = fields.Integer("Offset",default=0)
    moulinette = fields.Text('Moulinette')
    msg_log = fields.One2many('import.log','import_data',string='LOG')
    par_bloc = fields.Boolean("Par Bloc")
    taille_bloc = fields.Integer("Taille Bloc", default=1000)
    champs = fields.Char('Champs', related='source.champs')
    model_cree = fields.Boolean('Modèle Crée',related='source.model_cree')
    donnees_chargees = fields.Boolean('Données chargées',related='source.donnees_chargees')
    ordre = fields.Integer('Ordre')
    records = fields.Text('Records')
    model_action = fields.Many2one('ir.model',string='Model action')
    
    def get_model(self):
        return self.env[self.model_action.model].browse(self.get_active_ids())
    
    def get_active_ids(self):
        return eval(self.records)
    
    def log(self,name,message):
        log_obj = self.env['import.log']

        value_log = {
            'name': name,
            'message': message,
            'import_data': self.id,
        }
        log_obj.create(value_log)

    def char2boolean(self,chaine):
        if type(chaine) is str:
            return chaine.lower() not in ('0', 'false','none','','null')
        else:
            return chaine
    
    def char2date(self,chaine):
        if chaine not in [None,False] and len(chaine)>=10:
            annee = int(chaine[0:4])
            mois = int(chaine[5:7])
            jour = int(chaine[8:10])
            if mois <= 12 and jour <= 31:
                return datetime.datetime(annee,mois,jour).strftime('%Y-%m-%d')
            else:
                return False
        else:
            return False
        
    def char2int(self,chaine):
        try:
            return(int(chaine))
        except Exception as e:
            logger.info(str(e))
            return 0
        
    def char2float(self,chaine):
        try:
            return(float(chaine))
        except Exception as e:
            logger.info(str(e))
            return 0
 
    def char2many2one(self,chaine,objet,field,text="",id='id'):
        obj = self.env[objet]
        
        if self.char2int(chaine)>0:
            # on va chercher si le many2one existe
            many2one_id = obj.search([(field,'=',chaine)],limit=1)
            if len(many2one_id)==0:
                self.log("Erreur","{} non trouvé - value : {} - field : {}".format(text,chaine,field))
                many2one_id = False
            else:
                many2one_id = many2one_id[id]
        else:
            many2one_id = False
    
        return many2one_id

    def char2required(self,chaine,repl):
        if chaine and len(chaine)>0:
            return chaine
        else:
            return repl
    
    def char2selection(self,chaine, dictionnaire,default=''):
        if chaine and chaine in dictionnaire.keys():
            return dictionnaire[chaine]
        else:
            return default
            
    def char2one(self,chaine,dictionnaire,default):
        if chaine and chaine in dictionnaire.keys():
            return dictionnaire[chaine]
        else:
            return default
            
    def char2replace(self,chaine,src,repl,default):
        if chaine and type(chaine) is str:
            return chaine.replace(src,repl)
        else:
            return default

    def lancer_moulinette(self,records=None):
        logger.info(records)
        if records and type(records) is not dict:
            self.records = records.ids
        if not self.par_bloc:
            try:
                obj = self.env[self.source.modele.model]
                datas = obj.search(eval(self.domain),limit=self.limit,offset=self.offset)
                exec(self.moulinette)
            except Exception as e:
                traceback = RichTraceback()
                for (filename, lineno, function, line) in traceback.traceback:
                    logger.info("File %s, line %s, in %s" % (filename, lineno, function))
                    logger.info(line, "\n")
                logger.info("%s: %s" % (str(traceback.error.__class__.__name__), traceback.error)) 
                self.log(self.name,str(e))
        else:
            try:
                obj = self.env[self.source.modele.model]
                count = obj.search_count(eval(self.domain))
                for o in range(0,count,self.taille_bloc):
                    datas = obj.search(eval(self.domain),limit=self.taille_bloc,offset=o)
                    exec(self.moulinette)
                    self.env.cr.commit()
                    logger.info(o)
            except Exception as e:
                traceback = RichTraceback()
                for (filename, lineno, function, line) in traceback.traceback:
                    logger.info("File %s, line %s, in %s" % (filename, lineno, function))
                    logger.info(line, "\n")
                logger.info("%s: %s" % (str(traceback.error.__class__.__name__), traceback.error)) 
                self.log(self.name,str(e))

    def vider_logs(self):
        # log_obj = self.env['import.log']
        # log_ids = log_obj.search([('import_data','=',self.id)])
        self.msg_log.unlink()
        
    def creer_wizard(self):
        wz_obj = self.env['menu.wizard']
        
        value = {
            'name': self.name,
            'moulinette': self.id,
            
        }
        wz = wz_obj.create(value)
        
        return {
            'name': "Création du menu",
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'menu.wizard',
            'type': 'ir.actions.act_window',
            'key2': 'client_action_multi',
            'target': 'new',
            'res_id': wz.id,
            'view_id': self.env.ref('import_data.wizard_menu_form').id,            
        }
             
    def creer_bouton(self):
        wz_obj = self.env['bouton.wizard']
        
        value = {
            'name': self.name,
            'moulinette': self.id,
        }
        
        wz = wz_obj.create(value)
        
        return {
            'name': "Création du bouton",
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'bouton.wizard',
            'type': 'ir.actions.act_window',
            'key2': 'client_action_multi',
            'target': 'new',
            'res_id': wz.id,
            'view_id': self.env.ref('import_data.wizard_bouton_form').id,            
        }
        
    def creer_action(self):
        wz_obj = self.env['action.wizard']
        
        value = {
            'name': self.name,
            'moulinette': self.id,
        }
        
        wz = wz_obj.create(value)
        
        return {
            'name': "Création de l'action",
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'action.wizard',
            'type': 'ir.actions.act_window',
            'key2': 'client_action_multi',
            'target': 'new',
            'res_id': wz.id,
            'view_id': self.env.ref('import_data.wizard_action_form').id,            
        }
