class_name StateEvaluator
extends RefCounted

const CONDITION_SCHEMA_PATH := "res://schema/state_condition.schema.json"
const EFFECT_SCHEMA_PATH := "res://schema/state_effect.schema.json"
const DEPENDENCY_SCHEMA_PATH := "res://schema/content_dependency_index.schema.json"
const RUNTIME_POLICY_PATH := "res://data/state_runtime_policy.json"

var state: Dictionary = {}

var _condition_ops: Array = []
var _effect_ops: Array = []
var _state_path_regex: RegEx
var _monotonic_rules: Array = []


func _init() -> void:
	_load_schema_contracts()
	_load_runtime_policy()


func reset(initial_state: Dictionary = {}) -> void:
	state = initial_state.duplicate(true)


func get_state() -> Dictionary:
	return state.duplicate(true)


func get_value(path_value: Variant) -> Variant:
	return get_value_from_state(state, path_value)


func set_value(path_value: Variant, value: Variant) -> bool:
	if not _validate_state_path(path_to_string(path_value)):
		return false
	_set_path(state, path_value, value)
	return true


func has_path(path_value: Variant) -> bool:
	return _has_path(state, path_value)


func evaluate_condition(condition: Variant) -> bool:
	return evaluate_condition_with_state(state, condition)


func evaluate_condition_with_state(source_state: Dictionary, condition: Variant) -> bool:
	if condition == null:
		return true
	if typeof(condition) != TYPE_DICTIONARY:
		push_error("StateCondition must be a Dictionary or null.")
		return false

	var c: Dictionary = condition
	if c.has("all_of"):
		for child in c["all_of"]:
			if not evaluate_condition_with_state(source_state, child):
				return false
		return true

	if c.has("any_of"):
		for child in c["any_of"]:
			if evaluate_condition_with_state(source_state, child):
				return true
		return false

	if c.has("not"):
		return not evaluate_condition_with_state(source_state, c["not"])

	var op := str(c.get("op", ""))
	if not _condition_ops.has(op):
		push_error("StateCondition op is not declared by schema: %s" % op)
		return false

	var path_value: Variant = c.get("path")
	var path_string := path_to_string(path_value)
	if not _validate_state_path(path_string):
		return false

	var expected: Variant = c.get("value")
	var current: Variant = get_value_from_state(source_state, path_value)

	match op:
		"eq":
			return current == expected
		"neq":
			return current != expected
		"gt", "gte", "lt", "lte":
			return _compare_ordered(op, current, expected)
		"has":
			return _contains_value(current, expected)
		"has_not":
			return not _contains_value(current, expected)
		_:
			push_error("Unhandled StateCondition op: %s" % op)
			return false


func apply_effect(effect: Dictionary) -> bool:
	return apply_effect_to_state(state, effect)


func apply_effects(effects: Array) -> bool:
	for effect in effects:
		if typeof(effect) != TYPE_DICTIONARY or not apply_effect(effect):
			return false
	return true


func apply_effect_to_state(source_state: Dictionary, effect: Dictionary) -> bool:
	var op := str(effect.get("op", ""))
	if not _effect_ops.has(op):
		push_error("StateEffect op is not declared by schema: %s" % op)
		return false

	var path_value: Variant = effect.get("path")
	var path_string := path_to_string(path_value)
	if not _validate_state_path(path_string):
		return false

	var value: Variant = effect.get("value")
	if _violates_monotonic_policy(op, path_string, value):
		push_warning("Rejected monotonic StateEffect %s on %s" % [op, path_string])
		return false

	match op:
		"set":
			_set_path(source_state, path_value, value)
			return true
		"inc", "dec":
			return _apply_numeric_delta(source_state, path_value, value, op == "inc")
		"add":
			return _apply_add(source_state, path_value, value)
		"remove":
			return _apply_remove(source_state, path_value, value)
		_:
			push_error("Unhandled StateEffect op: %s" % op)
			return false


func path_to_string(path_value: Variant) -> String:
	var segments := _path_segments(path_value)
	return ".".join(segments)


func get_value_from_state(source_state: Dictionary, path_value: Variant) -> Variant:
	var segments := _path_segments(path_value)
	var node: Variant = source_state
	for segment in segments:
		if typeof(node) != TYPE_DICTIONARY or not node.has(segment):
			return null
		node = node[segment]
	return node


func is_monotonic_path(path_string: String) -> bool:
	for rule in _monotonic_rules:
		var regex: RegEx = rule.get("regex")
		if regex != null and regex.search(path_string) != null:
			return true
	return false


func _load_schema_contracts() -> void:
	var condition_schema := _read_json(CONDITION_SCHEMA_PATH)
	var effect_schema := _read_json(EFFECT_SCHEMA_PATH)
	var dependency_schema := _read_json(DEPENDENCY_SCHEMA_PATH)

	_condition_ops = _array_at(condition_schema, ["oneOf", 0, "properties", "op", "enum"])
	_effect_ops = _array_at(effect_schema, ["properties", "op", "enum"])

	var state_path_pattern := str(_value_at(dependency_schema, ["properties", "state_paths_written", "items", "pattern"], ""))
	_state_path_regex = RegEx.new()
	var err := _state_path_regex.compile(state_path_pattern)
	if err != OK:
		push_error("Failed to compile state path pattern from schema.")


