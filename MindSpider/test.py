#!/usr/bin/env python3
import subprocess
import sys
import os

# 设置正确的 MediaCrawler 路径
mediacrawler_path = os.path.join(os.path.dirname(__file__), 'DeepSentimentCrawling', 'MediaCrawler')
os.chdir(mediacrawler_path)

# platforms = ['bili', 'wb', 'dy', 'ks', 'zhihu', 'tieba']
platforms = ['dy', 'ks', 'zhihu', 'tieba']

for platform in platforms:
    print(f"\n=== 测试 {platform} 平台登录 ===")
    try:
        # 使用不存在的页面参数，让爬虫快速失败（仅测试登录）
        cmd = [sys.executable, 'main.py', '--platform', platform, '--keywords', '测试', '--start', '9999']
        print(f"执行命令: {' '.join(cmd)}")
        result = subprocess.run(cmd, timeout=60)  # 1分钟超时，只测试登录
        print(f"✅ {platform} 登录测试完成")
    except subprocess.TimeoutExpired:
        print(f"⏰ {platform} 测试超时（可能登录成功但页面不存在）")
    except Exception as e:
        print(f"💥 {platform} 测试异常: {e}")
