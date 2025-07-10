import pandas as pd
import json
import math
# --- 配置区 (Config) ---

# 规则1: 定义 GameEngineTick 的阈值
GAME_ENGINE_TICK_THRESHOLD = 33.0
GATEKEEPER_EVENT_NAME = 'GameThread/GameEngineTick'

# 规则2: 定义各模块的性能阈值 (单位: ms)
THRESHOLDS = {
    "AI": 4.0,
    "Physics": 4.0,
    "Network": 3.5,
    "NetworkInComing": 3.5,
    "Ability": 3.0,
    "Animation": 2.5,
    "Movement": 3.0,
    "Character": 2.0,
    "Monster": 3.0,
    "SOC": 3.0,
    "OW": 3.0,
    "GamePlay": 2.0,
    "System": 1.5,
    "LuaTick": 1.5,
    "Navmesh": 1.0,
    "Other": 3.0,
    "CSVProfiler": 0.5
}

# 规则3: 定义当模块超标时，需要分析的Top K个子函数
TOP_K_SUB_FUNCTIONS = 5

# 输入输出文件名
CSV_INPUT_FILE = 'profiler_data.csv'
JSON_OUTPUT_FILE = 'performance_report.json'

# 输入输出文件名
CSV_INPUT_FILE = 'profiler_data.csv'
JSON_OUTPUT_FILE = 'performance_report.json'

# --- 算法参数 ---
# Z-score方法的标准差倍数，k越大，筛选越严格
Z_SCORE_K = 2.0
# 内部波动比率，用于检测尖峰
SPIKE_RATIO = 10.0
# 单一函数耗时占模块总耗时的百分比阈值
MAJOR_CONTRIBUTOR_THRESHOLD = 0.4 # 40%

def clean_and_prepare_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """清理和预处理从CSV加载的DataFrame"""
    if 'pct' in df.columns:
        df['pct'] = df['pct'].astype(str).str.replace('%', '', regex=False).astype(float)

    numeric_cols = ['max', 'min', 'avg']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    return df


def find_problematic_modules(df: pd.DataFrame, thresholds: dict) -> list:
    """
    重构后的函数：直接从DataFrame中查找并返回超标的模块及其数据。
    """
    problematic_modules = []
    current_block_rows = []

    print("\n--- 开始扫描模块并与阈值比较 ---")

    # 迭代DataFrame的每一行
    for index, row in df.iterrows():
        is_empty_row = row.isnull().all()

        if not is_empty_row:
            current_block_rows.append(row)
        else:
            # 当遇到空行时，处理之前收集到的数据块
            if len(current_block_rows) > 0:
                module_header = current_block_rows[0]
                module_name = module_header['Event']
                module_avg = module_header['avg']

                # 检查模块名和avg是否有效
                if pd.notna(module_name) and pd.notna(module_avg):
                    threshold = thresholds.get(module_name)

                    print(f"扫描模块: '{module_name}' | 平均耗时: {module_avg:.3f}ms | 阈值: {str(threshold)}ms")

                    # 只有当模块存在阈值且耗时超标时，才处理它
                    if threshold is not None and module_avg > threshold:
                        print(f"  [!] 问题发现: 模块 '{module_name}' 耗时超标，将被记录分析。")

                        sub_functions = []
                        if len(current_block_rows) > 1:
                            for sub_row in current_block_rows[1:]:
                                sub_functions.append({
                                    'Event': sub_row['Event'],
                                    'max': sub_row['max'],
                                    'min': sub_row['min'],
                                    'avg': sub_row['avg'],
                                    'pct': sub_row['pct']
                                })

                        problematic_modules.append({
                            "module_name": module_name,
                            "stats": {
                                'max': module_header['max'],
                                'min': module_header['min'],
                                'avg': module_header['avg'],
                                'pct': module_header['pct']
                            },
                            "sub_functions": sub_functions
                        })

            # 重置当前块，准备下一个模块
            current_block_rows = []

    # 确保文件末尾的最后一个模块也被处理
    if len(current_block_rows) > 0:
        module_header = current_block_rows[0]
        module_name = module_header['Event']
        module_avg = module_header['avg']
        if pd.notna(module_name) and pd.notna(module_avg):
            threshold = thresholds.get(module_name)
            print(f"扫描模块: '{module_name}' | 平均耗时: {module_avg:.3f}ms | 阈值: {str(threshold)}ms")
            if threshold is not None and module_avg > threshold:
                print(f"  [!] 问题发现: 模块 '{module_name}' 耗时超标，将被记录分析。")
                sub_functions = []
                if len(current_block_rows) > 1:
                    for sub_row in current_block_rows[1:]:
                        sub_functions.append(sub_row.to_dict())
                problematic_modules.append({
                    "module_name": module_name,
                    "stats": module_header.to_dict(),
                    "sub_functions": sub_functions
                })
    print("有问题的模块：")
    print(problematic_modules)

    return problematic_modules


