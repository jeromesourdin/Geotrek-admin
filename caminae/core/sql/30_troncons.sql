-------------------------------------------------------------------------------
-- Add spatial index (will boost spatial filters)
-------------------------------------------------------------------------------

DROP INDEX IF EXISTS troncons_geom_idx;
DROP INDEX IF EXISTS l_t_troncon_geom_idx;
CREATE INDEX l_t_troncon_geom_idx ON l_t_troncon USING gist(geom);

DROP INDEX IF EXISTS troncons_start_point_idx;
DROP INDEX IF EXISTS l_t_troncon_start_point_idx;
CREATE INDEX l_t_troncon_start_point_idx ON l_t_troncon USING gist(ST_StartPoint(geom));

DROP INDEX IF EXISTS troncons_end_point_idx;
DROP INDEX IF EXISTS l_t_troncon_end_point_idx;
CREATE INDEX l_t_troncon_end_point_idx ON l_t_troncon USING gist(ST_EndPoint(geom));

DROP INDEX IF EXISTS troncons_geom_cadastre_idx;
DROP INDEX IF EXISTS l_t_troncon_geom_cadastre_idx;
CREATE INDEX l_t_troncon_geom_cadastre_idx ON l_t_troncon USING gist(geom_cadastre);


-------------------------------------------------------------------------------
-- Keep dates up-to-date
-------------------------------------------------------------------------------

DROP TRIGGER IF EXISTS l_t_troncon_date_insert_tgr ON l_t_troncon;
CREATE TRIGGER l_t_troncon_date_insert_tgr
    BEFORE INSERT ON l_t_troncon
    FOR EACH ROW EXECUTE PROCEDURE ft_date_insert();

DROP TRIGGER IF EXISTS l_t_troncon_date_update_tgr ON l_t_troncon;
CREATE TRIGGER l_t_troncon_date_update_tgr
    BEFORE INSERT OR UPDATE ON l_t_troncon
    FOR EACH ROW EXECUTE PROCEDURE ft_date_update();


-------------------------------------------------------------------------------
-- Check overlapping paths
-------------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION check_path_not_overlap(pid integer, line geometry) RETURNS BOOL AS $$
DECLARE
    t_count integer;
    tolerance float;
BEGIN
    -- Note: I gave up with the idea of checking almost overlap/touch.

    -- tolerance := 1.0;
    -- Crossing and extremity touching is OK. 
    -- Overlapping and --almost overlapping-- is KO.
    SELECT COUNT(*) INTO t_count
    FROM l_t_troncon 
    WHERE pid != id 
      AND ST_GeometryType(ST_intersection(geom, line)) IN ('ST_LineString', 'ST_MultiLineString');
      -- not extremity touching
      -- AND ST_Touches(geom, line) = false
      -- not crossing
      -- AND ST_GeometryType(ST_intersection(geom, line)) NOT IN ('ST_Point', 'ST_MultiPoint')
      -- overlap is a line
      -- AND ST_GeometryType(ST_intersection(geom, ST_buffer(line, tolerance))) IN ('ST_LineString', 'ST_MultiLineString')
      -- not almost touching, at most twice
      -- AND       ST_Length(ST_intersection(geom, ST_buffer(line, tolerance))) > (4 * tolerance);
    RETURN t_count = 0;
END;
$$ LANGUAGE plpgsql;


-------------------------------------------------------------------------------
-- Automatic link between Troncon and Commune/Zonage/Secteur
-------------------------------------------------------------------------------

DROP TRIGGER IF EXISTS l_t_troncon_couches_sig_iu_tgr ON l_t_troncon;

CREATE OR REPLACE FUNCTION lien_auto_troncon_couches_sig_iu() RETURNS trigger AS $$
DECLARE
    rec record;
    tab varchar;
    eid integer;
