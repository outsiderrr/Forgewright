# SCHEMA_v0.2.md — 项目 Schema 设计基线 · v0.2 增量

> 本文件承接 SCHEMA_v0.md（v0.1.x）；记录 v0.2.0 引入的 Schema 增量。
>
> **重要**：v0.2.0 是项目**首次新增 schema 文件**（不是修改 existing schema）。existing `/schema/*.json` + `/content/test_scene_v0/scene.json` 的 schema_version 保持 0.1.1（沿用阶段 1 T-1.0 commit `c47c9cf` "非结构性变更不联动 schema_version" 先例）。仅新增文件 `/schema/image_asset.schema.json` 起步 schema_version=0.2.0。

## 1. 增量摘要（占位 — T-1.5.2 填）

## 2. ImageAsset Schema 定义（占位 — T-1.5.2 填）

## 3. 本体角色实体扩展：visual_assets 字段（占位 — T-1.5.2 填）

## 4. 兼容性约束

- v0.2.0 不破坏 v0.1.x 任何 existing 字段
- v0.1.x 数据加载时 visual_assets 视为空数组（默认）
- DialogueNode / DialogueGraph / Option / StateEffect / StateCondition 在 v0.2.0 内**不变**

## 版本

本文件版本：v0.2.0（占位；T-1.5.2 落地正式内容）
最后更新：2026-04-30
