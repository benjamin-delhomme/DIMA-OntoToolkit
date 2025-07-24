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

from typing import List, Dict

from dima_otk.bias_analysis.detect.detect_logic import get_detect_techniques
from dima_otk.bias_analysis.inform.inform_logic import get_inform_techniques
from dima_otk.bias_analysis.memorise.memorise_logic import get_memorise_techniques
from dima_otk.bias_analysis.act.act_logic import get_act_techniques

def print_phase_result(phase_name, results_dict):
        found = [k for k, v in results_dict.items() if v]  # Technique names with non-empty result
        if found:
            print(f"[INFO] {len(found)} {phase_name} technique(s) found: {', '.join(found)}")
        else:
            print(f"[INFO] No {phase_name} techniques found.")

def get_biases_from_article(processed_article: dict) -> dict:

    detect = get_detect_techniques(processed_article)
    inform = get_inform_techniques(processed_article)
    memorise = get_memorise_techniques(processed_article)
    act = get_act_techniques(processed_article)

    print_phase_result("Detect", detect)
    print_phase_result("Inform", inform)
    print_phase_result("Memorise", memorise)
    print_phase_result("Act", act)

    return {
        "Detect": detect,
        "Inform": inform,
        "Memorise": memorise,
        "Act": act,
    }
