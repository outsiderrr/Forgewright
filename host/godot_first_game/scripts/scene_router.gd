class_name SceneRouter
extends RefCounted

const DEFAULT_SCENE_PATH := "content/test_scene_v0/scene.json"
const PACKAGED_SCENE_PATH := "res://data/test_scene_v0/scene.json"
const EXPECTED_SCHEMA_MAJOR := "0"

var evaluator: StateEvaluator
var skill_checker: SkillCheck

var current_graph: Dictionary = {}
var current_scene_id := ""
var current_node_id := ""
var scene_paths: Dictionary = {}
var last_check_result: Dictionary = {}
var last_status_message := ""


func _init(state_evaluator: StateEvaluator = null, checker: SkillCheck = null) -> void:
	evaluator = state_evaluator if state_evaluator != null else StateEvaluator.new()
	skill_checker = checker if checker != null else SkillCheck.new()


func start(scene_path: String = DEFAULT_SCENE_PATH, initial_state: Dictionary = {}) -> bool:
	evaluator.reset(initial_state)
	scene_paths.clear()
	last_check_result.clear()
	last_status_message = ""
	if not load_scene(scene_path):
		return false
	return enter_node(str(current_graph.get("entry_node_id", "")))


func load_scene(scene_path: String) -> bool:
	var resolved_path := resolve_scene_path(scene_path)
	if resolved_path == "":
		push_error("Scene file not found: %s" % scene_path)
		return false

	var payload := _read_json(resolved_path)
	if payload.is_empty():
		return false

	var version := str(payload.get("schema_version", ""))
	if version.split(".")[0] != EXPECTED_SCHEMA_MAJOR:
		push_error("Incompatible dialogue graph schema major: %s" % version)
		return false

	current_graph = payload
	current_scene_id = str(payload.get("graph_id", resolved_path.get_file().get_basename()))
	scene_paths[current_scene_id] = resolved_path
	return true


func register_scene(scene_id: String, scene_path: String) -> void:
	scene_paths[scene_id] = scene_path


func enter_node(node_id: String) -> bool:
	if not current_graph.has("nodes") or typeof(current_graph["nodes"]) != TYPE_DICTIONARY:
		push_error("Current scene has no nodes map.")
		return false
	var nodes: Dictionary = current_graph["nodes"]
	if not nodes.has(node_id):
		push_error("Node not found in current scene: %s" % node_id)
		return false
	current_node_id = node_id
	_apply_scene_reveal_for_node(get_current_node())
	var effects: Array = get_current_node().get("on_enter_effects", [])
	if not evaluator.apply_effects(effects):
		last_status_message = "进入节点时应用状态失败。"
		return false
	return true


func get_current_node() -> Dictionary:
	if current_graph.is_empty() or current_node_id == "":
		return {}
	return current_graph.get("nodes", {}).get(current_node_id, {})


func get_scene_metaparams() -> Dictionary:
	return current_graph.get("scene_metaparams", {}).duplicate(true)


func get_option_availability(option: Dictionary) -> Dictionary:
	var condition: Variant = option.get("condition")
	var available := evaluator.evaluate_condition(condition)
	var behavior := str(option.get("unavailable_behavior", "hide"))
	return {
		"available": available,
		"behavior": behavior,
		"visible": available or behavior != "hide",
		"hint": "" if available else "条件不满足",
	}


func select_option(option_id: String) -> Dictionary:
	var node := get_current_node()
	for option in node.get("options", []):
		if typeof(option) != TYPE_DICTIONARY or str(option.get("option_id", "")) != option_id:
			continue
		var availability := get_option_availability(option)
		if not availability["available"]:
			last_status_message = "该选项当前不可选。"
			return {"ok": false, "message": last_status_message}

		var target_node_id := str(option.get("target_node_id", ""))
		var check := _extract_active_check(option)
		if not check.is_empty():
			last_check_result = skill_checker.roll_check(check, evaluator.get_state())
			if last_check_result.get("success", false):
				target_node_id = str(check.get("success_target_node_id", target_node_id))
			else:
				target_node_id = str(check.get("failure_target_node_id", target_node_id))
			last_status_message = "检定 %s：%s + %s = %s / DC %s" % [
				last_check_result.get("skill_id", ""),
				last_check_result.get("roll", 0),
				last_check_result.get("modifier", 0),
				last_check_result.get("total", 0),
				last_check_result.get("dc", 0),
			]
		else:
			last_check_result.clear()
			last_status_message = ""

		if not evaluator.apply_effects(option.get("effects", [])):
			last_status_message = "选择后应用状态失败。"
			return {"ok": false, "message": last_status_message}
		return _go_to_target(target_node_id)

	last_status_message = "选项不存在：%s" % option_id
	return {"ok": false, "message": last_status_message}


