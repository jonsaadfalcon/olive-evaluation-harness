
import re
from transformers import AutoTokenizer
import torch

import json
import torch
from transformers.utils import WEIGHTS_NAME, CONFIG_NAME
from transformers.utils.hub import cached_file

from lm_eval.api.registry import register_model
from lm_eval.models.huggingface import HFLM

from __future__ import annotations
from typing import List, Optional, Union
from pathlib import Path

import torch
from torch import nn
import os

import hydra
from omegaconf import OmegaConf, DictConfig
from pytorch_lightning import (
    Callback,
    LightningDataModule,
    LightningModule,
    Trainer,
    seed_everything,
)

import sys
import torch 

from train.config import Config

@register_model("moe_lm")
class MoELMWrapper(HFLM):
    def __init__(
            self, 
            run_id: str,
            config: any=None,
            device: str = "cuda",
            **kwargs
        ) -> None:

        if config is not None and hasattr(config, "code_path"):
            sys.path.append(config.code_path)

        # 1: Get configuration from wandb
        config: Config = Config.from_wandb(run_id)
        path = config.checkpointer.dirpath

        # 2: Instantiate model
        model = config.model.instantiate()

        # 3: Load model
        # load the state dict, but remove the "model." prefix and all other keys from the
        # the PyTorch Lightning module that are not in the actual model
        ckpt = torch.load(os.path.join(path, "last.ckpt"), map_location=torch.device(device))

        print("Checkpoint Path: " + path)

        model.load_state_dict({
            k[len("model."):]: v 
            for k, v in ckpt["state_dict"].items() 
            if k.startswith("model.")
        })
        model.to(device=device)

        # 4: load tokenizer if it's available
        if hasattr(config.datamodule, "tokenizer_name"):
            from transformers import AutoTokenizer
            tokenizer = AutoTokenizer.from_pretrained(config.datamodule.tokenizer_name)
        else:
            tokenizer = None
        
        super().__init__(
            pretrained=model,
            # set appropriate defaults for tokenizer, max length, etc
            #backend=kwargs.get("backend", "causal"),
            max_length=kwargs.get("max_length", 2048),
            tokenizer=tokenizer,
            device=device,
            **kwargs,
        )