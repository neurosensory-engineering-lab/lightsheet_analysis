import io
import unittest
import zipfile

from app import app


XML = b"""<mbf><vessel color="#00FF00"><edges><edge>
<point x="0" y="0" z="0" d="1"/><point x="0" y="1" z="0" d="1"/>
</edge></edges></vessel></mbf>"""


class AppTests(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

    def test_home_page_loads(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Neurolucida Vessel Mesh Exporter", response.data)

    def test_conversion_downloads_obj_and_mtl(self):
        response = self.client.post(
            "/convert",
            data={
                "xml_file": (io.BytesIO(XML), "sample.xml"),
                "radial_segments": "6",
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "application/zip")
        with zipfile.ZipFile(io.BytesIO(response.data)) as archive:
            self.assertEqual(archive.namelist(), ["sample.obj", "vessels.mtl"])
            self.assertIn(b"mtllib vessels.mtl", archive.read("sample.obj"))
            self.assertIn(b"newmtl vessel_0001", archive.read("vessels.mtl"))

    def test_rejects_non_xml_upload(self):
        response = self.client.post(
            "/convert",
            data={"xml_file": (io.BytesIO(b"not xml"), "sample.txt")},
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn(b"must have an .xml extension", response.data)


if __name__ == "__main__":
    unittest.main()
