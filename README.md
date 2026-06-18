# 腾讯云服务器秒杀工具

[comment]: <> (Tencent Cloud Server Seckill Tool)

使用 Python 编写的自动化抢购脚本，支持并发抢购腾讯云轻量应用服务器。

## 运行指令

```powershell
py -3.13 get_cookies.py
py -3.13 snap_up_server.py
```

![Tencent Cloud](image.png)

## 功能特点

- **自动获取 Cookie**：使用 Playwright 模拟浏览器登录，自动保存登录态
- **多地域并发抢购**：支持华北、华东、华南同时抢购
- **实时库存检测**：循环检测目标商品库存状态
- **服务器时间校准**：自动获取腾讯云服务器时间，确保准时抢购
- **自动等待秒杀**：监控时间，到点自动发起抢购

## 环境要求

- Python 3.8+
- Windows / macOS / Linux

## 安装步骤

### 1. 安装依赖

```bash
py -3.13 -m pip install playwright requests
py -3.13 -m playwright install chromium
```

### 2. 获取登录 Cookie

```powershell
py -3.13 get_cookies.py
```

运行后会自动打开浏览器，点击二维码扫码登录腾讯云。登录成功后 Cookie 会自动保存到 `cookies.json` 文件。

## 使用方法

### 配置参数

脚本启动时会自动读取活动页配置，匹配目标商品“轻量 4核4G3M”，并同步当前场次的 `activity_id`、`act_id`、`business_id` 和下单参数。

如需调整地域优先级，可编辑 `snap_up_server.py` 中的：

```python
region_ids = [1, 4, 8]  # 1=华北，4=华东，8=华南
```

**CSRF Token**：

脚本会自动从 `cookies.json` 里读取 `skey` 并计算 `x-csrf-token`，不需要手工更新。若提示 `CSRF-ERROR`，先重新运行 `get_cookies.py` 登录一次，再执行主脚本。

秒杀时间现在会自动选择当天最接近的 `10:00` 或 `15:00` 时间点；如果已经超过当前时间点 5 分钟，则自动切到下一个时间点。

### 运行秒杀

```powershell
py -3.13 snap_up_server.py
```

脚本会自动：

1. 加载登录 Cookie
2. 校准服务器时间
3. 循环检测库存
4. 到达秒杀时间后自动发起抢购

## 地域配置说明

| region_id | 地域         |
| --------- | ------------ |
| 1         | 华北（广州） |
| 4         | 华东（上海） |
| 8         | 华南（北京） |

## 注意事项

1. **Cookie 有效期**：Cookie 有时效性，建议每次秒杀前重新获取
2. **CSRF Token**：每次登录后可能变化，秒杀前需确认更新
3. **抢购成功率**：脚本只提升效率，不保证抢购成功
4. **仅供学习**：仅限个人学习研究使用，请勿用于商业用途

## 工作原理

1. 加载 `cookies.json` 建立登录会话
2. 循环调用库存检测接口 (`check-available`)
3. 检测到有货后，并发调用下单接口 (`do-goods`)
4. 返回抢购结果

## 常见问题

**Q: 提示 "商品无购买权限"**
A: 检查是否已通过实名认证，或该商品是否对你的账号开放

**Q: 库存检测正常但抢购失败**
A: 确认 `x-csrf-token` 是否为最新值，检查 Cookie 是否有效

**Q: 抢购脚本运行正常但无响应**
A: 检查网络连接，确认秒杀时间是否正确设置

## 文件结构

```
tencentyun/
├── get_cookies.py     # Cookie 获取脚本
├── snap_up_server.py  # 秒抢购主程序
├── cookies.json       # 登录 Cookie 存储
├── image.png          # 演示图片
└── README.md          # 项目文档
```

## 免责声明

本项目仅供学习交流使用，请勿用于商业用途。使用本工具产生的任何后果由使用者自行承担。
