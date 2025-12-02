# MindSpider 特定关键词定向爬虫

## 概述

`keyword_crawler.py` 是一个独立的Python脚本，用于在特定社交媒体平台上定向爬取包含指定关键词的内容。它基于MediaCrawler构建，提供灵活的关键词、平台和数量配置功能。

## 功能特性

- ✅ **平台支持**：支持7大主流社交平台（小红书、抖音、快手、哔哩哔哩、微博、贴吧、知乎）
- ✅ **关键词搜索**：支持单个或多个关键词搜索
- ✅ **数量控制**：灵活设置每个关键词的爬取上限
- ✅ **数据存储**：直接保存到MySQL数据库，与MindSpider兼容
- ✅ **安全配置**：自动备份和恢复配置文件，不影响其他进程

## 系统要求

- Python 3.9+
- 已安装并配置好的MySQL数据库
- 已安装MindSpider项目依赖
- 已设置正确的.env配置文件

## 快速开始

### 1. 查看帮助信息

```bash
cd MindSpider
python keyword_crawler.py --help
```

### 2. 基本用法

```bash
# 爬取微博相关内容（推荐测试用例）
python keyword_crawler.py --platform wb --keywords "人工智能" --max-notes 5

# 爬取小红书多个关键词
python keyword_crawler.py --platform xhs --keywords "AI,机器学习,Python" --max-notes 10

# 爬取B站内容，跳过前几页
python keyword_crawler.py --platform bili --keywords "编程教程" --max-notes 20 --start-page 2
```

### 3. 调试模式和测试用例

脚本内置了多个预设测试用例，便于调试和功能验证：

```bash
# 启用调试模式（会运行预设测试用例）
export DEBUG_TEST=1
python keyword_crawler.py

# 或者直接设置环境变量运行
DEBUG_TEST=1 python keyword_crawler.py
```

**调试模式功能**：
- 在`run_debug_test_case()`函数中修改`test_case`变量来选择测试场景
- 支持6种预设测试用例：基础功能、多关键词、不同平台、性能测试、错误处理、帮助信息
- 每个测试用例都可以设置断点进行详细调试
- 自动模拟命令行参数，完全兼容正常使用模式

**预设测试用例**：
1. **basic** - 基础功能：微博平台，'人工智能'关键词，5个结果
2. **multi_keywords** - 多关键词：B站平台，['Python','编程','教程']，10个结果
3. **different_platform** - 不同平台：小红书平台，'美食'关键词，8个结果
4. **performance** - 性能测试：知乎平台，'机器学习'关键词，30个结果
5. **error** - 错误处理：验证参数错误时的提示信息
6. **help** - 帮助信息：显示完整的帮助文档

## 详细参数说明

### 必需参数

| 参数 | 简写 | 说明 | 示例 |
|------|------|------|------|
| `--platform` | `-p` | 爬取平台 | `wb` (微博)、`xhs` (小红书) |
| `--keywords` | `-k` | 搜索关键词 | `"人工智能"` 或 `"AI,Python,机器学习"` |

### 可选参数

| 参数 | 简写 | 默认值 | 说明 |
|------|------|--------|------|
| `--max-notes` | `-n` | 20 | 每个关键词最大爬取数量 |
| `--login-type` | `-l` | qrcode | 登录方式 (qrcode/phone/cookie) |
| `--start-page` | `-s` | 1 | 起始页码 |

## 使用示例

### 示例1：舆情监测 - 品牌声誉分析

```bash
# 监控特定品牌在社交媒体的讨论
python keyword_crawler.py --platform wb --keywords "苹果公司" --max-notes 50
python keyword_crawler.py --platform xhs --keywords "苹果新品" --max-notes 30
python keyword_crawler.py --platform bili --keywords "苹果发布会" --max-notes 40
```

### 示例2：危机公关监测

```bash
# 监控负面舆情关键词
python keyword_crawler.py --platform wb --keywords "品牌名称 负面词" --max-notes 100
```

### 示例3：热点事件跟踪

