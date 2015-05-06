# -*- encoding: utf-8 -*-

from django.conf import settings
from django.contrib.gis.geos import Point
from django.utils.translation import ugettext as _

from geotrek.common.models import Theme
from geotrek.common.parsers import (ExcelParser, AttachmentParserMixin,
                                    TourInSoftParser, GlobalImportError,
                                    RowImportError, ValueImportError)
from geotrek.tourism.models import InformationDesk, InformationDeskType, TouristicContent, TouristicContentType
from geotrek.trekking.models import Trek, Practice, TrekRelationship, POI, POIType
from geotrek.trekking.parsers import TrekParser
from geotrek.zoning.parsers import CityParser


class CG44TourInSoftParser(AttachmentParserMixin, TourInSoftParser):
    base_url = 'http://cdt44.media.tourinsoft.eu/upload/'


class CG44TouristicContentParser(CG44TourInSoftParser):
    model = TouristicContent
    eid = 'eid'
    fields = {
        'eid': 'SyndicObjectID',
        'name': 'SyndicObjectName',
        'description_teaser': 'DescriptifSynthetique',
        'description': 'Descriptif',
        'contact': ('Adresse1', 'Adresse1Suite', 'Adresse2', 'Adresse3', 'CodePostal', 'Commune', 'Cedex'),
        'email': 'CommMail',
        'website': 'CommWeb',
        'geom': ('GmapLatitude', 'GmapLongitude'),
    }
    natural_keys = {
        'category': 'label',
        'type1': 'label',
        'type2': 'label',
    }

    def filter_description(self, src, val):
        return val or ""  # transform null to blank

    def filter_description_teaser(self, src, val):
        return val or ""  # transform null to blank

    def filter_contact(self, src, val):
        (Adresse1, Adresse1Suite, Adresse2, Adresse3, CodePostal, Commune, Cedex) = val
        lines = [line for line in [
            ' '.join([part for part in [Adresse1, Adresse1Suite] if part]),
            Adresse2,
            Adresse3,
            ' '.join([part for part in [CodePostal, Commune, Cedex] if part]),
        ] if line]
        return '<br>'.join(lines)

    def filter_geom(self, src, val):
        lat, lng = val
        if lng == '' or lat == '':
            raise RowImportError(u"Required value for fields 'GmapLatitude' and 'GmapLongitude'.")
        geom = Point(float(lng), float(lat), srid=4326)  # WGS84
        geom.transform(settings.SRID)
        return geom


class CG44POIParser(CG44TourInSoftParser):
    model = POI
    eid = 'eid'
    fields = {
        'eid': 'SyndicObjectID',
        'name': 'SyndicObjectName',
        'description': ('Adresse1', 'Adresse1Suite', 'Adresse2', 'Adresse3', 'CodePostal', 'Commune', 'Cedex', 'CommMail', 'CommWeb'),
        'geom': ('GmapLatitude', 'GmapLongitude'),
    }
    natural_keys = {
        'type': 'label',
    }

    def filter_description(self, src, val):
        (Adresse1, Adresse1Suite, Adresse2, Adresse3, CodePostal, Commune, Cedex, CommMail, CommWeb) = val
        lines = [line for line in [
            ' '.join([part for part in [Adresse1, Adresse1Suite] if part]),
            Adresse2,
            Adresse3,
            ' '.join([part for part in [CodePostal, Commune, Cedex] if part]),
            u'<a href="mailto:{email}">{email}</a>'.format(email=CommMail) if CommMail else '',
            u'<a href="{url}">{url}</a>'.format(url=CommWeb) if CommWeb else '',
        ] if line]
        return '<br>'.join(lines)

    def filter_geom(self, src, val):
        lat, lng = val
        if lng == '' or lat == '':
            raise RowImportError(u"Required value for fields 'GmapLatitude' and 'GmapLongitude'.")
        geom = Point(float(lng), float(lat), srid=4326)  # WGS84
        geom.transform(settings.SRID)
        return geom


class CG44HebergementParser(CG44POIParser):
    filename = 'http://wcf.tourinsoft.com/Syndication/cdt44/b94de37c-b0b1-414f-9559-53510be235dc/Objects'
    constant_fields = {
        'type': u"Hébergement",
        'published': True,
    }
    non_fields = {
        'attachments': 'Photos',
    }


