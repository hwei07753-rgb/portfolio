-- 数据库初始化脚本 · 项目: 看板式敏捷项目任务管理系统
-- 数据库名: project_db

CREATE DATABASE IF NOT EXISTS project_db
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

USE project_db;

-- ============================================================
-- 表 1：user（P0 · 用户基本信息与登录凭据）
-- ============================================================
CREATE TABLE user (
  id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  username VARCHAR(32) NOT NULL COMMENT '用户名（登录用 · 2-50字符 · 字母/数字/下划线）',
  password VARCHAR(255) NOT NULL COMMENT 'BCrypt加密密码（禁止明文存储）',
  nickname VARCHAR(50) NULL COMMENT '昵称（展示用 · NULL时全站统一fallback显示username：成员列表/任务指派列/评论作者等）',
  email VARCHAR(100) NULL COMMENT '邮箱（可空 · 唯一约束 · NULL值不参与唯一校验 · P2 @提醒功能需要时再提示补填）',
  is_deleted TINYINT(1) NOT NULL DEFAULT 0 COMMENT '逻辑删除 0=正常 1=已删除',
  create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  UNIQUE INDEX uniq_username (username),
  UNIQUE INDEX uniq_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户表（P0）';

-- ============================================================
-- 表 2：project（P0 · 项目信息 · 物理删除为运维操作：应用层不支持删除仅归档隐藏，子表CASCADE规则仅用于保障数据一致性；task_log RESTRICT阻止有日志任务的物理删除）
-- ============================================================
CREATE TABLE project (
  id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  name VARCHAR(100) NOT NULL COMMENT '项目名称（1-100字符）',
  owner_id BIGINT NOT NULL COMMENT '创建者ID（不可变 · 用于溯源 · 创建时自动设为当前用户）',
  archived TINYINT(1) NOT NULL DEFAULT 0 COMMENT '归档状态 0=活跃 1=已归档（单向流转 · 不支持取消归档）· 并发保护：UPDATE SET archived=1 WHERE id=? AND archived=0（幂等 · 重复执行无副作用）',
  is_deleted TINYINT(1) NOT NULL DEFAULT 0 COMMENT '逻辑删除（预留字段 · 当前业务不支持项目删除仅归档隐藏 · PRD P0-2）',
  create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  INDEX idx_owner_id (owner_id),
  FOREIGN KEY (owner_id) REFERENCES user(id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='项目表（P0）';

-- ============================================================
-- 表 3：project_member（P0 · 项目成员关联与角色）
-- ============================================================
CREATE TABLE project_member (
  id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  project_id BIGINT NOT NULL COMMENT '项目ID',
  user_id BIGINT NOT NULL COMMENT '用户ID',
  role VARCHAR(16) NOT NULL DEFAULT 'member' COMMENT '角色 owner=项目负责人（独有管成员+归档权限） member=普通成员（参与任务协作）',
  create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  UNIQUE INDEX uniq_project_user (project_id, user_id),
  INDEX idx_user_id (user_id),
  FOREIGN KEY (project_id) REFERENCES project(id) ON DELETE CASCADE,
  FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='项目成员表（P0 · 整表替换模式：DELETE旧+INSERT新在事务内完成）';

-- ============================================================
-- 表 4：task（P0 核心表 · P2 字段 block_reason/version/milestone_id 预建）
-- ============================================================
CREATE TABLE task (
  id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  project_id BIGINT NOT NULL COMMENT '所属项目ID',
  title VARCHAR(200) NOT NULL COMMENT '任务标题（1-200字符）',
  description TEXT NULL COMMENT '任务描述（支持Markdown · NULL时任务详情不展示描述区 · P2 富文本）',
  status VARCHAR(20) NOT NULL DEFAULT 'todo' COMMENT '任务状态 todo=待办 in_progress=进行中 done=已完成 blocked=已阻塞 deleted=已删除 · 并发保护：条件UPDATE WHERE status=expected_status（affectedRows=0→409 Conflict）',
  priority VARCHAR(10) NOT NULL DEFAULT 'medium' COMMENT '优先级 low=低 medium=中 high=高 urgent=紧急',
  assignee_id BIGINT NULL COMMENT '指派人ID（NULL=未分配 · 在看板指派列显示"未分配"· 不参与"我的待办"筛选与待办数统计 · 成员被移除后保持不变成为孤儿指派）',
  creator_id BIGINT NOT NULL COMMENT '创建者ID（不可变）',
  due_date DATE NULL COMMENT '截止日期（NULL=无截止日期 · 不参与"即将逾期"提醒 · P1筛选时跳过NULL）',
  order_no INT NOT NULL DEFAULT 0 COMMENT '同status列内排序序号（拖拽后全量重新编号0,1,2,... · 并发保护：教学简化以最后一次提交为准）',
  block_reason TEXT NULL COMMENT '阻塞原因（status≠blocked时为NULL · status=blocked时必填≥10字符 · P2字段）',
  version INT NOT NULL DEFAULT 0 COMMENT '乐观锁版本号（P2状态机增强用 · P0/P1阶段填0不校验 · P2升级为@Version）',
  milestone_id BIGINT NULL COMMENT '关联Sprint ID（NULL=不属于任何Sprint · 不参与Sprint过滤与燃尽图统计 · P2字段 · 外键见ALTER TABLE）',
  create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  INDEX idx_project_id (project_id),
  INDEX idx_assignee_id (assignee_id),
  INDEX idx_status (status),
  INDEX idx_due_date (due_date),
  INDEX idx_milestone_id (milestone_id),
  FOREIGN KEY (project_id) REFERENCES project(id) ON DELETE CASCADE,
  FOREIGN KEY (assignee_id) REFERENCES user(id) ON DELETE SET NULL,
  INDEX idx_creator_id (creator_id),
  FOREIGN KEY (creator_id) REFERENCES user(id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='任务表（P0核心 · P2扩展字段：block_reason/version/milestone_id）';

-- ============================================================
-- 表 5：task_log（P1 · 任务活动流 + 评论 · 只追加不可编辑/删除）
-- ============================================================
CREATE TABLE task_log (
  id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  task_id BIGINT NOT NULL COMMENT '关联任务ID',
  user_id BIGINT NOT NULL COMMENT '操作人ID',
  type VARCHAR(20) NOT NULL COMMENT '类型 system=系统自动记录 comment=用户评论',
  action VARCHAR(30) NULL COMMENT '系统动作 status_change=状态变更 assignee_change=指派人变更 created=创建任务 blocked=阻塞 unblocked=解阻（type=system时有值 · type=comment时为NULL）',
  content TEXT NULL COMMENT '内容（type=comment时为用户评论文字 · type=system时可为空或存变更详情JSON）',
  create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间（日志只追加 · 无update_time）',
  INDEX idx_task_created (task_id, create_time),
  INDEX idx_user_id (user_id),
  FOREIGN KEY (task_id) REFERENCES task(id) ON DELETE RESTRICT,
  FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='任务活动日志表（P1 · 只追加不可编辑/删除 · 任务物理删前检查日志存在→RESTRICT拒绝）';

-- ============================================================
-- 表 6：label（P1 · 项目级标签）
-- ============================================================
CREATE TABLE label (
  id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  project_id BIGINT NOT NULL COMMENT '所属项目ID（标签作用域为项目级）',
  name VARCHAR(20) NOT NULL COMMENT '标签名（1-20字符 · 项目内唯一）',
  color VARCHAR(7) NOT NULL DEFAULT '#409EFF' COMMENT '标签颜色 HEX格式 #RRGGBB',
  create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  UNIQUE INDEX uniq_project_name (project_id, name),
  FOREIGN KEY (project_id) REFERENCES project(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='标签表（P1 · 项目级 · 创建后不支持重命名与改颜色 · 教学简化：如需修改请删除后重建）';

-- ============================================================
-- 表 7：task_label（P1 · 任务-标签多对多关联）
-- ============================================================
CREATE TABLE task_label (
  id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  task_id BIGINT NOT NULL COMMENT '任务ID',
  label_id BIGINT NOT NULL COMMENT '标签ID',
  create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  UNIQUE INDEX uniq_task_label (task_id, label_id),
  INDEX idx_label_id (label_id),
  FOREIGN KEY (task_id) REFERENCES task(id) ON DELETE CASCADE,
  FOREIGN KEY (label_id) REFERENCES label(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='任务-标签关联表（P1 · 多对多 · 业务软删task(status=deleted)时级联DELETE本表记录避免已删任务污染标签筛选）';

-- ============================================================
-- 表 8：milestone（P2 · Sprint/迭代周期）
-- ============================================================
CREATE TABLE milestone (
  id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  project_id BIGINT NOT NULL COMMENT '所属项目ID',
  name VARCHAR(100) NOT NULL COMMENT 'Sprint名称（1-100字符）',
  start_date DATE NOT NULL COMMENT '开始日期',
  end_date DATE NOT NULL COMMENT '结束日期',
  create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  INDEX idx_project_id (project_id),
  FOREIGN KEY (project_id) REFERENCES project(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Sprint/里程碑表（P2 · 起止日期创建后不可改 · 状态由日期自动推断：未开始/进行中/已结束）';

-- ============================================================
-- 追加 task.milestone_id 外键（milestone 表已创建）
-- ============================================================
ALTER TABLE task
  ADD FOREIGN KEY (milestone_id) REFERENCES milestone(id) ON DELETE SET NULL;

-- ============================================================
-- 表 9：task_dependency（P2 · 甘特图任务依赖边）
-- ============================================================
CREATE TABLE task_dependency (
  id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  project_id BIGINT NOT NULL COMMENT '所属项目ID（冗余 · 便于按项目查询依赖）',
  predecessor_task_id BIGINT NOT NULL COMMENT '前置任务ID',
  successor_task_id BIGINT NOT NULL COMMENT '后置任务ID',
  dependency_type VARCHAR(10) NOT NULL DEFAULT 'FS' COMMENT '依赖类型（教学简化仅支持FS=完成-开始 · predecessor完成后successor才可开始）',
  create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  UNIQUE INDEX uniq_predecessor_successor (predecessor_task_id, successor_task_id),
  INDEX idx_successor_task_id (successor_task_id),
  INDEX idx_project_id (project_id),
  FOREIGN KEY (project_id) REFERENCES project(id) ON DELETE CASCADE,
  FOREIGN KEY (predecessor_task_id) REFERENCES task(id) ON DELETE CASCADE,
  FOREIGN KEY (successor_task_id) REFERENCES task(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='任务依赖表（P2 · 甘特图依赖边 · 仅FS类型 · 应用层校验循环依赖A→B→C→A拒绝）';

-- ============================================================
-- 表 10：task_transition（P2 · 状态转移白名单规则 · 全局种子数据）
-- ============================================================
CREATE TABLE task_transition (
  id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  from_status VARCHAR(20) NOT NULL COMMENT '源状态',
  to_status VARCHAR(20) NOT NULL COMMENT '目标状态',
  require_owner TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否需要owner权限 0=不需要 1=仅owner可执行此转移（如unblock解阻）',
  create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  UNIQUE INDEX uniq_from_to (from_status, to_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='任务状态转移规则表（P2 · 白名单校验 · P0无此表时容错=允许任意转移（done→*除外））';

-- ============================================================
-- 测试数据（按外键依赖顺序）
-- 密码字段为 BCrypt 哈希值（明文均为 123456）
-- 实际使用时请用 new BCryptPasswordEncoder().encode("123456") 重新生成
-- ============================================================

-- 1. user（4 条测试用户）
INSERT INTO user (id, username, password, nickname, email) VALUES
(1, 'admin',   '$2a$10$N.zmdr9k7uOCQb376NoUnuTJ8iAt6Z5EHsM8lE9lBOsl7iKj9Z5Eh', '管理员', 'admin@example.com'),
(2, 'zhangsan', '$2a$10$N.zmdr9k7uOCQb376NoUnuTJ8iAt6Z5EHsM8lE9lBOsl7iKj9Z5Eh', '张三',   NULL),
(3, 'lisi',    '$2a$10$N.zmdr9k7uOCQb376NoUnuTJ8iAt6Z5EHsM8lE9lBOsl7iKj9Z5Eh', NULL,     'lisi@example.com'),
(4, 'wangwu',  '$2a$10$N.zmdr9k7uOCQb376NoUnuTJ8iAt6Z5EHsM8lE9lBOsl7iKj9Z5Eh', '王五',   'wangwu@example.com');

-- 2. project（2 条测试项目）
INSERT INTO project (id, name, owner_id) VALUES
(1, '网站重构', 1),
(2, '移动端App', 2);

-- 3. project_member（项目1: admin(owner)+zhangsan+lisi · 项目2: zhangsan(owner)+admin）
INSERT INTO project_member (id, project_id, user_id, role) VALUES
(1, 1, 1, 'owner'),
(2, 1, 2, 'member'),
(3, 1, 3, 'member'),
(4, 2, 2, 'owner'),
(5, 2, 1, 'member');

-- 4. task（项目1 的 6 条任务 · 覆盖全部 5 种状态 + 未分配场景）
INSERT INTO task (id, project_id, title, description, status, priority, assignee_id, creator_id, due_date, order_no) VALUES
(1, 1, '设计数据库ER图', '使用MySQL Workbench绘制ER图并导出', 'todo', 'high', 1, 1, '2026-05-20', 0),
(2, 1, '编写API接口文档', '基于RESTful规范编写所有P0接口文档', 'in_progress', 'urgent', 2, 1, '2026-05-18', 0),
(3, 1, '前端页面开发', '使用Vue3+ElementPlus开发看板页面', 'todo', 'medium', 3, 1, '2026-05-25', 1),
(4, 1, '需求评审', '已完成的需求文档评审会议', 'done', 'medium', 1, 2, '2026-05-10', 0),
(5, 1, '后端环境搭建', 'Docker部署开发环境受阻', 'blocked', 'high', 2, 2, '2026-05-15', 0),
(6, 1, '编写单元测试', NULL, 'todo', 'low', NULL, 1, NULL, 2);

-- 任务5 补充阻塞原因（P2字段 · 创建后再UPDATE）
UPDATE task SET block_reason = '等待IT部门审批服务器资源，预计下周一完成' WHERE id = 5;

-- 5. task_log（任务1-5 的活动流 + 评论 · 覆盖 system/comment 两种类型）
INSERT INTO task_log (id, task_id, user_id, type, action, content) VALUES
(1, 1, 1, 'system', 'created', NULL),
(2, 2, 1, 'system', 'created', NULL),
(3, 2, 2, 'system', 'status_change', '{"from":"todo","to":"in_progress"}'),
(4, 3, 1, 'system', 'created', NULL),
(5, 4, 2, 'system', 'created', NULL),
(6, 4, 1, 'system', 'status_change', '{"from":"in_progress","to":"done"}'),
(7, 5, 2, 'system', 'created', NULL),
(8, 5, 2, 'system', 'status_change', '{"from":"in_progress","to":"blocked"}'),
(9, 2, 3, 'comment', NULL, '接口文档的响应格式需要统一，建议参考RESTful最佳实践'),
(10, 5, 1, 'comment', NULL, '服务器资源预计下周一到位，届时可继续推进'),
(11, 1, 2, 'comment', NULL, 'ER图建议加上task_log和label的关联关系');

-- 6. label（项目1 的 4 个标签）
INSERT INTO label (id, project_id, name, color) VALUES
(1, 1, 'Bug', '#F56C6C'),
(2, 1, '前端', '#409EFF'),
(3, 1, '后端', '#67C23A'),
(4, 1, '紧急', '#E6A23C');

-- 7. task_label（为任务打标签）
INSERT INTO task_label (id, task_id, label_id) VALUES
(1, 1, 3),   -- 设计数据库ER图 → 后端
(2, 2, 3),   -- 编写API接口文档 → 后端
(3, 2, 4),   -- 编写API接口文档 → 紧急
(4, 3, 2),   -- 前端页面开发 → 前端
(5, 5, 3),   -- 后端环境搭建 → 后端
(6, 5, 4);   -- 后端环境搭建 → 紧急

-- 8. milestone（项目1 的 2 个 Sprint）
INSERT INTO milestone (id, project_id, name, start_date, end_date) VALUES
(1, 1, 'Sprint 1 - 基础架构', '2026-05-12', '2026-05-23'),
(2, 1, 'Sprint 2 - 功能开发', '2026-05-24', '2026-06-05');

-- 关联任务到 Sprint
UPDATE task SET milestone_id = 1 WHERE id IN (1, 2, 4, 5);   -- Sprint 1 的任务
UPDATE task SET milestone_id = 2 WHERE id IN (3, 6);           -- Sprint 2 的任务

-- 9. task_dependency（甘特图依赖边 · 仅 FS 类型）
INSERT INTO task_dependency (id, project_id, predecessor_task_id, successor_task_id, dependency_type) VALUES
(1, 1, 1, 2, 'FS'),   -- 设计数据库ER图 → 编写API接口文档
(2, 1, 2, 3, 'FS');   -- 编写API接口文档 → 前端页面开发

-- 10. task_transition（P2 白名单种子数据 · 覆盖 P0 合法转移 + 解阻审批）
INSERT INTO task_transition (id, from_status, to_status, require_owner) VALUES
-- 基础转移（任意角色）
(1,  'todo',        'in_progress', 0),
(2,  'todo',        'done',        0),
(3,  'todo',        'blocked',     0),
(4,  'in_progress', 'done',        0),
(5,  'in_progress', 'blocked',     0),
(6,  'in_progress', 'todo',        0),
(7,  'blocked',     'todo',        1),
-- 解阻（blocked→todo / blocked→in_progress）需要 owner 审批
(8,  'blocked',     'in_progress', 1),
-- 软删（任意角色）
(9,  'todo',        'deleted',     0),
(10, 'in_progress', 'deleted',     0),
(11, 'done',        'deleted',     0),
(12, 'blocked',     'deleted',     0);
-- 注：done→* 三类回退（done→todo / done→in_progress / done→blocked）不在白名单中 → P2 阶段拒绝
-- 注：P0→P2 收紧项：P0 允许 blocked→done（仅拒绝 done→*），P2 白名单有意排除 blocked→done（阻塞任务应先解阻再完成：blocked→in_progress→done 两段路径）
-- 注：P0 无此表时容错策略：无记录=允许任意转移（done→*除外）