FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /srv

COPY pyproject.toml constraints.txt ./
COPY app ./app
RUN pip install --no-cache-dir -c constraints.txt .

# /data and /vault are created owned by the app user so a fresh named volume inherits it
RUN useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin kairos \
    && mkdir /data /vault \
    && chown kairos /data /vault
USER kairos

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
