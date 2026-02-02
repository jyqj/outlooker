#!/usr/bin/env python3
"""
Automatic database backup script.

Usage:
    python auto_backup.py [--backup-dir /path/to/backups] [--keep-days 7]
    python auto_backup.py --encrypt --encryption-key "your-secret-key"
    
    或使用环境变量设置加密密钥:
    BACKUP_ENCRYPTION_KEY="your-secret-key" python auto_backup.py --encrypt
"""

import argparse
import gzip
import logging
import os
import shutil
import sqlite3
import stat
import sys
from datetime import datetime, timedelta
from pathlib import Path

# 添加项目路径
PROJECT_ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_database_path() -> Path:
    """获取数据库路径"""
    from app.settings import get_settings
    settings = get_settings()
    return PROJECT_ROOT / settings.database_path


def encrypt_file(file_path: Path, key: str) -> Path | None:
    """
    使用 AES 加密文件。
    
    Args:
        file_path: 要加密的文件路径
        key: 加密密钥
        
    Returns:
        加密后的文件路径，失败返回 None
    """
    try:
        from cryptography.fernet import Fernet
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
        import base64
        
        # 从密码派生密钥
        salt = b'outlooker_backup_salt'  # 固定盐值（或可配置）
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        derived_key = base64.urlsafe_b64encode(kdf.derive(key.encode()))
        f = Fernet(derived_key)
        
        # 加密文件
        encrypted_path = file_path.with_suffix(file_path.suffix + ".enc")
        with open(file_path, 'rb') as src:
            encrypted_data = f.encrypt(src.read())
        with open(encrypted_path, 'wb') as dst:
            dst.write(encrypted_data)
        
        # 设置安全权限
        os.chmod(encrypted_path, stat.S_IRUSR | stat.S_IWUSR)  # 600 - 仅所有者可读写
        
        logger.info(f"备份已加密: {encrypted_path}")
        return encrypted_path
        
    except ImportError:
        logger.error("加密需要安装 cryptography 库: pip install cryptography")
        return None
    except Exception as e:
        logger.error(f"加密失败: {e}")
        return None


