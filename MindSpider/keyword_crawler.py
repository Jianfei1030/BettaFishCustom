#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
特定关键词定向爬虫脚本
基于MediaCrawler的命令行工具，支持灵活配置关键词、平台和数量

作者: MindSpider团队
版本: 1.0.0
最后更新: 2025-11-26

使用示例:
  python keyword_crawler.py --platform wb --keywords "汝南县一高" --max-notes 20
  python keyword_crawler.py --platform xhs --keywords "AI,爬虫,Python" --max-notes 50
  python keyword_crawler.py --platform bili --keywords "机器学习教程" --max-notes 30 --login-type qrcode

支持的平台:
  xhs=小红书, dy=抖音, ks=快手, bili=哔哩哔哩, wb=微博, tieba=百度贴吧, zhihu=知乎

注意事项:
- 首次使用需登录对应平台（可能会弹出二维码）
- 数据将保存到MySQL数据库（需提前配置.env文件）
- 爬取速度受平台限制，请合理设置max-notes数量
- 脚本会自动恢复原始配置，不会影响其他进程

数据存储:
- 结果保存到平台对应的数据表中
- 支持后续通过MindSpider的舆情分析系统检索这些数据
"""

import sys
import os
from pathlib import Path

# 🔧 关键：显式加载MindSpider的.env配置，确保MediaCrawler能读取到环境变量
# .env文件位于项目根目录，需要向上两级查找
mindspider_env_file = Path(__file__).parent.parent / ".env"
if mindspider_env_file.exists():
    from dotenv import load_dotenv
    load_dotenv(mindspider_env_file)
    print(f"✅ 已加载MindSpider环境配置文件: {mindspider_env_file}")
    print(f"   数据库连接: {os.environ.get('DB_USER', '未设置')}@{os.environ.get('DB_HOST', '未设置')}:{os.environ.get('DB_PORT', '未设置')}")
    print(f"   数据库名称: {os.environ.get('DB_NAME', '未设置')}")
else:
    print(f"⚠️  未找到MindSpider环境配置文件: {mindspider_env_file}")

# 现在环境变量已加载，MediaCrawler可以读取到DB_*变量
import argparse
import subprocess

# 导入SQLAlchemy相关库和数据模型用于数据验证
try:
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker
    import pymysql
    # 导入MindSpider的数据模型用于验证
    import sys
    sys.path.append(str(Path(__file__).parent))
    from schema.models_bigdata import (
        BilibiliVideo, BilibiliVideoComment, WeiboNote, WeiboNoteComment,
        XhsNote, XhsNoteComment, KuaishouVideo, KuaishouVideoComment,
        TiebaNote, ZhihuContent, ZhihuComment, DouyinAweme, DouyinAwemeComment
    )
    SQL_ALCHEMY_AVAILABLE = True
except ImportError as e:
    SQL_ALCHEMY_AVAILABLE = False
    print(f"⚠️ SQLAlchemy相关库不可用，数据验证功能将被禁用: {e}")

class KeywordCrawler:
    """特定关键词定向爬虫管理器"""

    SUPPORTED_PLATFORMS = ['xhs', 'dy', 'ks', 'bili', 'wb', 'tieba', 'zhihu']
    PLATFORM_NAMES = {
        'xhs': '小红书', 'dy': '抖音', 'ks': '快手', 'bili': '哔哩哔哩',
        'wb': '微博', 'tieba': '百度贴吧', 'zhihu': '知乎'
    }

    def __init__(self):
        """初始化爬虫管理器"""
        self.mindspider_path = Path(__file__).parent
        self.mediacrawler_path = self.mindspider_path / "DeepSentimentCrawling" / "MediaCrawler"
        self.config_path = self.mediacrawler_path / "config" / "base_config.py"

        # 验证路径存在
        if not self.mediacrawler_path.exists():
            raise FileNotFoundError(f"MediaCrawler路径不存在: {self.mediacrawler_path}")
        if not self.config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {self.config_path}")

    def backup_config(self):
        """备份原始配置文件"""
        self.backup_content = ""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.backup_content = f.read()
        except Exception as e:
            raise RuntimeError(f"无法读取配置文件: {e}")

    def restore_config(self):
        """恢复原始配置文件"""
        if hasattr(self, 'backup_content') and self.backup_content:
            try:
                with open(self.config_path, 'w', encoding='utf-8') as f:
                    f.write(self.backup_content)
            except Exception as e:
                print(f"⚠️ 警告：无法恢复配置文件: {e}")

    def modify_config_file(self, max_notes: int):
        """动态修改MediaCrawler配置文件中的爬取数量限制"""
        if not hasattr(self, 'backup_content'):
            raise RuntimeError("配置文件未备份，请先调用backup_config()")

        try:
            # 读取当前配置
            with open(self.config_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 查找并替换CRAWLER_MAX_NOTES_COUNT
            lines = content.split('\n')
            modified = False

            for i, line in enumerate(lines):
                if line.startswith('CRAWLER_MAX_NOTES_COUNT = '):
                    lines[i] = f'CRAWLER_MAX_NOTES_COUNT = {max_notes}'
                    modified = True
                    break

            if not modified:
                # 如果没找到，在合适位置插入
                for i, line in enumerate(lines):
                    if line.startswith('# 爬取视频/帖子的数量控制'):
                        lines.insert(i + 1, f'CRAWLER_MAX_NOTES_COUNT = {max_notes}')
                        modified = True
                        break

            if not modified:
                # 最后备选方案：添加到文件末尾
                lines.append(f'CRAWLER_MAX_NOTES_COUNT = {max_notes}')
                modified = True

            # 写回修改后的配置
            new_content = '\n'.join(lines)
            with open(self.config_path, 'w', encoding='utf-8') as f:
                f.write(new_content)

        except Exception as e:
            raise RuntimeError(f"修改配置文件失败: {e}")

    def build_command(self, args) -> list[str]:
        """构建MediaCrawler命令行参数"""
        cmd = [
            sys.executable,
            str(self.mediacrawler_path / "main.py"),
            "--platform", args.platform,
            "--keywords", args.keywords,
            "--save_data_option", "db"  # 必须保存到数据库
        ]

        # 可选参数
        if args.login_type:
            cmd.extend(["--lt", args.login_type])
        if args.start_page and args.start_page > 1:
            cmd.extend(["--start", str(args.start_page)])

        return cmd

    def run(self, args) -> bool:
        """执行爬取任务"""
        try:
            print(f"🚀 开始爬取任务...")
            print(f"📍 平台: {args.platform} ({self.PLATFORM_NAMES[args.platform]})")
            print(f"🔍 关键词: {args.keywords}")
            print(f"📊 最大数量: {args.max_notes}")
            print(f"🔐 登录方式: {args.login_type}")
            if args.start_page > 1:
                print(f"📄 起始页码: {args.start_page}")

            # 备份配置
            print(f"📁 备份配置文件...")
            self.backup_config()

            # 修改配置
            print(f"⚙️ 修改爬取数量配置为: {args.max_notes}")
            self.modify_config_file(args.max_notes)

            # 构建并执行命令
            cmd = self.build_command(args)
            print(f"🔧 执行命令: {' '.join(cmd)}")

            # 切换到MediaCrawler目录并执行
            original_cwd = os.getcwd()
            try:
                os.chdir(self.mediacrawler_path)
                print(f"📂 工作目录切换到: {self.mediacrawler_path}")

                # 执行命令
                result = subprocess.run(cmd, capture_output=False, text=True)

                return result.returncode == 0

            finally:
                os.chdir(original_cwd)

        except Exception as e:
            print(f"❌ 执行失败: {e}")
            return False

        finally:
            # 恢复配置
            print(f"🔄 恢复原始配置...")
            self.restore_config()

    def verify_crawl_results_simple(self, platform: str, keywords: str, max_notes: int) -> dict:
        """
        用mysql命令行验证爬取结果（简化版，避免SQLAlchemy依赖）

        Args:
            platform: 平台代码
            keywords: 关键字字符串（逗号分隔）
            max_notes: 预期最大数量

        Returns:
            验证结果字典
        """
        result = {
            "success": True,
            "platform": platform,
            "keywords": keywords,
            "main_table_count": 0,
            "comment_table_count": 0,
            "total_records": 0,
            "keyword_match": [],
            "recent_samples": [],
            "warnings": []
        }

        try:
            # 获取数据库连接信息
            db_user = os.environ.get('DB_USER', 'jfzhou1')
            db_password = os.environ.get('DB_PASSWORD', '19941010')
            db_host = os.environ.get('DB_HOST', '127.0.0.1')
            db_port = os.environ.get('DB_PORT', '3306')
            db_name = os.environ.get('DB_NAME', 'bettafish_db')

            # 根据平台确定表名
            tables_info = self._get_table_info(platform)
            if not tables_info:
                result["success"] = False
                result["error"] = f"不支持的平台: {platform}"
                return result

            main_table = tables_info["main"]
            comment_table = tables_info["comment"]

            # 构建mysql命令基础部分
            mysql_cmd_base = [
                "mysql",
                "-u", db_user,
                "-p" + db_password,
                "-h", db_host,
                "-P", str(db_port),
                "-D", db_name,
                "-e"
            ]

            # 查询主表数据（最近1小时内更新）
            try:
                main_query = f"""
                SELECT COUNT(*) as total
                FROM {main_table}
                WHERE last_modify_ts >= UNIX_TIMESTAMP() - 3600
                """
                main_cmd = mysql_cmd_base + [main_query]

                main_result = subprocess.run(main_cmd, capture_output=True, text=True, timeout=30)
                if main_result.returncode == 0 and main_result.stdout.strip():
                    # 解析输出（去掉表头，获取数据行）
                    lines = main_result.stdout.strip().split('\n')
                    if len(lines) >= 2:  # 有表头+数据
                        count_str = lines[1].strip()  # 第二行是数据
                        result["main_table_count"] = int(count_str) if count_str.isdigit() else 0
                else:
                    result["warnings"].append(f"主表查询失败: {main_result.stderr.strip()}")

            except subprocess.TimeoutExpired:
                result["warnings"].append("主表查询超时")
            except Exception as e:
                result["warnings"].append(f"主表查询异常: {str(e)}")

            # 查询评论表数据
            if comment_table:
                try:
                    comment_query = f"""
                    SELECT COUNT(*) as total
                    FROM {comment_table}
                    WHERE add_ts >= UNIX_TIMESTAMP() - 3600
                    """
                    comment_cmd = mysql_cmd_base + [comment_query]

                    comment_result = subprocess.run(comment_cmd, capture_output=True, text=True, timeout=30)
                    if comment_result.returncode == 0 and comment_result.stdout.strip():
                        lines = comment_result.stdout.strip().split('\n')
                        if len(lines) >= 2:
                            count_str = lines[1].strip()
                            result["comment_table_count"] = int(count_str) if count_str.isdigit() else 0
                    else:
                        result["warnings"].append(f"评论表查询失败: {comment_result.stderr.strip()}")

                except subprocess.TimeoutExpired:
                    result["warnings"].append("评论表查询超时")
                except Exception as e:
                    result["warnings"].append(f"评论表查询异常: {str(e)}")

            # 计算总数
            result["total_records"] = result["main_table_count"] + result["comment_table_count"]

            # 检查关键词匹配（简化版：只检查主表的关键字）
            try:
                keyword_query = f"""
                SELECT GROUP_CONCAT(DISTINCT source_keyword) as keywords_found
                FROM {main_table}
                WHERE last_modify_ts >= UNIX_TIMESTAMP() - 3600
                """
                keyword_cmd = mysql_cmd_base + [keyword_query]

                keyword_result = subprocess.run(keyword_cmd, capture_output=True, text=True, timeout=30)
                if keyword_result.returncode == 0 and keyword_result.stdout.strip():
                    lines = keyword_result.stdout.strip().split('\n')
                    if len(lines) >= 2:
                        keywords_found = lines[1].strip()

                        keyword_list = [k.strip() for k in keywords.split(',')]
                        result["keyword_match"] = []

                        for keyword in keyword_list:
                            if keywords_found and keyword in keywords_found:
                                result["keyword_match"].append(keyword)

            except Exception as e:
                result["warnings"].append(f"关键词检查失败: {str(e)}")

            # 获取最近的样本数据
            try:
                sample_query = f"""
                SELECT source_keyword, create_time, add_ts
                FROM {main_table}
                WHERE last_modify_ts >= UNIX_TIMESTAMP() - 3600
                ORDER BY last_modify_ts DESC
                LIMIT 3
                """
                sample_cmd = mysql_cmd_base + [sample_query]

                sample_result = subprocess.run(sample_cmd, capture_output=True, text=True, timeout=30)
                if sample_result.returncode == 0 and sample_result.stdout.strip():
                    lines = sample_result.stdout.strip().split('\n')
                    if len(lines) >= 2:  # 表头+数据
                        # 跳过表头，从数据行开始
                        for line in lines[1:]:
                            parts = line.strip().split('\t')  # mysql tab分隔输出
                            if len(parts) >= 3:
                                result["recent_samples"].append({
                                    "keyword": parts[0],
                                    "create_time": parts[1],
                                    "add_time": parts[2]
                                })
                else:
                    result["warnings"].append(f"样本数据查询失败: {sample_result.stderr.strip()}")

            except subprocess.TimeoutExpired:
                result["warnings"].append("样本查询超时")
            except Exception as e:
                result["warnings"].append(f"样本查询异常: {str(e)}")

            # 验证结果合理性
            if result["total_records"] == 0:
                result["warnings"].append("⚠️ 未找到新爬取的数据，可能爬取失败或数据仍在处理中")

            if len(result["keyword_match"]) == 0:
                result["warnings"].append("⚠️ 没有找到匹配的关键字数据")

            # 这里不做上限检查，因为实际数据量可能合理

        except Exception as e:
            result["success"] = False
            result["error"] = f"数据库验证失败: {str(e)}"

        return result

    def _get_table_info(self, platform: str) -> dict:
        """
        根据平台返回对应的表信息

        Args:
            platform: 平台代码

        Returns:
            包含表信息和主键字段的字典
        """
        table_mapping = {
            'bili': {
                'main': 'bilibili_video',
                'comment': 'bilibili_video_comment',
                'id_column': 'video_id'
            },
            'wb': {
                'main': 'weibo_note',
                'comment': 'weibo_note_comment',
                'id_column': 'note_id'
            },
            'xhs': {
                'main': 'xhs_note',
                'comment': 'xhs_note_comment',
                'id_column': 'note_id'
            },
            'dy': {
                'main': 'douyin_aweme',
                'comment': 'douyin_aweme_comment',
                'id_column': 'aweme_id'
            },
            'ks': {
                'main': 'kuaishou_video',
                'comment': 'kuaishou_video_comment',
                'id_column': 'video_id'
            },
            'tieba': {
                'main': 'tieba_note',
                'comment': None,  # tieba没有单独的评论表
                'id_column': 'note_id'
            },
            'zhihu': {
                'main': 'zhihu_content',
                'comment': 'zhihu_comment',
                'id_column': 'content_id'
            }
        }

        return table_mapping.get(platform)


def main():
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="MindSpider特定关键词定向爬虫",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python keyword_crawler.py --platform wb --keywords "汝南县一高" --max-notes 20
  python keyword_crawler.py --platform xhs --keywords "AI,爬虫,Python" --max-notes 50
  python keyword_crawler.py --platform bili --keywords "机器学习教程" --max-notes 30 --login-type qrcode

支持的平台:
  xhs=小红书, dy=抖音, ks=快手, bili=哔哩哔哩, wb=微博, tieba=百度贴吧, zhihu=知乎

数据存储:
  所有爬取数据将保存到MySQL数据库中，供MindSpider舆情分析系统使用。

注意事项:
• 首次使用每个平台都需要登录（可能会弹出二维码扫码界面）
• 确保已正确配置.env文件中的数据库连接信息
• 爬取速度受平台限制，请合理设置max-notes数量
• 如果遇到登录问题，请查看MediaCrawler的README文档
        """
    )

    # 必需参数
    parser.add_argument(
        "--platform", "-p", required=True,
        choices=KeywordCrawler.SUPPORTED_PLATFORMS,
        help="指定爬取平台"
    )

    parser.add_argument(
        "--keywords", "-k", required=True,
        help="搜索关键词，多个关键词用逗号分隔"
    )

    # 可选参数
    parser.add_argument(
        "--max-notes", "-n", type=int, default=20,
        help="每个关键词最大爬取数量（默认20，建议不超过100）"
    )

    parser.add_argument(
        "--login-type", "-l",
        choices=['qrcode', 'phone', 'cookie'],
        default='qrcode',
        help="登录方式（默认qrcode=二维码登录）"
    )

    parser.add_argument(
        "--start-page", "-s", type=int, default=1,
        help="起始页码（默认1，从第一页开始）"
    )

    # 解析参数
    args = parser.parse_args()

    # 参数验证
    if args.max_notes <= 0:
        parser.error("错误：max-notes参数必须大于0")

    if args.max_notes > 200:
        print("⚠️ 警告：max-notes设置较大，可能需要较长时间，请确认是否继续...")

    if not args.keywords or not args.keywords.strip():
        parser.error("错误：keywords参数不能为空")

    # 处理关键词（去除空格，合并多余逗号）
    args.keywords = ','.join([k.strip() for k in args.keywords.split(',') if k.strip()])

    # 执行爬取
    try:
        crawler = KeywordCrawler()
        success = crawler.run(args)

        if success:
            print(f"\n✅ 爬取任务完成！")
            print(f"📊 爬取统计: 平台={args.platform}, 关键词={args.keywords}, 目标数量={args.max_notes}")
            print(f"💾 数据已保存到MySQL数据库")

            # 🔍 验证爬取结果 (使用简化版mysql命令验证)
            verification_result = crawler.verify_crawl_results_simple(args.platform, args.keywords, args.max_notes)

            if verification_result["success"]:
                print(f"\n🔍 📊 数据验证结果:")
                print(f"📍 验证平台: {args.platform} ({crawler.PLATFORM_NAMES[args.platform]})")
                print(f"📊 主表记录数: {verification_result['main_table_count']}")
                if verification_result['comment_table_count'] > 0:
                    print(f"💬 评论表记录数: {verification_result['comment_table_count']}")
                print(f"📈 总记录数: {verification_result['total_records']}")
                print(f"🔍 关键词匹配: {len(verification_result['keyword_match'])}/{len(args.keywords.split(','))} 个")

                # 显示最近的样本数据
                if verification_result["recent_samples"]:
                    print(f"📋 最近3条数据样本:")
                    for i, sample in enumerate(verification_result["recent_samples"], 1):
                        print(f"   {i}. 关键词:'{sample['keyword']}' 创建时间:{sample['create_time']}")

                # 显示警告信息
                if verification_result["warnings"]:
                    print(f"⚠️ 数据验证警告:")
                    for warning in verification_result["warnings"]:
                        print(f"   {warning}")
                else:
                    print(f"✅ 数据验证通过，无异常发现")
            else:
                print(f"⚠️ 无法验证数据: {verification_result.get('error', '未知错误')}")
                print(f"💡 数据可能仍在处理中，请稍后手动检查数据库")

            print(f"\n🔍 您可以通过MindSpider的舆情分析功能来查看和分析这些数据")
        else:
            print("\n❌ 爬取任务失败！请检查错误信息并重试")
            sys.exit(1)

    except FileNotFoundError as e:
        print(f"❌ 路径错误: {e}")
        print("💡 建议：确认MindSpider项目结构完整，MediaCrawler目录存在")
        sys.exit(1)

    except RuntimeError as e:
        print(f"❌ 配置错误: {e}")
        print("💡 建议：检查文件权限，确认配置文件可读写")
        sys.exit(1)

    except Exception as e:
        print(f"❌ 未知错误: {e}")
        print("💡 建议：检查Python环境和依赖包")
        sys.exit(1)


