# Forgewright Godot Demo — ADR-035 v_godot_custom 体感验证
# throwaway 原型 (50 行) ；跑通后即丢
# 故意不做：condition 评估 / effect 应用 / 本体解析 / 中文字体打包
extends Control

@onready var narration_label: RichTextLabel = $NarrationLabel
@onready var options_container: VBoxContainer = $OptionsContainer

var graph: Dictionary = {}
var current_node_id: String = ""


func _ready() -> void:
	# 读 scene.json
	var file := FileAccess.open("res://scene.json", FileAccess.READ)
	if file == null:
		push_error("无法打开 scene.json")
		return
	var content := file.get_as_text()
	file.close()

	# 解析 JSON
	var json := JSON.new()
	var err := json.parse(content)
	if err != OK:
		push_error("JSON 解析失败: " + json.get_error_message())
		return
	graph = json.data
	current_node_id = graph["entry_node_id"]
	render_node()


func render_node() -> void:
	var node: Dictionary = graph["nodes"][current_node_id]

	# 旁白 vs 角色对白
	var speaker := "（旁白）"
	if node.get("speaker_ref") != null:
		speaker = str(node["speaker_ref"])
	var location := str(node.get("location_ref", ""))

	# 渲染叙述文本（BBCode 富文本）
	narration_label.text = "[b]【%s · %s】[/b]\n\n%s" % [speaker, location, node["narration"]]

	# 清旧按钮
	for child in options_container.get_children():
		child.queue_free()

	# end 节点
	if node["type"] == "end":
		var end_label := Label.new()
		end_label.text = "—— 结局 ——"
		options_container.add_child(end_label)
		return

	# dialogue 节点：渲染选项为按钮（demo 版不评估 condition）
	for option in node["options"]:
		var button := Button.new()
		button.text = str(option["text"])
		var target := str(option["target_node_id"])
		button.pressed.connect(func(): _on_option_pressed(target))
		options_container.add_child(button)


func _on_option_pressed(target_node_id: String) -> void:
	current_node_id = target_node_id
	render_node()
