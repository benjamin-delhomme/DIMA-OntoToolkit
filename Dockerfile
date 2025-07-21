# Copyright 2025 Benjamin Delhomme, NATO Strategic Communications Centre of Excellence
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

FROM python:3.14-rc-bookworm

RUN pip install --upgrade pip

# Install Java (needed for HermiT reasoner)
RUN apt-get update && \
    apt-get install -y default-jre && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

#Display print when called
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

#local reauirements
RUN pip install --no-cache-dir -r requirements.txt

COPY src/dima_otk ./dima_otk
COPY ontologies ./ontologies

# copy all licences into the image
COPY LICENSE ./licenses/
COPY licenses/ ./licenses/

ENTRYPOINT ["python", "-m", "dima_otk.cli"]
