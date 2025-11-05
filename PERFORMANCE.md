# 性能优化指南

## 📊 性能基准

### 当前性能指标
- **处理速度**: ~50MB/分钟（单线程）
- **内存占用**: <2GB（100MB文件）
- **CPU使用率**: 单核~80%
- **脱敏准确率**: >95%

## 🚀 优化策略

### 1. 并行处理优化

#### 多进程处理
```python
from multiprocessing import Pool, cpu_count

class ParallelPreProcessor:
    def __init__(self, num_workers=None):
        self.num_workers = num_workers or cpu_count()
    
    def process_files_parallel(self, file_list):
        with Pool(self.num_workers) as pool:
            results = pool.map(self.process_single_file, file_list)
        return results
```

**配置建议**：
```yaml
performance:
  parallel_processing: true
  num_workers: 4  # 根据CPU核心数调整
  batch_size: 10
```

### 2. 内存优化

#### 流式处理大文件
```python
def process_large_file_streaming(file_path, chunk_size=1024*1024):
    """流式处理大文件，减少内存占用"""
    with open(file_path, 'r', encoding='utf-8') as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            # 处理块
            yield process_chunk(chunk)
```

#### 内存映射
```python
import mmap

def process_with_mmap(file_path):
    """使用内存映射处理大文件"""
    with open(file_path, 'r+b') as f:
        with mmap.mmap(f.fileno(), 0) as mmapped_file:
            # 直接操作映射的内存
            content = mmapped_file.read()
            return process_content(content)
```

### 3. 缓存优化

#### LRU缓存
```python
from functools import lru_cache

@lru_cache(maxsize=128)
def compile_pattern(pattern_str):
    """缓存编译的正则表达式"""
    return re.compile(pattern_str)

class CachedDesensitizer:
    def __init__(self):
        self.cache = {}
    
    @lru_cache(maxsize=1000)
    def desensitize_value(self, value, rule_type):
        """缓存脱敏结果"""
        return self._apply_rule(value, rule_type)
```

#### Redis缓存（分布式场景）
```python
import redis
import json

class RedisCache:
    def __init__(self):
        self.redis_client = redis.Redis(
            host='localhost',
            port=6379,
            decode_responses=True
        )
    
    def get_or_compute(self, key, compute_func):
        # 尝试从缓存获取
        cached = self.redis_client.get(key)
        if cached:
            return json.loads(cached)
        
        # 计算并缓存
        result = compute_func()
        self.redis_client.setex(
            key, 
            3600,  # TTL: 1小时
            json.dumps(result)
        )
        return result
```

### 4. 算法优化

#### 批量正则匹配
```python
import re

class OptimizedMatcher:
    def __init__(self, patterns):
        # 合并多个模式为一个
        self.combined_pattern = re.compile(
            '|'.join(f'(?P<{name}>{pattern})' 
                    for name, pattern in patterns.items())
        )
    
    def match_all(self, text):
        """一次匹配多个模式"""
        matches = {}
        for match in self.combined_pattern.finditer(text):
            for name, value in match.groupdict().items():
                if value:
                    if name not in matches:
                        matches[name] = []
                    matches[name].append(value)
        return matches
```

#### 使用Aho-Corasick算法进行多模式匹配
```python
import pyahocorasick

class FastKeywordMatcher:
    def __init__(self, keywords):
        self.automaton = pyahocorasick.Automaton()
        for idx, key in enumerate(keywords):
            self.automaton.add_word(key, (idx, key))
        self.automaton.make_automaton()
    
    def find_all(self, text):
        """快速查找所有关键词"""
        matches = []
        for end_index, (idx, keyword) in self.automaton.iter(text):
            start_index = end_index - len(keyword) + 1
            matches.append((keyword, start_index, end_index))
        return matches
```

### 5. I/O优化

#### 异步I/O
```python
import asyncio
import aiofiles

async def process_file_async(file_path):
    """异步文件处理"""
    async with aiofiles.open(file_path, 'r') as f:
        content = await f.read()
        # 异步处理
        result = await process_content_async(content)
        return result

async def process_multiple_files(file_paths):
    """并发处理多个文件"""
    tasks = [process_file_async(fp) for fp in file_paths]
    results = await asyncio.gather(*tasks)
    return results
```

#### 批量写入
```python
class BatchWriter:
    def __init__(self, batch_size=1000):
        self.batch_size = batch_size
        self.buffer = []
    
    def write(self, data):
        self.buffer.append(data)
        if len(self.buffer) >= self.batch_size:
            self.flush()
    
    def flush(self):
        if self.buffer:
            # 批量写入
            with open(self.output_file, 'a') as f:
                f.write('\n'.join(self.buffer))
            self.buffer = []
```

### 6. 数据库优化（如果使用）

#### 连接池
```python
from contextlib import contextmanager
import sqlite3
from queue import Queue

class ConnectionPool:
    def __init__(self, db_path, max_connections=10):
        self.db_path = db_path
        self.pool = Queue(maxsize=max_connections)
        for _ in range(max_connections):
            conn = sqlite3.connect(db_path)
            self.pool.put(conn)
    
    @contextmanager
    def get_connection(self):
        conn = self.pool.get()
        try:
            yield conn
        finally:
            self.pool.put(conn)
```

