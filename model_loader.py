# model_loader.py
# model_loader.py
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, PretrainedConfig
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_gemma_config():
    """Create Gemma model configuration"""
    config = {
        "model_type": "gemma",
        "architectures": ["GemmaForCausalLM"],
        "attention_bias": False,
        "attention_dropout": 0,
        "hidden_act": "gelu",
        "hidden_dropout": 0,
        "hidden_size": 3072,
        "intermediate_size": 24576,
        "max_position_embeddings": 8192,
        "num_attention_heads": 16,
        "num_hidden_layers": 28,
        "num_key_value_heads": 16,
        "rms_norm_eps": 1e-06,
        "rope_theta": 10000,
        "tie_word_embeddings": True,
        "torch_dtype": "float16",
        "transformers_version": "4.36.2",
        "use_cache": True,
        "vocab_size": 256000
    }
    return PretrainedConfig.from_dict(config)

def initialize_model():
    try:
        # Set model path
        MODEL_PATH = r"C:\Users\Ansh\OneDrive\Desktop\ml farmet\model\final_multilingual_model"
        os.makedirs(MODEL_PATH, exist_ok=True)
        
        logger.info(f"Initializing Gemma model from: {MODEL_PATH}")
        
        # Create and save config
        config = create_gemma_config()
        config.save_pretrained(MODEL_PATH)
        logger.info("Created Gemma configuration")
        
        # Set device and memory optimization
        device_map = "auto"
        max_memory = {0: "8GiB"}  # Limit GPU memory usage
        
        if torch.cuda.is_available():
            dtype = torch.float16
            logger.info(f"Using GPU with dtype: {dtype}")
        else:
            dtype = torch.float32
            device_map = "cpu"
            logger.info("Using CPU")
        
        # Load model with memory optimization
        logger.info("Loading model...")
        model = AutoModelForCausalLM.from_pretrained(
            "google/gemma-2b",  # Using smaller 2B model
            device_map=device_map,
            max_memory=max_memory,
            torch_dtype=dtype,
            trust_remote_code=True,
            low_cpu_mem_usage=True,
            offload_folder="offload",  # Temporary directory for offloading
            offload_state_dict=True    # Enable state dict offloading
        )
        
        # Load tokenizer
        logger.info("Loading tokenizer...")
        tokenizer = AutoTokenizer.from_pretrained(
            "google/gemma-2b",
            trust_remote_code=True
        )
        
        logger.info("✓ Model and tokenizer loaded successfully!")
        return model, tokenizer
        
    except Exception as e:
        logger.error(f"Error initializing model: {e}")
        raise

if __name__ == "__main__":
    # Initialize and test model
    model, tokenizer = initialize_model()
    logger.info("Model initialized successfully!")