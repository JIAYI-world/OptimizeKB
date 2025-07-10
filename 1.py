import pandas as pd
file_name=r"C:\Users\36265\Desktop\个人-汇报\OptimizeKB\top_data\file\profiler_data.csv"
pd.set_option('display.max_columns', None)
df = pd.read_csv(file_name, engine='python')
# df = pd.read_csv('Profile(20250709_154120).csv')
print("成功读取文件！")
print(df.head())  # 打印前几行看看数据是否正常