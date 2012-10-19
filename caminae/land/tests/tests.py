from django.test import TestCase
from django.conf import settings
from django.contrib.gis.geos import LineString, Polygon, MultiPolygon
from django.core.urlresolvers import reverse

from caminae.mapentity.tests import MapEntityTest
from caminae.authent.factories import PathManagerFactory

from caminae.core.models import TopologyMixin
from caminae.core.factories import PathFactory, PathAggregationFactory
from caminae.common.factories import OrganismFactory
from caminae.land.models import (PhysicalEdge, LandEdge, CompetenceEdge,
    WorkManagementEdge, SignageManagementEdge, City, RestrictedArea)


from caminae.land.factories import (PhysicalEdgeFactory, LandEdgeFactory, DistrictEdgeFactory,
    CompetenceEdgeFactory, WorkManagementEdgeFactory, SignageManagementEdgeFactory, 
    PhysicalTypeFactory, LandTypeFactory)


class LandEdgeTest(TestCase):
    
    def test_helpers(self):
        p = PathFactory.create()
        self.assertEquals(len(p.lands), 0)
        l = LandEdgeFactory.create(no_path=True)
        PathAggregationFactory.create(topo_object=l, path=p)
        self.assertItemsEqual(p.lands, [l])


class DistrictEdgeTest(TestCase):
    
    def test_helpers(self):
        p = PathFactory.create()
        self.assertEquals(len(p.districts), 0)
        d = DistrictEdgeFactory.create(no_path=True)
        PathAggregationFactory.create(topo_object=d, path=p)
        self.assertItemsEqual(p.districts, [d.district])


class PhysicalEdgeViewsTest(MapEntityTest):
    model = PhysicalEdge
    modelfactory = PhysicalEdgeFactory
    userfactory = PathManagerFactory

    def get_good_data(self):
        path = PathFactory.create()
        return {
            'physical_type': PhysicalTypeFactory.create().pk,
            'topology': '{"paths": [%s]}' % path.pk,
        }


class LandEdgeViewsTest(MapEntityTest):
    model = LandEdge
    modelfactory = LandEdgeFactory
    userfactory = PathManagerFactory

    def get_good_data(self):
        path = PathFactory.create()
        return {
            'land_type': LandTypeFactory.create().pk,
            'topology': '{"paths": [%s]}' % path.pk,
        }


class CompetenceEdgeViewsTest(MapEntityTest):
    model = CompetenceEdge
    modelfactory = CompetenceEdgeFactory
    userfactory = PathManagerFactory

    def get_good_data(self):
        path = PathFactory.create()
        return {
            'organization': OrganismFactory.create().pk,
            'topology': '{"paths": [%s]}' % path.pk,
        }


class WorkManagementEdgeViewsTest(MapEntityTest):
    model = WorkManagementEdge
    modelfactory = WorkManagementEdgeFactory
    userfactory = PathManagerFactory

    def get_good_data(self):
        path = PathFactory.create()
        return {
            'organization': OrganismFactory.create().pk,
            'topology': '{"paths": [%s]}' % path.pk,
        }



class SignageManagementEdgeViewsTest(MapEntityTest):
    model = SignageManagementEdge
    modelfactory = SignageManagementEdgeFactory
    userfactory = PathManagerFactory

    def get_good_data(self):
        path = PathFactory.create()
        return {
            'organization': OrganismFactory.create().pk,
            'topology': '{"paths": [%s]}' % path.pk,
        }


