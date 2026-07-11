from typing import Optional

from sqlalchemy.orm import Session

from models.user import User
from core.security import hash_password, verify_password


class UserRepository:
    """用户仓储服务：封装所有与 User 模型相关的数据库操作与业务逻辑。"""

    def list_all(
        self,
        db: Session,
        status: Optional[int] = None,
        keyword: Optional[str] = None,
    ) -> list[User]:
        """
        查询用户列表，可选按账号状态过滤、按用户名模糊搜索。
        :param db: 数据库会话
        :param status: 可选，1=正常 2=禁用
        :param keyword: 可选，用户名关键字
        :return: 符合条件的用户实体列表
        """
        query = db.query(User)
        if status is not None:
            query = query.filter(User.status == status)
        if keyword:
            query = query.filter(User.username.contains(keyword.lower()))
        return query.all()

    def get(self, db: Session, user_id: int) -> Optional[User]:
        """
        按用户主键 ID 查询单个用户。
        :param db: 数据库会话
        :param user_id: 用户 ID
        :return: 找到返回 User，否则 None
        """
        return db.query(User).filter(User.id == user_id).first()

    def get_by_username_or_email(self, db: Session, identifier: str) -> Optional[User]:
        """
        按用户名 或 邮箱查找用户（登录时使用，支持两种登录名）。
        :param db: 数据库会话
        :param identifier: 用户名或邮箱
        :return: 匹配到的用户或 None
        """
        return db.query(User).filter(
            (User.username == identifier) | (User.email == identifier)
        ).first()

    def exists(self, db: Session, username: Optional[str] = None, email: Optional[str] = None) -> bool:
        """
        判断指定用户名/邮箱是否已存在，用于注册前的唯一性校验。
        :param db: 数据库会话
        :param username: 用户名
        :param email: 邮箱
        :return: 任意一项存在即返回 True
        """
        query = db.query(User)
        conditions = []
        if username:
            conditions.append(User.username == username)
        if email:
            conditions.append(User.email == email)
        if not conditions:
            return False
        return query.filter(*conditions).first() is not None

    def register(
        self,
        db: Session,
        *,
        username: str,
        email: str,
        password: str,
        mobile: str = "",
        dept_id: int = 0,
    ) -> Optional[User]:
        """
        注册新用户：先做唯一性校验，通过后哈希密码并写入数据库。
        :param db: 数据库会话
        :param username: 用户名（唯一）
        :param email: 邮箱（唯一）
        :param password: 明文密码，会被 bcrypt 哈希
        :param mobile: 手机号
        :param dept_id: 所属部门 ID
        :return: 创建成功返回新用户，用户名/邮箱冲突返回 None
        """
        if self.exists(db, username=username, email=email):
            return None
        user = User(
            username=username,
            email=email,
            mobile=mobile or "",
            dept_id=dept_id or 0,
            status=1,
            password_hash=hash_password(password),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    def authenticate(self, db: Session, identifier: str, password: str) -> Optional[User]:
        """
        用户认证：按用户名/邮箱找到用户后校验密码。
        :param db: 数据库会话
        :param identifier: 用户名或邮箱
        :param password: 明文密码
        :return: 验证通过返回 User 对象，否则 None
        """
        user = self.get_by_username_or_email(db, identifier)
        if not user:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user

    def count(self, db: Session) -> int:
        """统计 users 表总记录数，用于种子数据插入前判断是否为空库。"""
        return db.query(User).count()

    def bulk_create(self, db: Session, users: list[dict], default_password: str) -> int:
        """
        批量创建用户（用于种子数据初始化），跳过已存在用户名/邮箱。
        所有新用户使用同一个默认密码哈希，减少重复计算。
        :param db: 数据库会话
        :param users: 用户字典列表，可包含 id/username/email/mobile/dept_id/status
        :param default_password: 默认明文密码
        :return: 实际创建成功的用户数量
        """
        created = 0
        pwd_hash = hash_password(default_password)
        for u in users:
            if self.exists(db, username=u.get("username"), email=u.get("email")):
                continue
            db.add(User(
                id=u.get("id"),
                username=u.get("username"),
                email=u.get("email") or f"{u.get('username')}@example.com",
                mobile=u.get("mobile") or "",
                dept_id=u.get("dept_id") or 0,
                status=u.get("status") or 1,
                password_hash=pwd_hash,
            ))
            created += 1
        db.commit()
        return created


user_service = UserRepository()
