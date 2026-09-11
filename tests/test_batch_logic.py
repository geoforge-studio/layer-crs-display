import tempfile
import unittest
from pathlib import Path
from layer_crs_display.batch_logic import output_names, plan_outputs


class NamingTests(unittest.TestCase):
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
            p=Path(folder)/'ROAD_39.GPKG'; p.write_bytes(b'keep')
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


if __name__=='__main__': unittest.main()
