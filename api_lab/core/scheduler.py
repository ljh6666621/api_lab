try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    _APSCHEDULER_AVAILABLE = True
except ImportError:  # 防御性：APScheduler 未安装时，提供 Noop 实现，不阻塞服务启动
    BackgroundScheduler = None  # type: ignore
    CronTrigger = None  # type: ignore
    _APSCHEDULER_AVAILABLE = False


def _job_func(pipeline_id: int):
    """
    调度器内部执行函数：创建数据库会话并调用管道执行器。
    由 APScheduler 在 cron 触发时调用，负责数据采集流水线的定时执行。
    :param pipeline_id: 要执行的管道 ID
    """
    from services.data_pipeline import execute_pipeline
    from core.database import SessionLocal

    db = SessionLocal()
    try:
        execute_pipeline(db, pipeline_id, triggered_by="scheduler")
    finally:
        db.close()


class SchedulerManager:
    """
    APScheduler 后台调度器管理类：封装定时任务的启动、关闭、增删操作。
    采用单例模式，模块级变量 SCHEDULER 供全局使用。
    当环境未安装 APScheduler 时自动降级为 No-op 实现，不阻塞主服务启动。
    """

    def __init__(self):
        """初始化 BackgroundScheduler（不可用时置 None），设置时区为 Asia/Shanghai。"""
        if _APSCHEDULER_AVAILABLE:
            self.scheduler = BackgroundScheduler(timezone="Asia/Shanghai")
        else:
            self.scheduler = None

    def start(self):
        """启动调度器，开始监听并执行已注册的 cron 任务；未安装依赖时静默跳过。"""
        if self.scheduler is not None and not self.scheduler.running:
            self.scheduler.start()

    def shutdown(self):
        """关闭调度器，不等待当前正在运行的任务结束；未安装依赖时静默跳过。"""
        if self.scheduler is not None and self.scheduler.running:
            self.scheduler.shutdown(wait=False)

    def add_pipeline_job(self, pipeline_id: int, cron_expr: str):
        """
        为指定管道添加或替换 cron 定时任务。
        任务 ID 格式为 pipeline_{pipeline_id}，若已存在则覆盖；
        错过的执行在 300 秒内会补发（misfire_grace_time）。
        未安装 APScheduler 依赖时抛出 RuntimeError 告知用户。
        :param pipeline_id: 管道 ID
        :param cron_expr: 标准 crontab 表达式（如 "*/5 * * * *"）
        """
        if self.scheduler is None:
            raise RuntimeError("APScheduler 未安装，请 pip install APScheduler>=3.10.4 后再使用定时任务")
        self.scheduler.add_job(
            id=f"pipeline_{pipeline_id}",
            func=_job_func,
            trigger=CronTrigger.from_crontab(cron_expr),
            args=[pipeline_id],
            replace_existing=True,
            misfire_grace_time=300,
        )

    def remove_pipeline_job(self, pipeline_id: int):
        """
        移除指定管道的定时任务。
        :param pipeline_id: 管道 ID
        """
        if self.scheduler is None:
            return
        job_id = f"pipeline_{pipeline_id}"
        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)


SCHEDULER = SchedulerManager()
