extends Control

@onready var dialogue_control: DialogueControl = %DialogueControl

var evaluator := StateEvaluator.new()
var skill_checker := SkillCheck.new()
var router := SceneRouter.new(evaluator, skill_checker)
var ontology_resolver := OntologyResolver.new()


func _ready() -> void:
	ontology_resolver.load_default()
	var scene_path := _scene_path_from_args()
	if not router.start(scene_path):
		push_error("Failed to start Forgewright scene: %s" % scene_path)
		return
	ontology_resolver.load_from_graph(router.current_graph)
	dialogue_control.setup(router, ontology_resolver)


func _scene_path_from_args() -> String:
	for arg in OS.get_cmdline_args():
		if arg.begins_with("--scene="):
			return arg.substr("--scene=".length())
	return SceneRouter.DEFAULT_SCENE_PATH
