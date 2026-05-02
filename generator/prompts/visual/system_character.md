# Forgewright character-sheet prompt template

> Bilingual prompt for character portraits (T-1.5.6 / ADR-014). The Chinese
> half (`## 中文`) is for author review only and is NOT shown to ChatGPT;
> the English half (`## English`) is what `ManualImportProvider` hashes and
> what the author copies into chatgpt.com.

## 中文（给作者审）

> 这一段**不**会被 ChatGPT 读到。它存在的目的是让作者一眼判断英文段是否真表达了你想要的意思——若不一致，改对应英文段。

### 设计意图（ADR-014 一致性 C+B 兜底）

- **风格基准**：半写实、油画感、戏剧光影；参考博德之门 3 / Disco Elysium 等"画风"，**不点名具体游戏品牌**避免开源剥离时的 IP 争议。
- **角色固定特征**（来自 `character_features.py` 的 `{{TARGET_REF}}` 词条）放在 prompt 的最高优先级位置，是 B 兜底——多张立绘之间的一致性主要靠这一段维持。
- **场景上下文**（情境氛围 / 时间 / 光源；从本体桩或 narration 反推）放第二段。
- **镜头规格**：character_sheet = 上半身肖像，脸部清晰可读；带 alpha 通道。
- **否定段**放最后（GPT-Image 对靠后的否定指令更敏感）。

### 本次生成参数

- 角色锚点 `target_ref`：`{{TARGET_REF}}`
- 表情：`{{EXPRESSION}}`
- 姿势：`{{POSE}}`
- 风格基准图（仅引用路径，不读图片字节；T-1.5.9 OpenAIImageProvider 决定是否上传）：
{{STYLE_REFERENCES_BLOCK_ZH}}

### 角色固定特征（B 兜底；与 narration 对齐）

{{CHARACTER_FEATURES_BLOCK}}

### 本体卡片片段（如果有，用于场景氛围回扣）

{{ONTOLOGY_CARD_BLOCK}}

---

## English (for ChatGPT)

> Paste **everything below this line, including this header**, into chatgpt.com (GPT-Image). Generate, pick the best, and download to the same folder as this file with the filename printed at the top of `README.md`.

You are generating a single character sheet portrait for an in-development tabletop-style narrative RPG. Render in a half-realistic painterly style with strong oil-painting brushwork and dramatic, low-key cinematic lighting. The mood is comparable to high-end Western CRPG character art — rich shadow values, warm key light, painted skin tones, no anime / cel-shading / cartoon stylisation. Do **not** name or imitate any specific commercial game's branding.

### Fixed character anchors (these MUST stay consistent across every portrait of this character)

Subject: `{{TARGET_REF}}`.

{{CHARACTER_FEATURES_BLOCK}}

The features above are the identity contract. Across multiple portraits of `{{TARGET_REF}}` they are non-negotiable; minor natural variation in expression, head angle, and lighting is allowed and expected.

### Scene context (atmosphere only — the portrait itself is character-focused)

{{ONTOLOGY_CARD_BLOCK_EN}}

### Per-portrait variant

- Expression: **{{EXPRESSION}}**.
- Pose / framing: **{{POSE}}**.

### Camera and composition

- Torso-up portrait. The face must be clearly readable; eyes in focus.
- Single subject, centred, neutral or scene-flavoured background (do not let the background dominate).
- Aspect ratio 1:1, output 1024×1024 minimum.

### Output specification

- File: PNG with **alpha channel** (transparent background acceptable; otherwise a soft, low-contrast wash that won't fight the character).
- No text, captions, watermarks, signatures, frame borders, or HUD overlays anywhere in the image.
- No modern items (eyeglasses, wristwatches, smartphones, ballpoint pens, plastics, zippers).
- No second character, no crowd; if hands or props are visible they must match the **Identifying props** line above.

### Style reference images (descriptive — for the artist / model to mirror, not to copy)

{{STYLE_REFERENCES_BLOCK_EN}}

### Negative directives

Do not produce: anime style, cel-shading, photo-real CGI, cartoon mascot, chibi, low-poly, pixel art, 3D render look, toy figurine, plastic skin, comic-book line art, manga screentone, modern clothing, modern technology, text overlays, captions, signatures, watermarks, picture frames, multiple subjects, NSFW content.
