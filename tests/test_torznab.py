from app.hispamula import Ed2kFile
from app.torznab import capabilities, feed


def test_caps():
    xml = capabilities()
    assert "<caps>" in xml
    assert "searching" in xml
    assert 'category id="2000"' in xml
    assert 'category id="5000"' in xml


def test_feed_escapes_and_item():
    f = Ed2kFile(
        url="ed2k://|file|a&b|10|ABC|/",
        name='a & "b"',
        size=10,
        hash="ABC",
        group_id=1,
        group_label="x",
    )
    xml = feed([(f, 2000)])
    assert 'a &amp; "b"' in xml
    assert 'url="ed2k://|file|a&amp;b|10|ABC|/"' in xml
    assert "<category>2000</category>" in xml
    assert "<pubDate>" in xml
    assert 'torznab:attr name="seeders"' in xml
