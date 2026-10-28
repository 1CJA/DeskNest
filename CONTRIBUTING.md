# 参与贡献

感谢使用和改进 DeskNest。当前版本为 v0.1.1，后续会持续迭代。

## 反馈问题

请在 Issues 中写明：应用版本、Windows 版本、复现步骤、预期结果和实际结果。可以附截图或脱敏日志，请不要上传个人数据库、私人文件或含凭据的信息。

## 本地开发

使用 Windows 和 Python 3.10+（项目已记录验证的版本为 3.12.10）：

```powershell
git clone https://github.com/1CJA/DeskNest.git
cd DeskNest
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

修改后运行测试：

```powershell
.\.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -v
```

测试覆盖临时数据和 Qt 交互。`tools/verify_windows.py` 会打开原生测试窗口并创建项目内测试样本，详见 [验证记录](docs/VALIDATION.md)。

## 提交修改

请为改动创建分支并提交 Pull Request，描述要解决的问题、最终行为和验证结果。较大的功能建议先通过 Issue 讨论。

保持扫描与导入只保存引用的行为；新增真实文件操作时需单独设计恢复机制。不要提交 `.runtime`、`dist`、`build`、`test-data`、数据库、日志或凭据。

提交内容按项目 MIT 许可证提供；第三方组件继续遵循其自身许可证。
