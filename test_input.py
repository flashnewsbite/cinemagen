import sys

print("Testing input...")
try:
    val = input("Enter something: ")
    print(f"Received: '{val}'")
except EOFError:
    print("EOFError caught")
except Exception as e:
    print(f"Error: {e}")