def create_backup(
    db_path: Path,
    backup_dir: Path,
    compress: bool = True,
    encrypt: bool = False,
    encryption_key: str | None = None,
) -> Path | None:
    """
    创建数据库备份。
    
    Args:
        db_path: 数据库文件路径
        backup_dir: 备份目录
        compress: 是否压缩
        encrypt: 是否加密
        encryption_key: 加密密钥（如果启用加密）
        
    Returns:
        备份文件路径，失败返回 None
    """
    if not db_path.exists():
        logger.error(f"数据库文件不存在: {db_path}")
        return None
    
    # 创建备份目录时设置安全权限
    backup_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(backup_dir, stat.S_IRWXU)  # 700 - 仅所有者可访问
    
    # 生成备份文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"backup_{timestamp}.db"
    backup_path = backup_dir / backup_name
    
    try:
        # 使用 SQLite 的 backup API（确保一致性）
        logger.info(f"开始备份: {db_path} -> {backup_path}")
        
        source_conn = sqlite3.connect(str(db_path))
        backup_conn = sqlite3.connect(str(backup_path))
        
        source_conn.backup(backup_conn)
        
        source_conn.close()
        backup_conn.close()
        
        # 设置备份文件权限
        os.chmod(backup_path, stat.S_IRUSR | stat.S_IWUSR)  # 600 - 仅所有者可读写
        
        # 压缩备份
        if compress:
            compressed_path = backup_path.with_suffix(".db.gz")
            logger.info(f"压缩备份: {compressed_path}")
            
            with open(backup_path, 'rb') as f_in:
                with gzip.open(compressed_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            # 删除未压缩的备份
            backup_path.unlink()
            backup_path = compressed_path
            
            # 设置压缩文件权限
            os.chmod(backup_path, stat.S_IRUSR | stat.S_IWUSR)  # 600 - 仅所有者可读写
        
        # 加密备份
        if encrypt:
            if not encryption_key:
                logger.error("启用加密但未提供密钥")
                return None
            
            encrypted_path = encrypt_file(backup_path, encryption_key)
            if encrypted_path:
                backup_path.unlink()  # 删除未加密版本
                backup_path = encrypted_path
            else:
                logger.error("加密失败，保留未加密备份")
        
        # 获取备份大小
        size_mb = backup_path.stat().st_size / (1024 * 1024)
        logger.info(f"备份完成: {backup_path} ({size_mb:.2f} MB)")
        
        return backup_path
        
    except Exception as e:
        logger.error(f"备份失败: {e}")
        # 清理失败的备份
        if backup_path.exists():
            backup_path.unlink()
        return None


def cleanup_old_backups(backup_dir: Path, keep_days: int) -> int:
    """
    清理过期备份。
    
    Args:
        backup_dir: 备份目录
        keep_days: 保留天数
        
    Returns:
        删除的文件数
    """
    if not backup_dir.exists():
        return 0
    
    cutoff_time = datetime.now() - timedelta(days=keep_days)
    deleted = 0
    
    for backup_file in backup_dir.glob("backup_*.db*"):
        try:
            # 从文件名解析时间
            name = backup_file.stem
            if name.endswith(".db"):
                name = name[:-3]  # 处理 .db.gz
            
            timestamp_str = name.replace("backup_", "")
            file_time = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
            
            if file_time < cutoff_time:
                backup_file.unlink()
                logger.info(f"删除过期备份: {backup_file}")
                deleted += 1
                
        except (ValueError, OSError) as e:
            logger.warning(f"处理备份文件失败 {backup_file}: {e}")
    
    return deleted


def verify_backup(backup_path: Path) -> bool:
    """
    验证备份完整性。
    
    Args:
        backup_path: 备份文件路径
        
    Returns:
        是否有效
    """
    tmp_path = None
    conn = None
    
    try:
        # 如果是压缩文件，先解压
        if backup_path.suffix == ".gz":
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
                with gzip.open(backup_path, 'rb') as f_in:
                    shutil.copyfileobj(f_in, tmp)
                tmp_path = tmp.name
            
            conn = sqlite3.connect(tmp_path)
        else:
            conn = sqlite3.connect(str(backup_path))
        
        # 执行完整性检查
        cursor = conn.cursor()
        cursor.execute("PRAGMA integrity_check")
        result = cursor.fetchone()
        
        if result[0] == "ok":
            logger.info(f"备份验证通过: {backup_path}")
            return True
        else:
            logger.error(f"备份验证失败: {result[0]}")
            return False
            
    except Exception as e:
        logger.error(f"备份验证异常: {e}")
        return False
    finally:
        if conn:
            conn.close()
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


def main():
    parser = argparse.ArgumentParser(description="数据库自动备份")
    parser.add_argument(
        "--backup-dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "backups",
        help="备份目录"
    )
    parser.add_argument(
        "--keep-days",
        type=int,
        default=7,
        help="保留备份天数"
    )
    parser.add_argument(
        "--no-compress",
        action="store_true",
        help="不压缩备份"
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="验证备份"
    )
    parser.add_argument(
        "--encrypt",
        action="store_true",
        help="加密备份文件"
    )
    parser.add_argument(
        "--encryption-key",
        type=str,
        default=None,
        help="加密密钥（也可通过 BACKUP_ENCRYPTION_KEY 环境变量设置）"
    )
    
    args = parser.parse_args()
    
    # 获取数据库路径
    db_path = get_database_path()
    
    # 获取加密密钥
    encryption_key = args.encryption_key or os.environ.get("BACKUP_ENCRYPTION_KEY")
    
    # 创建备份
    backup_path = create_backup(
        db_path=db_path,
        backup_dir=args.backup_dir,
        compress=not args.no_compress,
        encrypt=args.encrypt,
        encryption_key=encryption_key,
    )
    
    if backup_path is None:
        sys.exit(1)
    
    # 验证备份
    if args.verify:
        if not verify_backup(backup_path):
            logger.error("备份验证失败，删除无效备份")
            backup_path.unlink()
            sys.exit(1)
    
    # 清理旧备份
    deleted = cleanup_old_backups(args.backup_dir, args.keep_days)
    if deleted > 0:
        logger.info(f"清理了 {deleted} 个过期备份")
    
    logger.info("备份任务完成")


if __name__ == "__main__":
    main()
