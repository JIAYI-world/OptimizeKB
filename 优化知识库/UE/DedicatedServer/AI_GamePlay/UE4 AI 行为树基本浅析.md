## **前言**

经沟通了解目前项目的AI采用的默认UE的行为树的方案.本文是基于官方行为树的一些概念的讲解,具体比较详细的操作步骤就得看看官方教程,比如写的详细多了,后面再拿到工程会以工程的可复用的流程和工作模式为主

(这几天时间,一天赶路一天老家走亲戚,文档比较粗糙,忘见谅)

## 名词概念

1. BehaviorTree 简称BT,主要用于处理行为树的各种流水线的逻辑关系
   
2. Blackboard(黑板报) 类似于键值对 所有自定义类型的基类都是object,一种数据集中式的设计模式,一般用于多模块之间的数据共享.
   
3. EQS (Environment Query System),环境查询系统,可以理解成对当前场景状态的扫描或者检查,往往配合AI行为树一起使用
   

## 基本目标方案

1. 将一些复用性比较高的逻辑封装成C++代码,防止蓝图逻辑过于复杂,冗余过大
   
2. 在官方的节点基础上再次进行二次封装(lua或C++),将部分参数变的更简单易用
   

## 其他细分节点

在内容面板中右键点击 人工智能/行为树节点

创建完成之后双击打开,进入行为树的编辑界面,默认进去会看到一个Root节点

还需要创建黑板值,黑板

将Root节点下来会出现三个选项

1. Selector 选择合成节点
   
2. Sequence 顺序执行节点
   
3. Simple Parallel 并行行为节点(有一个主事件+一个后台运行的其他事件)
![](C:\Users\36265\Desktop\个人-汇报\OptimizeKB\优化知识库\Pasted image 20250703220954.png)
每个拖出来的节点都可添加装饰器,这个概念类似于修饰当前节点一些逻辑行为

更详细的操作步骤大家看下面的引用资料

## 引用其他资料

1. https://zhuanlan.zhihu.com/p/139514376
   
2. https://zhuanlan.zhihu.com/p/143298443
   
3. https://docs.unrealengine.com/4.27/zh-CN/InteractiveExperiences/ArtificialIntelligence/EQS/
   
4. https://www.bilibili.com/read/cv8219823/