def setup_test_case_basic_functionality():
    """
    测试用例：基础功能测试
    测试单个平台、单个关键词、小数据量
    适用于验证基本爬取功能是否正常
    """
    print("🧪 运行测试用例：基础功能测试")
    print("📝 测试内容：微博平台，'人工智能'关键词，5个结果")

    # 设置断点在这里可以调试参数设置过程
    test_args = [
        'keyword_crawler.py',  # 脚本名
        # '--platform', 'bili',
        # '--platform', 'ks',
        '--platform', 'zhihu',
        '--keywords', '小米',  # 关键词
        '--max-notes', '1'    # 小数据量
    ]

    # 可以在这里打断点进行调试
    sys.argv = test_args

    return test_args


def setup_test_case_multi_keywords():
    """
    测试用例：多关键词测试
    测试单个平台、多个关键词
    适用于验证关键词处理和多关键词策略
    """
    print("🧪 运行测试用例：多关键词测试")
    print("📝 测试内容：B站平台，['Python','编程','教程']，10个结果")

    test_args = [
        'keyword_crawler.py',
        '--platform', 'bili',
        '--keywords', 'Python,编程,教程',  # 注意这里的语法，可以在这里打断点验证处理过程
        '--max-notes', '10'
    ]

    sys.argv = test_args
    return test_args


