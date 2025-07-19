FROM python:3.14-rc-bookworm

RUN pip install --upgrade pip

WORKDIR /app

COPY requirements.txt .

#Display print when called
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

#local reauirements
RUN pip install --no-cache-dir -r requirements.txt

COPY src/dima_otk ./dima_otk
COPY ontologies ./ontologies

ENTRYPOINT ["python", "-m", "dima_otk.cli"]
