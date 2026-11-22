from app import __version__
from app.hispamula import Ed2kFile, torznab_subcategories
from app.torznab import capabilities, feed, to_magnet


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
        url="ed2k://|file|a&b|10|0123456789ABCDEF0123456789ABCDEF|/",
        name='a & "b"',
        size=10,
        hash="0123456789ABCDEF0123456789ABCDEF",
        group_id=1,
        group_label="x",
    )
    xml = feed([(f, [2000, 2040])])
    assert 'a &amp; "b" [x]' in xml
    assert 'type="application/x-bittorrent"' in xml
    assert "magnet:?xt=urn:btih:" in xml
    assert "&amp;tr=http://amulerr" in xml
    assert "<category>2000</category>" in xml
    assert "<category>2040</category>" in xml
    assert 'torznab:attr name="category" value="2040"' in xml
    assert '<torznab:attr name="size" value="10"/>' in xml
    assert "<pubDate>" in xml
    assert 'torznab:attr name="seeders"' in xml


def test_feed_includes_page_link():
    f = Ed2kFile(
        url="ed2k://|file|a|10|0123456789ABCDEF0123456789ABCDEF|/",
        name="a",
        size=10,
        hash="0123456789ABCDEF0123456789ABCDEF",
        group_id=1,
        group_label="",
        title_id=41554,
    )
    xml = feed([(f, [2000])])
    assert "<comments>https://www.hispamula.org/?title=41554</comments>" in xml


def _movie_file(name: str, year: int | None = None) -> Ed2kFile:
    return Ed2kFile(
        url="ed2k://|file|a|10|0123456789ABCDEF0123456789ABCDEF|/",
        name=name,
        size=10,
        hash="0123456789ABCDEF0123456789ABCDEF",
        group_id=1,
        group_label="HD 1080p: mkv (HEVC 10b-AC3)",
        year=year,
    )


def test_feed_anade_anio_para_radarr():
    """Sin año Radarr rechaza el release con "Unable to parse release"."""
    xml = feed([(_movie_file("El Robo Del Siglo.mkv", 2020), [2000, 2040])])
    assert "<title>El Robo Del Siglo (2020).mkv [HD 1080p: mkv (HEVC 10b-AC3)]</title>" in xml


def test_magnet_usa_el_nombre_con_anio():
    """aMulerr usa el ``dn`` del magnet como nombre del fichero; sin año
    Radarr bloquea el import ("Movie title mismatch")."""
    xml = feed([(_movie_file("El Robo Del Siglo.mkv", 2020), [2000, 2040])])
    assert "dn=El%20Robo%20Del%20Siglo%20%282020%29.mkv" in xml


def test_feed_no_duplica_anio():
    xml = feed([(_movie_file("Los Ladrones (2022).mkv", 2022), [2000, 2080])])
    assert "<title>Los Ladrones (2022).mkv [HD 1080p" in xml
    assert "Los Ladrones (2022) (2022)" not in xml


def test_feed_no_anade_anio_a_subtitulos():
    """Un .srt con año se consideraría release válido y Radarr lo descargaría."""
    xml = feed([(_movie_file("El Robo Del Siglo.srt", 2020), [2000, 2040])])
    assert "<title>El Robo Del Siglo.srt [HD 1080p" in xml


def test_feed_no_anade_anio_a_series():
    xml = feed([(_movie_file("Terminator.mkv", 2008), [5000, 5040])])
    assert "<title>Terminator.mkv [HD 1080p" in xml


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


def test_to_magnet_matches_amulerr_format():
    # Vector real de aMulerr: btih = base32(ed2k_hash + 4 bytes de relleno),
    # y dn/xl/tr que su shim qBittorrent sabe decodificar de vuelta al ed2k.
    magnet = to_magnet("42DA861488152E607AD69BB2DE5E1D05", "Sky Fighters.mkv", 970972587)
    assert magnet == (
        "magnet:?xt=urn:btih:ILNIMFEICUXGA6WWTOZN4XQ5AUAAAAAA"
        "&dn=Sky%20Fighters.mkv&xl=970972587&tr=http://amulerr"
    )


def test_subcategories_por_calidad():
    assert torznab_subcategories("Serie", "WEB-DL 1080p: mkv (HEVC 10b-EAC3)") == [5000, 5040, 5010, 5090]
    assert torznab_subcategories("Serie", "WEB-DL UHD 4K DV-HDR10+: mkv (HEVC 10b-AC3)") == [5000, 5045, 5010, 5090]
    assert torznab_subcategories("Serie", "HDTV-TDT: avi (XviD-mp3)") == [5000, 5030]  # XviD es SD
    assert torznab_subcategories("Película", "BDrip 1080p: mkv (HEVC 10b-AC3)") == [2000, 2040, 2050, 2090]
    assert torznab_subcategories("Docuserie", "WEB-DL 720p: mkv (x264)") == [5000, 5040, 5010]
