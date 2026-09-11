"""当前时间工具：回答日期/时间类问题前先调用。"""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from app.agent.tools import register_tool

TZ = ZoneInfo("Asia/Shanghai")


@register_tool(
    name="get_current_time",
    description="获取当前的日期、星期和时间（香港时区）。回答'今天/现在/本周'类问题前先调用。",
    parameters={"type": "object", "properties": {}},
)
async def get_current_time() -> str:
    now = datetime.now(TZ)
    weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    return (
        f"当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')} {weekdays[now.weekday()]} "
        f"(Asia/Shanghai, UTC{now.strftime('%z')})"
    )