def calculate_anomaly_score(sub_function_data: dict) -> float:
    """
    根据函数自身的max, min, avg计算其异常分数。

    """
    print(sub_function_data)
    max_val = sub_function_data.get('max', 0)
    min_val = sub_function_data.get('min', 0)
    avg_val = sub_function_data.get('avg', 0)

    # 过滤掉无效或无意义的数据
    if max_val is None or avg_val is None or min_val is None or max_val < 0.01:
        return 0.0

    epsilon = 1e-6  # 避免除以零

    # 指标1: 波动范围 (绝对波动)
    value_range = max_val - min_val

    # 指标2: 峰值-均值比 (相对波动)
    spike_ratio = max_val / (avg_val + epsilon)

    # 简单的加权评分模型。这里的权重可以调整。
    # 我们给予spike_ratio更高的权重，因为它更能反映卡顿问题。
    # avg_val也作为一个因子，因为高耗时函数的波动更值得关注。
    # score = (0.5 * value_range) + (1.5 * spike_ratio)

    score = math.log(1 + value_range) * math.log(1 + spike_ratio)

    # 进一步加权，让平均耗时高的函数分数更高
    score *= (1 + avg_val)

    return score


def generate_report_from_problematic_modules(problem_modules: list) -> dict:
    """
    使用基于函数自身数据的异常评分模型，分析并标记可优化的子函数。
    """
    final_report = {"problem_modules": []}
    print("\n--- 为超标模块生成详细分析报告 (纯内部数据异常评分) ---")


    for module in problem_modules:
        sub_functions = module['sub_functions']
        sub_functions = pd.DataFrame([s for s in sub_functions if s.get('avg', 0) > 0.01])
        print("SUB-FUNCTIONS")
        print(sub_functions)

        if sub_functions.empty:
            final_report["problem_modules"].append({
                "module_name": module['module_name'], "average_ms": round(module['stats']['avg'], 3),
                "threshold_ms": THRESHOLDS.get(module['module_name']), "culprit_sub_functions": []
            })
            continue

        # 1. 为每个子函数计算异常分数
        scored_subs = []
        for index, sub in sub_functions.iterrows():
            print(sub)
            score = calculate_anomaly_score(sub)
            if score > 0:
                # 将分数添加到函数数据中，方便排序
                sub_with_score = sub.copy()
                sub_with_score['anomaly_score'] = score
                scored_subs.append(sub_with_score)

        # 2. 根据异常分数降序排序
        scored_subs.sort(key=lambda x: x['anomaly_score'], reverse=True)

        # 3. 选取Top-K作为罪魁祸首
        top_anomalies = scored_subs[:5]

        # 4. 格式化输出
        culprit_functions = []
        for sub in top_anomalies:
            culprit_functions.append({
                "Event": sub['Event'],
                "avg_ms": round(sub['avg'], 3),
                "max_ms": round(sub['max'], 3),
                "min_ms": round(sub['min'], 3),
                "anomaly_score": round(sub['anomaly_score'], 2),
                "reason": "High internal performance volatility and/or wide performance range."
            })

        final_report["problem_modules"].append({
            "module_name": module['module_name'],
            "average_ms": round(module['stats']['avg'], 3),
            "threshold_ms": THRESHOLDS.get(module['module_name']),
            "culprit_sub_functions": culprit_functions
        })

    return final_report

