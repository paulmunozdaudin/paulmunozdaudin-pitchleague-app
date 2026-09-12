"""Quantitative match-prediction engine, deliberately separate from the
odds providers (`app.services.odds_providers`) and from the web layer.

Nothing in here talks to FastAPI, SQLAlchemy sessions from requests, or the
frontend. It takes real historical matches in, produces calibrated
probabilities out, and is validated entirely by backtesting — see
docs/ARCHITECTURE.md#model-engine for the full design and
docs/DATA_SOURCES.md for where the training data comes from.
"""