BEGIN
    -- Remove obsolete evenement
    IF TG_OP = 'UPDATE' THEN
        -- Related evenement/zonage/secteur/commune will be cleared by another trigger
        DELETE FROM e_r_evenement_troncon et USING f_t_zonage z WHERE et.troncon = OLD.id AND et.evenement = z.evenement;
        DELETE FROM e_r_evenement_troncon et USING f_t_secteur s WHERE et.troncon = OLD.id AND et.evenement = s.evenement;
        DELETE FROM e_r_evenement_troncon et USING f_t_commune c WHERE et.troncon = OLD.id AND et.evenement = c.evenement;
    END IF;

    -- Add new evenement
    -- Note: Column names differ between commune, secteur and zonage, we can not use an elegant loop.

    -- Commune
    FOR rec IN EXECUTE 'SELECT id, ST_Line_Locate_Point($1, ST_StartPoint(geom)) as pk_a, ST_Line_Locate_Point($1, ST_EndPoint(geom)) as pk_b FROM (SELECT insee AS id, (ST_Dump(ST_Multi(ST_Intersection(geom, $1)))).geom AS geom FROM l_commune WHERE ST_Intersects(geom, $1)) AS sub' USING NEW.geom
    LOOP
        INSERT INTO e_t_evenement (date_insert, date_update, kind, decallage, longueur, geom, supprime) VALUES (now(), now(), 'CITYEDGE', 0, 0, NEW.geom, FALSE) RETURNING id INTO eid;
        INSERT INTO e_r_evenement_troncon (troncon, evenement, pk_debut, pk_fin) VALUES (NEW.id, eid, least(rec.pk_a, rec.pk_b), greatest(rec.pk_a, rec.pk_b));
        INSERT INTO f_t_commune (evenement, city_id) VALUES (eid, rec.id);
    END LOOP;

    -- Secteur
    FOR rec IN EXECUTE 'SELECT id, ST_Line_Locate_Point($1, ST_StartPoint(geom)) as pk_a, ST_Line_Locate_Point($1, ST_EndPoint(geom)) as pk_b FROM (SELECT id, (ST_Dump(ST_Multi(ST_Intersection(geom, $1)))).geom AS geom FROM l_secteur WHERE ST_Intersects(geom, $1)) AS sub' USING NEW.geom
    LOOP
        INSERT INTO e_t_evenement (date_insert, date_update, kind, decallage, longueur, geom, supprime) VALUES (now(), now(), 'DISTRICTEDGE', 0, 0, NEW.geom, FALSE) RETURNING id INTO eid;
        INSERT INTO e_r_evenement_troncon (troncon, evenement, pk_debut, pk_fin) VALUES (NEW.id, eid, least(rec.pk_a, rec.pk_b), greatest(rec.pk_a, rec.pk_b));
        INSERT INTO f_t_secteur (evenement, district_id) VALUES (eid, rec.id);
    END LOOP;

    -- Zonage
    FOR rec IN EXECUTE 'SELECT id, ST_Line_Locate_Point($1, ST_StartPoint(geom)) as pk_a, ST_Line_Locate_Point($1, ST_EndPoint(geom)) as pk_b FROM (SELECT id, (ST_Dump(ST_Multi(ST_Intersection(geom, $1)))).geom AS geom FROM l_zonage_reglementaire WHERE ST_Intersects(geom, $1)) AS sub' USING NEW.geom
    LOOP
        INSERT INTO e_t_evenement (date_insert, date_update, kind, decallage, longueur, geom, supprime) VALUES (now(), now(), 'RESTRICTEDAREAEDGE', 0, 0, NEW.geom, FALSE) RETURNING id INTO eid;
        INSERT INTO e_r_evenement_troncon (troncon, evenement, pk_debut, pk_fin) VALUES (NEW.id, eid, least(rec.pk_a, rec.pk_b), greatest(rec.pk_a, rec.pk_b));
        INSERT INTO f_t_zonage (evenement, restricted_area_id) VALUES (eid, rec.id);
    END LOOP;

    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER l_t_troncon_couches_sig_iu_tgr
AFTER INSERT OR UPDATE OF geom ON l_t_troncon
FOR EACH ROW EXECUTE PROCEDURE lien_auto_troncon_couches_sig_iu();


-------------------------------------------------------------------------------
-- Update geometry of related topologies
-------------------------------------------------------------------------------

DROP TRIGGER IF EXISTS l_t_troncon_evenements_geom_u_tgr ON l_t_troncon;

CREATE OR REPLACE FUNCTION update_evenement_geom_when_troncon_changes() RETURNS trigger AS $$
DECLARE
    eid integer;
    egeom geometry;
    linear_offset float;
    side_offset float;