# def generate_report_from_problematic_modules(problem_modules: list) -> dict:
#     """
#     使用无监督异常检测算法，分析并标记可优化的子函数。
#     """
#     final_report = {"problem_modules": []}
#     print("\n--- 为超标模块生成详细分析报告 (无监督异常检测算法) ---")
#     print(problem_modules)
#
#     for module in problem_modules:
#         culprit_functions = {}
#         sub_functions = module['sub_functions']
#         print(sub_functions)
#
#         # 过滤掉无效数据，只保留用于统计的有效函数
#         valid_subs_df = pd.DataFrame([s for s in sub_functions if s.get('avg', 0) > 0.01])
#
#         if valid_subs_df.empty:
#             final_report["problem_modules"].append({
#                 "module_name": module['module_name'], "average_ms": round(module['stats']['avg'], 3),
#                 "threshold_ms": THRESHOLDS.get(module['module_name']), "culprit_sub_functions": []
#             })
#             continue
#
#         # --- 计算统计基准 ---
#         # 1. 针对 avg
#         avg_mean = valid_subs_df['avg'].mean()
#         avg_std = valid_subs_df['avg'].std()
#         avg_sum = valid_subs_df['avg'].sum()
#
#         # 2. 针对 max
#         max_mean = valid_subs_df['max'].mean()
#         max_std = valid_subs_df['max'].std()
#         print(valid_subs_df)
#
#         # --- 遍历并应用规则 ---
#         for index, sub in valid_subs_df.iterrows():
#             event_name = sub['Event']
#             problem_tags = []
#
#             # --- 异常检测规则 ---
#             # 规则 A: 稳定高耗时 (avg)
#             if sub['avg'] > avg_mean + (Z_SCORE_K * avg_std):
#                 problem_tags.append("High_Avg_Cost(Statistical_Outlier)")
#             if avg_sum > 0 and (sub['avg'] / avg_sum) > MAJOR_CONTRIBUTOR_THRESHOLD:
#                 problem_tags.append("High_Avg_Cost(Major_Contributor)")
#
#             # 规则 B: 卡顿尖峰 (max)
#             if sub['max'] > max_mean + (Z_SCORE_K * max_std):
#                 problem_tags.append("Spike_Max(Statistical_Outlier)")
#             if sub['avg'] > 0 and (sub['max'] / sub['avg']) > SPIKE_RATIO:
#                 problem_tags.append("Spike_Max(High_Internal_Volatility)")
#
#             if problem_tags:
#                 if event_name not in culprit_functions:
#                     culprit_functions[event_name] = {
#                         "event": event_name, "avg_ms": round(sub['avg'], 3),
#                         "max_ms": round(sub['max'], 3), "problem_tags": []
#                     }
#                 culprit_functions[event_name]["problem_tags"].extend(problem_tags)
#
#         # 整理输出
#         final_culprits = list(culprit_functions.values())
#         for func in final_culprits:
#             func['problem_tags'] = sorted(list(set(func['problem_tags'])))
#
#         final_report["problem_modules"].append({
#             "module_name": module['module_name'],
#             "average_ms": round(module['stats']['avg'], 3),
#             "threshold_ms": THRESHOLDS.get(module['module_name']),
#             "culprit_sub_functions": final_culprits
#         })
#
#     return final_report
#

# ... (main 函数和其它辅助函数保持不变，只需替换上面的函数，并确保导入numpy) ...
# 注意: 确保你已经 `pip install numpy`