class CG44RestaurationParser(CG44POIParser):
    filename = 'http://wcf.tourinsoft.com/Syndication/cdt44/e079fe27-11ad-4389-ac67-34bda49cc324/Objects'
    constant_fields = {
        'type': u"Restauration",
        'published': True,
    }
    non_fields = {
        'attachments': 'Photos',
    }


class CG44AVoirParser(CG44TouristicContentParser):
    filename = 'http://wcf.tourinsoft.com/Syndication/cdt44/99c93523-4194-428c-97f4-56bd3f774982/Objects'
    constant_fields = {
        'category': u"A voir",
        'published': True,
    }
    #m2m_fields = {
        #'type1': 'ObjectTypeName',
    #}
    non_fields = {
        'attachments': 'Photos',
    }


class CG44AFaireParser(CG44TouristicContentParser):
    filename = 'http://wcf.tourinsoft.com/Syndication/cdt44/7b171134-26bf-485f-b1e1-65f9f4187c6f/Objects'
    constant_fields = {
        'category': u"A faire",
        'published': True,
    }
    non_fields = {
        'attachments': 'Photos',
    }


class CG44LADTrekParser(AttachmentParserMixin, TourInSoftParser):
    filename = 'http://wcf.tourinsoft.com/Syndication/cdt44/31cd7100-e547-4780-8292-53dabbc884a9/Objects'
    base_url = 'http://cdt44.media.tourinsoft.eu/upload/'
    model = Trek
    update_only = True
    warn_on_missing_fields = True
    eid = 'eid2'
    duplicate_eid_allowed = True
    information_desk_type_name = u"Office du tourisme"
    fields = {
        'eid2': 'SyndicObjectID',
        'description_teaser': 'DescriptifSynthetique',
        'description': 'Descriptif',
    }
    m2m_fields = {
        #'information_desks': ('Tel', 'Contact', 'Mail'),
    }
    non_fields = {
        'attachments': 'Photos',
    }

    def start(self):
        super(CG44LADTrekParser, self).start()
        try:
            self.information_desk_type = InformationDeskType.objects.get(label=self.information_desk_type_name)
        except InformationDeskType.DoesNotExist:
            raise GlobalImportError(u"Information desk type '{name}' does not exists in Geotrek-Admin. Please add it.".format(name=self.information_desk_type_name))

    def filter_information_desks(self, src, val):
        tel, contact, mail = val
        if not contact:
            return []
        information_desk = self.obj.information_desks.first()
        if not information_desk:
            information_desk = InformationDesk(type=self.information_desk_type)
        information_desk.phone = tel
        information_desk.name = contact
        information_desk.email = mail
        information_desk.save()
        return [information_desk]


class CG44TrekParser(TrekParser):
    warn_on_missing_fields = True
    eid = 'eid'
    fields = {
        'eid': 'NUM_OBJ',
        'name': 'FIRST_ALIA',
        'duration': ('FIRST_PARC', 'FIRST_USAG'),
        'difficulty': 'FIRST_DIFF',
        'eid2': 'FIRST_GENC',
        'route': 'FIRST_CARA',
        'practice': 'FIRST_USAG',
        'geom': 'geom',
    }
    m2m_fields = {
        'themes': 'FIRST_AVIS',
    }
    non_fields = {
        'related_treks': 'FIRST_LIAI',
    }
    field_options = {
        'route': {'mapping': {u"Boucle": u"Boucle", u"Itinerance": u"Itinérance"}, 'partial': True},
        'themes': {'mapping': {u"VIGNOBLE": u"Vignoble", u"LITTORAL": u"Littoral", u"FLEUVE ET RIVIERE": u"Fleuve et rivière", u"CAMPAGNE": u"Campagne", u"MARAIS": u"Marais", u"PATRIMOINE": u"Patrimoine", u"INCONTOURNABLE": u"Incontournables"}},
    }
    FIRST_ALIA_to_pk = {}
    relationships = []

    def end(self):
        for pk_a, name_b in self.relationships:
            try:
                pk_b = self.FIRST_ALIA_to_pk[name_b]
            except KeyError:
                self.add_warning(u"Bad value '{name}' for field FIRST_LIAI (separated by {separator}). No trek with this name in data to import.".format(name=name_b, separator=self.separator))
                continue
            TrekRelationship.objects.get_or_create(
                trek_a=Trek.objects.get(pk=pk_a),
                trek_b=Trek.objects.get(pk=pk_b),
                is_circuit_step=True
            )
        super(CG44TrekParser, self).end()

    def parse_row(self, row):
        super(CG44TrekParser, self).parse_row(row)
        if self.obj:
            self.FIRST_ALIA_to_pk[row['FIRST_ALIA']] = self.obj.pk

    def filter_name(self, src, val):
        return val.split(':', 1)[1].strip()

    def filter_practice(self, src, val):
        val = [subval.strip() for subval in val.split(self.separator)]
        if not self.practice in val:
            raise RowImportError(u"Bad value '{val}' for field {src} (separated by '{separator}'). Should contain '{practice}'.".format(val=val, src=src, separator=self.separator, practice=self.practice))
        return self.filter_fk(src, self.practice, Practice, 'name')

    def filter_duration(self, src, val):
        duration, usages = val
        first_usage = usages.split(self.separator)[0].strip()
        if first_usage == self.practice:
            return super(CG44TrekParser, self).filter_duration(src, duration)
        else:
            raise ValueImportError(u"Ignore duration since it does not correspond to practice")

    def save_related_treks(self, src, val):
        if not val:
            return
        val = val.split(self.separator)
        self.relationships += [(self.obj.pk, name.strip()) for name in val]


