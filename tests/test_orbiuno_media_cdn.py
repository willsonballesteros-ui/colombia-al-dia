"""Verificación adversarial: dominio oficial de miniaturas de Wikimedia Commons.
Pruebas puras: sin red, escritura ni publicación.
"""
import json
import unittest
from unittest.mock import patch
from scripts.orbiuno_media_assets import commons_info, fetch

TITLE = "File:Shenzhen Skyline from Nanshan.jpg"

def mock_commons_doc(host):
    return {"query":{"pages":{"1":{
        "title":TITLE,"imageinfo":[{
            "size":2000000,"width":2000,"height":1335,"mime":"image/jpeg",
            "thumburl":f"https://{host}/wikipedia/commons/thumb/3/35/Shenzhen_Skyline_from_Nanshan.jpg/1280px-Shenzhen_Skyline_from_Nanshan.jpg",
            "url":"https://upload.wikimedia.org/wikipedia/commons/3/35/Shenzhen_Skyline_from_Nanshan.jpg",
            "extmetadata":{
                "LicenseShortName":{"value":"CC BY-SA 4.0"},
                "Artist":{"value":"Simbaxu"},
                "ImageDescription":{"value":"Shenzhen skyline from Nanshan"}
            }
        }]
    }}}}

class WikimediaCdnTests(unittest.TestCase):
    def test_official_thumb_host_is_accepted(self):
        data = json.dumps(mock_commons_doc("thumb.wikimedia.org")).encode()
        info = commons_info(TITLE, getter=lambda _: data)
        self.assertEqual(info["author"], "Simbaxu")
        self.assertEqual(info["license"], "CC BY-SA 4.0")
        self.assertTrue(info["url"].startswith("https://thumb.wikimedia.org/wikipedia/commons/"))

    def test_upload_host_is_still_accepted(self):
        data = json.dumps(mock_commons_doc("upload.wikimedia.org")).encode()
        self.assertIn("upload.wikimedia.org", commons_info(TITLE, getter=lambda _:data)["url"])

    def test_untrusted_host_is_blocked(self):
        data = json.dumps(mock_commons_doc("wikimedia.org.evil.example")).encode()
        with self.assertRaisesRegex(ValueError, "Archivo no alojado en Wikimedia"):
            commons_info(TITLE, getter=lambda _: data)

    def test_request_host_allowlist(self):
        class Response:
            def __init__(self,url): self.url=url
            def __enter__(self): return self
            def __exit__(self,*args): return False
            def read(self,limit): return b"valid-bytes"
        with patch("scripts.orbiuno_media_assets.urlopen",
                   side_effect=lambda request,timeout: Response(request.full_url)):
            self.assertEqual(fetch("https://thumb.wikimedia.org/wikipedia/commons/thumb/test.jpg"),b"valid-bytes")
            with self.assertRaisesRegex(ValueError,"Host multimedia no autorizado"):
                fetch("https://thumb.wikimedia.org.evil.example/file.jpg")


    def test_google_favicon_official_cdn_redirect(self):
        class Response:
            url = "https://t0.gstatic.com/faviconV2?type=FAVICON&url=bogota.gov.co"
            def __enter__(self): return self
            def __exit__(self,*args): return False
            def read(self,limit): return b"icon-image-data"
        with patch("scripts.orbiuno_media_assets.urlopen", return_value=Response()):
            self.assertEqual(
                fetch("https://www.google.com/s2/favicons?domain=bogota.gov.co&sz=256"),
                b"icon-image-data"
            )

    def test_google_favicon_spoofed_redirect_is_rejected(self):
        class Response:
            url = "https://t0.gstatic.com.evil.example/faviconV2"
            def __enter__(self): return self
            def __exit__(self,*args): return False
            def read(self,limit): return b"fake"
        with patch("scripts.orbiuno_media_assets.urlopen", return_value=Response()):
            with self.assertRaisesRegex(ValueError,"Redireccion fuera de hosts autorizados"):
                fetch("https://www.google.com/s2/favicons?domain=bogota.gov.co&sz=256")

    def test_wikimedia_photo_cannot_redirect_to_google(self):
        class Response:
            url = "https://t0.gstatic.com/faviconV2"
            def __enter__(self): return self
            def __exit__(self,*args): return False
            def read(self,limit): return b"fake"
        with patch("scripts.orbiuno_media_assets.urlopen", return_value=Response()):
            with self.assertRaisesRegex(ValueError,"Redireccion fuera de hosts autorizados"):
                fetch("https://thumb.wikimedia.org/wikipedia/commons/thumb/abc.jpg")

if __name__ == "__main__":
    unittest.main()