```bash
# 跟踪热点事件讨论
python keyword_crawler.py --platform zhihu --keywords "热门事件名称" --max-notes 30
python keyword_crawler.py --platform tieba --keywords "事件名称" --max-notes 50
```

### 示例4：学术研究 - 议题分析

```bash
# 研究特定议题的公共意见
python keyword_crawler.py --platform wb --keywords "气候变化" --max-notes 200
python keyword_crawler.py --platform zhihu --keywords "可持续发展" --max-notes 100
```

## 平台代码对照表

| 代码 | 平台名称 | 特色内容 |
|------|----------|----------|
| `xhs` | 小红书 | 生活方式、消费指南 |
| `dy` | 抖音 | 短视频、娱乐内容 |
| `ks` | 快手 | 短视频、地方内容 |
| `bili` | 哔哩哔哩 | 专业教程、科技内容 |
| `wb` | 微博 | 时政新闻、热点话题 |
| `tieba` | 百度贴吧 | 兴趣小组、专业讨论 |
| `zhihu` | 知乎 | Q&A、专业回答 |

## 数据验证

爬取完成后，可以通过以下方式验证数据是否成功保存：

### 方法1：通过脚本提供的验证命令

脚本执行成功后会自动显示验证命令，类似：
```bash
mysql -u jfzhou1 -p bettafish_db -e "SELECT COUNT(*) as count FROM wb_note WHERE keyword IN ('人工智能')"
```

### 方法2：手动检查数据库

```bash
# 进入MySQL
mysql -u jfzhou1 -p bettafish_db

# 查看数据表
SHOW TABLES LIKE '%_note';

# 检查特定平台的数据
SELECT COUNT(*) FROM wb_note WHERE keyword = '人工智能';
SELECT * FROM wb_note WHERE keyword = '人工智能' LIMIT 5;

# 检查数据结构
DESCRIBE wb_note;
```

### 方法3：通过MindSpider分析

爬取完成后，可以使用MindSpider的舆情分析功能来分析这些数据：

```bash
# 运行完整流程进行分析
python main.py --complete
```

## 注意事项

### ⚠️ 重要提醒

1. **首次使用平台登录**：
   - 每个平台首次使用都需要扫二维码登录
   - 登录状态会被保存，下次可以直接使用

2. **数据量控制**：
   - 建议单个关键词不超过100个帖子
   - 多个关键词会分别处理，每个都有独立的数量限制

3. **运行频率**：
   - 避免频繁大量爬取，遵守平台规则
   - 建议间隔一段时间后再进行新的爬取

4. **存储空间**：
   - 确保MySQL有足够存储空间
   - 定期清理历史数据

### 🔧 故障排除

#### 登录问题
- 如果二维码不显示，修改headless模式：编辑MediaCrawler配置文件
- 如果扫码失败，删除浏览器数据文件夹重新登录

#### 数据为空
- 检查关键词是否存在相关内容
- 尝试扩大关键词范围
- 确认平台登录状态正常

#### 数据库连接失败
- 确认MySQL服务正在运行
- 检查.env文件中的数据库配置
- 验证数据库和用户权限

#### 爬取速度慢
- 适当减少max-notes数量
- 尝试减少关键词数量
- 考虑使用不同的平台

## 技术架构

### 配置管理
- 安全地备份和修改MediaCrawler配置
- 自动恢复原始配置，保证系统稳定性

### 命令构建
- 动态构建MediaCrawler命令行参数
- 支持所有MediaCrawler支持的功能

### 错误处理
- 完整的异常处理机制
- 用户友好的错误提示信息
- 安全的退出和状态管理

## 最佳实践

1. **测试先行**：先用少量数据测试爬取功能
2. **关键词优化**：选择有针对性的关键词组合
3. **数量合理**：根据需求和资源情况设置合适的数量
4. **定期监控**：检查数据质量和爬取效果
5. **合规使用**：遵守平台条款和法律法规

## 扩展开发

### 添加新平台支持
在MediaCrawler中实现新平台的爬虫后，只需在脚本中添加对应的代码即可。

### 添加新参数
可以根据需求在MediaCrawler基础上添加更多控制参数。

---
