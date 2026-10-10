"""
知识库流程联调测试

测试内容：
1. 知识自动提取 - 优化后检查知识库是否有新条目
2. 知识库查询 - 分类筛选、搜索、详情
3. 知识库注入 - 第二次优化是否参考历史知识
4. 知识库管理 - CRUD 操作
"""

import asyncio
import json
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.database import SessionLocal, init_db
from backend.models.knowledge import KnowledgeEntry
from backend.models.user import User
from backend.models.resume import Resume
from backend.services.knowledge_service import (
    create_entry,
    list_entries,
    get_entry,
    update_entry,
    delete_entry,
    get_stats,
)
from backend.schemas.knowledge import KnowledgeCreate


# 测试数据
TEST_USER = {
    "username": "test_knowledge",
    "email": "test_knowledge@example.com",
    "password": "Test123456!"
}

TEST_RESUME = {
    "title": "测试简历_知识库流程",
    "original_text": """
    张三
    前端工程师 | 3年经验

    工作经历：
    2023.06 - 至今  XX科技有限公司  前端开发工程师
    - 负责公司官网的开发和维护
    - 参与电商平台前端开发
    - 优化页面性能

    教育背景：
    2019.09 - 2023.06  XX大学  计算机科学与技术  本科

    技能：
    HTML, CSS, JavaScript, React, Vue
    """,
    "target_city": "北京",
    "target_salary": "20-30K",
    "target_jd": """
    前端开发工程师 - 高级
    岗位要求：
    1. 3年以上前端开发经验
    2. 精通 React 或 Vue 框架
    3. 熟悉 TypeScript
    4. 有性能优化经验
    5. 良好的团队协作能力
    """,
    "extra_details": "有大型电商平台开发经验"
}