def setup_test_case_different_platform():
    """
    测试用例：不同平台测试
    测试非微博平台的爬取能力
    适用于验证平台兼容性
    """
    print("🧪 运行测试用例：不同平台测试")
    print("📝 测试内容：小红书平台，'美食'关键词，8个结果")

    test_args = [
        'keyword_crawler.py',
        '--platform', 'xhs',   # 测试小红书平台（记得首次需要扫码登录）
        '--keywords', '美食',
        '--max-notes', '8'
    ]

    sys.argv = test_args
    return test_args


def setup_test_case_performance_test():
    """
    测试用例：性能测试
    测试较大规模的数据爬取
    适用于验证系统在较大压力下的表现
    """
    print("🧪 运行测试用例：性能测试")
    print("📝 测试内容：知乎平台，'机器学习'关键词，30个结果")
    print("⚠️  注意：这个测试将爬取较多数据，请确保网络和系统性能充足")

    test_args = [
        'keyword_crawler.py',
        '--platform', 'zhihu',
        '--keywords', '机器学习',
        '--max-notes', '30'  # 较大数量，用于性能测试
    ]

    sys.argv = test_args
    return test_args


def setup_test_case_error_handling():
    """
    测试用例：错误处理测试
    测试错误的参数输入和异常情况
    适用于验证错误处理机制
    """
    print("🧪 运行测试用例：错误处理测试")
    print("📝 测试内容：错误的关键词参数，验证错误提示")

    test_args = [
        'keyword_crawler.py',
        '--platform', 'wb',
        '--keywords', '',  # 空关键词，应该触发错误
        '--max-notes', '5'
    ]

    sys.argv = test_args
    return test_args


