# -*- coding: utf-8 -*-
from app import create_app

app = create_app()

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", "5000"))
    debug = os.environ.get("FEIXU_DEBUG", "1") == "1"
    # 默认开启热重载(改代码自动生效)；后台启动时设 FEIXU_NORELOAD=1 避免孤儿进程
    reloader = debug and os.environ.get("FEIXU_NORELOAD") != "1"
    app.run(host="0.0.0.0", port=port, debug=debug, use_reloader=reloader)
