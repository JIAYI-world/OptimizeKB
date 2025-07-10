##### 1.一次Lua->C++调用链的举例

GameCharacter对象在lua中调用K2_GetActorLocation()等成员函数的调用链

Lua->C++的一次调用

GameCharacter IndexFind->MoeGameCharacter IndexFind->反射调用K2_GetActorLocation() ->压栈返回FVector->Lua读栈,构造FVector

- 当 GameCharacter或者MEGameCharacter成员过多,tablefind一次不小的消耗
    
    - 如果明确知道需要访问的函数是调用CPP的函数,可通过写静态函数的方法,比如static FVector GetMEActorLocation(AActor* Actor);的方式进行获取
        
    - 但是不利于大规模更改,可针对Tick级别的函数体进行改造
        
- 利用反射进行调用也是巨量的消耗
    
    - 关键常用函数可进行必要的静态导出,绕过Unlua调用UE的反射
        
    - 可大大减少反射带来的消耗,函数接口固定后,可进行批量替换
        
    - 无法避免大的table对象的IndexFind的消耗
        

##### 2.对于从CPP返回TArray进行遍历操作

大家看到防御性代码已经进行6次,每次都是一次穿梭,个别函数会有1ms以上的消耗,比如 IsValid()等等

如果这个容器超过10个,前面的这些防御性代码就会代码至少会带来10ms以上的消耗

在DS如果AI的单位超过20个,稍微计算下预计会达到20* 10ms 将近200ms消耗

所以针对这次调用,我们采用了如果静态绑定的操作,具体数据能提升到多少,还需要测试下

可将上述意义不大的防御性代码基本上0消耗

- 首先改造获取函数的至少四次次的CPP穿梭操作->1次
    
    - _SP.GetGameInfo->GetCurrentRoundGameInfo( _SP.GetCurrentWorld() )->GetAllPlayerInfos()->返回 Tarray()
        
    - 一次静态绑定的lua调用GetAllCharacter_Lua,直接new出来lua的table,将判断好的对象塞入table中
        
    - lua中遍历原生table的性能要远远大于Tarray的操作
        
    - 并将防御性措施提前在CPP中进行过滤掉,lua中放心的使用
        

|**对比测试**|**100次**|**1000次**|**1000次**|
|---|---|---|---|
|优化前|1.3ms|14.3ms|137.2ms|
|优化后|92.2us = 0.0922ms|3ms|39.5ms|
|profiler文件||||

##### 3.其他纯lua模式的优化

- 全局变量进行local化
    
- 大for循环尽量不访问全局变量,或者进行local化
    
- 等等等,这块资料很多,后期收集一波补充下
    

##### 4.项目组注意点

1. 能用Lua原生的数学库尽量用,比如 abs 等等

例子,测试下来有3-4倍左右的提升,这块还能更低,试着干掉UE的FVector

|**对比测试**|**100次**|**1000次**|**1000次**|
|---|---|---|---|
|优化前|336.7us|3.4ms|33ms|
|优化后|160.7us|1.6ms|15.8ms|
