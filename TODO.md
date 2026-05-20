


1. 第一件事：验证数据是否真的可检索

2. 第二件事：设计查询入口 QueryEngine / Retriever

3. 第三件事：加 metadata filter

4. 第四件事：做 hybrid search

5. 第五件事：加 reranker

6. 第六件事：做 Context Builder

7. 第七件事：设计 Prompt 约束

8. 第八件事：建立评估集

9. 第九件事：做灰度测试

10. 第十件事：做数据更新机制

11. 第十一件事：做观测 Observability

12. 第十二件事：接入客服 Agent

```
第一步：写 retriever 调试接口

第二步：打印 top_k 召回 Node，检查 text / metadata / score

第三步：加 tenant_id / kb_id / visibility / status metadata filter

第四步：整理 50 条测试问题

第五步：评估 Recall@5 / Recall@10

第六步：加 reranker

第七步：做上下文组装和引用来源

第八步：接 LLM 生成回答

第九步：做 answer faithfulness 评估

第十步：加 trace 日志

第十一步：做文档更新 / 删除机制

第十二步：封装成客服 Agent 的 RAG Tool
```