import json
import logging
from datetime import date, datetime

from odoo import fields, models
from odoo.tools import config

from odoo.addons.http_routing.models.ir_http import slugify

_logger = logging.getLogger(__name__)


def json_serial(obj):
    _logger.info(obj)
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    else:
        return obj


def is_jsonable(x):
    try:
        json.dumps(x)
        return True
    except Exception as error:
        _logger.error(error)
        return False


class ApikData(models.Model):
    _name = "apik.data"
    _description = "Apik Data"

    name = fields.Char("Nom")
    requete = fields.Text("Requete SQL")
    resultat = fields.Text("Résultat")
    historique = fields.One2many("apik.historique", "requete", string="Historique")
    export_csv = fields.Boolean("Export en CSV ?")
    path = fields.Char("Path du ficher à exporter")
    delimiter = fields.Selection([(",", ","), (";", ";"), ("|", "|")])
    afficher = fields.Boolean("Afficher la requête", default=True)
    vue_cree = fields.Boolean("Vue créée")
    disable_linking = fields.Boolean("Supprimer les liens sur la vue")

    requete_maj = fields.Text("Requete SQL")
    resultat_maj = fields.Text("Résultat")

    def write(self, vals):
        old_requete = self.requete
        requete = vals.get("requete", False)
        if requete and old_requete != requete:
            vals["afficher"] = False

        res = super().write(vals)

        return res

    def executer_maj(self):
        historique_obj = self.env["apik.historique"]
        for r in self:
            if self.env.user.apik_data_select:
                # on se connecte avec les identifiants fournis directement sur la base
                host = config.options.get("db_host") or "localhost"
                base = self.env.cr.dbname
                port = config.options.get("db_port") or "5432"

                import psycopg2

                conn = psycopg2.connect(
                    host=host,
                    user=self.env.user.company_id.apik_data_user,
                    password=self.env.user.company_id.apik_data_password,
                    database=base,
                    port=port,
                )
                cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                # on lance la requête sur le serveur
                cursor.execute(r.requete_maj)
                res = cursor.fetchall()
                r.resultat_maj = str(res)
            else:
                self.env.cr.execute(r.requete_maj)
                try:
                    res = self.env.cr.dictfetchall()
                    r.resultat_maj = str(res)
                except Exception as e:
                    _logger.info(str(e))
                    r.resultat_maj = str(e)
            value = {
                "name": "Requête de MAJ : {}".format(r.requete_maj),
                "requete": r.id,
            }
            historique_obj.create(value)

    def executer(self):
        historique_obj = self.env["apik.historique"]
        for r in self:
            if self.env.user.apik_data_select:
                # on se connecte avec les identifiants fournis directement sur la base
                host = config.options.get("db_host") or "localhost"
                base = self.env.cr.dbname
                port = config.options.get("db_port") or "5432"

                import psycopg2

                conn = psycopg2.connect(
                    host=host,
                    user=self.env.user.company_id.apik_data_user,
                    password=self.env.user.company_id.apik_data_password,
                    database=base,
                    port=port,
                )
                cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                # on lance la requête sur le serveur
                cursor.execute(r.requete)
                res = cursor.fetchall()
                _logger.info(res)
            else:
                self.env.cr.execute(r.requete)
                try:
                    res = self.env.cr.dictfetchall()
                    r.afficher = True
                except Exception as e:
                    _logger.info(str(e))
                    r.afficher = False
            columns = []
            if len(res) > 0:
                for k in res[0]:
                    value = {
                        "title": k,
                        "field": k,
                        "width": len(k) * 20,
                        "minWidth": 80,
                    }
                    columns.append(value)
            res2 = []
            for rs in res:
                val = {}
                for key, value in rs.items():
                    if is_jsonable(value):
                        val[key] = value
                res2.append(val)

            r.resultat = json.dumps(
                {
                    "data": res2,
                    "column": columns,
                },
                default=json_serial,
            )

            historique = historique_obj.search(
                [("name", "=", r.requete), ("requete", "=", r.id)]
            )
            if len(historique) == 0:
                value = {"name": r.requete, "requete": r.id}
                historique_obj.create(value)

    def creer_vue(self):
        self.ensure_one()

        model_obj = self.env["ir.model"]
        self.env["ir.model.fields"]
        action_obj = self.env["ir.actions.act_window"]
        menu_obj = self.env["ir.ui.menu"]
        access_obj = self.env["ir.model.access"]

        dict_sql_odoo = {
            "boolean": "boolean",
            "bigint": "integer",
            "integer": "integer",
            "double precision": "float",
            "numeric": "float",
            "text": "char",
            "character varying": "char",
            "date": "datetime",
            "timestamp without time zone": "datetime",
        }

        name_model = "x_" + slugify(self.name)
        name_model = name_model.replace("-", "_")
        name_model = name_model.replace(":", "_")
        name_model = name_model.replace("/", "_")

        sql = "CREATE OR REPLACE view {} AS SELECT * from ({}) as mon_modele".format(
            name_model, self.requete
        )

        self.env.cr.execute(sql)
        sql_type_column = "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = '{}' ORDER  BY ordinal_position;".format(
            name_model
        )

        self.env.cr.execute(sql_type_column)
        columns = self.env.cr.dictfetchall()

        sql = "drop view {}".format(name_model)
        self.env.cr.execute(sql)

        # on crée chaque champs de colonne dans Odoo
        mon_model = model_obj.search([("model", "=", name_model)])

        if len(mon_model) == 0:
            field_id = []
            for column in columns:
                value_field = {
                    "name": "x_{}".format(column["column_name"]),
                    "field_description": column["column_name"],
                    "ttype": dict_sql_odoo[column["data_type"]],
                    "readonly": True,
                    "store": True,
                }
                field_id.append((0, False, value_field))

            value_model = {
                "name": self.name,
                "model": name_model,
                "field_id": field_id,
            }
            _logger.info(value_model)
            mon_model = model_obj.create(value_model)

            # on crée les droits d'accès
            value_access = {
                "name": self.name,
                "model_id": mon_model.id,
                "perm_create": True,
                "perm_read": True,
                "perm_unlink": True,
                "perm_write": True,
                "group_id": self.env.ref("base.group_system").id,
            }
            access_obj.create(value_access)

        action = action_obj.search([("name", "=", self.name)])

        if len(action) == 0:
            view_obj = self.env["ir.ui.view"]
            action_view_obj = self.env["ir.actions.act_window.view"]

            # on crée l'action qui va permettre de l'afficher et le menu
            value_action = {
                "name": self.name,
                "res_model": name_model,
                "view_mode": "pivot",
            }
            _logger.info(value_action)
            action = action_obj.create(value_action)

            arch_base = (
                '<?xml version="1.0"?><pivot disable_linking="{}" string="{}">'.format(
                    self.disable_linking, name_model
                )
            )
            for f in columns:
                arch_base += '<field name="' + "x_{}".format(f["column_name"]) + '"/>'
            arch_base += "</pivot>"

            # on ajoute la vue tree (pour ne pas avoir que le champs name)
            value_view_pivot = {
                "name": self.name + " pivot",
                "type": "pivot",
                "arch_base": arch_base,
                "model": name_model,
            }

            view = view_obj.create(value_view_pivot)

            value_action_view = {
                "view_id": view.id,
                "view_mode": "pivot",
                "act_window_id": action.id,
            }

            action_view_obj.create(value_action_view)

            # on ajoute le menu

            value_menu = {
                "name": self.name,
                "action": "ir.actions.act_window," + str(action.id),
                "parent_id": self.env.ref("apik_data.menu_apik_data_pivots").id,
            }
            menu_obj.create(value_menu)

        # on drop la table crée par odoo
        sql = "drop table {}".format(name_model)
        _logger.info("drop table : {}".format(sql))
        self.env.cr.execute(sql)

        sql = "SELECT CAST(row_number() OVER () as integer) AS id,CAST(Null as timestamp without time zone) as create_date,CAST(Null as integer) as create_uid, CAST(Null as timestamp without time zone) as write_date, CAST(Null as integer) as write_uid,{} from ({}) as mon_modele".format(
            ",".join(
                [
                    '"{}" as {}'.format(
                        column["column_name"], "x_{}".format(column["column_name"])
                    )
                    for column in columns
                ]
            ),
            self.requete,
        )

        _logger.info(sql)

        # on crée la vue pour remplacer ça
        sql = "CREATE OR REPLACE view {} AS {}".format(name_model, sql)
        self.env.cr.execute(sql)

        self.vue_cree = True
        return self.voir_vue()

    def supprimer_vue(self):
        self.ensure_one()
        model_obj = self.env["ir.model"]
        field_obj = self.env["ir.model.fields"]
        action_obj = self.env["ir.actions.act_window"]
        menu_obj = self.env["ir.ui.menu"]
        access_obj = self.env["ir.model.access"]
        view_obj = self.env["ir.ui.view"]

        name_model = "x_" + slugify(self.name)
        name_model = name_model.replace("-", "_")
        name_model = name_model.replace(":", "_")
        name_model = name_model.replace("/", "_")

        mon_model = model_obj.search([("model", "=", name_model)])

        # on supprime le menu
        menu = menu_obj.search([("name", "=", self.name)])
        if len(menu) > 0:
            menu.unlink()

        views = view_obj.search([("model", "=", name_model)])
        actions = action_obj.search([("res_model", "=", name_model)])
        # on supprime l'action
        actions.unlink()
        # on supprime la vue
        views.unlink()
        # on supprime les règles d'accès
        access = access_obj.search([("model_id", "=", mon_model.id)])
        access.unlink()

        # on supprime les champs
        mon_model = model_obj.search([("model", "=", name_model)])

        # on supprime le modèle
        mon_model.unlink()

        fields = field_obj.search([("model_id", "=", mon_model.id)])
        fields.unlink()

        # on supprime la vue sql
        sql = "drop view if exists {}".format(name_model)
        self.env.cr.execute(sql)
        self.vue_cree = False

    def voir_vue(self):
        self.ensure_one()
        # view_obj = self.env["ir.ui.view"]

        name_model = "x_" + slugify(self.name)
        name_model = name_model.replace("-", "_")
        name_model = name_model.replace(":", "_")
        name_model = name_model.replace("/", "_")

        # views = view_obj.search([("model", "=", name_model)])

        return {
            "name": "{}".format(self.name),
            "view_mode": "pivot",
            "res_model": name_model,
            "type": "ir.actions.act_window",
        }
