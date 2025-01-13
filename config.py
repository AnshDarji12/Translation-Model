# create_config.py
import json
import os

def create_model_config():
    model_path = r"C:\Users\Ansh\OneDrive\Desktop\ml farmet\model\final_multilingual_model"
    os.makedirs(model_path, exist_ok=True)
    
    # Create config similar to your Kaggle model
    config = {
        "model_type": "gemma2",  # or "gemma" depending on your base model
        "architectures": ["LlamaForCausalLM"],
        "hidden_size": 4096,
        "intermediate_size": 11008,
        "num_attention_heads": 32,
        "num_hidden_layers": 32,
        "num_key_value_heads": 32,
        "vocab_size": 32000,
        "max_position_embeddings": 2048,
        "torch_dtype": "float16",
        "transformers_version": "4.36.2"
    }
    
    # Save config
    config_path = os.path.join(model_path, "config.json")
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2)
    print(f"Created config.json at {config_path}")

if __name__ == "__main__":
    create_model_config()