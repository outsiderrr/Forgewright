class_name DialogueOptionButton
extends Button

signal option_chosen(option_id: String)

var option_id := ""
var _available := true


func _ready() -> void:
	focus_mode = Control.FOCUS_ALL
	pressed.connect(_on_pressed)


func configure(option: Dictionary, availability: Dictionary) -> void:
	option_id = str(option.get("option_id", ""))
	_available = bool(availability.get("available", true))
	var behavior := str(availability.get("behavior", "hide"))
	var base_text := str(option.get("text", ""))
	var hint := str(availability.get("hint", ""))

	disabled = not _available
	text = base_text
	tooltip_text = base_text
	if not _available and behavior == "disable_with_hint" and hint != "":
		text = "%s  （%s）" % [base_text, hint]
		tooltip_text = "%s\n%s" % [base_text, hint]

	_apply_state_style(behavior)


func _on_pressed() -> void:
	if _available:
		option_chosen.emit(option_id)


func _apply_state_style(behavior: String) -> void:
	var normal := StyleBoxFlat.new()
	normal.corner_radius_top_left = 6
	normal.corner_radius_top_right = 6
	normal.corner_radius_bottom_left = 6
	normal.corner_radius_bottom_right = 6
	normal.content_margin_left = 18
	normal.content_margin_right = 18
	normal.content_margin_top = 12
	normal.content_margin_bottom = 12

	var hover := normal.duplicate() as StyleBoxFlat
	var pressed_style := normal.duplicate() as StyleBoxFlat
	var disabled_style := normal.duplicate() as StyleBoxFlat

	if _available:
		normal.bg_color = Color(0.16, 0.13, 0.11, 0.94)
		normal.border_color = Color(0.55, 0.39, 0.22, 0.85)
		normal.set_border_width_all(1)
		hover.bg_color = Color(0.24, 0.18, 0.13, 0.98)
		hover.border_color = Color(0.88, 0.63, 0.33, 0.95)
		hover.set_border_width_all(1)
		pressed_style.bg_color = Color(0.30, 0.20, 0.12, 1.0)
		add_theme_color_override("font_color", Color(0.94, 0.89, 0.79, 1.0))
		add_theme_color_override("font_hover_color", Color(1.0, 0.94, 0.82, 1.0))
	else:
		disabled_style.bg_color = Color(0.11, 0.11, 0.11, 0.78)
		disabled_style.border_color = Color(0.35, 0.33, 0.30, 0.55)
		disabled_style.set_border_width_all(1)
		var color := Color(0.58, 0.55, 0.50, 1.0)
		if behavior == "disable_with_hint":
			color = Color(0.72, 0.62, 0.47, 1.0)
		add_theme_color_override("font_disabled_color", color)

	add_theme_stylebox_override("normal", normal)
	add_theme_stylebox_override("hover", hover)
	add_theme_stylebox_override("pressed", pressed_style)
	add_theme_stylebox_override("disabled", disabled_style)