class CG44PedestreTrekParser(CG44TrekParser):
    practice = u"Pédestre"

    def filter_eid(self, src, val):
        return 'P-' + str(val)


class CG44VTTTrekParser(CG44TrekParser):
    practice = u"VTT"

    def filter_eid(self, src, val):
        return 'V-' + str(val)


class CG44EquestreTrekParser(CG44TrekParser):
    practice = u"Equestre"

    def filter_eid(self, src, val):
        return 'E-' + str(val)


class CG44AVeloTrekParser(TrekParser):
    warn_on_missing_fields = True
    eid = 'eid'
    fields = {
        'eid': 'ID_LOCAL',
        'name': 'INTITULE',
        'practice': 'USAGE',
        'duration': 'DUREE',
        'difficulty': 'NIVEAU',
        'route': 'TYPE',
        'eid2': 'ID_LAD',
        'geom': 'geom',
    }
    m2m_fields = {
        'themes': ('THEME', 'PRIORITE'),
    }
    non_fields = {
        'related_treks': ('ID_ITI', 'ORDRE_ETAP'),
    }
    field_options = {
        'difficulty': {'mapping': {1: u"Facile", 2: u"Moyen", 3: u"Difficile"}},
        'route': {'mapping': {1: u"Boucle", 2: u"Itinérance"}},
    }
    relationships = {}

    def end(self):
        for treks in self.relationships.itervalues():
            for etap, trek_a in treks.items():
                trek_b = treks.get(etap + 1)
                if not trek_b:
                    continue
                TrekRelationship.objects.get_or_create(
                    trek_a=trek_a,
                    trek_b=trek_b,
                    is_circuit_step=True
                )
        super(CG44AVeloTrekParser, self).end()

    def filter_eid(self, src, val):
        return 'C-' + str(val)

    def filter_themes(self, src, val):
        val_theme, val_priorite = val
        val_theme = str(val_theme)
        val_theme = self.filter_m2m(src, val_theme, Theme, 'label', {'1': u"Vignoble", '2': u"Littoral", '3': u"Fleuve et rivière", '4': u"Campagne", '5': u"Marais", '6': u"Patrimoine", '7': u"Incontournables"})
        if val_priorite == 1:
            try:
                val_priorite = [Theme.objects.get(label='Incontournables')]
            except Theme.DoesNotExist:
                self.add_warning(u"Theme 'Incontournables' does not exists in Geotrek-Admin. Please add it.")
                val_priorite = []
        else:
            val_priorite = []
        return val_theme + val_priorite

    def save_related_treks(self, src, val):
        iti, etap = val
        if not iti or etap == 0:
            return
        self.relationships.setdefault(iti, {})
        self.relationships[iti][int(etap)] = self.obj


class CG44CityParser(CityParser):
    warn_on_missing_fields = True
    fields = {
        'code': 'INSEE',
        'name': 'NOM',
        'geom': 'geom',
    }
