# 测试说明

运行合同与结构检查：

```powershell
py -3 tests/validate_contract.py
```

运行确定性评分单元测试：

```powershell
py -3 -m unittest tests/test_calculate_risk.py
```

这些测试检查结构、缺失处理、评分计算和危险请求边界，不能证明 Skill 能准确预测失业、降薪或裁员。
