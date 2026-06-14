# -*- coding: utf-8 -*-
from app import create_app

app = create_app()

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", "5000"))
    debug = os.environ.get("FEIXU_DEBUG", "1") == "1"
    # use_reloader 默认关闭，避免后台启动时产生孤儿子进程
    app.run(host="0.0.0.0", port=port, debug=debug, use_reloader=False)
