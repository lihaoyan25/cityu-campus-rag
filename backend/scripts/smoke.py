"""端到端冒烟测试：验证 登录→上传→入库→建会话→流式问答 全链路。

前置：已启动后端服务，且 .env 中 API key / MySQL 已正确配置。

用法（在 backend/ 目录下）:
  .venv\\Scripts\\python scripts\\smoke.py
"""
import asyncio
import json
import sys

import httpx

BASE = "http://127.0.0.1:8000"
ADMIN_USER = "admin"
ADMIN_PASS = "wJG$%pKTtPvt$lph"

SAMPLE_MD = """# 澳门城市大学简介

澳门城市大学（City University of Macau，简称 CityU Macau）位于澳门氹仔徐日升寅公马路，
是澳门一所综合性私立大学，以应用型人才培养见长，设有商学院、数据科学学院、
人文社会科学学院等学院。

## 校园设施

### 图书馆

大学图书馆位于主教学楼，学期内开放至晚上10点，
提供借阅、研讨室预约与打印服务。

## 常见问题

学生证遗失后可前往教务处办理补领，需携带身份证明文件。
"""


async def main() -> int:
    async with httpx.AsyncClient(timeout=180) as c:
        print("[1/6] 健康检查 ...", end=" ")
        r = await c.get(f"{BASE}/")
        r.raise_for_status()
        print("OK")

        print("[2/6] 管理员登录 ...", end=" ")
        r = await c.post(
            f"{BASE}/api/admin/auth/login",
            json={"username": ADMIN_USER, "password": ADMIN_PASS},
        )
        r.raise_for_status()
        headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
        print("OK")

        print("[3/6] 上传测试文档 ...", end=" ")
        r = await c.post(
            f"{BASE}/api/admin/documents/upload",
            files={"file": ("smoke_test.md", SAMPLE_MD.encode("utf-8"), "text/markdown")},
            headers=headers,
        )
        if r.status_code == 409:
            print("SKIP (内容已存在)")
            items = (await c.get(f"{BASE}/api/admin/documents", headers=headers)).json()["items"]
            doc_id = next(d["id"] for d in items if d["filename"] == "smoke_test.md")
        else:
            r.raise_for_status()
            doc_id = r.json()["id"]
            print(f"OK (doc_id={doc_id})")

        print("[4/6] 轮询入库状态 ...", end=" ")
        for _ in range(120):
            doc = (await c.get(f"{BASE}/api/admin/documents/{doc_id}", headers=headers)).json()
            if doc["status"] == "done":
                print(f"OK ({doc['chunk_count']} 个分片)")
                break
            if doc["status"] == "failed":
                print("FAILED:", doc["error"])
                return 1
            await asyncio.sleep(2)
        else:
            print("超时")
            return 1

        print("[5/6] 创建会话 ...", end=" ")
        session_id = (
            await c.post(f"{BASE}/api/chat/sessions")
        ).json()["id"]
        print(f"OK (session_id={session_id})")

        print("[6/6] 流式问答 ...")
        question = "学生证丢了去哪里补办？图书馆几点关门？"
        answer_parts: list[str] = []
        got_sources, got_done = False, False
        async with c.stream(
            "POST",
            f"{BASE}/api/chat/sessions/{session_id}/stream",
            json={"question": question},
        ) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line.startswith("data: "):
                    continue
                payload = line[6:]
                if payload == "[DONE]":
                    break
                event = json.loads(payload)
                etype = event.get("type")
                if etype == "sources":
                    got_sources = True
                    print(f"    <sources> {len(event['sources'])} 条引用")
                elif etype == "delta":
                    answer_parts.append(event["content"])
                elif etype == "tool":
                    print(f"    <tool> {event['name']}({event.get('arguments')})")
                elif etype == "error":
                    print("    <error>", event["message"])
                    return 1
                elif etype == "done":
                    got_done = True

        answer = "".join(answer_parts)
        print("\n=== 回答 ===")
        print(answer)
        ok = got_done and bool(answer.strip())
        print(f"\nsources事件: {'有' if got_sources else '无'} | done事件: {'有' if got_done else '无'}")

        # 清理测试会话（保留文档便于手动体验）
        await c.delete(f"{BASE}/api/chat/sessions/{session_id}")
        print("测试会话已清理。测试文档 doc_id=%d 已保留，可手动删除。" % doc_id)
        return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
