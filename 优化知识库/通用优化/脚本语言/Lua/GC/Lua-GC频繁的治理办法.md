#### Table

- 非必要不创建临时的table
    
- 尽量使Table可复用,Array的模式最佳,可通过Remove的方式移除element
    
- 针对大量对象,业务可采用对象池的方式进行复用(只能针对业务具体分析)
    
- 固定长度的table,可使用元梦的特性,创建table可指定table长度,CreateFixedTable

#### Function

- 尽量少使用匿名函数,闭包的模式,对gc影响很大,尽量用预定好的函数
    

#### UserData

- 针对简答使用的的FVector尽量用 SP_GetActorLocationFast()类似返回xyz的接口代替
    
- 针对特定场景,可预先创建好FVector,然后每次更新直接刷新预创建好的FVector的内容,减少UserData的创建
    

#### String

- 尽量用table.concat()代替 … 的方式拼接字符串
    
- 针对debug信息,可省掉文件描述头,直接输出value,可大量减少string的拼接