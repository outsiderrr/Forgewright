# Forgewright scene-background prompt template

> Bilingual prompt for environmental establishing shots (T-1.5.6 / ADR-014).
> The Chinese half (`## 中文`) is for author review only and is NOT shown
> to ChatGPT; the English half (`## English`) is what `ManualImportProvider`
> hashes and what the author copies into chatgpt.com.

## 中文（给作者审）

> 这一段**不**会被 ChatGPT 读到。仅用于让作者快速判断英文段意图。

### 设计意图（ADR-014 风格一致 + 场景背景规约）

- **风格基准**与角色立绘同源（半写实、油画感、戏剧光影；不点名具体游戏品牌），保证立绘 + 背景在同一画面里不撕裂。
- **场景上下文**（建筑 / 地理 / 旗帜 / 标志物）从本体桩 + scene.json narration 反推；不矛盾原文为底线。
- **镜头规格**：场景背景 = 环境镜头，**画面内不出现任何角色**（角色由立绘层另出）。
- **输出**：PNG，**不带 alpha**（背景层应为完整画面）。
- **否定段**强调"无角色 / 无现代元素 / 无文字"。

### 本次生成参数

- 场景锚点 `target_ref`：`{{TARGET_REF}}`（类型：`{{TARGET_TYPE}}`）
- 时段：`{{TIME_OF_DAY}}`
- 天气：`{{WEATHER}}`
- 风格基准图（仅引用路径；T-1.5.9 决定是否上传）：
{{STYLE_REFERENCES_BLOCK_ZH}}

### 本体卡片片段

{{ONTOLOGY_CARD_BLOCK}}

---

## English (for ChatGPT)

> Paste everything below this line into chatgpt.com (GPT-Image). Generate, pick the best, and download to the same folder as this file (filename in `README.md`).

You are generating a single environmental establishing shot for an in-development tabletop-style narrative RPG. Render in a half-realistic painterly style with oil-painting brushwork and dramatic cinematic lighting. The visual register matches a high-end Western CRPG environment painting — atmospheric perspective, painted textures, hand-crafted feel, no photo-real CGI, no anime / cel-shading. Do **not** name or imitate any specific commercial game's branding.

### Scene anchors (must stay consistent across multiple variants of this same scene)

Subject: `{{TARGET_REF}}` (type: `{{TARGET_TYPE}}`).

{{ONTOLOGY_CARD_BLOCK_EN}}

These anchors are the identity contract for the location. Across `dusk` / `interior_lamplight` / etc. variants the architecture, key landmarks, banners, and material palette stay the same; lighting, weather, and time-of-day vary.

### Per-variant variant

- Time of day: **{{TIME_OF_DAY}}**.
- Weather: **{{WEATHER}}**.

### Camera and composition

- Wide environmental shot. **No characters visible anywhere in the frame.**
- The composition should be readable as the establishing shot for a scene that will later be populated by character sprites layered on top — leave clear visual room near the lower-middle / foreground for that overlay.
- Aspect ratio 1:1, output 1024×1024 minimum.

### Output specification

- File: PNG, **no alpha channel** — solid full-frame background.
- No text, captions, watermarks, signatures, banners reading real-world languages, frame borders, or UI overlays anywhere in the image.
- No characters, no figures, no animals as focal subjects (incidental wildlife such as a distant bird is acceptable).
- No modern items (electric lights, vehicles, road signs, pavement markings, satellite dishes).

### Style reference images (descriptive — mirror, do not copy)

{{STYLE_REFERENCES_BLOCK_EN}}

### Negative directives

Do not produce: anime style, cel-shading, photo-real CGI, cartoon, chibi, low-poly, pixel art, 3D render look, isometric video-game tile art, comic-book line art, manga screentone, modern clothing, modern technology, present-day infrastructure, text overlays, captions, signatures, watermarks, picture frames, characters, human figures, NSFW content.
