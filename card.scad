// Path to the pre-generated template card STL used as the base shape.
template_file = "template_card.stl";

// Default text and font used for the card label.
text = "Jon Smith";
font = "Arial Rounded MT Bold";
text_margin = 0.1;  // Margin from the card edges for text placement.

// Card dimensions in millimeters. These are used when calculating the size of the text.
card_h = 30;
card_l = 100;
card_d = 2;

// Text sizing and emboss settings.
sample_size = 10;   // Starting sample size used for text metrics.
max_font_size = 9;  // Maximum allowed font size after scaling.
emboss_height = 1.0;  // Height of the raised embossed text.
text_resolution = 128;  // Resolution used only for text geometry.

generate_hole = false;  // Toggle to create a hole in the card.
hole_offset = 5.5;      // Offset from the top-right corner for the hole.
hole_depth = 20;        // Depth of the hole cylinder.
hole_radius = 2;        // Radius of the hole cylinder.

// Polygon resolution setting. Override from OpenSCAD with -D resolution=<value>.
resolution = 64;
$fn = resolution;  // Resolution used for circles and cylinders.

// Import BOSL2 helpers for textmetrics and other utilities.
include <BOSL2/std.scad>

// Create the text card model by importing the template shape and embossing centered text.
module text_card(x=card_l, y=card_h, z=card_d, card_text=text, emboss_height=emboss_height, font=font, template_file=template_file) {
    // Compute the available area inside the card margins.
    usable_x = x * (1 - text_margin * 2);
    usable_y = y * (1 - text_margin * 2);

    // Measure text metrics at a sample size to scale text to fit.
    m = textmetrics(card_text, size=sample_size, font=font);

    // Determine the scale factor needed to fit the text inside the usable area.
    scale_x = usable_x / m.advance.x;
    scale_y = usable_y / (m.ascent - m.descent);
    final_size = min(max_font_size, sample_size * min(scale_x, scale_y));

    // Import the card template and emboss the text on top.
    import(template_file);
    $fn = text_resolution;
    linear_extrude(height=emboss_height+z)
        text(card_text, size=final_size, halign="center", valign="center", font=font);
}

// Render the card and optionally subtract a hole for hanging or attaching.
difference() {
    text_card();
    $fn = resolution;
    if (generate_hole) {
        back(card_h / 2 - hole_offset) right(card_l / 2 - hole_offset) down(1)
            cylinder(hole_depth, hole_radius);
    }
}