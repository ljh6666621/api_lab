from __future__ import annotations

from datetime import datetime
from typing import List, Optional

try:
    import httpx
    _HTTPX_AVAILABLE = True
except ImportError:  # 防御性：httpx 未安装时不阻塞模块导入，实际使用时报错
    httpx = None  # type: ignore
    _HTTPX_AVAILABLE = False

from sqlalchemy.orm import Session

from models.data_pipeline import DataSource, DataPipeline, PipelineRun


class DataSourceRepository:
    """数据源仓储服务：封装数据源 CRUD 及分页查询的数据库操作。"""

    def list(self, db: Session, skip: int = 0, limit: int = 100) -> List[DataSource]:
        """
        分页查询数据源列表。
        :param db: 数据库会话
        :param skip: 偏移量
        :param limit: 每页条数
        :return: 数据源列表
        """
        return db.query(DataSource).offset(skip).limit(limit).all()

    def get(self, db: Session, source_id: int) -> Optional[DataSource]:
        """
        按 ID 查找单个数据源。
        :param db: 数据库会话
        :param source_id: 数据源主键
        :return: 找到返回 DataSource，否则 None
        """
        return db.query(DataSource).filter(DataSource.id == source_id).first()

    def create(self, db: Session, data: dict) -> DataSource:
        """
        创建新数据源，写入数据库并刷新。
        :param db: 数据库会话
        :param data: 数据源字段字典
        :return: 新建后的数据源实体
        """
        item = DataSource(**data)
        db.add(item)
        db.commit()
        db.refresh(item)
        return item

    def update(self, db: Session, source_id: int, data: dict) -> Optional[DataSource]:
        """
        按 ID 局部更新数据源字段。
        :param db: 数据库会话
        :param source_id: 目标数据源 ID
        :param data: 待更新字段字典
        :return: 更新后的数据源实体，或 None
        """
        item = self.get(db, source_id)
        if not item:
            return None
        for key, value in data.items():
            setattr(item, key, value)
        db.commit()
        db.refresh(item)
        return item

    def delete(self, db: Session, source_id: int) -> bool:
        """
        按 ID 删除数据源。
        :param db: 数据库会话
        :param source_id: 目标数据源 ID
        :return: 删除成功 True，不存在 False
        """
        item = self.get(db, source_id)
        if not item:
            return False
        db.delete(item)
        db.commit()
        return True


def _extract_by_path(raw: dict, path: str):
    """
    按点路径（如 data.items）从 JSON 中递归提取值。
    :param raw: 原始字典
    :param path: 点分隔路径字符串
    :return: 提取到的值
    """
    current = raw
    for key in path.split("."):
        if isinstance(current, dict):
            current = current.get(key)
        else:
            return None
        if current is None:
            return None
    return current


def _apply_field_map(data_list: List[dict], field_map: dict) -> tuple[List[dict], List[str]]:
    """
    对数据列表应用字段重命名映射。
    :param data_list: 原始数据字典列表
    :param field_map: {旧字段名: 新字段名}
    :return: (重命名后的列表, 错误信息列表)
    """
    errors = []
    result = []
    for idx, row in enumerate(data_list):
        try:
            new_row = {}
            for old_key, new_key in field_map.items():
                if old_key in row:
                    new_row[new_key] = row[old_key]
            if not new_row:
                new_row = row.copy()
            result.append(new_row)
        except Exception as e:
            errors.append(f"第{idx}行字段映射失败: {str(e)}")
    return result, errors


def _apply_filter(data_list: List[dict], filter_rule: dict) -> List[dict]:
    """
    按等值过滤规则筛选数据。
    :param data_list: 数据字典列表
    :param filter_rule: {字段名: 目标值} 的等值过滤
    :return: 过滤后的列表
    """
    if not filter_rule:
        return data_list
    result = []
    for row in data_list:
        match = True
        for field, value in filter_rule.items():
            if row.get(field) != value:
                match = False
                break
        if match:
            result.append(row)
    return result