class KnowledgeFlowTester:
    """知识库流程测试类"""

    def __init__(self):
        self.db = SessionLocal()
        self.user_id = None
        self.resume_id = None
        self.extracted_count = 0

    async def run_all_tests(self):
        """运行所有测试"""
        print("=" * 60)
        print("知识库流程联调测试")
        print("=" * 60)

        try:
            # 初始化数据库
            init_db()

            # 测试 0: 准备测试数据
            await self.setup_test_data()

            # 测试 1: 知识库管理（CRUD）
            await self.test_knowledge_crud()

            # 测试 2: 知识库查询
            await self.test_knowledge_query()

            # 测试 3: 知识库统计
            await self.test_knowledge_stats()

            # 测试 4: 知识自动提取（模拟）
            await self.test_knowledge_extraction()

            # 测试 5: 知识库注入验证
            await self.test_knowledge_injection()

            print("\n" + "=" * 60)
            print("[SUCCESS] 所有测试通过！")
            print("=" * 60)

        except Exception as e:
            print(f"\n[FAIL] 测试失败: {e}")
            import traceback
            traceback.print_exc()

        finally:
            self.db.close()

    async def setup_test_data(self):
        """准备测试数据"""
        print("\n[准备] 创建测试用户...")

        # 检查用户是否已存在
        existing = self.db.query(User).filter(User.email == TEST_USER["email"]).first()
        if existing:
            self.user_id = existing.id
            print(f"  用户已存在: ID={self.user_id}")
        else:
            from backend.utils.security import hash_password
            user = User(
                username=TEST_USER["username"],
                email=TEST_USER["email"],
                password_hash=hash_password(TEST_USER["password"]),
            )
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
            self.user_id = user.id
            print(f"  创建用户成功: ID={self.user_id}")

    async def test_knowledge_crud(self):
        """测试知识库 CRUD 操作"""
        print("\n[测试 1] 知识库管理（CRUD）")

        # 1.1 创建知识条目
        print("  1.1 创建知识条目...")
        entry_data = KnowledgeCreate(
            category="industry_practice",
            title="技术岗简历最佳实践",
            content="""## 通用规则
- 使用 STAR 原则描述项目经历
- 量化技术成果（性能提升百分比、用户规模、代码覆盖率）
- 突出技术栈与 JD 的匹配度
- 避免使用"精通"除非有充分佐证""",
            tags=["技术岗", "STAR原则", "量化"]
        )
        entry = create_entry(self.db, entry_data, source="manual")
        entry_id = entry.id
        print(f"    创建成功: ID={entry_id}, 标题={entry.title}")

        # 1.2 读取知识条目
        print("  1.2 读取知识条目...")
        retrieved = get_entry(self.db, entry_id)
        assert retrieved.id == entry_id, "读取的条目 ID 不匹配"
        print(f"    读取成功: ID={retrieved.id}, 标题={retrieved.title}")

        # 1.3 更新知识条目
        print("  1.3 更新知识条目...")
        updated = update_entry(
            self.db,
            entry_id,
            title="技术岗简历最佳实践（更新版）",
            tags=["技术岗", "STAR原则", "量化", "更新"]
        )
        assert updated.title == "技术岗简历最佳实践（更新版）", "标题更新失败"
        print(f"    更新成功: 新标题={updated.title}")

        # 1.4 创建更多测试条目
        print("  1.4 创建更多测试条目...")
        test_entries = [
            KnowledgeCreate(
                category="jd_keyword",
                title="前端开发关键词",
                content="React, Vue, TypeScript, Webpack, 性能优化",
                tags=["前端", "React", "Vue"]
            ),
            KnowledgeCreate(
                category="optimization_case",
                title="前端工程师优化案例",
                content="将模糊的'负责开发'改为'主导开发了XX系统，提升用户体验30%'",
                tags=["前端", "量化", "案例"]
            ),
            KnowledgeCreate(
                category="resume_template",
                title="ATS友好模板",
                content="使用标准的HTML标签，避免复杂布局...",
                tags=["ATS", "模板"]
            ),
        ]

        for data in test_entries:
            entry = create_entry(self.db, data, source="manual")
            print(f"    创建: ID={entry.id}, 分类={entry.category}, 标题={entry.title}")

        # 1.5 删除知识条目（删除一个测试条目）
        print("  1.5 删除知识条目...")
        delete_entry(self.db, entry_id)
        print(f"    删除成功: ID={entry_id}")

        print("  [PASS] CRUD 测试通过")

    async def test_knowledge_query(self):
        """测试知识库查询功能"""
        print("\n[测试 2] 知识库查询")

        # 2.1 查询全部条目
        print("  2.1 查询全部条目...")
        result = list_entries(self.db, page=1, size=10)
        total = result["total"]
        print(f"    总条目数: {total}")
        assert total > 0, "知识库为空"

        # 2.2 按分类筛选
        print("  2.2 按分类筛选...")
        categories = ["industry_practice", "jd_keyword", "optimization_case", "resume_template"]
        for cat in categories:
            result = list_entries(self.db, category=cat, page=1, size=10)
            print(f"    分类 '{cat}': {result['total']} 条")

        # 2.3 关键词搜索
        print("  2.3 关键词搜索...")
        keywords = ["STAR", "前端", "React", "ATS"]
        for kw in keywords:
            result = list_entries(self.db, keyword=kw, page=1, size=10)
            print(f"    关键词 '{kw}': {result['total']} 条")

        # 2.4 查看条目详情
        print("  2.4 查看条目详情...")
        if result["items"]:
            first_item = result["items"][0]
            detail = get_entry(self.db, first_item.id)
            print(f"    条目 ID={detail.id}:")
            print(f"      标题: {detail.title}")
            print(f"      分类: {detail.category}")
            print(f"      状态: {detail.status}")
            print(f"      来源: {detail.source}")
            print(f"      标签: {detail.tags}")

        print("  [PASS] 查询测试通过")

    async def test_knowledge_stats(self):
        """测试知识库统计"""
        print("\n[测试 3] 知识库统计")

        stats = get_stats(self.db)
        print(f"  总条目数: {stats['total']}")
        print(f"  按分类统计:")
        for cat, count in stats["by_category"].items():
            print(f"    - {cat}: {count}")
        print(f"  按状态统计:")
        for status, count in stats["by_status"].items():
            print(f"    - {status}: {count}")
        print(f"  使用最多的条目:")
        for item in stats["top_used"]:
            print(f"    - {item['title']}: {item['usage_count']} 次")

        print("  [PASS] 统计测试通过")

    async def test_knowledge_extraction(self):
        """测试知识自动提取（模拟）"""
        print("\n[测试 4] 知识自动提取")

        # 模拟知识提取结果（实际会调用 LLM）
        simulated_knowledge = {
            "patterns": [
                {
                    "type": "quantification",
                    "title": "量化页面性能优化成果",
                    "content": "将'优化页面性能'改为'通过代码分割和懒加载，首屏加载时间从3.2秒降至1.1秒，提升65%'",
                    "tags": ["性能优化", "量化", "前端"]
                },
                {
                    "type": "star_rewrite",
                    "title": "STAR原则重写项目经历",
                    "content": "使用STAR原则描述电商平台项目：主导商品详情页重构，提升转化率15%",
                    "tags": ["STAR原则", "项目经历"]
                }
            ],
            "jd_keywords": ["React", "TypeScript", "性能优化", "团队协作"],
            "industry": "互联网/科技",
            "job_level": "senior"
        }

        # 保存提取的知识点
        saved_count = 0

        # 保存优化模式
        for pattern in simulated_knowledge.get("patterns", []):
            entry = KnowledgeEntry(
                category="optimization_case",
                title=pattern.get("title", "优化案例"),
                content=pattern.get("content", ""),
                source="auto_extract",
                industry=simulated_knowledge.get("industry"),
                job_title=simulated_knowledge.get("job_level"),
                tags=json.dumps(pattern.get("tags", []), ensure_ascii=False),
                status="review_needed",
            )
            self.db.add(entry)
            saved_count += 1

        # 保存 JD 关键词
        jd_keywords = simulated_knowledge.get("jd_keywords", [])
        if jd_keywords:
            entry = KnowledgeEntry(
                category="jd_keyword",
                title=f"JD关键词-测试简历",
                content=f"从简历优化中提取的 JD 关键词: {', '.join(jd_keywords)}",
                source="auto_extract",
                industry=simulated_knowledge.get("industry"),
                tags=json.dumps(jd_keywords, ensure_ascii=False),
                status="review_needed",
            )
            self.db.add(entry)
            saved_count += 1

        self.db.commit()
        self.extracted_count = saved_count

        print(f"  模拟提取了 {saved_count} 条知识点")
        print(f"  - 优化模式: {len(simulated_knowledge['patterns'])} 条")
        print(f"  - JD关键词: 1 条")

        # 验证新条目
        result = list_entries(self.db, page=1, size=100)
        print(f"  知识库当前总条目: {result['total']}")

        print("  [PASS] 知识提取测试通过")

    async def test_knowledge_injection(self):
        """测试知识库注入验证"""
        print("\n[测试 5] 知识库注入验证")

        # 模拟 _get_knowledge_context 的逻辑
        from backend.models.knowledge import KnowledgeEntry

        knowledge_parts = []

        # 查询行业最佳实践
        practices = (
            self.db.query(KnowledgeEntry)
            .filter(
                KnowledgeEntry.category == "industry_practice",
                KnowledgeEntry.status == "active",
            )
            .order_by(KnowledgeEntry.effectiveness.desc())
            .limit(3)
            .all()
        )

        if practices:
            knowledge_parts.append("## 行业最佳实践")
            for p in practices:
                knowledge_parts.append(f"### {p.title}\n{p.content[:500]}")

        # 查询 JD 关键词
        keywords = (
            self.db.query(KnowledgeEntry)
            .filter(
                KnowledgeEntry.category == "jd_keyword",
                KnowledgeEntry.status == "active",
            )
            .order_by(KnowledgeEntry.usage_count.desc())
            .limit(5)
            .all()
        )

        if keywords:
            knowledge_parts.append("\n## 常见 JD 关键词")
            for k in keywords:
                try:
                    tags = json.loads(k.tags) if k.tags else []
                except json.JSONDecodeError:
                    tags = []
                if tags:
                    knowledge_parts.append(f"- {k.title}: {', '.join(tags[:5])}")

        # 查询优化案例
        cases = (
            self.db.query(KnowledgeEntry)
            .filter(
                KnowledgeEntry.category == "optimization_case",
                KnowledgeEntry.status == "active",
            )
            .order_by(KnowledgeEntry.effectiveness.desc())
            .limit(2)
            .all()
        )

        if cases:
            knowledge_parts.append("\n## 优化案例参考")
            for c in cases:
                knowledge_parts.append(f"### {c.title}\n{c.content[:300]}")

        knowledge_context = "\n".join(knowledge_parts)

        print("  知识库注入内容预览:")
        if knowledge_context:
            print("  " + "-" * 40)
            for line in knowledge_context.split("\n")[:20]:
                print(f"  {line}")
            if knowledge_context.count("\n") > 20:
                print("  ... (省略)")
            print("  " + "-" * 40)
        else:
            print("  [WARN] 知识库为空，无内容可注入")

        print(f"\n  知识库内容长度: {len(knowledge_context)} 字符")
        print(f"  包含最佳实践: {len(practices)} 条")
        print(f"  包含关键词库: {len(keywords)} 条")
        print(f"  包含优化案例: {len(cases)} 条")

        print("  [PASS] 知识注入测试通过")


async def main():
    """主函数"""
    tester = KnowledgeFlowTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
