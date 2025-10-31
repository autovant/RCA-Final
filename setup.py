"""Setup configuration for RCA Engine."""

from setuptools import setup, find_packages

setup(
    name="rca-engine",
    version="1.0.0",
    description="Root Cause Analysis Engine with LLM Integration",
    author="RCA Team",
    packages=find_packages(exclude=["tests", "tests.*"]),
    python_requires=">=3.11",
    install_requires=[
        "fastapi>=0.104.1",
        "uvicorn[standard]>=0.24.0",
        "pydantic>=2.5.0",
        "pydantic-settings>=2.1.0",
        "sqlalchemy>=2.0.23",
        "asyncpg>=0.29.0",
        "alembic>=1.13.0",
        "pgvector>=0.2.4",
        "python-jose[cryptography]>=3.3.0",
        "passlib[bcrypt]>=1.7.4",
        "python-multipart>=0.0.6",
        "httpx>=0.25.2",
        "aiofiles>=23.2.1",
        "redis>=5.0.1",
        "prometheus-client>=0.19.0",
        "structlog>=23.2.0",
        "python-magic>=0.4.27",
        "chardet>=5.2.0",
        "ollama>=0.1.7",
        "openai>=1.3.8",
        "anthropic>=0.7.8",
        "boto3>=1.34.0",
        "numpy>=1.26.2",
        "python-dotenv>=1.0.0",
        "click>=8.1.7",
        "jinja2>=3.1.2",
        "pyyaml>=6.0.1",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.3",
            "pytest-asyncio>=0.21.1",
            "pytest-cov>=4.1.0",
            "black>=23.11.0",
            "isort>=5.12.0",
            "flake8>=6.1.0",
            "mypy>=1.7.1",
        ]
    },
    entry_points={
        "console_scripts": [
            "rca-engine=apps.api.main:main",
            "rca-file-watcher=core.watchers.runner:run_cli",
        ],
    },
)
