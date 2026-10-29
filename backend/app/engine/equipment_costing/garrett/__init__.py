"""Garrett equipment modules. Explicit registry; no fallback to another author."""

from importlib import import_module

METHOD_MODULES = {
    "garrett-a1-256": "activated_carbon_adsorbers",
    "garrett-a1-257": "agitators",
    "garrett-a1-258": "agitated_tanks",
    "garrett-a1-259": "air_conditioning",
    "garrett-a1-260": "blenders",
    "garrett-a1-261": "blowers",
    "garrett-a1-262": "boilers",
    "garrett-a1-263": "waste_heat_boilers",
    "garrett-a1-264": "buildings",
    "garrett-a1-265": "centrifuges",
    "garrett-a1-266": "chimneys_and_stacks",
    "garrett-a1-267": "rake_or_spiral_classifiers",
    "garrett-a1-268": "distillation_columns_and_absorption_towers",
    "garrett-a1-269": "column_trays",
    "garrett-a1-270": "column_packing",
    "garrett-a1-271": "medium_low_pressure_compressors",
    "garrett-a1-272": "high_capacity_high_pressure_compressors",
    "garrett-a1-273": "conveyors",
    "garrett-a1-274": "coolers_and_quenchers",
    "garrett-a1-275": "cooling_towers",
    "garrett-a1-276": "crystallizers",
    "garrett-a1-277": "dryers",
    "garrett-a1-278": "ducts",
    "garrett-a1-279": "dust_collectors",
    "garrett-a1-280": "evaporators",
    "garrett-a1-281": "fans",
    "garrett-a1-282": "filters",
    "garrett-a1-283": "flares",
    "garrett-a1-284": "furnaces",
    "garrett-a1-285": "electric_power_generators",
    "garrett-a1-286": "shell_and_tube_double_pipe_and_air_cooled_heat_exchangers",
    "garrett-a1-287": "spiral_and_plate_and_frame_heat_exchangers",
    "garrett-a1-288": "incinerators",
    "garrett-a1-289": "insulation",
    "garrett-a1-290": "ion_exchange",
    "garrett-a1-291": "hammer_mills_jaw_gyratory_and_roll_crushers",
    "garrett-a1-292": "ball_rod_pebble_jet_and_rubbish_mills",
    "garrett-a1-293": "motors_and_drives",
    "garrett-a1-294": "pipe_and_pipelines",
    "garrett-a1-295": "roll_and_screw_presses",
    "garrett-a1-296": "centrifugal_pumps",
    "garrett-a1-297": "miscellaneous_pumps",
    "garrett-a1-298": "pressure_vessels",
    "garrett-a1-299": "reactors",
    "garrett-a1-300": "refrigeration",
    "garrett-a1-301": "vibrating_screens",
    "garrett-a1-302": "size_enlargement_equipment",
    "garrett-a1-303": "tanks",
    "garrett-a1-304": "small_tanks",
    "garrett-a1-305": "thickeners_and_clarifiers",
    "garrett-a1-306": "vacuum_equipment",
}


def estimate_base_price(*, equipment_id: str, catalog_id: str, **design_inputs):
    if catalog_id not in METHOD_MODULES:
        raise ValueError(f"Unknown Garrett equipment catalog ID: {catalog_id}")
    method = import_module(f"{__name__}.{METHOD_MODULES[catalog_id]}")
    return method.estimate_base_price(equipment_id=equipment_id, **design_inputs)