class CouchesSIGTest(TestCase):

    def test_views_status(self):
        for layer in ['city', 'restrictedarea', 'district']:
            url = reverse('land:%s_layer' % layer)
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)

    def test_troncons_link(self):
        p1 = PathFactory.create(geom=LineString((0,0,0), (1,1,1)))
        p2 = PathFactory.create(geom=LineString((1,1,1), (3,3,3)))
        p3 = PathFactory.create(geom=LineString((3,3,3), (4,4,4)))
        p4 = PathFactory.create(geom=LineString((4,1,1), (6,2,2), (4,3,3)))

        # Paths should not be linked to anything at this stage
        self.assertEquals(p1.aggregations.count(), 0)
        self.assertEquals(p2.aggregations.count(), 0)
        self.assertEquals(p3.aggregations.count(), 0)

        c1 = City.objects.create(code='005177', name='Trifouillis-les-oies',
                 geom=MultiPolygon(Polygon(((0,0), (2,0), (2,4), (0,4), (0,0)),
                              srid=settings.SRID)))
        c2 = City.objects.create(code='005179', name='Trifouillis-les-poules',
                 geom=MultiPolygon(Polygon(((2,0), (5,0), (5,4), (2,4), (2,0)),
                              srid=settings.SRID)))

        # There should be automatic link after insert
        self.assertEquals(p1.aggregations.count(), 1)
        self.assertEquals(p2.aggregations.count(), 2)
        self.assertEquals(p3.aggregations.count(), 1)
        self.assertEquals(p4.aggregations.count(), 2)

        c1.geom = MultiPolygon(Polygon(((1.5,0), (2,0), (2,4), (1.5,4), (1.5,0)),
                                       srid=settings.SRID))
        c1.save()

        # Links should have been updated after geom update
        self.assertEquals(p1.aggregations.count(), 0)
        self.assertEquals(p2.aggregations.count(), 2)
        self.assertEquals(p3.aggregations.count(), 1)
        self.assertEquals(p4.aggregations.count(), 2)

        c1.delete()

        # Links should have been updated after delete
        self.assertEquals(p1.aggregations.count(), 0)
        self.assertEquals(p2.aggregations.count(), 1)
        self.assertEquals(p3.aggregations.count(), 1)
        self.assertEquals(p4.aggregations.count(), 2)

    def test_couches_sig_link(self):
        # Fake restricted areas
        ra1 = RestrictedArea(name='Zone 1', order=1, geom=MultiPolygon(
            Polygon(((0,0), (2,0), (2,1), (0,1), (0,0)))))
        ra1.save()
        ra2 = RestrictedArea(name='Zone 2', order=1, geom=MultiPolygon(
            Polygon(((0,1), (2,1), (2,2), (0,2), (0,1)))))
        ra2.save()

        # Fake city
        c = City(code='005178', name='Trifouillis-les-marmottes',
                 geom=MultiPolygon(Polygon(((0,0), (2,0), (2,2), (0,2), (0,0)),
                              srid=settings.SRID)))
        c.save()

        # Fake paths in these areas
        p = PathFactory(geom=LineString((0.5,0.5,0), (0.5,1.5,0), (1.5,1.5,0), (1.5,0.5,0)))
        p.save()

        # This should results in 3 PathAggregation (2 for RA1, 1 for RA2, 1 for City)
        self.assertEquals(p.aggregations.count(), 4)
        self.assertEquals(p.topologymixin_set.count(), 4)

        # PathAgg is plain for City
        t_c = c.cityedge_set.get().topo_object
        pa = c.cityedge_set.get().aggregations.get()
        self.assertEquals(pa.start_position, 0.0)
        self.assertEquals(pa.end_position, 1.0)

        # PathAgg is splitted for RA
        self.assertEquals(ra1.restrictedareaedge_set.count(), 2)
        self.assertEquals(ra2.restrictedareaedge_set.count(), 1)
        rae1a = ra1.restrictedareaedge_set.filter(aggregations__start_position=0).get()
        rae1b = ra1.restrictedareaedge_set.filter(aggregations__end_position=1).get()
        pa1a = rae1a.aggregations.get()
        pa1b = rae1b.aggregations.get()
        t_ra1a = rae1a.topo_object
        t_ra1b = rae1b.topo_object
        pa2 = ra2.restrictedareaedge_set.get().aggregations.get()
        t_ra2 = ra2.restrictedareaedge_set.get().topo_object
        self.assertAlmostEqual(pa1a.start_position, 0.0)
        self.assertAlmostEqual(pa1a.end_position, 0.5/3)
        self.assertAlmostEqual(pa1b.start_position, 2.5/3)
        self.assertAlmostEqual(pa1b.end_position, 1.0)
        self.assertAlmostEqual(pa2.start_position, 0.5/3)
        self.assertAlmostEqual(pa2.end_position, 2.5/3)

        # Ensure everything is in order after update
        p.geom = LineString((0.5,0.5,0), (1.5,0.5,0))
        p.save()
        self.assertEquals(p.aggregations.count(), 2)
        self.assertEquals(p.topologymixin_set.count(), 2)
        # TopologyMixin are re-created at DB-level after any update
        self.assertRaises(TopologyMixin.DoesNotExist,
                          TopologyMixin.objects.get, pk=t_c.pk)
        self.assertRaises(TopologyMixin.DoesNotExist,
                          TopologyMixin.objects.get, pk=t_ra1a.pk)
        self.assertRaises(TopologyMixin.DoesNotExist,
                          TopologyMixin.objects.get, pk=t_ra1b.pk)
        self.assertRaises(TopologyMixin.DoesNotExist,
                          TopologyMixin.objects.get, pk=t_ra2.pk)
        self.assertEquals(ra1.restrictedareaedge_set.count(), 1)
        # a new association exists for C
        t_c = c.cityedge_set.get().topo_object
        self.assertEquals(TopologyMixin.objects.filter(pk=t_c.pk).count(), 1)
        # a new association exists for RA1
        t_ra1 = ra1.restrictedareaedge_set.get().topo_object
        self.assertEquals(TopologyMixin.objects.filter(pk=t_ra1.pk).count(), 1)
        pa1 = ra1.restrictedareaedge_set.get().aggregations.get()
        self.assertEquals(pa1.start_position, 0.0)
        self.assertEquals(pa1.end_position, 1.0)
        # RA2 is not connected anymore
        self.assertEquals(ra2.restrictedareaedge_set.count(), 0)
        self.assertEquals(TopologyMixin.objects.filter(pk=t_ra2.pk).count(), 0)

        # All intermediary objects should be cleaned on delete
        p.delete()
        self.assertEquals(c.cityedge_set.count(), 0)
        self.assertEquals(TopologyMixin.objects.filter(pk=t_c.pk).count(), 0)
        self.assertEquals(ra1.restrictedareaedge_set.count(), 0)
        self.assertEquals(TopologyMixin.objects.filter(pk=t_ra1.pk).count(), 0)
        self.assertEquals(ra2.restrictedareaedge_set.count(), 0)
        self.assertEquals(TopologyMixin.objects.filter(pk=t_ra2.pk).count(), 0)
