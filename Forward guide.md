### 以docker-compose启动

- Compose file: docker/docker-compose.yml
- Services:
  - main: 主后端 port7860
  - runner1: 分后端 port7861
  - nginx: nginx负载均衡 port8080
  - postgres: PostgreSQL数据库 5432

环境变量:

- FORWARD_FLOW=true: 设置转发
- FORWARD_FLOW_URL=http://localhost:8080: Nginx endpoint
- FORWARD_FLOW_STRATEGY=forward: 两种转发逻辑
  - forward： 代理请求，利用forward_flow_request
  - redirect：HTTP307，利用RedirectResponse


启动:

```bash
docker compose -f docker/docker-compose.yml up -d --build
```



### Benchmar Docker

Python script: docker/benchmark_docker.py

* 新建简易flow（e.g. 只由chat input和chat output构成）

* 在benchmark_docker.py中benchmark添加flow_id

  ```python
  async def benchmark(self, flow_id="d3f20939-c3a3-4003-80a6-c6777334a4be"):
  ```

* 运行

  ```sh
  cd docker
  python benchmark_docker.py
  ```

  

### 测试Streaming

Python script: test_streaming.py

* 新建流式传输flow（e.g. Basic Prompting）

* 运行

  ```sh
  python test_streaming.py
  ```

* 输入flow_id



### 测试OpenAI‑Compatible api

Python script: test_openai_endpoint.py

POST /api/v1/openai_run_flow/{flow_id}

* 新建flow

* 运行

  ```sh
  python test_openai_endpoint.py
  ```

* 输入flow_id

