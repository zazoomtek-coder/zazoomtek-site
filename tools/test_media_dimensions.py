import struct
import tempfile
import unittest
from pathlib import Path

from media_dimensions import dimension_attributes, image_dimensions, parse_image_dimensions


class MediaDimensionsTests(unittest.TestCase):
    def test_png_dimensions(self):
        data = b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\x0dIHDR"
        data += struct.pack(">II", 1200, 675) + b"\x08\x02\x00\x00\x00"
        self.assertEqual(parse_image_dimensions(data), (1200, 675))

    def test_jpeg_dimensions(self):
        data = bytes.fromhex("FFD8 FFC0 000B 08 02A0 04B0 01 01 11 00")
        self.assertEqual(parse_image_dimensions(data), (1200, 672))

    def test_gif_dimensions(self):
        data = b"GIF89a" + struct.pack("<HH", 640, 480)
        self.assertEqual(parse_image_dimensions(data), (640, 480))

    def test_svg_viewbox_dimensions(self):
        data = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 675"></svg>'
        self.assertEqual(parse_image_dimensions(data), (1200, 675))

    def test_local_asset_dimensions(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cover.svg"
            path.write_text('<svg width="1280" height="720"></svg>', encoding="utf-8")
            self.assertEqual(image_dimensions("/cover.svg", root=directory), (1280, 720))
            self.assertEqual(dimension_attributes("/cover.svg", root=directory),
                             ' width="1280" height="720"')

    def test_metadata_dimensions_take_priority(self):
        self.assertEqual(image_dimensions("https://cdn.example/cover.jpg",
                                           metadata={"image_width": 1000, "image_height": 1000}),
                         (1000, 1000))

    def test_known_youtube_thumbnail_dimensions(self):
        self.assertEqual(image_dimensions("https://i.ytimg.com/vi/example/hqdefault.jpg"),
                         (480, 360))

    def test_unknown_remote_dimensions_are_not_guessed(self):
        self.assertIsNone(image_dimensions("https://cdn.example/cover.jpg"))
        self.assertEqual(dimension_attributes("https://cdn.example/cover.jpg"), "")

    def test_path_traversal_is_rejected(self):
        self.assertIsNone(image_dimensions("/../secret.jpg", root="/tmp"))


if __name__ == "__main__":
    unittest.main()
