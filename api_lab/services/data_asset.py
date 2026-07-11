import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, desc, func
from sqlalchemy.orm import Session
from sqlalchemy.sql import text

from schemas.data_asset import OverviewResponse

try:
    import pandas as pd
except ImportError:
    pd = None


def _python_type_to_sql_type(value: Any) -> str:
    """将 Python 值的类型映射为 SQL 类型字符串。

    :param value: 任意 Python 值
    :return: "INTEGER" / "REAL" / "TEXT"
    """
    if isinstance(value, bool):
        return "INTEGER"
    if isinstance(value, int):
        return "INTEGER"
    if isinstance(value, float):
        return "REAL"
    return "TEXT"


class DataAssetRepository:
    """数据资产仓储：封装 DataAsset 模型的 CRUD 与概览统计静态方法。"""

    @staticmethod
    def create(db: Session, data: Dict[str, Any]):
        """创建新的数据资产。

        :param db: 数据库会话
        :param data: 资产字段字典
        :return: 新建的 DataAsset 实体
        """
        from models.data_asset import DataAsset

        asset = DataAsset(**data)
        db.add(asset)
        db.commit()
        db.refresh(asset)
        return asset

    @staticmethod
    def get(db: Session, asset_id: int):
        """按 ID 获取单个数据资产。

        :param db: 数据库会话
        :param asset_id: 资产 ID
        :return: 匹配的 DataAsset 或 None
        """
        from models.data_asset import DataAsset

        return db.query(DataAsset).filter(DataAsset.id == asset_id).first()

    @staticmethod
    def list(db: Session, skip: int = 0, limit: int = 100):
        """分页列出数据资产（按创建时间倒序）。

        :param db: 数据库会话
        :param skip: 跳过条数，默认 0
        :param limit: 最大返回条数，默认 100
        :return: DataAsset 列表
        """
        from models.data_asset import DataAsset

        return (
            db.query(DataAsset)
            .order_by(desc(DataAsset.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )

    @staticmethod
    def update(db: Session, asset_id: int, data: Dict[str, Any]):
        """按 ID 局部更新数据资产字段。

        :param db: 数据库会话
        :param asset_id: 资产 ID
        :param data: 待更新字段字典
        :return: 更新后的 DataAsset，不存在则返回 None
        """
        asset = DataAssetRepository.get(db, asset_id)
        if asset is None:
            return None
        for key, value in data.items():
            if hasattr(asset, key):
                setattr(asset, key, value)
        db.commit()
        db.refresh(asset)
        return asset

    @staticmethod
    def delete(db: Session, asset_id: int) -> bool:
        """按 ID 删除数据资产。

        :param db: 数据库会话
        :param asset_id: 资产 ID
        :return: 成功 True，不存在 False
        """
        asset = DataAssetRepository.get(db, asset_id)
        if asset is None:
            return False
        db.delete(asset)
        db.commit()
        return True

    @staticmethod
    def overview(db: Session) -> OverviewResponse:
        """获取数据资产概览统计信息。

        :param db: 数据库会话
        :return: OverviewResponse 实体（总数、总行数、按来源分组、今日画像数）
        """
        from models.data_asset import AssetProfile, DataAsset

        total_assets = db.query(func.count(DataAsset.id)).scalar() or 0
        total_rows = db.query(func.coalesce(func.sum(DataAsset.row_count), 0)).scalar() or 0

        by_source_type_rows = (
            db.query(DataAsset.source_type, func.count(DataAsset.id))
            .group_by(DataAsset.source_type)
            .all()
        )
        by_source_type = {row[0] or "unknown": int(row[1]) for row in by_source_type_rows}

        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_profiles = (
            db.query(func.count(AssetProfile.id))
            .filter(AssetProfile.generated_at >= today_start)
            .scalar()
            or 0
        )

        return OverviewResponse(
            total_assets=int(total_assets),
            total_rows=int(total_rows),
            by_source_type=by_source_type,
            today_profiles=int(today_profiles),
        )

    @staticmethod
    def create_from_pipeline_run(
        db: Session,
        asset_name: str,
        pipeline_run: Optional[Any] = None,
        data: Optional[List[Dict[str, Any]]] = None,
        pipeline_id: Optional[int] = None,
        owner_id: Optional[int] = None,
    ):
        """根据流水线运行记录或给定 data 创建/同步数据资产。

        - columns_info：从所有记录 key 的并集推断，类型由首条非空值 Python type→SQL type
        - row_count = len(data)
        - last_sync_at = utcnow()
        - source_type 默认 "pipeline"

        :param db: 数据库会话
        :param asset_name: 资产名称
        :param pipeline_run: 可选 PipelineRun 实体（若存在且 data 为空则从其 .data 取数据）
        :param data: 可选样例数据列表，优先级高于 pipeline_run.data
        :param pipeline_id: 可选关联流水线 ID
        :param owner_id: 可选负责人用户 ID
        :return: 新建/更新后的 DataAsset
        """
        from models.data_asset import DataAsset

        records = data
        if records is None and pipeline_run is not None:
            records = getattr(pipeline_run, "data", None)
        if records is None:
            records = []

        columns_set: Dict[str, str] = {}
        for record in records:
            if isinstance(record, dict):
                for key, value in record.items():
                    if key not in columns_set and value is not None:
                        columns_set[key] = _python_type_to_sql_type(value)

        columns_info = [
            {"name": col_name, "type": col_type, "comment": ""}
            for col_name, col_type in columns_set.items()
        ]

        existing = (
            db.query(DataAsset)
            .filter(DataAsset.name == asset_name)
            .first()
        )

        payload: Dict[str, Any] = {
            "name": asset_name,
            "source_type": "pipeline" if (pipeline_id or pipeline_run is not None) else "manual",
            "pipeline_id": pipeline_id,
            "columns_info": columns_info,
            "row_count": len(records),
            "last_sync_at": datetime.utcnow(),
            "owner_id": owner_id,
        }

        if existing is None:
            return DataAssetRepository.create(db, payload)
        return DataAssetRepository.update(db, existing.id, payload)


class AssetProfileRepository:
    """资产画像仓储：封装 AssetProfile 模型的 CRUD 静态方法。"""

    @staticmethod
    def create(
        db: Session,
        asset_id: int,
        summary: Dict[str, Any],
        report_text: str,
        generated_by: Optional[int] = None,
    ):
        """创建新的资产画像记录。

        :param db: 数据库会话
        :param asset_id: 关联资产 ID
        :param summary: 画像统计摘要 dict
        :param report_text: LLM 生成的自然语言报告
        :param generated_by: 可选触发用户 ID
        :return: 新建的 AssetProfile 实体
        """
        from models.data_asset import AssetProfile

        profile = AssetProfile(
            asset_id=asset_id,
            summary=summary,
            report_text=report_text,
            generated_by=generated_by,
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)
        return profile

    @staticmethod
    def get(db: Session, profile_id: int):
        """按 ID 获取单个画像。

        :param db: 数据库会话
        :param profile_id: 画像 ID
        :return: AssetProfile 或 None
        """
        from models.data_asset import AssetProfile

        return db.query(AssetProfile).filter(AssetProfile.id == profile_id).first()

    @staticmethod
    def list_by_asset(db: Session, asset_id: int):
        """按资产 ID 列出历史画像（按生成时间倒序）。

        :param db: 数据库会话
        :param asset_id: 资产 ID
        :return: AssetProfile 列表
        """
        from models.data_asset import AssetProfile

        return (
            db.query(AssetProfile)
            .filter(AssetProfile.asset_id == asset_id)
            .order_by(desc(AssetProfile.generated_at))
            .all()
        )

    @staticmethod
    def get_recent_within(db: Session, asset_id: int, minutes: int = 60):
        """获取某资产最近 N 分钟内生成的画像（用于缓存判断）。

        :param db: 数据库会话
        :param asset_id: 资产 ID
        :param minutes: 回溯时间窗口（分钟）
        :return: 最近画像或 None
        """
        from models.data_asset import AssetProfile

        cutoff = datetime.utcnow() - timedelta(minutes=minutes)
        return (
            db.query(AssetProfile)
            .filter(
                and_(
                    AssetProfile.asset_id == asset_id,
                    AssetProfile.generated_at >= cutoff,
                )
            )
            .order_by(desc(AssetProfile.generated_at))
            .first()
        )


def _load_dataframe_from_asset(db: Session, asset) -> Any:
    """根据资产配置加载数据来源并返回 pandas DataFrame。

    优先级：source_table → pipeline_id → columns_info 空样本

    :param db: 数据库会话
    :param asset: DataAsset 实体
    :return: pandas DataFrame（若 pandas 未安装则抛 ValueError）
    """
    if pd is None:
        raise ValueError("未安装 pandas，请 pip install pandas")

    records: List[Dict[str, Any]] = []

    if asset.source_table:
        try:
            safe_table = asset.source_table
            cursor = db.execute(text(f"SELECT * FROM {safe_table} LIMIT 10000"))
            columns = list(cursor.keys())
            rows = cursor.fetchall()
            for row in rows:
                records.append(dict(zip(columns, row)))
        except Exception as e:
            raise ValueError(f"读取 source_table 失败: {e}")

    if not records and asset.pipeline_id is not None:
        try:
            from models.data_pipeline import PipelineRun

            latest_run = (
                db.query(PipelineRun)
                .filter(
                    and_(
                        PipelineRun.pipeline_id == asset.pipeline_id,
                        getattr(PipelineRun, "status", None) == "success",
                    )
                )
                .order_by(desc(getattr(PipelineRun, "created_at", PipelineRun.id)))
                .first()
            )
            if latest_run is not None:
                run_data = getattr(latest_run, "data", None)
                if isinstance(run_data, list):
                    records = run_data[:10000]
        except ImportError:
            pass
        except Exception:
            pass

    if not records and isinstance(asset.columns_info, list):
        columns = []
        for col in asset.columns_info:
            if isinstance(col, dict):
                cname = col.get("name") or col.get("column_name")
                if cname:
                    columns.append(cname)
        records = []

    df = pd.DataFrame(records)
    return df


def _compute_summary(df: Any) -> Dict[str, Any]:
    """对 DataFrame 计算画像统计摘要。

    - total_rows, cols
    - 每列：missing_count, missing_rate, dtype
    - 数值列：min/max/mean/std
    - 离散列（唯一值 <=20 或 object/str）：value_counts top 10

    :param df: pandas DataFrame
    :return: summary 字典
    """
    if pd is None:
        raise ValueError("未安装 pandas，请 pip install pandas")

    summary: Dict[str, Any] = {
        "total_rows": int(len(df)),
        "cols": list(df.columns.astype(str)) if len(df.columns) else [],
        "columns": {},
    }

    total = len(df)

    for col in df.columns:
        col_name = str(col)
        series = df[col]
        missing_count = int(series.isna().sum())
        missing_rate = float(missing_count / total) if total > 0 else 0.0
        col_info: Dict[str, Any] = {
            "missing_count": missing_count,
            "missing_rate": missing_rate,
            "dtype": str(series.dtype),
        }

        is_numeric = pd.api.types.is_numeric_dtype(series) and not pd.api.types.is_bool_dtype(series)
        if is_numeric:
            col_info["min"] = float(series.min()) if total > 0 and missing_count < total else None
            col_info["max"] = float(series.max()) if total > 0 and missing_count < total else None
            col_info["mean"] = float(series.mean()) if total > 0 and missing_count < total else None
            col_info["std"] = float(series.std()) if total > 1 and missing_count < total else None

        unique_values = series.dropna().unique()
        is_categorical = (
            (len(unique_values) <= 20)
            or pd.api.types.is_object_dtype(series)
            or pd.api.types.is_string_dtype(series)
        )
        if is_categorical and total > 0:
            try:
                vc = series.dropna().value_counts().head(10)
                col_info["value_counts"] = {str(k): int(v) for k, v in vc.items()}
            except Exception:
                pass

        summary["columns"][col_name] = col_info

    return summary


def _generate_report_with_llm(asset_name: str, summary: Dict[str, Any]) -> str:
    """调用 LLM 生成 150 字中文资产分析报告。

    :param asset_name: 资产名称
    :param summary: 画像统计摘要
    :return: 报告文本，失败时返回占位字符串
    """
    try:
        from services.llm_service import build_messages, chat_completion

        system_prompt = (
            "你是数据分析师，请根据画像 summary 生成 150 字中文的资产分析报告，"
            "指出主要特征、数据质量问题与关注点。"
        )
        user_prompt = (
            f"资产名称：{asset_name}\n"
            f"画像：{json.dumps(summary, ensure_ascii=False, indent=2, default=str)}"
        )

        messages = build_messages(system_prompt, [{"role": "user", "content": user_prompt}])
        response = chat_completion(messages)
        report_text = getattr(response.choices[0].message, "content", "") or ""
        return report_text.strip() or "[LLM返回内容为空，仅存储统计结果]"
    except Exception:
        return "[LLM不可用，仅存储统计结果]"


def generate_profile(
    db: Session,
    asset_id: int,
    generated_by: Optional[int] = None,
) -> Any:
    """为指定数据资产生成完整画像：加载数据 → 统计 summary → LLM 生成报告 → 持久化。

    :param db: 数据库会话
    :param asset_id: 目标资产 ID
    :param generated_by: 可选触发用户 ID
    :return: 新生成的 AssetProfile
    :raises ValueError: 任一步骤失败时抛出
    """
    try:
        asset = DataAssetRepository.get(db, asset_id)
        if asset is None:
            raise ValueError("数据资产不存在")

        try:
            df = _load_dataframe_from_asset(db, asset)
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"加载数据失败: {e}")

        try:
            summary = _compute_summary(df)
        except Exception as e:
            raise ValueError(f"统计画像失败: {e}")

        report_text = _generate_report_with_llm(asset.name, summary)

        try:
            profile = AssetProfileRepository.create(
                db,
                asset_id=asset.id,
                summary=summary,
                report_text=report_text,
                generated_by=generated_by,
            )

            asset.last_sync_at = datetime.utcnow()
            if summary.get("total_rows") is not None:
                asset.row_count = int(summary["total_rows"])
            db.commit()
            db.refresh(profile)
            return profile
        except Exception as e:
            db.rollback()
            raise ValueError(f"保存画像失败: {e}")
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"生成画像失败: {e}")
