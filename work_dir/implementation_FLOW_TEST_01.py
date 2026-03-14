```python
# /app/src/rae_core/rae_core/utils/math_metrics.py

def calculate_ttr(text: str) -> float:
    """
    Calculate the Type-Token Ratio (TTR) of a given text.
    
    The TTR is calculated as the ratio of unique tokens to the total number of tokens in the text.
    
    Args:
        text (str): The input text from which to calculate the TTR.
        
    Returns:
        float: The Type-Token Ratio, representing the ratio of unique tokens to total tokens.
    """
    tokens = text.split()  # Split the text into tokens
    total_tokens = len(tokens)  # Count the total number of tokens
    unique_tokens = len(set(tokens))  # Count the number of unique tokens
    
    if total_tokens == 0:
        return 0.0  # Avoid division by zero
    
    ttr = unique_tokens / total_tokens
    return ttr
```