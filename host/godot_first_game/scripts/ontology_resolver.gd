class_name OntologyResolver
extends RefCounted

const DEFAULT_ONTOLOGY_DIR := "res://data/ontology"
const NARRATOR_NAME := "（旁白）"

var entities: Dictionary = {}


func load_default() -> bool:
	return load_dir(DEFAULT_ONTOLOGY_DIR)


func load_dir(dir_path: String) -> bool:
	var dir := DirAccess.open(dir_path)
	if dir == null:
		push_error("Unable to open ontology directory: %s" % dir_path)
		return false

	var ok := true
	dir.list_dir_begin()
	var file_name := dir.get_next()
	while file_name != "":
		if not dir.current_is_dir() and file_name.ends_with(".json"):
			ok = load_file(dir_path.path_join(file_name)) and ok
		file_name = dir.get_next()
	dir.list_dir_end()
	return ok


func load_file(path: String) -> bool:
	var payload := _read_json(path)
	if payload.is_empty():
		return false
	return load_payload(payload, path)


func load_payload(payload: Dictionary, source_name: String = "<payload>") -> bool:
	var raw_entities: Array = []
	if payload.has("entities"):
		raw_entities = payload["entities"]
	elif payload.has("ontology_stub") and typeof(payload["ontology_stub"]) == TYPE_DICTIONARY:
		raw_entities = payload["ontology_stub"].get("entities", [])
	else:
		return true

	for entity in raw_entities:
		if typeof(entity) != TYPE_DICTIONARY or not entity.has("id"):
			continue
		var entity_id := str(entity["id"])
		if entities.has(entity_id):
			push_error("Duplicate ontology id %s while loading %s" % [entity_id, source_name])
			return false
		entities[entity_id] = entity
	return true


func load_from_graph(graph: Dictionary) -> bool:
	return load_payload(graph, "dialogue graph")


func get_entity(entity_ref: Variant) -> Dictionary:
	if entity_ref == null:
		return {}
	var entity_id := str(entity_ref)
	if entities.has(entity_id) and typeof(entities[entity_id]) == TYPE_DICTIONARY:
		return entities[entity_id]
	return {}


func resolve_display_name(entity_ref: Variant, null_name: String = NARRATOR_NAME) -> String:
	if entity_ref == null:
		return null_name
	var entity := get_entity(entity_ref)
	if entity.has("display_name"):
		return str(entity["display_name"])
	return str(entity_ref)


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