func _load_runtime_policy() -> void:
	var policy := _read_json(RUNTIME_POLICY_PATH)
	_monotonic_rules.clear()
	for raw_rule in policy.get("monotonic_paths", []):
		if typeof(raw_rule) != TYPE_DICTIONARY:
			continue
		var pattern := str(raw_rule.get("pattern", ""))
		var regex := RegEx.new()
		if regex.compile(pattern) != OK:
			push_error("Failed to compile monotonic path pattern: %s" % pattern)
			continue
		var rule := raw_rule.duplicate(true)
		rule["regex"] = regex
		_monotonic_rules.append(rule)


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


func _array_at(source: Variant, keys: Array) -> Array:
	var value: Variant = _value_at(source, keys, [])
	if typeof(value) == TYPE_ARRAY:
		return value
	return []


func _value_at(source: Variant, keys: Array, fallback: Variant = null) -> Variant:
	var current: Variant = source
	for key in keys:
		if typeof(current) == TYPE_DICTIONARY:
			if not current.has(key):
				return fallback
			current = current[key]
		elif typeof(current) == TYPE_ARRAY and typeof(key) == TYPE_INT:
			if key < 0 or key >= current.size():
				return fallback
			current = current[key]
		else:
			return fallback
	return current


func _path_segments(path_value: Variant) -> Array:
	var segments: Array = []
	if typeof(path_value) == TYPE_STRING:
		for part in str(path_value).split("."):
			segments.append(str(part))
	elif typeof(path_value) == TYPE_ARRAY:
		for part in path_value:
			segments.append(str(part))
	else:
		push_error("State path must be a dotted string or an array of strings.")
		return []

	for segment in segments:
		if segment == "":
			push_error("State path contains an empty segment.")
			return []
	return segments


func _validate_state_path(path_string: String) -> bool:
	if path_string == "":
		push_error("State path must not be empty.")
		return false
	if _state_path_regex == null:
		push_error("State path schema pattern is not loaded.")
		return false
	if _state_path_regex.search(path_string) == null:
		push_error("State path is outside ADR-016 schema namespaces: %s" % path_string)
		return false
	return true


func _has_path(source_state: Dictionary, path_value: Variant) -> bool:
	var segments := _path_segments(path_value)
	var node: Variant = source_state
	for segment in segments:
		if typeof(node) != TYPE_DICTIONARY or not node.has(segment):
			return false
		node = node[segment]
	return true


func _set_path(source_state: Dictionary, path_value: Variant, value: Variant) -> void:
	var segments := _path_segments(path_value)
	if segments.is_empty():
		return
	var node: Dictionary = source_state
	for i in range(segments.size() - 1):
		var segment := str(segments[i])
		if not node.has(segment) or typeof(node[segment]) != TYPE_DICTIONARY:
			node[segment] = {}
		node = node[segment]
	node[str(segments[segments.size() - 1])] = value


func _compare_ordered(op: String, current: Variant, expected: Variant) -> bool:
	if not _is_number(current) or not _is_number(expected):
		return false
	match op:
		"gt":
			return current > expected
		"gte":
			return current >= expected
		"lt":
			return current < expected
		"lte":
			return current <= expected
	return false


func _contains_value(current: Variant, expected: Variant) -> bool:
	match typeof(current):
		TYPE_ARRAY:
			return current.has(expected)
		TYPE_DICTIONARY:
			return current.has(expected)
		TYPE_STRING:
			return typeof(expected) == TYPE_STRING and str(current).contains(str(expected))
		_:
			return false


func _apply_numeric_delta(source_state: Dictionary, path_value: Variant, value: Variant, positive: bool) -> bool:
	if not _is_number(value):
		push_error("inc/dec StateEffect requires numeric value.")
		return false
	var current: Variant = get_value_from_state(source_state, path_value)
	if current == null:
		current = 0
	if not _is_number(current):
		push_error("inc/dec StateEffect requires numeric current state.")
		return false
	var delta: Variant = value if positive else -value
	_set_path(source_state, path_value, current + delta)
	return true


func _apply_add(source_state: Dictionary, path_value: Variant, value: Variant) -> bool:
	var current: Variant = get_value_from_state(source_state, path_value)
	if current == null:
		current = []
	if typeof(current) != TYPE_ARRAY:
		push_error("add StateEffect requires an array current state.")
		return false
	var next_value: Array = current.duplicate(true)
	if not next_value.has(value):
		next_value.append(value)
	_set_path(source_state, path_value, next_value)
	return true


func _apply_remove(source_state: Dictionary, path_value: Variant, value: Variant) -> bool:
	var current: Variant = get_value_from_state(source_state, path_value)
	if current == null:
		return true
	if typeof(current) != TYPE_ARRAY:
		push_error("remove StateEffect requires an array current state.")
		return false
	var next_value: Array = []
	for item in current:
		if item != value:
			next_value.append(item)
	_set_path(source_state, path_value, next_value)
	return true


func _violates_monotonic_policy(op: String, path_string: String, value: Variant) -> bool:
	for rule in _monotonic_rules:
		var regex: RegEx = rule.get("regex")
		if regex == null or regex.search(path_string) == null:
			continue
		if rule.get("forbidden_ops", []).has(op):
			return true
		if op == "set" and rule.get("forbidden_set_values", []).has(value):
			return true
	return false


func _is_number(value: Variant) -> bool:
	var value_type := typeof(value)
	return value_type == TYPE_INT or value_type == TYPE_FLOAT
