---
# 通用设置
common:
  # 日志等级，可选 ["debug", "info", "warning", "error"]
  loggingLevel: debug
  # 是否将 GPT4 的令牌用于 GPT3.5 的请求
  gpt.degradeBackend: false
  # API类型，offapi为官方API,unoffapi为模拟网页操作
  gpt.apiType: offical
  # 代理设置
  proxies:
    # 代理地址
  - address: socks5://127.0.0.1:10818
    # 用户名（可选）
    # username: foo
    # 密码（可选）
    # password: bar
  # 字典
  dictionary:
    # 通用预处理字典
    preDict:
    - foo
    - bar
    # 通用后处理字典
    postDict:
    - foo
    - bar
    # GPT 字典
    gpt.dict:
    - foo
    - bar
# 与翻译后端所特定的设置
backendSpecific:
  GPT35:    # GPT3.5 官方 API
    token:  # 令牌
    - token: sk-xxxxxxxx    # 你的令牌
      # endpoint: ''  # 令牌所对应的 API 端点，一般不需要设置
    - token: sk-yyyyyyyy
      endpoint: ''
    defaultEndpoint: https://api.openai.com # 默认 API 端点，不知道别修改
  GPT4: # GPT4 官方 API
    token:
    - token: sk-xxxxxxxx
      endpoint: ''
    - token: sk-yyyyyyyy
      endpoint: ''
    defaultEndpoint: https://api.openai.com
  ChatGPT:  # ChatGPT / GPT3.5(4) 非官方 API
    ak: xxxxxxxx
  # newBing: 
