# -*- coding: utf-8 -*-

#import json
from odoo.exceptions import UserError, ValidationError
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero
from datetime import datetime, timedelta
from tempfile import TemporaryFile
import base64
import io

from jours_feries_france import JoursFeries

import logging
logger = logging.getLogger(__name__)


def calcul_date_ouvree(date_debut, delai, nb_jour_weekend, zone_geo, type_date='date'):
    #
    # On calcule la date en fonction des jours ouvres de la société
    #
    # Date : date de base pour le calcul 
    # Delai : nbre de jours à ajouter à la date de base
    # nb_jour_weekend : nb de jour de duree du weekend (2 jours = samedi/dimanche, 3 jours = samedi/dimanche/lundi)
    # 
    date_trouve = date_debut
    if not delai:
        delai = 0
    if not nb_jour_weekend:
        nb_jour_weekend = 0   
    if not zone_geo:
        zone_geo = 'Métropole' 


    date_fin = date_debut + timedelta(days=delai)
    #logger.info("date fin")
    #logger.info(date_fin)

    nb_samedi = 0 
    nb_jour_ajout = 0
    nb_jour_ferie = 0
    #
    # On recherche le nombre de samedi entre les 2 dates 
    #
    date_calcul = date_debut
    while date_calcul <= date_fin:  
        jour_semaine = date_calcul.weekday()
        if jour_semaine == 5:
            nb_samedi += 1
        date_calcul = date_calcul + timedelta(days=1)   
    if nb_samedi != 0:
        nb_jour_ajout = nb_samedi * nb_jour_weekend
    nb_semaine = int(nb_jour_ajout/6)   
    nb_jour_ajout = nb_jour_ajout + (nb_semaine * nb_jour_weekend)
    date_trouve = date_debut + timedelta(days=delai+nb_jour_ajout)

    '''
    logger.info("Nb samedi")
    logger.info(nb_samedi)
    logger.info("nb_jour_ajout")
    logger.info(nb_jour_ajout)
    logger.info("nb_semaine")
    logger.info(nb_semaine)
    logger.info("delai+nb_jour_ajout")
    logger.info(delai+nb_jour_ajout)
    logger.info("date Trouvé Avant")
    logger.info(date_trouve)
    '''

    #
    # On regarde s'il y a un ou des jours fériés dans l'intervalle de date
    # 
    date_calcul_ferie = date_debut
    while date_calcul_ferie <= date_trouve:  
        date_ferie = controle_jour_ferie(date_calcul_ferie, zone_geo, type_date)  
        if date_ferie:
            nb_jour_ferie += 1
        date_calcul_ferie = date_calcul_ferie + timedelta(days=1)     

    '''
    logger.info("Nombre de jours fériés trouvés : ")
    logger.info(nb_jour_ferie)
    logger.info("_________________________________")
    '''

    if nb_jour_ferie >=1:
        date_trouve = date_trouve + timedelta(days=nb_jour_ferie)

    #
    # On regarde s'il y a un ou des jours fériés entre la date de début et la date trouvée 
    # 
    nb_jour_ferie_fin = 0
    date_calcul_ferie_fin = date_debut
    while date_calcul_ferie_fin <= date_trouve:  
        date_ferie = controle_jour_ferie(date_calcul_ferie_fin, zone_geo, type_date) 
        if date_ferie:
            nb_jour_ferie_fin += 1
        date_calcul_ferie_fin = date_calcul_ferie_fin + timedelta(days=1)   

    #logger.info("jours férié")    
    #logger.info(nb_jour_ferie)
    #logger.info(nb_jour_ferie_fin)
    if nb_jour_ferie_fin >=1:
        date_trouve = date_trouve + timedelta(days=nb_jour_ferie_fin)

    #logger.info("date trouvée avec jours fériés") 
    #logger.info(date_trouve)   

    # 
    # On regarde si la date trouvé n'est pas un samedi ou un dimanche 
    # 
    jour_date_trouve = date_trouve.weekday()
    if jour_date_trouve == 5:
        date_trouve = date_trouve + timedelta(days=2) 
    if jour_date_trouve == 6:
        date_trouve = date_trouve + timedelta(days=1)  

    #logger.info("date Trouvé apres controle week-end")
    #logger.info(jour_date_trouve)
    #logger.info(date_trouve)
    

    #
    # On regarde si la date trouvée est un jour férié en France
    #    
    erreur_date = True  
    while erreur_date == True:
        erreur_date = controle_jour_ferie(date_trouve, zone_geo, type_date)
        if erreur_date:
            date_trouve = date_trouve + timedelta(days=1) 
            erreur_date = controle_jour_ferie(date_trouve, zone_geo, type_date)  

    #logger.info("date Trouvé finale")
    #logger.info(date_trouve)

    return date_trouve