func get_scene_transition_for_current_node() -> Dictionary:
	var branches: Array = current_graph.get("scene_branches", [])
	for branch in branches:
		if typeof(branch) != TYPE_DICTIONARY:
			continue
		if str(branch.get("exit_node_id", "")) != current_node_id:
			continue
		if evaluator.evaluate_condition(branch.get("condition")):
			return branch
	return {}


func advance_from_current_scene() -> Dictionary:
	var branch := get_scene_transition_for_current_node()
	if branch.is_empty():
		return {"ok": false, "message": "当前节点没有可用的 scene transition。"}
	var target_scene_id := str(branch.get("target_scene_id", ""))
	if not scene_paths.has(target_scene_id):
		return {"ok": false, "message": "未注册目标 scene：%s" % target_scene_id}
	if not load_scene(str(scene_paths[target_scene_id])):
		return {"ok": false, "message": "加载目标 scene 失败：%s" % target_scene_id}
	if not enter_node(str(current_graph.get("entry_node_id", ""))):
		return {"ok": false, "message": "进入目标 scene 入口节点失败。"}
	return {"ok": true, "message": ""}


func resolve_scene_path(scene_path: String) -> String:
	var candidates: Array[String] = []
	if scene_path != "":
		candidates.append(scene_path)
		if not scene_path.begins_with("res://") and not scene_path.begins_with("/"):
			candidates.append("res://" + scene_path)
			var project_dir := ProjectSettings.globalize_path("res://").trim_suffix("/")
			candidates.append(project_dir.path_join(scene_path))
			candidates.append(project_dir.get_base_dir().get_base_dir().path_join(scene_path))
	candidates.append(PACKAGED_SCENE_PATH)

	for candidate in candidates:
		if FileAccess.file_exists(candidate):
			return candidate
	return ""


func _go_to_target(target_node_id: String) -> Dictionary:
	if current_graph.get("nodes", {}).has(target_node_id):
		if enter_node(target_node_id):
			return {"ok": true, "message": ""}
		return {"ok": false, "message": "进入节点失败：%s" % target_node_id}

	if scene_paths.has(target_node_id):
		if not load_scene(str(scene_paths[target_node_id])):
			return {"ok": false, "message": "加载 scene 失败：%s" % target_node_id}
		if enter_node(str(current_graph.get("entry_node_id", ""))):
			return {"ok": true, "message": ""}
		return {"ok": false, "message": "进入 scene 入口失败：%s" % target_node_id}

	last_status_message = "目标节点或 scene 不存在：%s" % target_node_id
	return {"ok": false, "message": last_status_message}


func _apply_scene_reveal_for_node(node: Dictionary) -> void:
	var foreground_goal := str(node.get("foreground_goal", ""))
	for reveal in current_graph.get("scene_reveals", []):
		if typeof(reveal) != TYPE_DICTIONARY:
			continue
		var reveal_id := str(reveal.get("reveal_id", ""))
		if not reveal.get("trigger_node_ids", []).has(current_node_id):
			continue
		var stage := _stage_from_foreground_goal(foreground_goal, reveal_id)
		var path := "knowledge.%s.stage_%s" % [reveal_id, stage]
		evaluator.apply_effect({"op": "set", "path": path, "value": true})


func _stage_from_foreground_goal(goal: String, reveal_id: String) -> int:
	var prefix := reveal_id + ".stage_"
	if goal.begins_with(prefix):
		return int(goal.substr(prefix.length()))
	return 1


func _extract_active_check(option: Dictionary) -> Dictionary:
	if option.has("active_check") and typeof(option["active_check"]) == TYPE_DICTIONARY:
		return option["active_check"]
	var plugin_metadata: Variant = option.get("plugin_metadata", {})
	if typeof(plugin_metadata) == TYPE_DICTIONARY:
		var check: Variant = plugin_metadata.get("active_check", {})
		if typeof(check) == TYPE_DICTIONARY:
			return check
	return {}


func _read_json(path: String) -> Dictionary:
	var file := FileAccess.open(path, FileAccess.READ)
	if file == null:
		push_error("Unable to open JSON file: %s" % path)
		return {}
	var parser := JSON.new()
	var err := parser.parse(file.get_as_text())
	if err != OK:
		push_error("JSON parse failed for %s: %s" % [path, parser.get_error_message()])
		return {}
	if typeof(parser.data) != TYPE_DICTIONARY:
		push_error("Expected JSON object in %s" % path)
		return {}
	return parser.data
