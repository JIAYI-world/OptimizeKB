### lua-gc各个阶段

- GCSpause 暂停阶段,默认初始阶段
    
- GCSpropagate 传播阶段 可打断 开始标记存活对象
    
- GCSatomic 原子阶段 标记的最后阶段 不可打断
    
- GCSswpallgc 开始清理阶段,可打断 清理常规的白色对象
    
- GCSswpfinobj 清理finobj链表阶段, 可打断
    
- GCSswptobefnz 清理tobefnz链条阶段 可打断
    
- GCSswpend 清理结束阶段 不可打断
    
- GCScallfin 调用析构函数阶段 可打断
    

目前主要大头在用清理常规的白色阶段,即 GCSswpallgc 本质上还是lua-gc被标记的对象过多导致峰值问题

开始标记传播阶段 GCSpropagate 可通过收束lua-gc的对象来解决

### collectgarbage参数说明

pause

作用：控制两次完整 GC 周期之间的“空闲间隔”  
值越大，GC 触发频率越低（内存使用可能更高）  
默认值：200（表示 GC 在内存增长 200% 后触发新周期）  
stepmul

作用：定义每次增量步骤的工作量，影响单次 GC 的回收速度  
值越大，单次回收处理的内存越多，但可能导致程序卡顿  
默认值：200（单位是百分比，200% 表示每次处理内存量的 2 倍