def calcul_date_ouvree_negative(date_debut, delai, nb_jour_weekend, zone_geo, type_date='date'):
    #
    # On calcule la date en fonction des jours ouvres de la société
    #
    # Date : date de base pour le calcul 
    # Delai : nbre de jours à ajouter à la date de base
    # nb_jour_weekend : nb de jour de duree du weekend (2 jours = samedi/dimanche, 3 jours = samedi/dimanche/lundi)
    # 
    date_trouve = date_debut
    if not delai:
        delai = 0
    if not nb_jour_weekend:
        nb_jour_weekend = 0   
    if not zone_geo:
        zone_geo = 'Métropole' 

    date_fin = date_debut + timedelta(days=delai)

    #logger.info("Delai début"+str(delai))
    #logger.info("Date debut début"+str(date_debut))
    #logger.info("Date de fin début"+str(date_fin))

    nb_samedi = 0 
    nb_jour_ajout = 0
    nb_jour_ferie = 0
    #
    # On recherche le nombre de samedi entre les 2 dates en partant de la date de fin
    #
    date_calcul = date_fin
    while date_calcul <= date_debut:
        jour_semaine = date_calcul.weekday()
        if jour_semaine == 5:
            nb_samedi += 1
        date_calcul = date_calcul + timedelta(days=1)   
    if nb_samedi != 0:
        nb_jour_ajout = nb_samedi * nb_jour_weekend
    nb_semaine = int(nb_jour_ajout/6)   
    nb_jour_ajout = nb_jour_ajout + (nb_semaine * nb_jour_weekend)
    date_trouve = date_debut + timedelta(days=delai-nb_jour_ajout)

    #logger.info("Nb samedi")
    #logger.info(nb_samedi)
    #logger.info("nb_jour_ajout")
    #logger.info(nb_jour_ajout)
    #logger.info("nb_semaine")
    #logger.info(nb_semaine)
    #logger.info("delai-nb_jour_ajout")
    #logger.info(delai-nb_jour_ajout)
    #logger.info("date Trouvé Avant")
    #logger.info(date_trouve)

    #
    # On regarde s'il y a un ou des jours fériés dans l'intervalle de date
    # 
    date_calcul_ferie = date_debut
    while date_calcul_ferie <= date_trouve:  
        date_ferie = controle_jour_ferie(date_calcul_ferie, zone_geo, type_date) 
        if date_ferie:
            nb_jour_ferie += 1
        date_calcul_ferie = date_calcul_ferie + timedelta(days=1)     
    
    #logger.info("Nombre de jours fériés trouvés : ")
    #logger.info(nb_jour_ferie)
    #logger.info("_________________________________")

    if nb_jour_ferie >=1:
        date_trouve = date_trouve + timedelta(days=nb_jour_ferie)
    
    #
    # On regarde s'il y a un ou des jours fériés entre la date de début et la date trouvée 
    #     
    nb_jour_ferie_fin = 0
    date_calcul_ferie_fin = date_trouve

    #logger.info("Date début "+str(date_debut))
    #logger.info("Date fin "+str(date_fin))
    #logger.info("Date calcul férié fin "+str(date_calcul_ferie_fin))
    #logger.info("Date trouvé "+str(date_trouve))
    #logger.info("Zone geo "+str(zone_geo))
    #logger.info("Type date "+str(type_date))
    #logger.info("----------------------")

    while date_calcul_ferie_fin <= date_debut:  
        date_ferie = controle_jour_ferie(date_calcul_ferie_fin, zone_geo, type_date) 
        
        if date_ferie:
            nb_jour_ferie_fin += 1
        date_calcul_ferie_fin = date_calcul_ferie_fin + timedelta(days=1)   
    
    #logger.info("----------------------")
    #logger.info("jours férié")    
    #logger.info(nb_jour_ferie)
    #logger.info(nb_jour_ferie_fin)

    if nb_jour_ferie_fin >=1:
        nb_jour_ferie_fin = nb_jour_ferie_fin * (-1)
        date_trouve = date_trouve + timedelta(days=nb_jour_ferie_fin)      

    #logger.info("date trouvée avec jours fériés") 
    #logger.info(date_trouve)   

    # 
    # On regarde si la date trouvé n'est pas un samedi ou un dimanche 
    # 
    jour_date_trouve = date_trouve.weekday()
    if jour_date_trouve == 5:
        date_trouve = date_trouve + timedelta(days=-1) 
    if jour_date_trouve == 6:
        date_trouve = date_trouve + timedelta(days=-2)  
    
    #logger.info("date Trouvé apres controle week-end")
    #logger.info(jour_date_trouve)
    #logger.info(date_trouve)
    
    #
    # On regarde si la date trouvée est un jour férié en France
    #    
    erreur_date = True  
    while erreur_date == True:
        erreur_date = controle_jour_ferie(date_trouve, zone_geo, type_date)
        if erreur_date:
            date_trouve = date_trouve + timedelta(days=1) 
            erreur_date = controle_jour_ferie(date_trouve, zone_geo, type_date)

    #logger.info("date Trouvé finale")
    #logger.info(date_trouve)

    return date_trouve