def setup_test_case_help():
    """
    测试用例：帮助信息测试
    测试帮助信息显示
    """
    print("🧪 运行测试用例：帮助信息测试")
    print("📝 测试内容：显示脚本的完整帮助信息")

    test_args = [
        'keyword_crawler.py',
        '--help'
    ]

    sys.argv = test_args
    return test_args


def run_debug_test_case():
    """
    调试测试用例选择器
    通过修改这里面的变量来选择运行哪个测试用例
    在调试时来到这里，通过修改test_case变量来选择测试场景
    """
    # ==================== 修改这个变量来选择测试用例 ====================
    # 可选值：'basic', 'multi_keywords', 'different_platform', 'performance', 'error', 'help'
    test_case = 'basic'  # 🔥 在这里修改测试用例，在调试时可以打断点修改这个变量
    # ====================================================================

    print(f"🐛 调试模式：选择测试用例 '{test_case}'")

    # 根据选择执行对应的测试用例设置
    if test_case == 'basic':
        return setup_test_case_basic_functionality()
    elif test_case == 'multi_keywords':
        return setup_test_case_multi_keywords()
    elif test_case == 'different_platform':
        return setup_test_case_different_platform()
    elif test_case == 'performance':
        return setup_test_case_performance_test()
    elif test_case == 'error':
        return setup_test_case_error_handling()
    elif test_case == 'help':
        return setup_test_case_help()
    else:
        print(f"❌ 未知的测试用例：{test_case}")
        print("📝 可用的测试用例：basic, multi_keywords, different_platform, performance, error, help")
        sys.exit(1)


if __name__ == "__main__":
    # 检查是否启用调试测试模式
    # 可以通过环境变量或命令行参数启用，例如：
    # DEBUG_TEST=1 python keyword_crawler.py
    # 或者在运行前设置：export DEBUG_TEST=1

    # debug_test_enabled = os.environ.get('DEBUG_TEST', '').lower() in ('1', 'true', 'yes')

    # if debug_test_enabled:
        # 运行调试测试用例
        
    print("🔧 启用调试模式 - 使用预设测试用例")
    print("💡 在 run_debug_test_case() 函数中可以设置断点来调试不同的测试场景")
    run_debug_test_case()

    # 调用主函数，可以在这里设置断点查看最终的sys.argv参数
    try:
        main()
    except SystemExit as e:
        # 重新抛出SystemExit异常（比如--help退出）
        raise e
    except Exception as e:
        print(f"❌ 测试过程中出现异常：{e}")
        print("💡 这可能是正常的错误处理测试结果，也可能是意外错误")