class PipelineRepository:
    """
    流水线仓储服务：封装流水线 CRUD、分页查询，以及定时任务的启停管理。
    create/update 时会根据 schedule 字段自动注册或移除 APScheduler 任务。
    """

    def list(self, db: Session, skip: int = 0, limit: int = 100) -> List[DataPipeline]:
        """
        分页查询流水线列表。
        :param db: 数据库会话
        :param skip: 偏移量
        :param limit: 每页条数
        :return: 流水线列表
        """
        return db.query(DataPipeline).offset(skip).limit(limit).all()

    def get(self, db: Session, pipeline_id: int) -> Optional[DataPipeline]:
        """
        按 ID 查找单个流水线。
        :param db: 数据库会话
        :param pipeline_id: 流水线主键
        :return: 找到返回 DataPipeline，否则 None
        """
        return db.query(DataPipeline).filter(DataPipeline.id == pipeline_id).first()

    def enable_schedule(self, db: Session, pipeline_id: int):
        """
        为流水线启用定时调度：根据 pipeline.schedule 注册 cron 任务。
        :param db: 数据库会话
        :param pipeline_id: 流水线 ID
        """
        pipeline = self.get(db, pipeline_id)
        if not pipeline:
            return
        if pipeline.schedule:
            from core.scheduler import SCHEDULER
            SCHEDULER.add_pipeline_job(pipeline_id, pipeline.schedule)

    def disable_schedule(self, db: Session, pipeline_id: int):
        """
        为流水线禁用定时调度：从 APScheduler 中移除对应任务。
        :param db: 数据库会话
        :param pipeline_id: 流水线 ID
        """
        from core.scheduler import SCHEDULER
        SCHEDULER.remove_pipeline_job(pipeline_id)

    def create(self, db: Session, data: dict) -> DataPipeline:
        """
        创建新流水线，自动根据 schedule 决定是否注册定时任务。
        :param db: 数据库会话
        :param data: 流水线字段字典
        :return: 新建后的流水线实体
        """
        item = DataPipeline(**data)
        db.add(item)
        db.commit()
        db.refresh(item)
        if item.schedule and item.status == 1:
            self.enable_schedule(db, item.id)
        return item

    def update(self, db: Session, pipeline_id: int, data: dict) -> Optional[DataPipeline]:
        """
        按 ID 局部更新流水线字段；schedule 变化时自动重新注册/移除 cron 任务。
        :param db: 数据库会话
        :param pipeline_id: 目标流水线 ID
        :param data: 待更新字段字典
        :return: 更新后的流水线实体，或 None
        """
        item = self.get(db, pipeline_id)
        if not item:
            return None
        for key, value in data.items():
            setattr(item, key, value)
        db.commit()
        db.refresh(item)
        self.disable_schedule(db, pipeline_id)
        if item.schedule and item.status == 1:
            self.enable_schedule(db, pipeline_id)
        return item

    def delete(self, db: Session, pipeline_id: int) -> bool:
        """
        按 ID 删除流水线，同步移除已注册的定时任务。
        :param db: 数据库会话
        :param pipeline_id: 目标流水线 ID
        :return: 删除成功 True，不存在 False
        """
        item = self.get(db, pipeline_id)
        if not item:
            return False
        self.disable_schedule(db, pipeline_id)
        db.delete(item)
        db.commit()
        return True

    def list_runs(self, db: Session, pipeline_id: int, skip: int = 0, limit: int = 100) -> List[PipelineRun]:
        """
        查询指定流水线的历史运行记录，按 start_at 倒序排列。
        :param db: 数据库会话
        :param pipeline_id: 流水线 ID
        :param skip: 偏移量
        :param limit: 每页条数
        :return: PipelineRun 列表
        """
        return (
            db.query(PipelineRun)
            .filter(PipelineRun.pipeline_id == pipeline_id)
            .order_by(PipelineRun.start_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def has_running(self, db: Session, pipeline_id: int) -> bool:
        """
        判断流水线当前是否存在状态为 running 的执行记录。
        :param db: 数据库会话
        :param pipeline_id: 流水线 ID
        :return: 存在 True / 不存在 False
        """
        return (
            db.query(PipelineRun)
            .filter(PipelineRun.pipeline_id == pipeline_id, PipelineRun.status == "running")
            .first()
            is not None
        )


def execute_pipeline(
    db: Session,
    pipeline_id: int,
    triggered_by: str = "manual",
    uploaded_rows: Optional[List] = None,
) -> PipelineRun:
    """
    核心流水线执行器：按策略采集数据 → 字段映射 → 过滤 → 持久化运行记录。
    无论成功或失败，都会将最终状态写入 PipelineRun 并提交到数据库。
    :param db: 数据库会话
    :param pipeline_id: 流水线 ID
    :param triggered_by: 触发来源（manual/scheduler/user_<id>/upload）
    :param uploaded_rows: CSV 上传时传入的行列表，非上传模式为 None
    :return: 已持久化的 PipelineRun 记录
    """
    run = PipelineRun(
        pipeline_id=pipeline_id,
        triggered_by=triggered_by,
        status="running",
        start_at=datetime.utcnow(),
    )
    db.add(run)
    db.flush()

    data = []
    error_messages = []

    try:
        pipeline = db.query(DataPipeline).filter(DataPipeline.id == pipeline_id).first()
        if not pipeline:
            raise Exception(f"流水线 {pipeline_id} 不存在")

        source = db.query(DataSource).filter(DataSource.id == pipeline.source_id).first()
        if not source:
            raise Exception(f"数据源 {pipeline.source_id} 不存在")

        if uploaded_rows is not None:
            data = uploaded_rows
        elif source.type == "http_api":
            if not _HTTPX_AVAILABLE:
                raise RuntimeError("httpx 未安装，请 pip install httpx>=0.27 后再使用 http_api 类型数据源")
            config = source.config or {}
            url = config.get("url")
            if not url:
                raise Exception("HTTP API 数据源缺少 url 配置")
            method = (config.get("method") or "GET").upper()
            headers = config.get("headers", {}) or {}
            params = config.get("params", {}) or {}

            with httpx.Client(timeout=30) as client:
                if method == "GET":
                    resp = client.get(url, headers=headers, params=params)
                elif method == "POST":
                    resp = client.post(url, headers=headers, params=params, json=params)
                else:
                    resp = client.request(method, url, headers=headers, params=params)
                resp.raise_for_status()
                raw = resp.json()

            jq_path = config.get("jq_path") or config.get("extract_path")
            if jq_path:
                extracted = _extract_by_path(raw, jq_path)
                if isinstance(extracted, list):
                    data = extracted
                elif extracted is None:
                    raise Exception(f"提取路径 {jq_path} 未找到数据")
                else:
                    data = [extracted]
            elif isinstance(raw, list):
                data = raw
            else:
                data = [raw]

        elif source.type == "crawler":
            if not _HTTPX_AVAILABLE:
                raise RuntimeError("httpx 未安装，请 pip install httpx>=0.27 后再使用 crawler 类型数据源")
            config = source.config or {}
            url = config.get("url")
            if not url:
                raise Exception("Crawler 数据源缺少 url 配置")
            with httpx.Client(timeout=30) as client:
                resp = client.get(url)
                resp.raise_for_status()
            data = [{"raw_text": resp.text}]

        elif source.type == "upload":
            raise Exception("upload 类型数据源需要通过 /upload 接口传入文件")
        else:
            raise Exception(f"未知的数据源类型: {source.type}")

        extract_rules = pipeline.extract_rules or {}
        field_map = extract_rules.get("field_map", {}) if isinstance(extract_rules, dict) else {}
        if field_map:
            data, map_errors = _apply_field_map(data, field_map)
            error_messages.extend(map_errors)

        filter_rule = extract_rules.get("filter", {}) if isinstance(extract_rules, dict) else {}
        if filter_rule:
            data = _apply_filter(data, filter_rule)

        run.status = "success"
        run.rows_count = len(data)
        run.data = data
        if error_messages:
            run.error_msg = "; ".join(error_messages)

    except Exception as e:
        run.status = "failed"
        run.rows_count = 0
        run.error_msg = str(e)
        run.data = None
    finally:
        run.end_at = datetime.utcnow()
        db.commit()
        db.refresh(run)

    return run


def run_pipeline(pipeline_id: int) -> PipelineRun:
    """
    内置技能风格的 callable 入口：自行创建数据库会话并执行流水线。
    供 model_skill 等模块以函数引用方式注册为技能。
    :param pipeline_id: 流水线 ID
    :return: PipelineRun 执行记录
    """
    from core.database import SessionLocal

    db = SessionLocal()
    try:
        return execute_pipeline(db, pipeline_id, triggered_by="manual")
    finally:
        db.close()


data_source_service = DataSourceRepository()
pipeline_service = PipelineRepository()
