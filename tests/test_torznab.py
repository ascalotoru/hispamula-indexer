from app import __version__
from app.hispamula import Ed2kFile, torznab_subcategories
from app.torznab import capabilities, feed


def test_caps_exposes_package_version():
    xml = capabilities()
    assert f'appversion="{__version__}"' in xml
    assert f'version="{__version__}"' in xml


def test_caps():
    xml = capabilities()
    assert "<caps>" in xml
    assert "searching" in xml
    assert 'category id="2000"' in xml
    assert 'category id="5000"' in xml


def test_caps_declares_standard_subcats():
    xml = capabilities()
    for subcat in ("2010", "2040", "2045", "2050", "2080", "2090", "5010", "5030", "5040", "5045", "5090"):
        assert f'<subcat id="{subcat}"' in xml, f"falta subcat {subcat}"


def test_feed_escapes_and_item():
    f = Ed2kFile(
        url="ed2k://|file|a&b|10|ABC|/",
        name='a & "b"',
        size=10,
        hash="ABC",
        group_id=1,
        group_label="x",
    )
    xml = feed([(f, [2000, 2040])])
    assert 'a &amp; "b" [x]' in xml
    assert 'url="ed2k://|file|a&amp;b|10|ABC|/"' in xml
    assert "<category>2000</category>" in xml
    assert "<category>2040</category>" in xml
    assert 'torznab:attr name="category" value="2040"' in xml
    assert '<torznab:attr name="size" value="10"/>' in xml
    assert "<pubDate>" in xml
    assert 'torznab:attr name="seeders"' in xml


def test_feed_includes_page_link():
    f = Ed2kFile(
        url="ed2k://|file|a|10|ABC|/",
        name="a",
        size=10,
        hash="ABC",
        group_id=1,
        group_label="",
        title_id=41554,
    )
    xml = feed([(f, [2000])])
    assert "<comments>https://www.hispamula.org/?title=41554</comments>" in xml


def test_feed_includes_quality_label():
    def make(hash_, label):
        return Ed2kFile(
            url=f"ed2k://|file|x|10|{hash_}|/",
            name="Linternas 1x01.mkv",
            size=10,
            hash=hash_,
            group_id=1,
            group_label=label,
        )

    xml = feed(
        [
            (make("A" * 32, "1080p: mkv (HEVC 10b-AC3)"), [5000, 5040, 5090]),
            (make("B" * 32, "UHD 4K: mkv (HEVC 10b-AC3)"), [5000, 5045, 5090]),
        ]
    )
    assert "Linternas 1x01.mkv [1080p: mkv (HEVC 10b-AC3)]" in xml
    assert "Linternas 1x01.mkv [UHD 4K: mkv (HEVC 10b-AC3)]" in xml
    assert "<category>5040</category>" in xml
    assert "<category>5045</category>" in xml


def test_subcategories_por_calidad():
    assert torznab_subcategories("Serie", "WEB-DL 1080p: mkv (HEVC 10b-EAC3)") == [5000, 5040, 5010, 5090]
    assert torznab_subcategories("Serie", "WEB-DL UHD 4K DV-HDR10+: mkv (HEVC 10b-AC3)") == [5000, 5045, 5010, 5090]
    assert torznab_subcategories("Serie", "HDTV-TDT: avi (XviD-mp3)") == [5000, 5030]  # XviD es SD
    assert torznab_subcategories("Película", "BDrip 1080p: mkv (HEVC 10b-AC3)") == [2000, 2040, 2050, 2090]
    assert torznab_subcategories("Docuserie", "WEB-DL 720p: mkv (x264)") == [5000, 5040, 5010]
