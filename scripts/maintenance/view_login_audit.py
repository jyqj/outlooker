#!/usr/bin/env python3
"""
登录审计日志查看工具

用于查看和分析登录审计日志,帮助管理员识别可疑的登录活动
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from typing import List, Dict

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "backend"))

AUDIT_LOG_FILE = project_root / "data" / "logs" / "login_audit.log"


def load_audit_logs() -> List[Dict]:
    """加载审计日志"""
    if not AUDIT_LOG_FILE.exists():
        return []
    
    logs = []
    with AUDIT_LOG_FILE.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                logs.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    
    return logs


def display_recent_logs(logs: List[Dict], limit: int = 20):
    """显示最近的登录记录"""
    print(f"\n{'='*80}")
    print(f"最近 {min(limit, len(logs))} 条登录记录")
    print(f"{'='*80}\n")
    
    recent = logs[-limit:] if len(logs) > limit else logs
    recent.reverse()  # 最新的在前
    
    for log in recent:
        status = "✓ 成功" if log.get("success") else "✗ 失败"
        dt = log.get("datetime", "未知时间")
        ip = log.get("ip", "未知IP")
        username = log.get("username", "未知用户")
        reason = log.get("reason", "")
        
        print(f"{dt} | {status:6} | IP: {ip:15} | 用户: {username:15} | {reason}")


def display_failed_attempts(logs: List[Dict]):
    """显示失败的登录尝试统计"""
    print(f"\n{'='*80}")
    print("失败登录尝试统计")
    print(f"{'='*80}\n")
    
    failed_logs = [log for log in logs if not log.get("success")]
    
    if not failed_logs:
        print("没有失败的登录记录")
        return
    
    # 按 IP 统计
    by_ip = defaultdict(int)
    # 按用户名统计
    by_username = defaultdict(int)
    # 按 IP+用户名统计
    by_combination = defaultdict(int)
    
    for log in failed_logs:
        ip = log.get("ip", "unknown")
        username = log.get("username", "unknown")
        
        by_ip[ip] += 1
        by_username[username] += 1
        by_combination[(ip, username)] += 1
    
    print("按 IP 地址统计:")
    for ip, count in sorted(by_ip.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {ip:20} - {count:3} 次失败")
    
    print("\n按用户名统计:")
    for username, count in sorted(by_username.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {username:20} - {count:3} 次失败")
    
    print("\n按 IP+用户名组合统计 (可能的暴力破解):")
    for (ip, username), count in sorted(by_combination.items(), key=lambda x: x[1], reverse=True)[:10]:
        if count >= 3:  # 只显示失败3次以上的
            print(f"  {ip:20} + {username:15} - {count:3} 次失败")


def display_success_rate(logs: List[Dict]):
    """显示登录成功率"""
    print(f"\n{'='*80}")
    print("登录成功率统计")
    print(f"{'='*80}\n")
    
    if not logs:
        print("没有登录记录")
        return
    
    total = len(logs)
    success = sum(1 for log in logs if log.get("success"))
    failed = total - success
    success_rate = (success / total * 100) if total > 0 else 0
    
    print(f"总登录次数: {total}")
    print(f"成功次数:   {success}")
    print(f"失败次数:   {failed}")
    print(f"成功率:     {success_rate:.2f}%")


def display_timeline(logs: List[Dict], hours: int = 24):
    """显示时间线分析"""
    print(f"\n{'='*80}")
    print(f"最近 {hours} 小时登录活动时间线")
    print(f"{'='*80}\n")
    
    if not logs:
        print("没有登录记录")
        return
    
    now = datetime.now().timestamp()
    cutoff = now - (hours * 3600)
    
    recent_logs = [log for log in logs if log.get("timestamp", 0) > cutoff]
    
    if not recent_logs:
        print(f"最近 {hours} 小时没有登录记录")
        return
    
    # 按小时分组
    by_hour = defaultdict(lambda: {"success": 0, "failed": 0})
    
    for log in recent_logs:
        dt = datetime.fromtimestamp(log.get("timestamp", 0))
        hour_key = dt.strftime("%Y-%m-%d %H:00")
        
        if log.get("success"):
            by_hour[hour_key]["success"] += 1
        else:
            by_hour[hour_key]["failed"] += 1
    
    for hour in sorted(by_hour.keys()):
        stats = by_hour[hour]
        success = stats["success"]
        failed = stats["failed"]
        total = success + failed
        
        bar_success = "█" * success
        bar_failed = "░" * failed
        
        print(f"{hour} | 成功:{success:2} 失败:{failed:2} | {bar_success}{bar_failed}")


def main():
    """主函数"""
    print("\n登录审计日志分析工具")
    
    logs = load_audit_logs()
    
    if not logs:
        print(f"\n未找到审计日志文件: {AUDIT_LOG_FILE}")
        print("提示: 登录审计日志会在首次登录尝试后自动创建")
        return
    
    print(f"\n已加载 {len(logs)} 条登录记录")
    
    # 显示各种统计信息
    display_success_rate(logs)
    display_recent_logs(logs, limit=20)
    display_failed_attempts(logs)
    display_timeline(logs, hours=24)
    
    print(f"\n{'='*80}\n")


if __name__ == "__main__":
    main()
