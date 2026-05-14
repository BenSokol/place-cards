// Card dimensions and thickness.
card_h = 30;   // Card height in millimeters.
card_l = 100;  // Card length in millimeters.
card_d = 2;    // Base card thickness in millimeters.

// Radius scaling and ridge dimensions for the card border.
radius_scale = 0.75;  // Scale for the inner rounded card used to cut the ridge.

ridge_w = 2;  // Width of the raised ridge around the card.
ridge_h = 1;  // Height of the raised ridge around the card.

// Optional hole parameters.
generate_hole = false;         // Toggle to create a hole in the card.
hole_offset = 5.5;            // Distance from the card edge to the hole center.
hole_depth = 20;             // Depth of the cylindrical hole.
hole_radius = 2;             // Radius of the cylindrical hole.

// Polygon resolution setting. Override from OpenSCAD with -D resolution=<value>.
resolution = 64;
$fn = resolution;

// Import BOSL2 utility library for useful geometry helpers.
include <BOSL2/std.scad>

// Create a rounded rectangle with fillets on XY and Z edges.
// Uses minkowski() around a centered cube plus a small rounding circle.
module rounded_card(size, xy_r=7, z_r=0.5) {
    minkowski() {
        up(size[2]/2)
            cube([size[0] - 2*xy_r, size[1] - 2*xy_r, size[2] - 2*z_r], center=true);
        rotate_extrude()
            translate([xy_r - z_r, 0]) circle(r=z_r);
    }
}

// Build the template card with an outer body and a recessed inner cutout.
// The result is a card with a raised border ridge.
module template_card(x=card_l, y=card_h, z=card_d, xy_r=7, z_r=0.5, ridge_w=ridge_w, ridge_h=ridge_h) {
    difference() {
        // Outer rounded card body, including ridge height.
        rounded_card([x, y, z+ridge_h], xy_r=xy_r, z_r=z_r);

        // Inner rounded section cut out to form the border ridge.
        up(z) rounded_card([x-ridge_w*2, y-ridge_w*2, 1+ridge_h], xy_r=(xy_r*radius_scale), z_r=0.001);
    }
}

// Render the final template card and optionally subtract a hole.
difference() {
    template_card();
    if (generate_hole) {
        // Position the hole offset from the top-right corner and subtract it.
        back(card_h / 2 - hole_offset) right(card_l / 2 - hole_offset) down(1) cylinder(hole_depth, hole_radius);
    }
}