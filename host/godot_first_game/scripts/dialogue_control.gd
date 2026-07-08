class_name DialogueControl
extends Control

const OPTION_BUTTON_SCENE := preload("res://scenes/option_button.tscn")

@onready var speaker_label: Label = %SpeakerLabel
@onready var location_label: Label = %LocationLabel
@onready var narration_label: RichTextLabel = %NarrationLabel
@onready var options_container: VBoxContainer = %OptionsContainer
@onready var status_label: Label = %StatusLabel
@onready var scene_label: Label = %SceneLabel

var router: SceneRouter
var ontology_resolver: OntologyResolver


func setup(scene_router: SceneRouter, resolver: OntologyResolver) -> void:
	router = scene_router
	ontology_resolver = resolver
	render_current_node()


func render_current_node() -> void:
	if router == null or ontology_resolver == null:
		return

	var node := router.get_current_node()
	if node.is_empty():
		_show_status("未加载对话节点。")
		return

	speaker_label.text = ontology_resolver.resolve_display_name(node.get("speaker_ref"))
	location_label.text = ontology_resolver.resolve_display_name(node.get("location_ref"), str(node.get("location_ref", "")))
	scene_label.text = str(router.current_scene_id)
	narration_label.text = _bbcode_escape(str(node.get("narration", "")))
	_show_status(router.last_status_message)
	_clear_options()

	if str(node.get("type", "")) == "end":
		_render_end_options()
		return

	for option in node.get("options", []):
		if typeof(option) != TYPE_DICTIONARY:
			continue
		var availability := router.get_option_availability(option)
		if not bool(availability.get("visible", true)):
			continue
		var button: DialogueOptionButton = OPTION_BUTTON_SCENE.instantiate()
		button.configure(option, availability)
		button.option_chosen.connect(_on_option_chosen)
		options_container.add_child(button)

	if options_container.get_child_count() == 0:
		var label := _make_info_label("[无可用选项]")
		options_container.add_child(label)


func _on_option_chosen(option_id: String) -> void:
	var result := router.select_option(option_id)
	if not bool(result.get("ok", false)):
		_show_status(str(result.get("message", "选项执行失败。")))
	render_current_node()


func _render_end_options() -> void:
	var end_label := _make_info_label("—— 结局 ——")
	options_container.add_child(end_label)

	var branch := router.get_scene_transition_for_current_node()
	if not branch.is_empty():
		var button := Button.new()
		button.text = "继续"
		button.custom_minimum_size = Vector2(0, 52)
		button.pressed.connect(func() -> void:
			var result := router.advance_from_current_scene()
			if not bool(result.get("ok", false)):
				_show_status(str(result.get("message", "scene transition 失败。")))
			render_current_node()
		)
		options_container.add_child(button)


func _clear_options() -> void:
	for child in options_container.get_children():
		child.queue_free()


func _show_status(message: String) -> void:
	status_label.text = message
	status_label.visible = message.strip_edges() != ""


func _make_info_label(text_value: String) -> Label:
	var label := Label.new()
	label.text = text_value
	label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	label.custom_minimum_size = Vector2(0, 44)
	return label


func _bbcode_escape(value: String) -> String:
	return value.replace("[", "[lb]").replace("]", "[rb]")
