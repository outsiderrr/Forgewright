class_name SkillCheck
extends RefCounted

var rng := RandomNumberGenerator.new()


func _init() -> void:
	rng.randomize()


func set_seed(seed_value: int) -> void:
	rng.seed = seed_value


func roll_check(check: Dictionary, actor_state: Dictionary = {}) -> Dictionary:
	var skill_id := str(check.get("skill_id", ""))
	var dc := int(check.get("dc", 0))
	var roll := int(check["roll"]) if check.has("roll") else rng.randi_range(1, 20)
	var modifier := int(check["modifier"]) if check.has("modifier") else _modifier_from_state(actor_state, skill_id)
	var total := roll + modifier
	return {
		"skill_id": skill_id,
		"dc": dc,
		"roll": roll,
		"modifier": modifier,
		"total": total,
		"success": total >= dc,
	}


func _modifier_from_state(actor_state: Dictionary, skill_id: String) -> int:
	if skill_id == "":
		return 0

	var player := actor_state.get("player", {})
	if typeof(player) == TYPE_DICTIONARY:
		var player_skills: Variant = player.get("skills", {})
		if typeof(player_skills) == TYPE_DICTIONARY and _is_number(player_skills.get(skill_id)):
			return int(player_skills[skill_id])

	var skills: Variant = actor_state.get("skills", {})
	if typeof(skills) == TYPE_DICTIONARY and _is_number(skills.get(skill_id)):
		return int(skills[skill_id])

	return 0


func _is_number(value: Variant) -> bool:
	var value_type := typeof(value)
	return value_type == TYPE_INT or value_type == TYPE_FLOAT
