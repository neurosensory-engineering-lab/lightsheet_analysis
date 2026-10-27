import io
import unittest

from mesh_converter import export_obj, read_vessels


MINIMAL_XML = b"""<?xml version="1.0"?>
<mbf xmlns="https://www.mbfbioscience.com/filespecification">
  <vessel color="#12aBcF" class="Test vessel">
    <nodes />
    <edges>
      <edge id="0">
        <point x="0" y="0" z="0" d="2" />
        <point x="0" y="0" z="4" d="2" />
      </edge>
    </edges>
  </vessel>
</mbf>
"""

REVERSING_XML = MINIMAL_XML.replace(
    b"      </edge>",
    b'        <point x="0" y="0" z="0" d="2" />\n      </edge>',
)


class MeshConverterTests(unittest.TestCase):
    def test_reads_namespaced_vessel_points_and_color(self):
        vessels = read_vessels(io.BytesIO(MINIMAL_XML))
        self.assertEqual(len(vessels), 1)
        self.assertEqual(vessels[0].color, "#12ABCF")
        self.assertEqual(len(vessels[0].edges[0]), 2)

    def test_exports_tube_mesh_and_matching_material(self):
        obj, mtl = export_obj(read_vessels(io.BytesIO(MINIMAL_XML)), radial_segments=6)
        self.assertIn("mtllib vessels.mtl", obj)
        self.assertIn("usemtl vessel_0001", obj)
        self.assertEqual(sum(line.startswith("v ") for line in obj.splitlines()), 14)
        self.assertEqual(sum(line.startswith("f ") for line in obj.splitlines()), 18)
        self.assertIn("newmtl vessel_0001", mtl)
        self.assertIn("Kd 0.070588 0.670588 0.811765", mtl)

    def test_rejects_non_positive_diameter(self):
        invalid_xml = MINIMAL_XML.replace(b'd="2" />\n        <point', b'd="0" />\n        <point')
        with self.assertRaisesRegex(ValueError, "non-positive diameter"):
            read_vessels(io.BytesIO(invalid_xml))

    def test_rejects_unsupported_mesh_resolution(self):
        vessels = read_vessels(io.BytesIO(MINIMAL_XML))
        with self.assertRaisesRegex(ValueError, "between 3 and 64"):
            export_obj(vessels, radial_segments=2)

    def test_handles_a_reversing_centerline(self):
        obj, _ = export_obj(read_vessels(io.BytesIO(REVERSING_XML)))
        self.assertTrue(any(line.startswith("f ") for line in obj.splitlines()))


if __name__ == "__main__":
    unittest.main()
