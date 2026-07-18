from svg2grasssymbol import converter


def test_simple_polygon_from_path():
    svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M12 2 22 9 18 21 6 21 2 9Z"/></svg>'
    out = converter.convert_svg_to_symbol(svg)
    assert "VERSION 1.0" in out
    assert "BOX -12.0000 -12.0000 12.0000 12.0000" in out
    assert "POLYGON" in out
    assert "RING" in out
    assert "LINE" in out
    # (12,2) -> symbol space (0, 10)
    assert "0.0000 10.0000" in out


def test_unfilled_path_becomes_string_not_polygon():
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
        '<path d="M12 1 23 12 12 23 1 12Z" fill="none" stroke="currentColor"/>'
        "</svg>"
    )
    out = converter.convert_svg_to_symbol(svg)
    assert "STRING" in out
    assert "POLYGON" not in out


def test_root_fill_none_is_inherited_but_overridable():
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none">'
        '<circle cx="12" cy="12" r="9"/>'
        '<circle cx="12" cy="12" r="1" fill="currentColor"/>'
        "</svg>"
    )
    w, h, shapes = converter.extract_shapes(svg)
    assert shapes[0].filled is False
    assert shapes[1].filled is True


def test_circle_maps_to_native_arc():
    svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><circle cx="12" cy="12" r="5"/></svg>'
    out = converter.convert_svg_to_symbol(svg)
    assert "ARC 0.0000 0.0000 5.0000 360 0 C" in out


def test_cubic_bezier_endpoint_matches_exactly():
    subpaths = converter.parse_path("M0,0 C3,5 7,-5 10,0")
    assert subpaths[0].points[-1] == (10.0, 0.0)


def test_elliptical_arc_endpoint_matches_exactly():
    subpaths = converter.parse_path("M0,0 A5,5 0 0 1 10,0")
    assert subpaths[0].points[-1] == (10.0, 0.0)


def test_elliptical_arc_semicircle_bulges_away_from_chord():
    subpaths = converter.parse_path("M0,0 A5,5 0 0 1 10,0")
    mid = subpaths[0].points[len(subpaths[0].points) // 2]
    assert abs(mid[1]) > 3  # well off the y=0 chord


def test_implicit_lineto_after_moveto_repeats_as_lineto():
    subpaths = converter.parse_path("M0,0 5,0 5,5")
    assert subpaths[0].points == [(0.0, 0.0), (5.0, 0.0), (5.0, 5.0)]


def test_horizontal_and_vertical_relative():
    subpaths = converter.parse_path("M0,0 h5 v5 H0 V0 Z")
    pts = subpaths[0].points
    assert pts[0] == (0.0, 0.0)
    assert (5.0, 0.0) in pts
    assert (5.0, 5.0) in pts
    assert (0.0, 5.0) in pts
