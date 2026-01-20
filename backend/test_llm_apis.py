"""
LLM API Health Check Script
Tests all LLM APIs used in the rKYC codebase
Updated: 2026-01-20 - Using actual existing models
"""

import os
import sys
from dotenv import load_dotenv

# Force UTF-8 output
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()

print('='*60)
print('LLM API Health Check')
print('='*60)

results = []

# 1. Test Anthropic (Claude 3.5 Sonnet)
print('\n[1/5] Testing Anthropic (Claude 3.5 Sonnet)...')
try:
    import anthropic
    client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
    response = client.messages.create(
        model='claude-3-5-sonnet-20241022',
        max_tokens=50,
        messages=[{'role': 'user', 'content': 'Say hello in one word'}]
    )
    print(f'  [OK] SUCCESS: {response.content[0].text[:50]}')
    results.append(('Anthropic Claude 3.5 Sonnet', 'SUCCESS', None))
except Exception as e:
    error_str = str(e)
    if 'credit' in error_str.lower() or 'billing' in error_str.lower():
        status = 'CREDIT_ISSUE'
    elif 'invalid' in error_str.lower() and 'key' in error_str.lower():
        status = 'INVALID_KEY'
    elif 'not found' in error_str.lower() or '404' in error_str:
        status = 'MODEL_NOT_FOUND'
    else:
        status = 'ERROR'
    print(f'  [FAIL] {status}')
    results.append(('Anthropic Claude 3.5 Sonnet', status, error_str[:300]))

# 2. Test OpenAI (GPT-4o)
print('\n[2/5] Testing OpenAI (GPT-4o)...')
try:
    from openai import OpenAI
    oai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    response = oai_client.chat.completions.create(
        model='gpt-4o',
        max_tokens=50,
        messages=[{'role': 'user', 'content': 'Say hello in one word'}]
    )
    print(f'  [OK] SUCCESS: {response.choices[0].message.content[:50]}')
    results.append(('OpenAI GPT-4o', 'SUCCESS', None))
except Exception as e:
    error_str = str(e)
    if 'credit' in error_str.lower() or 'billing' in error_str.lower() or 'quota' in error_str.lower():
        status = 'CREDIT_ISSUE'
    elif 'invalid' in error_str.lower() and 'key' in error_str.lower():
        status = 'INVALID_KEY'
    elif 'not found' in error_str.lower() or '404' in error_str or 'does not exist' in error_str.lower():
        status = 'MODEL_NOT_FOUND'
    else:
        status = 'ERROR'
    print(f'  [FAIL] {status}')
    results.append(('OpenAI GPT-4o', status, error_str[:300]))

# 3. Test Google (Gemini 1.5 Pro)
print('\n[3/5] Testing Google (Gemini 1.5 Pro)...')
try:
    import google.generativeai as genai
    genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))
    model = genai.GenerativeModel('gemini-1.5-pro')
    response = model.generate_content('Say hello in one word')
    print(f'  [OK] SUCCESS: {response.text[:50]}')
    results.append(('Gemini 1.5 Pro', 'SUCCESS', None))
except ImportError:
    print('  [FAIL] PACKAGE_NOT_INSTALLED (google-generativeai)')
    results.append(('Gemini 1.5 Pro', 'PACKAGE_NOT_INSTALLED', 'pip install google-generativeai'))
except Exception as e:
    error_str = str(e)
    if 'not found' in error_str.lower() or '404' in error_str:
        status = 'MODEL_NOT_FOUND'
    elif 'invalid' in error_str.lower() and 'key' in error_str.lower():
        status = 'INVALID_KEY'
    elif 'api key' in error_str.lower():
        status = 'INVALID_KEY'
    else:
        status = 'ERROR'
    print(f'  [FAIL] {status}')
    results.append(('Gemini 1.5 Pro', status, error_str[:300]))

# 4. Test Perplexity (sonar-pro)
print('\n[4/5] Testing Perplexity (sonar-pro)...')
try:
    pplx_client = OpenAI(
        api_key=os.getenv('PERPLEXITY_API_KEY'),
        base_url='https://api.perplexity.ai'
    )
    response = pplx_client.chat.completions.create(
        model='sonar-pro',
        max_tokens=50,
        messages=[{'role': 'user', 'content': 'Say hello in one word'}]
    )
    print(f'  [OK] SUCCESS: {response.choices[0].message.content[:50]}')
    results.append(('Perplexity sonar-pro', 'SUCCESS', None))
except Exception as e:
    error_str = str(e)
    if 'credit' in error_str.lower() or 'billing' in error_str.lower() or 'quota' in error_str.lower():
        status = 'CREDIT_ISSUE'
    elif 'invalid' in error_str.lower() or 'unauthorized' in error_str.lower():
        status = 'INVALID_KEY'
    else:
        status = 'ERROR'
    print(f'  [FAIL] {status}')
    results.append(('Perplexity sonar-pro', status, error_str[:300]))

# 5. Test OpenAI Embedding
print('\n[5/5] Testing OpenAI Embedding (text-embedding-3-large)...')
try:
    response = oai_client.embeddings.create(
        model='text-embedding-3-large',
        input='Hello world',
        dimensions=2000
    )
    print(f'  [OK] SUCCESS: Vector dimension={len(response.data[0].embedding)}')
    results.append(('OpenAI Embedding', 'SUCCESS', None))
except Exception as e:
    error_str = str(e)
    if 'credit' in error_str.lower() or 'billing' in error_str.lower() or 'quota' in error_str.lower():
        status = 'CREDIT_ISSUE'
    elif 'invalid' in error_str.lower() and 'key' in error_str.lower():
        status = 'INVALID_KEY'
    else:
        status = 'ERROR'
    print(f'  [FAIL] {status}')
    results.append(('OpenAI Embedding', status, error_str[:300]))

# Summary
print('\n' + '='*60)
print('SUMMARY')
print('='*60)
success_count = len([r for r in results if r[1] == 'SUCCESS'])
total = len(results)
print(f'\nTotal: {total} APIs tested, {success_count} working, {total - success_count} failed')

print('\n--- Working APIs ---')
for name, status, error in results:
    if status == 'SUCCESS':
        print(f'  [OK] {name}')

if not any(r[1] == 'SUCCESS' for r in results):
    print('  (none)')

print('\n--- Failed APIs ---')
for name, status, error in results:
    if status != 'SUCCESS':
        print(f'  [FAIL] {name}: {status}')
        if error:
            first_line = error.split('\n')[0][:120]
            print(f'         -> {first_line}')

print('\n' + '='*60)
print('RECOMMENDATIONS')
print('='*60)
for name, status, error in results:
    if status == 'INVALID_KEY':
        print(f'  - {name}: Set valid API key in .env file')
    elif status == 'CREDIT_ISSUE':
        print(f'  - {name}: Top up credits or check billing')
    elif status == 'MODEL_NOT_FOUND':
        print(f'  - {name}: Model not available, check model name')
    elif status == 'PACKAGE_NOT_INSTALLED':
        print(f'  - {name}: Run "pip install google-generativeai"')
    elif status == 'ERROR':
        print(f'  - {name}: Check error details above')

if success_count == total:
    print('  All APIs are working correctly!')
