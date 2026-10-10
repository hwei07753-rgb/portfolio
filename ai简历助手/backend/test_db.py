"""
数据库初始化测试脚本

功能：
1. 创建所有数据库表
2. 插入测试数据（用户、简历、知识库条目）
3. 查询验证数据正确性
4. 清理测试数据

用法：
    cd ai-resume-optimizer
    python -m backend.test_db
"""

import sys
from pathlib import Path

# 确保项目根目录在 Python 路径中
root_dir = str(Path(__file__).parent.parent)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from backend.database import SessionLocal, init_db
from backend.models import KnowledgeEntry, Resume, User
from backend.utils.security import hash_password


def run_test() -> None:
    """运行数据库测试全流程"""

    # ============================================================
    # Step 1: 初始化数据库，创建所有表
    # ============================================================
    print("=" * 60)
    print("Step 1: Init DB, create all tables")
    print("=" * 60)
    init_db()

    db = SessionLocal()
    test_passed = True
    try:
        # ============================================================
        # Step 2: 创建测试数据
        # ============================================================
        print("\n" + "=" * 60)
        print("Step 2: Create test data")
        print("=" * 60)

        # 2.1 创建测试用户
        test_user = User(
            username="test_user",
            email="test@example.com",
            password_hash=hash_password("Test1234!"),
            is_active=True,
        )
        db.add(test_user)
        db.flush()  # 刷新以获取自增 ID
        print(f"[OK] Create user: id={test_user.id}, username={test_user.username}")

        # 2.2 创建测试简历
        test_resume = Resume(
            user_id=test_user.id,
            title="test_user_frontend_20260601",
            original_text=(
                "Name: Zhang San\n"
                "3 years frontend experience, familiar with React, Vue, "
                "led company website redesign, improved page load speed."
            ),
            target_city="Beijing",
            target_salary="20K-30K",
            target_jd="Frontend Engineer, React/TypeScript, 3yr exp",
            model_used="qwen3.7-max",
            status="completed",
            version=1,
            optimization_score=85.0,
        )
        db.add(test_resume)
        db.flush()
        print(f"[OK] Create resume: id={test_resume.id}, title={test_resume.title}")

        # 2.3 创建测试知识库条目
        test_knowledge = KnowledgeEntry(
            category="optimization_case",
            title="Frontend resume quantification case",
            content=(
                "## Before\nLed company website redesign, improved page load speed.\n\n"
                "## After\nLed frontend rebuild (React + TypeScript), "
                "reduced FCP from 3.2s to 1.1s (65% improvement) "
                "via code splitting and lazy loading, "
                "Lighthouse perf score from 52 to 94."
            ),
            source="auto_extract",
            resume_id=test_resume.id,
            industry="Tech",
            job_title="Frontend Engineer",
            tags='["frontend","performance","STAR","quantification"]',
            status="active",
            usage_count=0,
            effectiveness=0.0,
        )
        db.add(test_knowledge)
        db.flush()
        print(f"[OK] Create knowledge: id={test_knowledge.id}, title={test_knowledge.title}")

        # 提交事务
        db.commit()
        print("\n[OK] All test data committed to database")

        # ============================================================
        # Step 3: 查询验证数据正确性
        # ============================================================
        print("\n" + "=" * 60)
        print("Step 3: Query and verify data correctness")
        print("=" * 60)

        # 3.1 验证用户
        queried_user = db.query(User).filter(User.username == "test_user").first()
        assert queried_user is not None, "FAIL: User query returned None"
        assert queried_user.email == "test@example.com", "FAIL: User email mismatch"
        assert queried_user.is_active is True, "FAIL: User is_active mismatch"
        print(f"[PASS] User verified: {queried_user}")

        # 3.2 验证简历
        queried_resume = db.query(Resume).filter(Resume.user_id == queried_user.id).first()
        assert queried_resume is not None, "FAIL: Resume query returned None"
        assert queried_resume.status == "completed", "FAIL: Resume status mismatch"
        assert queried_resume.optimization_score == 85.0, "FAIL: Score mismatch"
        assert queried_resume.user.username == "test_user", "FAIL: FK user mismatch"
        print(f"[PASS] Resume verified: {queried_resume}")
        print(f"       FK user: {queried_resume.user.username}")

        # 3.3 验证知识库条目
        queried_knowledge = (
            db.query(KnowledgeEntry)
            .filter(KnowledgeEntry.resume_id == test_resume.id)
            .first()
        )
        assert queried_knowledge is not None, "FAIL: Knowledge query returned None"
        assert queried_knowledge.category == "optimization_case", "FAIL: Category mismatch"
        assert queried_knowledge.source == "auto_extract", "FAIL: Source mismatch"
        assert queried_knowledge.resume.title == test_resume.title, "FAIL: FK resume mismatch"
        print(f"[PASS] Knowledge verified: {queried_knowledge}")
        print(f"       FK resume: {queried_knowledge.resume.title}")

        # 3.4 验证关系映射（用户 → 简历列表）
        assert len(queried_user.resumes) == 1, "FAIL: User resumes count mismatch"
        assert queried_user.resumes[0].id == test_resume.id, "FAIL: User->Resume FK error"
        print(f"[PASS] User->Resume relation verified: {len(queried_user.resumes)} resume(s)")

        print("\n" + "=" * 60)
        print("ALL TESTS PASSED")
        print("=" * 60)

    except AssertionError as e:
        test_passed = False
        print(f"\n[FAIL] Test failed: {e}")
    except Exception as e:
        test_passed = False
        print(f"\n[ERROR] Exception: {type(e).__name__}: {e}")

    # ============================================================
    # Step 4: 清理测试数据（无论测试是否通过都执行）
    # ============================================================
    finally:
        print("\n" + "=" * 60)
        print("Step 4: Cleanup test data")
        print("=" * 60)

        try:
            # 按外键依赖顺序删除：知识库 → 简历 → 用户
            # 使用原始 ID 值避免依赖 ORM 对象状态
            dk = db.query(KnowledgeEntry).filter(
                KnowledgeEntry.title == "Frontend resume quantification case"
            ).delete(synchronize_session=False)
            print(f"[OK] Deleted knowledge entries: {dk}")

            dr = db.query(Resume).filter(
                Resume.title == "test_user_frontend_20260601"
            ).delete(synchronize_session=False)
            print(f"[OK] Deleted resumes: {dr}")

            du = db.query(User).filter(User.username == "test_user").delete(
                synchronize_session=False
            )
            print(f"[OK] Deleted users: {du}")

            db.commit()
            print("\n[OK] Test data cleaned up")

            # 验证清理结果
            remaining = db.query(User).filter(User.username == "test_user").count()
            assert remaining == 0, "FAIL: Test user still exists after cleanup"
            print("[OK] Cleanup verified: no residual test data")
        except Exception as cleanup_err:
            db.rollback()
            print(f"[WARN] Cleanup error: {cleanup_err}")
        finally:
            db.close()
            print("\nDatabase connection closed.")

    if not test_passed:
        sys.exit(1)


if __name__ == "__main__":
    run_test()
