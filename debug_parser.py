
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

from app.assistants.parser import parse_address
from app.core import settings

print(f"ZHIPU_API_KEY: {settings.ZHIPU_API_KEY[:5]}***")
print(f"LLM_BASE_URL: {settings.LLM_BASE_URL}")

result = parse_address("浙江省杭州市余杭区五常街道文一西路969号")
print(f"Status: {result.get('status')}")
if result.get('status') == 'error':
    print(f"Error Message: {result.get('error_message')}")
else:
    print(result.get('data'))
