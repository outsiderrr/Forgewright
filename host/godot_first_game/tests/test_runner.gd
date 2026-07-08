extends SceneTree

var _failures := 0
var _tests_run := 0


func _init() -> void:
	_run("state_evaluator condition ops", Callable(self, "_test_state_evaluator_condition_ops"))
	_run("state_evaluator effects and monotonic policy", Callable(self, "_test_state_evaluator_effects_and_monotonic_policy"))
	_run("ontology_resolver display names", Callable(self, "_test_ontology_resolver"))
	_run("skill_check deterministic rolls", Callable(self, "_test_skill_check"))
	_run("unavailable_behavior routing flags", Callable(self, "_test_unavailable_behavior_flags"))
	_run("scene_router gold path smoke", Callable(self, "_test_scene_router_gold_path"))

	if _failures == 0:
		print("Godot host tests passed: %s" % _tests_run)
		quit(0)
	else:
		printerr("Godot host tests failed: %s/%s" % [_failures, _tests_run])
		quit(1)


func _run(test_name: String, test_callable: Callable) -> void:
	_tests_run += 1
	var before := _failures
	test_callable.call()
	if _failures == before:
		print("PASS %s" % test_name)


func _test_state_evaluator_condition_ops() -> void:
	var evaluator := StateEvaluator.new()
	evaluator.reset({
		"player": {
			"traits": ["observant", "patient"],
			"bonds": ["lanridge_shared_past"],
			"score": 5,
			"name": "iron road veteran",
		},
		"relationship": {
			"corvan": {"trust": 2},
		},
		"knowledge": {
			"blood_letter": {"stage_1": true},
		},
		"flag": {
			"read_the_room_used": false,
		},
	})

	_assert_true(evaluator.evaluate_condition({"op": "eq", "path": "player.score", "value": 5}), "eq should pass")
	_assert_true(evaluator.evaluate_condition({"op": "neq", "path": "player.score", "value": 4}), "neq should pass")
	_assert_true(evaluator.evaluate_condition({"op": "gt", "path": "player.score", "value": 4}), "gt should pass")
	_assert_true(evaluator.evaluate_condition({"op": "gte", "path": "relationship.corvan.trust", "value": 2}), "gte should pass")
	_assert_true(evaluator.evaluate_condition({"op": "lt", "path": "relationship.corvan.trust", "value": 3}), "lt should pass")
	_assert_true(evaluator.evaluate_condition({"op": "lte", "path": "relationship.corvan.trust", "value": 2}), "lte should pass")
	_assert_true(evaluator.evaluate_condition({"op": "has", "path": "player.traits", "value": "observant"}), "has should pass on arrays")
	_assert_true(evaluator.evaluate_condition({"op": "has", "path": "player.name", "value": "veteran"}), "has should pass on strings")
	_assert_true(evaluator.evaluate_condition({"op": "has_not", "path": "player.traits", "value": "reckless"}), "has_not should pass")
	_assert_true(evaluator.evaluate_condition({
		"all_of": [
			{"op": "has", "path": "player.traits", "value": "observant"},
			{"not": {"op": "eq", "path": "flag.read_the_room_used", "value": true}},
		],
	}), "all_of and not should pass")
	_assert_true(evaluator.evaluate_condition({
		"any_of": [
			{"op": "gte", "path": "relationship.corvan.trust", "value": 3},
			{"op": "has", "path": "player.bonds", "value": "lanridge_shared_past"},
		],
	}), "any_of should pass")
	_assert_true(evaluator.evaluate_condition({"op": "eq", "path": "knowledge.blood_letter.stage_1", "value": true}), "knowledge.* condition should pass")


func _test_state_evaluator_effects_and_monotonic_policy() -> void:
	var evaluator := StateEvaluator.new()
	evaluator.reset({})

	_assert_true(evaluator.apply_effect({"op": "set", "path": "knowledge.blood_letter.stage_1", "value": true}), "knowledge set true should pass")
	_assert_eq(evaluator.get_value("knowledge.blood_letter.stage_1"), true, "knowledge path should be set")
	_assert_false(evaluator.apply_effect({"op": "set", "path": "knowledge.blood_letter.stage_1", "value": false}), "knowledge set false should be rejected")
	_assert_eq(evaluator.get_value("knowledge.blood_letter.stage_1"), true, "knowledge path should remain true")
	_assert_false(evaluator.apply_effect({"op": "remove", "path": "knowledge.blood_letter.stage_1", "value": true}), "knowledge remove should be rejected")

	_assert_true(evaluator.apply_effect({"op": "set", "path": "flag.player_saw_blood_letter", "value": true}), "flag.player_* set true should pass")
	_assert_false(evaluator.apply_effect({"op": "set", "path": "flag.player_saw_blood_letter", "value": false}), "flag.player_* clear should be rejected")
	_assert_eq(evaluator.get_value("flag.player_saw_blood_letter"), true, "flag.player_* should remain true")

	_assert_true(evaluator.apply_effect({"op": "set", "path": "flag.non_player_temp", "value": true}), "non-monotonic set true should pass")
	_assert_true(evaluator.apply_effect({"op": "set", "path": "flag.non_player_temp", "value": false}), "non-monotonic set false should pass")
	_assert_eq(evaluator.get_value("flag.non_player_temp"), false, "non-monotonic flag can clear")

	_assert_true(evaluator.apply_effect({"op": "inc", "path": "relationship.vellin.trust", "value": 2}), "inc should pass")
	_assert_true(evaluator.apply_effect({"op": "dec", "path": "relationship.vellin.trust", "value": 1}), "dec should pass outside monotonic paths")
	_assert_eq(evaluator.get_value("relationship.vellin.trust"), 1, "inc/dec should update numeric state")
	_assert_true(evaluator.apply_effect({"op": "add", "path": "player.traits", "value": "observant"}), "add should pass")
	_assert_true(evaluator.apply_effect({"op": "remove", "path": "player.traits", "value": "observant"}), "remove should pass outside monotonic paths")
	_assert_eq(evaluator.get_value("player.traits"), [], "remove should delete array value")


