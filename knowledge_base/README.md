# Knowledge Base

本目录是 LLMTier 面向人阅读的静态 Knowledge Base 根目录。目录名采用项目明确指定的代码标识符形式 `knowledge_base`，展示名称为 **Knowledge Base**。

## 内容边界

- `knowledge_base/` 只承载静态知识页面、附件和站点配置。
- 产品本地页面位于 `src/web/tier.html`，不属于 Knowledge Base。
- `rag/` 中的 ingestion manifest、向量索引和外部检索服务不属于本目录。
- 建立本目录不启用问答、RAG、复杂 ACL、外部索引或 Runtime Activation。

## 当前状态

当前只建立可追踪的 Knowledge Base 根目录。尚无需要迁入的静态页面、素材或站点生成配置，因此暂不创建空的 `docs/`、`assets/` 或 `site/` 子目录，也没有站点构建或发布动作。

后续只有在实际内容进入时才创建对应子目录，并同时补充本地预览、构建、内部链接、资源存在性和页面路径唯一性检查。
