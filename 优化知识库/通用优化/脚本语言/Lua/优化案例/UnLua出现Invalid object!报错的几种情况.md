### 0.前言

大家经常会遇到Unlua报Invalid object!等等

下面举例说明下如果出现的

### 1.LogUnLua: Error: !!! NULL target object for UFunction 'XXXXFunction'! Check the usage of ':' and '.'!

这种case就会出现类似的报错

LogUnLua: Error: !!! NULL target object for UFunction 'GetBounds'! Check the usage of ':' and '.'!

切记对象被Destroy之后记得置空,尽量将对象收束到一个地方,方便进行声明周期的管理

### 2.LogUnLua: UObject_IsValid: Invalid object!

- 对已经Destroy的对象进行IsValid的判断会触发
    

- 对已经Destroy的对象进行属性的访问会触发
    

这种case就会触发Unlua的保护性措施打印log

和上面一样,大家也得对自己的对象负责

### 3.推荐使用方式

**推荐使用_SP.IsValid，避免无谓的nil对象透传至C++**

**这个函数仅适合对UObject对象进行使用**

可修改源代码方便进行lua的堆栈确认或者添加断点,然后打印输出下GetLuaCallStack(L)等等

### 总结

- 核心原因就是lua中存储的对象的UObject已经被GC了或者被Destroy掉但是Lua还持有着,当你想要对这个对象进行操作,比如调用这个对象的函数就是出现如上报错
    
- C++中ActorA持有ActorB的时候建议通过**TWeakObjectPtr<ActorB>**的方式进行存储,这个获取到对象,,lua中通过方法的形式进行调用获取,无需进行是否指针已经野了的判断,即可可放心使用
    
- lua中自有的组件或者单位存储其他模块组件或者单位一定要小心生命周期等问题,如果求稳可采用存储ID的方式,用到对象到对应Mgr中Get想要的单位等等方式