func _test_ontology_resolver() -> void:
	var resolver := OntologyResolver.new()
	_assert_true(resolver.load_default(), "ontology default load should pass")
	_assert_eq(resolver.resolve_display_name("char_vellin"), "Vellin", "char_vellin should resolve to display_name")
	_assert_eq(resolver.resolve_display_name("scene_waystation_of_iron_oath"), "Waystation of the Iron Oath", "location should resolve to display_name")
	_assert_eq(resolver.resolve_display_name(null), "（旁白）", "null speaker should resolve to narrator")
	_assert_eq(resolver.resolve_display_name("char_missing"), "char_missing", "missing entity should fall back to ref")


func _test_skill_check() -> void:
	var checker := SkillCheck.new()
	var pass_result := checker.roll_check(
		{"skill_id": "observe", "dc": 12, "roll": 10},
		{"player": {"skills": {"observe": 2}}}
	)
	_assert_true(pass_result["success"], "10 + 2 should pass DC 12")
	_assert_eq(pass_result["skill_id"], "observe", "skill_id should roundtrip")
	_assert_eq(pass_result["roll"], 10, "roll should roundtrip")
	_assert_eq(pass_result["dc"], 12, "dc should roundtrip")

	var fail_result := checker.roll_check({"skill_id": "observe", "dc": 15, "roll": 9})
	_assert_false(fail_result["success"], "9 should fail DC 15")


func _test_unavailable_behavior_flags() -> void:
	var router := SceneRouter.new()
	router.evaluator.reset({"flag": {"gate": false}})
	var condition := {"op": "eq", "path": "flag.gate", "value": true}

	var hidden := router.get_option_availability({
		"condition": condition,
		"unavailable_behavior": "hide",
	})
	var disabled := router.get_option_availability({
		"condition": condition,
		"unavailable_behavior": "disable",
	})
	var hinted := router.get_option_availability({
		"condition": condition,
		"unavailable_behavior": "disable_with_hint",
	})

	_assert_false(hidden["visible"], "hide should remove unavailable options")
	_assert_true(disabled["visible"], "disable should keep unavailable options visible")
	_assert_eq(disabled["behavior"], "disable", "disable behavior should roundtrip")
	_assert_true(hinted["visible"], "disable_with_hint should keep unavailable options visible")
	_assert_eq(hinted["hint"], "条件不满足", "disable_with_hint should expose a hint")


func _test_scene_router_gold_path() -> void:
	var router := SceneRouter.new()
	_assert_true(router.start("res://data/test_scene_v0/scene.json"), "router should load packaged gold scene")
	_assert_eq(router.current_node_id, "arrival_waystation", "router should enter graph entry node")

	var arrival := router.get_current_node()
	var gated_option: Dictionary = arrival["options"][2]
	var availability := router.get_option_availability(gated_option)
	_assert_false(availability["available"], "read-the-room option should start unavailable")
	_assert_eq(availability["behavior"], "disable_with_hint", "read-the-room option should use disable_with_hint")
	_assert_true(availability["visible"], "disable_with_hint option should remain visible")

	var first := router.select_option("opt_confront_letter")
	_assert_true(first["ok"], "first option should navigate")
	_assert_eq(router.current_node_id, "vellin_confession", "router should enter confession node")
	_assert_eq(router.evaluator.get_value("flag.player_saw_blood_letter"), true, "on_enter_effects should apply")

	var second := router.select_option("opt_promise_silence")
	_assert_true(second["ok"], "ending option should navigate")
	_assert_eq(router.current_node_id, "end_silent_ally", "router should reach ending")
	_assert_eq(router.evaluator.get_value("relationship.vellin.trust"), 2, "option effects should apply")


func _assert_true(value: Variant, message: String) -> void:
	if not bool(value):
		_fail(message)


func _assert_false(value: Variant, message: String) -> void:
	if bool(value):
		_fail(message)


func _assert_eq(actual: Variant, expected: Variant, message: String) -> void:
	if actual != expected:
		_fail("%s; expected=%s actual=%s" % [message, var_to_str(expected), var_to_str(actual)])


func _fail(message: String) -> void:
	_failures += 1
	printerr("FAIL %s" % message)
