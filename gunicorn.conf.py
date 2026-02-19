"""Gunicorn production configuration for BD_StockEvaluator."""

bind = "0.0.0.0:8000"
workers = 2
worker_class = "uvicorn.workers.UvicornWorker"
timeout = 120
accesslog = "-"
errorlog = "-"
loglevel = "info"
