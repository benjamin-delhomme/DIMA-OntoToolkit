# dima_otk/utils/gpt_client.py

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

"""
gpt_client.py

Utility for calling the OpenAI Chat API.
"""

import os
import requests


BASE_URL = "https://api.openai.com/v1/chat/completions"
GPT_API_KEY = os.getenv("OPENAI_API_KEY")

if not GPT_API_KEY:
    raise EnvironmentError("❌ OPENAI_API_KEY is not set. Please check your .env file.")

print("[DEBUG] GPT_API_KEY loaded")

def call_gpt(messages, temperature=0.3, model="gpt-4o", disable_cache=False):
    """
    Call OpenAI GPT model with structured chat messages.

    Args:
        messages (list): List of {"role": "user|system|assistant", "content": "..."} dicts
        temperature (float): Sampling temperature
        model (str): OpenAI model ID (e.g., "gpt-4o")
        disable_cache (bool): Add Cache-Control header if True

    Returns:
        str: GPT response content
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {GPT_API_KEY}"
    }

    if disable_cache:
        headers["Cache-Control"] = "no-cache"

    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature
    }

    response = requests.post(BASE_URL, headers=headers, json=payload)

    if response.status_code != 200:
        raise Exception(f"OpenAI API Error {response.status_code}: {response.text}")

    return response.json()["choices"][0]["message"]["content"].strip()
