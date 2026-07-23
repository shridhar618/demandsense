FROM python:3.11-slim

# build-essential + curl needed for cmdstanpy's CmdStan compilation (Prophet backend)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-build the CmdStan backend at image build time so container startup is fast
RUN python -m cmdstanpy.install_cmdstan --cores 4
ENV CMDSTAN=/root/.cmdstan/cmdstan-2.39.0

# The prophet wheel ships a stripped bundled CmdStan dir with no Makefile,
# which cmdstanpy's path validation rejects. Removing it forces prophet to
# use the fully-built CMDSTAN path above instead. See app/ml/prophet_model.py.
RUN rm -rf /usr/local/lib/python3.11/site-packages/prophet/stan_model/cmdstan-2.33.1 2>/dev/null || true

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