def main():
    print(f"正在从 '{CSV_INPUT_FILE}' 读取性能数据...")
    try:
        full_df = pd.read_csv(CSV_INPUT_FILE, index_col=0)
        full_df = clean_and_prepare_dataframe(full_df)
        print(full_df)
    except FileNotFoundError:
        print(f"错误: 找不到文件 {CSV_INPUT_FILE}")
        return
    except Exception as e:
        print(f"读取或处理CSV时出错: {e}")
        return
    gatekeeper_row = full_df[full_df['Event'] == GATEKEEPER_EVENT_NAME]
    if gatekeeper_row.empty:
        print(f"错误: 在文件中未找到门禁事件 '{GATEKEEPER_EVENT_NAME}'。无法继续分析。")
        return
    game_engine_avg = gatekeeper_row.iloc[0]['avg']
    print(f"\n--- 性能门禁检查 ---")
    print(f"事件 '{GATEKEEPER_EVENT_NAME}' 的平均耗时: {game_engine_avg:.3f}ms")
    print(f"设定的阈值: {GAME_ENGINE_TICK_THRESHOLD:.3f}ms")
    if game_engine_avg <= GAME_ENGINE_TICK_THRESHOLD:
        print("\n[✓] 性能正常: GameThread 总耗时在阈值范围内，无需进行详细模块分析。")
        return
    else:
        print(f"\n[!] 性能警告: GameThread 总耗时超标，将开始进行详细分析...")
    gatekeeper_index_pos = gatekeeper_row.index[0]
    df_for_analysis = full_df.iloc[:gatekeeper_index_pos]
    problem_modules = find_problematic_modules(df_for_analysis, THRESHOLDS)
    if not problem_modules:
        print("\n[✓] 扫描完成，虽然总耗时超标，但没有发现具体模块超过其独立阈值。")
        return
    analysis_report = generate_report_from_problematic_modules(problem_modules)
    try:
        with open(JSON_OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(analysis_report, f, ensure_ascii=False, indent=4)
        print(f"\n分析报告已成功保存到 '{JSON_OUTPUT_FILE}'")
    except IOError as e:
        print(f"错误: 无法写入文件 {JSON_OUTPUT_FILE}。错误信息: {e}")

if __name__ == '__main__':
    main()
#
# def generate_report_from_problematic_modules(problem_modules: list) -> dict:
#     """
#     对已筛选出的问题模块进行Top-K分析并生成最终报告。
#     """
#     final_report = {"problem_modules": []}
#
#     print("\n--- 为超标模块生成详细报告 ---")
#
#     for module in problem_modules:
#         # 使用pandas对子函数进行排序和筛选
#         sub_df = pd.DataFrame(module['sub_functions'])
#         culprits = []
#         if not sub_df.empty:
#             meaningful_subs = sub_df[sub_df['avg'] > 0.1].copy()
#             top_contributors = meaningful_subs.sort_values(by='avg', ascending=False).head(TOP_K_SUB_FUNCTIONS)
#             culprits = top_contributors.to_dict('records')
#
#         final_report["problem_modules"].append({
#             "module_name": module['module_name'],
#             "average_ms": round(module['stats']['avg'], 3),
#             "threshold_ms": THRESHOLDS.get(module['module_name']),
#             "culprit_sub_functions": culprits
#         })
#
#     return final_report
#

# def main():
#     """主执行函数，集成所有新规则。"""
#     print(f"正在从 '{CSV_INPUT_FILE}' 读取性能数据...")
#     try:
#         full_df = pd.read_csv(CSV_INPUT_FILE, index_col=0)
#         full_df = clean_and_prepare_dataframe(full_df)
#     except FileNotFoundError:
#         print(f"错误: 找不到文件 {CSV_INPUT_FILE}")
#         return
#
#     # --- 门禁检查 ---
#     gatekeeper_row = full_df[full_df['Event'] == GATEKEEPER_EVENT_NAME]
#     if gatekeeper_row.empty:
#         print(f"错误: 在文件中未找到门禁事件 '{GATEKEEPER_EVENT_NAME}'。无法继续分析。")
#         return
#
#     game_engine_avg = gatekeeper_row.iloc[0]['avg']
#     print(f"\n--- 性能门禁检查 ---")
#     print(f"事件 '{GATEKEEPER_EVENT_NAME}' 的平均耗时: {game_engine_avg:.3f}ms")
#     print(f"设定的阈值: {GAME_ENGINE_TICK_THRESHOLD:.3f}ms")
#
#     if game_engine_avg <= GAME_ENGINE_TICK_THRESHOLD:
#         print("\n[✓] 性能正常: GameThread 总耗时在阈值范围内，无需进行详细模块分析。")
#         return
#     else:
#         print(f"\n[!] 性能警告: GameThread 总耗时超标，将开始进行详细分析...")
#
#     # --- 数据准备和分析 ---
#     gatekeeper_index_pos = full_df.index.get_loc(gatekeeper_row.index[0])
#     df_for_analysis = full_df.iloc[:gatekeeper_index_pos]
#
#     problem_modules = find_problematic_modules(df_for_analysis, THRESHOLDS)
#
#     if not problem_modules:
#         print("\n[✓] 扫描完成，没有发现耗时超过阈值的模块。")
#         return
#
#     analysis_report = generate_report_from_problematic_modules(problem_modules)
#
#     # 保存到JSON文件
#     try:
#         with open(JSON_OUTPUT_FILE, 'w', encoding='utf-8') as f:
#             json.dump(analysis_report, f, ensure_ascii=False, indent=4)
#         print(f"\n分析报告已成功保存到 '{JSON_OUTPUT_FILE}'")
#     except IOError as e:
#         print(f"错误: 无法写入文件 {JSON_OUTPUT_FILE}。错误信息: {e}")
#
#
# if __name__ == '__main__':
#     main()