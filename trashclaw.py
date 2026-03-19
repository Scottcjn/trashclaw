import time
import sys

def llm_request(messages, stream=True, **kwargs):
    start_time = time.time()
    token_count = 0
    
    # Fallback to dummy implementation if no real client is provided
    client = kwargs.get('client')
    model = kwargs.get('model', 'gpt-3.5-turbo')
    
    if client:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            stream=stream
        )
    else:
        # Dummy response for testing/placeholder
        response = [{'choices': [{'delta': {'content': 'mock '}}]} for _ in range(5)]
        
    if stream:
        for chunk in response:
            # Handle standard OpenAI chunk format
            if hasattr(chunk, 'choices') and chunk.choices:
                content = chunk.choices[0].delta.content or ''
            elif isinstance(chunk, dict) and 'choices' in chunk:
                content = chunk['choices'][0]['delta'].get('content', '')
            else:
                content = str(chunk)
                
            if content:
                token_count += 1
                yield content
                
        time_elapsed = time.time() - start_time
        tokens_per_second = token_count / time_elapsed if time_elapsed > 0 else 0
        print(f"\n[Stats: {token_count} total tokens | {time_elapsed:.2f}s time elapsed | {tokens_per_second:.2f} tokens per second]")
    else:
        return response