def recherche_zone_geographique(zone_geo):
    zone = 'Métropole'
    if zone_geo == "metropole":
        zone = 'Métropole'
    if zone_geo == 'alsacemoselle':
        zone = 'Alsace-Moselle'
    if zone_geo == 'guadeloupe':
        zone = 'Guadeloupe'
    if zone_geo == 'guyane':
        zone = 'Guyane'
    if zone_geo == 'martinique':
        zone = 'Martinique'
    if zone_geo == 'mayotte':
        zone = 'Mayotte'
    if zone_geo == 'nouvellecaledonie':
        zone = 'Nouvelle-Calédonie'
    if zone_geo == 'lareunion':
        zone = 'La Réunion'
    if zone_geo == 'polynesie':
        zone = 'Polynésie Française'
    if zone_geo == 'saintbarth': 
        zone = 'Saint-Barthélémy'
    if zone_geo == 'saintmartin':
        zone = 'Saint-Martin'
    if zone_geo == 'wallis':
        zone = 'Wallis-et-Futuna'
    if zone_geo == 'saintpierre': 
        zone = 'Saint-Pierre-et-Miquelon'
    return zone


def controle_jour_ferie(date_trouve, zone_geo, type_date):
    year = date_trouve.year
    zone = recherche_zone_geographique(zone_geo)
    date_controle = date_trouve

    if type_date == 'datetime':
        date_typedate = date_controle.date()
        date_controle = date_typedate

    premier_janvier = JoursFeries.premier_janvier(year)
    premier_mai = JoursFeries.premier_mai(year)
    huit_mai = JoursFeries.huit_mai(year)
    quatorze_juillet = JoursFeries.quatorze_juillet(year)
    assomption = JoursFeries.assomption(year)
    toussaint = JoursFeries.toussaint(year)
    onze_novembre = JoursFeries.onze_novembre(year)
    noel = JoursFeries.jour_noel(year)
    lundi_paques = JoursFeries.lundi_paques(year)
    ascension = JoursFeries.ascension(year)
    lundi_pentecote = JoursFeries.lundi_pentecote(year)
    vendredi_saint = JoursFeries.vendredi_saint(year,zone)
    deuxieme_jour_noel = JoursFeries.deuxieme_jour_noel(year, zone)
    abolition_esclavage = JoursFeries.abolition_esclavage(year,zone)

    '''
    logger.info("_______ Jours Fériés ________")
    logger.info(type_date)
    logger.info(date_trouve)
    logger.info(date_controle)
    logger.info("------------------")
    logger.info(premier_janvier)
    logger.info(premier_mai)
    logger.info(huit_mai)
    logger.info(quatorze_juillet)
    logger.info(assomption)
    logger.info(toussaint)
    logger.info(onze_novembre)
    logger.info(noel)
    logger.info(lundi_paques)
    logger.info(ascension)
    logger.info(lundi_pentecote)
    logger.info(vendredi_saint)
    logger.info(deuxieme_jour_noel)
    logger.info(abolition_esclavage)
    logger.info("_____________________________")
    '''

    if date_controle == premier_janvier:
        return True 
    if date_controle == premier_mai:
        return True 
    if date_controle == huit_mai:
        return True 
    if date_controle == quatorze_juillet:
        return True 
    if date_controle == assomption:
        return True 
    if date_controle == toussaint:
        return True 
    if date_controle == onze_novembre:
        return True 
    if date_controle == noel:
        return True 
    if date_controle == lundi_paques:
        return True 
    if date_controle == ascension:
        return True 
    if date_controle == lundi_pentecote:
        return True 
    if date_controle == vendredi_saint and zone == 'Alsace-Moselle':
        return True
    if date_controle == deuxieme_jour_noel and zone == 'Alsace-Moselle':
        return True  
    if date_controle == abolition_esclavage and (zone in ('Guadeloupe','Guyane','La Réunion','Martinique','Mayotte','Saint-Barthélémy','Saint-Martin')):
        return True            
    
    return False                                                     

