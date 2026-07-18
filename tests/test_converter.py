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


def test_smooth_cubic_reflects_previous_control_point():
    # A straight C from (0,0)->(10,0) with control points on the chord,
    # then an S continuing symmetrically should produce a mirror-image
    # bulge on the other side of (10,0) -- not a flat line.
    subpaths = converter.parse_path("M0,0 C0,5 10,5 10,0 S20,-5 20,0")
    pts = subpaths[0].points
    second_curve = pts[len(pts) // 2 :]
    # the reflected control point puts the second curve's midpoint below y=0
    mid_y = second_curve[len(second_curve) // 2][1]
    assert mid_y < -1


def test_smooth_cubic_without_preceding_curve_uses_current_point():
    # S with no preceding C/S: first control point coincides with the
    # current point (per spec), not some leftover/garbage reflection.
    subpaths_s_alone = converter.parse_path("M0,0 S10,5 10,0")
    subpaths_equivalent_c = converter.parse_path("M0,0 C0,0 10,5 10,0")
    assert subpaths_s_alone[0].points == subpaths_equivalent_c[0].points


def test_maki_harbor_icon_parses_and_converts():
    # Regression test for the exact bug this fix addresses: Mapbox Maki's
    # harbor.svg uses S commands and previously raised ValueError.
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 15 15">'
        '<path d="M7.5,0C5.5,0,4,1.567,4,3.5c0.0024,1.5629,1.0397,2.902,2.5,3.3379v6.0391'
        'c-0.9305-0.1647-1.8755-0.5496-2.6484-1.2695C2.7992,10.6273,2.002,9.0676,2.002,6.498'
        'c0.0077-0.5646-0.4531-1.0236-1.0176-1.0137C0.4329,5.493-0.0076,5.9465,0,6.498'
        'c0,3.0029,1.0119,5.1955,2.4902,6.5723C3.9685,14.4471,5.8379,15,7.5,15'
        'c1.6656,0,3.535-0.5596,5.0117-1.9395S14.998,9.4868,14.998,6.498'
        'c0.0648-1.3953-2.0628-1.3953-1.998,0c0,2.553-0.7997,4.1149-1.8535,5.0996'
        'C10.3731,12.3203,9.4288,12.7084,8.5,12.875V6.8418C9.9607,6.4058,10.9986,5.0642,11,3.5'
        'C11,1.567,9.5,0,7.5,0z M7.5,2C8.3284,2,9,2.6716,9,3.5S8.3284,5,7.5,5S6,4.3284,6,3.5S6.6716,2,7.5,2z"/>'
        "</svg>"
    )
    out = converter.convert_svg_to_symbol(svg)  # must not raise
    assert "POLYGON" in out