#### 批量插入
```python
def batch_insert(data_list, batch_size=1000):
    """批量插入数据"""
    with connection_pool.get_connection() as conn:
        cursor = conn.cursor()
        for i in range(0, len(data_list), batch_size):
            batch = data_list[i:i+batch_size]
            cursor.executemany(
                "INSERT INTO configs VALUES (?, ?, ?)",
                batch
            )
        conn.commit()
```

### 7. 分布式处理

#### 使用Celery进行任务队列
```python
from celery import Celery

app = Celery('config_processor', 
             broker='redis://localhost:6379',
             backend='redis://localhost:6379')

@app.task
def process_config_task(file_path):
    """异步处理任务"""
    processor = ConfigPreProcessor()
    return processor.process_file(file_path)

# 使用
from celery import group

def process_files_distributed(file_paths):
    """分布式处理多个文件"""
    job = group(
        process_config_task.s(fp) for fp in file_paths
    )
    result = job.apply_async()
    return result.get()
```

## 📈 性能监控

### 性能分析工具
```python
import cProfile
import pstats
from memory_profiler import profile

# CPU性能分析
def profile_cpu():
    profiler = cProfile.Profile()
    profiler.enable()
    
    # 执行代码
    process_file("large_config.txt")
    
    profiler.disable()
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(20)

# 内存分析
@profile
def process_with_memory_profile(file_path):
    processor = ConfigPreProcessor()
    return processor.process_file(file_path)
```

### 实时监控
```python
import psutil
import time

class PerformanceMonitor:
    def __init__(self):
        self.process = psutil.Process()
    
    def monitor(self, interval=1):
        while True:
            cpu_percent = self.process.cpu_percent()
            memory_info = self.process.memory_info()
            
            print(f"CPU: {cpu_percent}%")
            print(f"Memory: {memory_info.rss / 1024 / 1024:.2f} MB")
            
            time.sleep(interval)
```

## 🎯 优化建议

### 根据文件大小选择策略

| 文件大小 | 推荐策略 |
|---------|---------|
| < 10MB  | 单线程处理 |
| 10-100MB | 多线程/流式处理 |
| 100MB-1GB | 内存映射/分块处理 |
| > 1GB | 分布式处理 |

### 根据场景优化

#### 实时处理场景
- 使用缓存减少重复计算
- 启用并行处理
- 优化正则表达式

#### 批量处理场景
- 使用异步I/O
- 批量写入结果
- 分布式任务队列

#### 内存受限场景
- 使用流式处理
- 减小块大小
- 及时释放内存

## 🔧 调优参数

### config.yaml优化配置
```yaml
performance:
  # 并行处理
  parallel_processing: true
  num_workers: 8
  
  # 内存管理
  max_memory_mb: 4096
  chunk_size_kb: 2048
  
  # 缓存设置
  cache_enabled: true
  cache_size: 1000
  cache_ttl: 3600
  
  # I/O优化
  batch_write_size: 1000
  async_io: true
  
  # 正则优化
  compile_patterns: true
  pattern_cache_size: 100
```

### 系统级优化

#### Linux内核参数
```bash
# 增加文件描述符限制
ulimit -n 65535

# 调整内存参数
echo 1 > /proc/sys/vm/swappiness
echo 3 > /proc/sys/vm/drop_caches

# TCP优化
sysctl -w net.core.somaxconn=1024
sysctl -w net.ipv4.tcp_max_syn_backlog=1024
```

#### Python GC调优
```python
import gc

# 调整垃圾回收阈值
gc.set_threshold(700, 10, 10)

# 在处理大文件前禁用GC
gc.disable()
process_large_file()
gc.enable()
```

## 📊 性能测试

### 基准测试脚本
```python
import time
import os
from statistics import mean, stdev

def benchmark(file_path, iterations=10):
    """运行基准测试"""
    times = []
    
    for i in range(iterations):
        start = time.time()
        process_file(file_path)
        elapsed = time.time() - start
        times.append(elapsed)
        
        print(f"Iteration {i+1}: {elapsed:.2f}s")
    
    file_size_mb = os.path.getsize(file_path) / (1024*1024)
    avg_time = mean(times)
    std_dev = stdev(times) if len(times) > 1 else 0
    throughput = file_size_mb / avg_time
    
    print(f"\n基准测试结果:")
    print(f"文件大小: {file_size_mb:.2f} MB")
    print(f"平均时间: {avg_time:.2f}s ± {std_dev:.2f}s")
    print(f"吞吐量: {throughput:.2f} MB/s")
```

## 🎯 优化目标

### 短期目标（1个月）
- 处理速度提升至 100MB/分钟
- 内存占用降低 30%
- 支持 500MB 文件流畅处理

### 中期目标（3个月）
- 处理速度达到 200MB/分钟
- 支持分布式处理
- 实现智能缓存机制

### 长期目标（6个月）
- 处理速度达到 500MB/分钟
- 支持 10GB+ 超大文件
- 实现自适应性能优化

## 📝 优化检查清单

- [ ] 启用并行处理
- [ ] 实施缓存机制
- [ ] 优化正则表达式
- [ ] 使用批量I/O
- [ ] 配置内存限制
- [ ] 启用性能监控
- [ ] 定期性能测试
- [ ] 优化数据结构
- [ ] 减少内存复制
- [ ] 使用性能分析工具

---

通过以上优化策略，可以显著提升配置预处理模块的性能。建议根据实际使用场景和资源情况，逐步实施相应的优化措施。