BEGIN
    -- Geometry of linear topologies are always updated
    -- Geometry of point topologies are updated if offset = 0
    FOR eid IN SELECT DISTINCT e.id
               FROM e_r_evenement_troncon et, e_t_evenement e
               WHERE et.troncon = NEW.id AND et.evenement = e.id AND (et.pk_debut != et.pk_fin OR e.decallage = 0.0)
    LOOP
        PERFORM update_geometry_of_evenement(eid);
    END LOOP;

    -- Special case of point geometries with offset != 0
    FOR eid, egeom IN SELECT e.id, e.geom
               FROM e_r_evenement_troncon et, e_t_evenement e
               WHERE et.troncon = NEW.id AND et.evenement = e.id AND et.pk_debut = et.pk_fin AND e.decallage != 0.0
    LOOP
        SELECT * INTO linear_offset, side_offset FROM ST_InterpolateAlong(NEW.geom, egeom) AS (position float, distance float);
        UPDATE e_t_evenement SET decallage = side_offset WHERE id = eid;
        UPDATE e_r_evenement_troncon SET pk_debut = linear_offset, pk_fin = linear_offset WHERE evenement = eid AND troncon = NEW.id;
    END LOOP;

    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER l_t_troncon_evenements_geom_u_tgr
AFTER UPDATE OF geom ON l_t_troncon
FOR EACH ROW EXECUTE PROCEDURE update_evenement_geom_when_troncon_changes();


-------------------------------------------------------------------------------
-- Ensure paths have valid geometries
-------------------------------------------------------------------------------

ALTER TABLE l_t_troncon DROP CONSTRAINT IF EXISTS troncons_geom_issimple;
ALTER TABLE l_t_troncon DROP CONSTRAINT IF EXISTS l_t_troncon_geom_issimple;
ALTER TABLE l_t_troncon ADD CONSTRAINT l_t_troncon_geom_issimple CHECK (ST_IsSimple(geom));


-------------------------------------------------------------------------------
-- Compute elevation and elevation-based indicators
-------------------------------------------------------------------------------

DROP TRIGGER IF EXISTS l_t_troncon_elevation_iu_tgr ON l_t_troncon;

CREATE OR REPLACE FUNCTION troncons_elevation_iu() RETURNS trigger AS $$
DECLARE
    line3d geometry;
    max_ele integer;
    min_ele integer;
    positive_gain integer;
    negative_gain integer;
BEGIN

    SELECT *
    FROM elevation_infos(NEW.geom) AS (line3d geometry, min_ele integer, max_ele integer, positive_gain integer, negative_gain integer)
    INTO line3d, min_ele, max_ele, positive_gain, negative_gain;

    -- Update path geometry
    NEW.geom := line3d;

    -- Update path indicators
    NEW.longueur := ST_3DLength(line3d);
    NEW.altitude_minimum := min_ele;
    NEW.altitude_maximum := max_ele;
    NEW.denivelee_positive := positive_gain;
    NEW.denivelee_negative := negative_gain;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER l_t_troncon_elevation_iu_tgr
BEFORE INSERT OR UPDATE OF geom ON l_t_troncon
FOR EACH ROW EXECUTE PROCEDURE troncons_elevation_iu();


-------------------------------------------------------------------------------
-- Change status of related objects when paths are deleted
-------------------------------------------------------------------------------

DROP TRIGGER IF EXISTS l_t_troncon_related_objects_d_tgr ON l_t_troncon;

CREATE OR REPLACE FUNCTION troncons_related_objects_d() RETURNS trigger AS $$
DECLARE
BEGIN
    -- Un-published treks because they might be broken
    UPDATE o_t_itineraire i
        SET published = FALSE
        FROM e_r_evenement_troncon et
        WHERE et.evenement = i.topology_ptr_id AND et.troncon = OLD.id;

    -- Mark empty topologies as deleted
    UPDATE e_t_evenement e
        SET supprime = TRUE
        FROM e_r_evenement_troncon et
        WHERE et.evenement = e.id AND et.troncon = OLD.id AND NOT EXISTS(
            SELECT * FROM e_r_evenement_troncon
            WHERE evenement = e.id AND troncon != OLD.id
        );

    RETURN OLD;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER l_t_troncon_related_objects_d_tgr
BEFORE DELETE ON l_t_troncon
FOR EACH ROW EXECUTE PROCEDURE troncons_related_objects_d();
