import tempfile
import unittest
from unittest import mock
import errno
import os
from pathlib import Path
from layer_crs_display.batch_logic import (
    geopackage_filename,
    output_names,
    plan_outputs,
    publish_file,
)


class NamingTests(unittest.TestCase):
    def test_staged_file_is_published_as_the_only_final_file(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            source = folder / 'stage.tmp'
            final = folder / 'result.gpkg'
            source.write_bytes(b'data')
            publish_file(source, final)
            self.assertEqual(set(folder.iterdir()), {final})
            self.assertEqual(final.read_bytes(), b'data')

    def test_publication_never_overwrites_an_existing_file(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            source = folder / 'stage.tmp'
            final = folder / 'result.gpkg'
            source.write_bytes(b'new')
            final.write_bytes(b'keep')
            with self.assertRaises(FileExistsError):
                publish_file(source, final)
            self.assertEqual(final.read_bytes(), b'keep')
            self.assertEqual(source.read_bytes(), b'new')

    def test_cross_device_publication_uses_a_sibling_transfer_file(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            source = folder / 'stage.tmp'
            final = folder / 'result.gpkg'
            source.write_bytes(b'data')
            real_replace = os.replace
            calls = []

            def replace(source_path, destination_path):
                calls.append((source_path, destination_path))
                if len(calls) == 1:
                    raise OSError(errno.EXDEV, 'cross-device link')
                return real_replace(source_path, destination_path)

            with mock.patch(
                'layer_crs_display.batch_logic.os.replace',
                side_effect=replace,
            ):
                publish_file(source, final)
            self.assertEqual(set(folder.iterdir()), {final})
            self.assertEqual(final.read_bytes(), b'data')

    def test_persian_name_is_preserved_and_only_suffix_added(self):
        self.assertEqual(output_names('راه‌های استان', '_UTM39', 'vector'), ('راه‌های استان_UTM39', 'راه‌های استان_UTM39.gpkg'))

    def test_raster_extension_and_reserved_filename(self):
        self.assertEqual(output_names('DEM', '_39', 'raster'), ('DEM_39', 'DEM_39.tif'))
        self.assertEqual(output_names('CON', '.x', 'vector'), ('CON.x', '_CON.x.gpkg'))

    def test_illegal_filename_is_sanitized_but_display_name_not_changed(self):
        self.assertEqual(output_names('road/river', '_39', 'vector'), ('road/river_39','road_river_39.gpkg'))

    def test_invalid_suffix_fails(self):
        for suffix in ('', ' ', '../x', '\\x', ':39', '_39.', '_39 '):
            with self.assertRaises(ValueError): output_names('a',suffix,'vector')

    def test_case_insensitive_and_sanitized_collisions_are_reported(self):
        with tempfile.TemporaryDirectory() as folder:
            for names in (('Road','road'),('a/b','a:b')):
                plans=plan_outputs([dict(name=n,kind='vector') for n in names],folder,'_39')
                self.assertTrue(all(p['error'] for p in plans))

    def test_existing_file_is_not_renamed_or_overwritten(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'REPROJECTED.GPKG'; p.write_bytes(b'keep')
            plans=plan_outputs([dict(name='road',kind='vector')],folder,'_39')
            self.assertTrue(plans[0]['error'])
            self.assertEqual(p.read_bytes(),b'keep')
            self.assertEqual(plans[0]['output_name'],'road_39')

    def test_different_formats_can_share_display_name(self):
        with tempfile.TemporaryDirectory() as folder:
            plans=plan_outputs([dict(name='a',kind=k) for k in ('vector','raster')],folder,'_39')
            self.assertFalse(any(p['error'] for p in plans))

    def test_existing_sidecar_blocks_stale_metadata_reuse(self):
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder)/'a_39.tif.aux.xml').write_text('old metadata')
            plans=plan_outputs([dict(name='a',kind='raster')],folder,'_39')
            self.assertTrue(plans[0]['error'])

    def test_unknown_kind_and_long_name_fail(self):
        for name, kind in [('a','mesh'),('ر'*110,'vector')]:
            with self.assertRaises(ValueError):output_names(name,'_39',kind)

    def test_vectors_share_one_package_with_distinct_named_layers(self):
        with tempfile.TemporaryDirectory() as folder:
            plans = plan_outputs([dict(name=n, kind='vector') for n in ('roads', 'رودخانه')], folder, '_39')
            self.assertFalse(any(p['error'] for p in plans))
            self.assertEqual({p['filename'] for p in plans}, {'reprojected.gpkg'})
            self.assertEqual([p['output_layer'] for p in plans], ['roads_39', 'رودخانه_39'])

    def test_custom_package_and_sidecar_conflict(self):
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / 'result.gpkg-wal').touch()
            plans = plan_outputs([dict(name='roads', kind='vector')], folder, '_39', 'result')
            self.assertEqual(plans[0]['filename'], 'result.gpkg')
            self.assertTrue(plans[0]['error'])

    def test_package_name_rejects_paths_and_reserved_names(self):
        for name in ('', '../out.gpkg', 'a/b.gpkg', 'CON', 'a|b', 'a.'):
            with self.assertRaises(ValueError): geopackage_filename(name)

    def test_reserved_table_prefix_is_escaped(self):
        with tempfile.TemporaryDirectory() as folder:
            plan = plan_outputs([dict(name='gpkg_roads', kind='vector')], folder, '_39')[0]
            self.assertEqual(plan['output_layer'], '_gpkg_roads_39')


if __name__=='__main__': unittest.main()
